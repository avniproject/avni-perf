"""H5 -- decide whether a generated dataset is good enough to measure against.

Section H6 rules out an anonymised production clone, so **the generated dataset is the only
dataset**. Nothing else will catch a generator that produces plausible row counts and unrealistic
cardinality, which makes this a gate rather than a nicety: run it before a dataset is used, and
again whenever the generator changes.

Two checks. The structural one is a procedure -- point the simulation at the dataset and confirm a
sync completes -- and lives in the README. This module is the statistical one.

**The checks are ordered by how hard they are to fake.** Row counts the generator sets directly, so
matching them proves only that it did what it was told. Observation key counts it targets through a
distribution, so matching them is weak evidence. **Index bytes per row it cannot target at all** --
that figure falls out of how many distinct keys each row actually carries, so it is the one number
that reflects whether the data is shaped like production rather than merely sized like it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from profile import Profile


class Verdict(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    WAIVED = "waived"


@dataclass(frozen=True)
class Check:
    name: str
    table: str
    verdict: Verdict
    observed: float | None
    expected: float | None
    tolerance: float
    detail: str

    @property
    def ratio(self) -> float | None:
        if self.observed is None or not self.expected:
            return None
        return self.observed / self.expected


@dataclass
class Report:
    profile_name: str
    checks: list[Check] = field(default_factory=list)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if c.verdict is Verdict.FAIL]

    @property
    def waived(self) -> list[Check]:
        return [c for c in self.checks if c.verdict is Verdict.WAIVED]

    @property
    def warned(self) -> list[Check]:
        return [c for c in self.checks if c.verdict is Verdict.WARN]

    @property
    def ok(self) -> bool:
        return not self.failed

    def render(self) -> str:
        width = max((len(c.name) for c in self.checks), default=10)
        lines = [f"H5 statistical gate against profile {self.profile_name}", ""]
        for c in self.checks:
            mark = {Verdict.PASS: "ok  ", Verdict.WARN: "warn", Verdict.FAIL: "FAIL",
                    Verdict.WAIVED: "wvd "}[c.verdict]
            ratio = f"{c.ratio:.2f}x" if c.ratio is not None else "-"
            lines.append(f"  {mark} {c.name:<{width}} {c.table:<18} {ratio:>7}  {c.detail}")
        lines += ["", f"  {len(self.checks)} checks, {len(self.failed)} failed, "
                      f"{len(self.warned)} warned, {len(self.waived)} waived"]
        if not self.ok:
            lines += ["", "  A failure means the dataset is not usable for measurement. Fix the "
                          "generator, reload, re-run."]
        if self.waived:
            lines += ["", "  Waived checks are accepted deviations, not passes. They are recorded "
                          "in the verdict with", "  the value accepted, and stop being waived if "
                          "the dataset drifts away from it."]
        return "\n".join(lines)


def _band(name, table, observed, expected, *, tolerance, fail_beyond, detail):
    """Compare a ratio, warning inside `fail_beyond` and failing outside it."""
    if observed is None or expected in (None, 0):
        return Check(name, table, Verdict.WARN, observed, expected, tolerance,
                     f"{detail} -- not measured")
    r = observed / expected
    off = abs(r - 1.0)
    if off <= tolerance:
        v = Verdict.PASS
    elif off <= fail_beyond:
        v = Verdict.WARN
    else:
        v = Verdict.FAIL
    return Check(name, table, v, observed, expected, tolerance,
                 f"{detail} (observed {observed:,.0f} against {expected:,.0f})")


# How far a waived figure may move before the waiver stops covering it. A waiver records a
# deviation someone looked at and accepted; it is not an instruction to ignore the check forever.
WAIVER_DRIFT = 0.25


def apply_waivers(report: Report, waivers: list[dict]) -> Report:
    """Turn accepted failures into `waived`, and leave everything else alone.

    **Why this exists rather than deleting the checks.** A gate that always reports the same four
    failures is a gate nobody reads, and the fifth failure — the real one — arrives invisible.
    Waiving keeps the check running and the number in front of you.

    **A waiver names the value it accepted.** If the dataset drifts more than `WAIVER_DRIFT` from
    it, the waiver no longer applies and the check fails again with the reason why. That is the
    difference between accepting a known shape and switching a check off: the first survives the
    thing changing underneath it, the second does not.
    """
    by_key = {(w["check"], w["table"]): w for w in waivers}
    out = []
    for c in report.checks:
        w = by_key.get((c.name, c.table))
        if w is None or c.verdict is not Verdict.FAIL:
            out.append(c)
            continue
        accepted = w.get("observed")
        if accepted and c.observed is not None and accepted:
            drift = abs(c.observed / accepted - 1.0)
            if drift > WAIVER_DRIFT:
                out.append(Check(
                    c.name, c.table, Verdict.FAIL, c.observed, c.expected, c.tolerance,
                    f"{c.detail} -- WAIVER NO LONGER APPLIES: accepted at {accepted:,.0f}, "
                    f"now {c.observed:,.0f}, {drift:.0%} away. Re-read the reason: {w['reason']}"))
                continue
        out.append(Check(c.name, c.table, Verdict.WAIVED, c.observed, c.expected, c.tolerance,
                         w["reason"]))
    report.checks = out
    return report


def run(observed: dict, profile: Profile, *, expected_rows: dict | None = None) -> Report:
    """Compare a generated dataset's statistics against the profile.

    `observed` is the output of `validate.sql` against the generated database, keyed by table:

        {"individual": {"rows": 150000, "all_index_bytes": 160000000,
                        "gin_observation_bytes": 14000000, "obs_keys_p50": 7,
                        "obs_keys_p95": 29, "obs_mean_bytes": 742,
                        "distinct_concepts": 151}}

    `expected_rows` is what the generator was asked to produce, so the row check tests the loader
    rather than the shape.
    """
    report = Report(profile_name=profile.name)

    for table, stats in sorted(observed.items()):
        rows = stats.get("rows")

        if expected_rows and table in expected_rows:
            report.checks.append(_band(
                "row count", table, rows, expected_rows[table],
                tolerance=0.001, fail_beyond=0.01,
                detail="the loader wrote what the generator produced"))

        weight = profile.index_weight_for(table)
        if weight and rows:
            for key, expected, label, tol, fail in (
                ("gin_observation_bytes", weight.gin_observation_bytes,
                 "GIN bytes/row", 0.35, 0.60),
                ("all_index_bytes", weight.all_index_bytes, "index bytes/row", 0.35, 0.60),
            ):
                total = stats.get(key)
                per_row = (total / rows) if total is not None else None
                report.checks.append(_band(
                    label, table, per_row, expected, tolerance=tol, fail_beyond=fail,
                    detail=("observation cardinality" if key.startswith("gin")
                            else "index definitions match production's")))

        target = profile.for_form_type_by_table(table) if hasattr(
            profile, "for_form_type_by_table") else None
        if target:
            report.checks.append(_band(
                "obs keys p50", table, stats.get("obs_keys_p50"), target.key_count.p50,
                tolerance=0.20, fail_beyond=0.50, detail="fill rate, median"))
            report.checks.append(_band(
                "obs keys p95", table, stats.get("obs_keys_p95"), target.key_count.p95,
                tolerance=0.25, fail_beyond=0.60,
                detail="fill rate spread -- a constant key count fails here while the median passes"))
            if target.mean_bytes:
                report.checks.append(_band(
                    "obs mean bytes", table, stats.get("obs_mean_bytes"), target.mean_bytes,
                    tolerance=0.30, fail_beyond=0.60, detail="payload size"))

    return report


def main(argv: list[str]) -> int:
    """`python3 validate.py stats.json [--profile p.json] [--expected-rows rows.json]`

    `stats.json` is validate.sql's output, reshaped per table. Exit code 1 on any failure, so this
    can gate a run rather than being read and ignored.
    """
    import argparse
    import json
    from pathlib import Path

    import profile as profile_mod

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("stats", help="statistics from validate.sql, as JSON keyed by table")
    ap.add_argument("--profile", default=None, help="production reference to judge against")
    ap.add_argument("--expected-rows", default=None,
                    help="what the generator was asked to produce, as JSON keyed by table")
    ap.add_argument("--waivers", default=None,
                    help="deviations already looked at and accepted, as JSON: a list of "
                         "{check, table, reason, observed}. A waived check still runs and is "
                         "still recorded; it stops being waived if the dataset drifts away from "
                         "the value the waiver names")
    ap.add_argument("--recipe", default=None,
                    help="recipe name this dataset was built from, recorded in the verdict")
    ap.add_argument("--out", default=None,
                    help="write the verdict here, as the record that the dataset was blessed")
    args = ap.parse_args(argv)

    with open(args.stats) as fh:
        stats = json.load(fh)
    expected = None
    if args.expected_rows:
        with open(args.expected_rows) as fh:
            expected = json.load(fh)

    report = run(stats, profile_mod.load(args.profile), expected_rows=expected)
    if args.waivers:
        with open(args.waivers) as fh:
            report = apply_waivers(report, json.load(fh))
    print(report.render())

    if args.out:
        import recipe as recipe_mod
        Path(args.out).write_text(
            json.dumps(recipe_mod.verdict_document(args.recipe or "(unnamed)", report),
                       indent=2) + "\n")
        print(f"\n  verdict written to {args.out}")

    return 0 if report.ok else 1


if __name__ == "__main__":
    import sys as _sys
    raise SystemExit(main(_sys.argv[1:]))
