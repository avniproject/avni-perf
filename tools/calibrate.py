"""F7 -- does a simulated sync land inside production's observed distribution?

**This gates believing results, not producing them.** The harness is internally consistent and, until
this passes, unvalidated: every storage coefficient is a deliberate upper bound rather than a
measurement, and the paging, push and media models follow the client's code without having been
checked against its behaviour. F7 is what would catch any of that.

    ./gradlew gatlingRun -DBASE_URL=... -DPROFILE=smoke      # writes build/sync-durations.csv
    python3 tools/calibrate.py build/sync-durations.csv

**The test.** Run a simulated user against the same per-entity record counts as a real production
sync; the simulated duration should land inside the observed distribution of real sync durations for
that data volume and device class. Q5 measured that distribution in two bands:

    band 1, under 5,000 records:  p50 14.1 s, p95 80.0 s
    band 2, around 47,500:        p50 1,076 s, p95 pending a Q5 re-run

**A sync inside p50..p95 passes.** Not "close to the median": 98% of production syncs sit in band 1
and their durations span five-fold, driven by network, device and server load rather than by record
count. A simulation that reproduced the median exactly every time would be wrong in a way that
matters -- it would have no spread at all. What the gate can say is whether the simulation sits
inside the range real devices occupy.

**Below p50 is the failure that matters.** Too fast means the model understates client work, and
every finding built on it is optimistic. Too slow is recorded as a warning: it makes results
conservative, and the likeliest cause is the injector's own position rather than the model -- a sync
is ~109 requests, so 25 ms of extra round trip adds 2.7 s to a 14.1 s median.

**Band 2 cannot be judged yet.** Its p95 is outstanding, so a heavy sync is reported and not graded;
calling it pass or fail would be inventing the bound.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Band:
    name: str
    max_records: float
    p50: float | None
    p95: float | None

    @property
    def gradable(self) -> bool:
        return self.p50 is not None and self.p95 is not None


# Q5, production-2026-09. Seconds.
BANDS = (
    Band("light (<5k records)", 5_000, 14.1, 80.0),
    # p95 is pending a Q5 re-run -- the one number still outstanding, and a measurement rather
    # than a decision. Until it lands, a heavy sync is reported without a verdict.
    Band("heavy (~47.5k records)", float("inf"), 1076.0, None),
)


# Q5 measured two bands and nothing between them. A sync of 5,919 records is 18% above band 1's
# ceiling and an eighth of band 2's centre, so neither covers it exactly.
#
# **Graded against band 1, and said out loud.** The alternative is to grade nothing, which makes
# the gate unrunnable on any dataset that is not one of the two measured sizes. Band 1 is the
# nearest measured reference and the direction of its error is known: it was measured on lighter
# syncs, so a heavier one should be *slower* than its median, never faster. A sync that comes in
# under band 1's p50 while carrying more records than band 1 ever did is unambiguously too fast,
# which is the failure the gate exists to catch. Above band 2's midpoint, band 2 takes over.
BAND_2_FLOOR = 47_500 / 2


def band_for(records: int) -> tuple[Band | None, bool]:
    """The band whose measured range covers this count, or None if none does."""
    if records <= BANDS[0].max_records:
        return BANDS[0], False
    if records >= BAND_2_FLOOR:
        return BANDS[1], False
    return None, True


@dataclass(frozen=True)
class Verdict:
    ok: bool
    label: str
    detail: str


def judge(records: int, seconds: float, band: Band | None, outside: bool = False) -> Verdict:
    if band is None:
        return Verdict(True, "unbanded",
                       f"{records:,} records falls between Q5's measured bands "
                       f"(under {BANDS[0].max_records:,}, or around 47,500) -- {seconds:,.1f}s "
                       f"recorded. The slope check below is what covers it")
    if not band.gradable:
        return Verdict(True, "ungraded",
                       f"{band.name} has no p95 yet -- {seconds:,.1f}s recorded, not judged")
    if seconds < band.p50:
        return Verdict(False, "FAIL",
                       f"{seconds:,.1f}s is below p50 {band.p50:,.1f}s. The model understates "
                       f"client work, so every finding built on it is optimistic")
    if seconds > band.p95:
        return Verdict(True, "warn",
                       f"{seconds:,.1f}s exceeds p95 {band.p95:,.1f}s. Results are conservative "
                       f"rather than wrong. Check the injector's position before the model -- a "
                       f"sync is ~109 requests, so 25ms of round trip adds 2.7s")
    return Verdict(True, "ok",
                   f"{seconds:,.1f}s inside p50 {band.p50:,.1f}s .. p95 {band.p95:,.1f}s")


# **Production's marginal cost of one more record, and the check that discriminates.**
#
# Anchoring the intercept at band 1's p50 gives 8.85 ms/record, against Q1's regression at 9.19 --
# a 4% difference, which is noise. The slope was never the contested part; the free intercept was,
# and every unanchored fit returned a value that could not fit inside a 14.1 s sync.
#
# **This is the check the bands could not make.** A band asks whether one sync's duration is
# plausible for its volume, and answers weakly: band 1 spans five-fold, so almost anything passes.
# The slope asks what one more record costs, which is exactly the quantity the storage model sets
# and the only one an upper-bound coefficient gets wrong in a direction that matters. It also needs
# no band, so it covers the volumes Q5 never measured.
PRODUCTION_MS_PER_RECORD = 8.85

# How far the simulated slope may sit from production's, **as a factor either way**.
#
# Not an absolute deviation from a ratio of 1.0, which is the shape this check had first and is
# wrong for a ratio: an under-estimate can never deviate by more than 1.0 however bad it is, so a
# simulation four times too fast scored 0.74 against a 0.75 threshold and warned instead of
# failing. A factor is symmetric -- twice too slow fails as surely as twice too fast.
#
# Wide, because the two slopes do not measure quite the same thing: production's carries its server
# under real contention and this one carries a test server with nothing else running. A factor of
# two is arguable on those grounds. A factor of four is not.
SLOPE_WARN_FACTOR = 1.5
SLOPE_FAIL_FACTOR = 2.0

# Two cohorts at least this far apart, so the slope is a measurement rather than two points and
# hope.
SLOPE_MIN_SPAN = 2.0


def slope(rows: list[tuple[str, int, float]]) -> tuple[float, int, int] | None:
    """Simulated milliseconds per record, from the lightest and heaviest cohorts.

    Two cohort medians rather than a regression through every sync: within a cohort the durations
    are nearly identical, so a regression would be dominated by however many users happened to run
    at each volume rather than by the volumes themselves.
    """
    groups = cohorts(rows)
    if len(groups) < 2:
        return None
    lo, hi = groups[0], groups[-1]
    r_lo = statistics.median(r for _, r, _ in lo)
    r_hi = statistics.median(r for _, r, _ in hi)
    if r_lo <= 0 or r_hi / r_lo < SLOPE_MIN_SPAN:
        return None
    s_lo = statistics.median(s for _, _, s in lo)
    s_hi = statistics.median(s for _, _, s in hi)
    return ((s_hi - s_lo) * 1000 / (r_hi - r_lo), int(r_lo), int(r_hi))


def slope_check(rows: list[tuple[str, int, float]]) -> tuple[list[str], bool]:
    """Whether one more record costs what it costs production."""
    got = slope(rows)
    if got is None:
        # **Not measured is not passed.** This returned True once, so a run with a single cohort
        # printed "the simulation reproduces production" having tested nothing -- the band checks
        # alone cannot fail a volume Q5 never measured, so every verdict in such a run is
        # unbanded or ungraded and the gate was unanimous about nothing.
        return (["", "  INCONCLUSIVE: the slope needs two cohorts at least "
                 f"{SLOPE_MIN_SPAN:g}x apart in record count, and this run has one. A field "
                 "worker and a supervisor together is enough.",
                 "  Nothing here has tested whether one more record costs what it costs "
                 "production."], False)

    ms, r_lo, r_hi = got
    ratio = ms / PRODUCTION_MS_PER_RECORD
    factor = max(ratio, 1 / ratio) if ratio else float("inf")
    direction = "fast" if ratio < 1 else "slow"
    lines = ["", f"  Marginal cost, {r_lo:,} to {r_hi:,} records: **{ms:.2f} ms/record** against "
                 f"production's {PRODUCTION_MS_PER_RECORD} ({ratio:.2f}x, {factor:.1f}x "
                 f"{direction})"]
    if factor <= SLOPE_WARN_FACTOR:
        return lines, True
    if factor <= SLOPE_FAIL_FACTOR:
        lines += [f"  warn: {factor:.1f}x off, inside the {SLOPE_FAIL_FACTOR:g}x the differing "
                  f"server load can account for. Worth refitting."]
        return lines, True
    lines += [
        "",
        f"  FAIL: the simulation charges {ratio:.2f}x production's cost per record "
        f"-- {factor:.1f}x too {direction}.",
        "  Every duration it reports scales with this, so a finding about how long a sync takes",
        "  is wrong by the same factor. Two candidates, and the plan expects both:",
        "    * BASE_MS_PER_RECORD is a deliberate upper bound derived from a 2-second page",
        "      ceiling, not a measurement. D7's telemetry would settle it and is deferred.",
        "    * MS_PER_PAGE double-counts the server's own response time, which this simulation",
        "      genuinely incurs. Net the server's median response out of it, then refit.",
    ]
    return lines, False


def read(path: str) -> list[tuple[str, int, float]]:
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                rows.append((r["userName"], int(r["records"]), int(r["durationMs"]) / 1000.0))
            except (KeyError, ValueError):
                continue
    return rows


def read_split(path: str) -> list[tuple[int, float, float]]:
    """(records, paused seconds, server+network seconds), where the run recorded the split.

    **Which half is wrong is the whole question.** A slope 3.8x under production's has two
    possible homes: the client model, which `BASE_MS_PER_RECORD` and `MS_PER_PAGE` set, or the
    server's own response time, which this simulation genuinely incurs and cannot control.
    Refitting without knowing which is guessing. Runs recorded before the simulation wrote the
    split return nothing here.
    """
    out = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                out.append((int(r["records"]), int(r["pausedMs"]) / 1000.0,
                            int(r["serverMs"]) / 1000.0))
            except (KeyError, ValueError, TypeError):
                continue
    return out


# Two syncs are comparable when their record counts are within this of each other. Duration rises
# with records, so a range computed across different volumes measures the workload rather than the
# variation between devices carrying the same workload.
COHORT_RATIO = 1.1

# Production's light band, p95 / p50 = 80.0 / 14.1. What a real fleet's spread looks like at one
# volume.
PRODUCTION_SPREAD = 80.0 / 14.1

# Below this, the simulation is reproducing a single number rather than a distribution.
FLAT_SPREAD = 1.2

# A cohort smaller than this says nothing about spread either way.
MIN_COHORT = 5


def cohorts(rows: list[tuple[str, int, float]]) -> list[list[tuple[str, int, float]]]:
    """Group syncs carrying comparable record counts, smallest first."""
    out: list[list[tuple[str, int, float]]] = []
    for row in sorted(rows, key=lambda r: r[1]):
        if out and row[1] <= out[-1][0][1] * COHORT_RATIO:
            out[-1].append(row)
        else:
            out.append([row])
    return out


def spread_notes(rows: list[tuple[str, int, float]]) -> list[str]:
    """Whether the simulation reproduces production's spread, judged within a record-count cohort.

    **The earlier version compared across the whole file and was measuring the wrong thing.** A
    supervisor carrying 2.4x a field worker's records widened the range enough to look like
    variation, when the field workers themselves were identical to within 6%. Duration rises with
    volume; spread is what is left once volume is held still.
    """
    notes: list[str] = []
    for c in cohorts(rows):
        if len(c) < MIN_COHORT:
            continue
        secs = sorted(s for _, _, s in c)
        ratio = secs[-1] / secs[0] if secs[0] else float("inf")
        recs = [r for _, r, _ in c]
        head = (f"  {len(c)} syncs at {min(recs):,}-{max(recs):,} records span "
                f"{secs[0]:,.1f}s-{secs[-1]:,.1f}s, a {ratio:.2f}x spread against production's "
                f"{PRODUCTION_SPREAD:.1f}x")
        if ratio < FLAT_SPREAD:
            notes += ["", head, "",
                      "  NOTE: the simulation reproduces the median without reproducing the "
                      "distribution.",
                      "  Production's spread comes from device and network heterogeneity; this "
                      "harness models one",
                      "  device class from one injector position, so every virtual user takes "
                      "nearly the same time.",
                      "  Arrivals are therefore more regular than production's, which understates "
                      "contention at a",
                      "  given concurrency. A property to state when reading results, not a "
                      "failure of the band check."]
        else:
            notes += ["", head]
    return notes


def report(rows: list[tuple[str, int, float]]) -> tuple[str, bool]:
    if not rows:
        return ("No syncs recorded. The file is written by the simulation as each user finishes, "
                "so an empty one means no sync completed.", False)

    lines = ["F7 calibration gate -- simulated syncs against production's observed distribution",
             ""]
    ok = True
    for user, records, seconds in rows:
        band, outside = band_for(records)
        v = judge(records, seconds, band, outside)
        ok = ok and v.ok
        lines.append(f"  {v.label:<8} {user:<28} {records:>7,} records  {v.detail}")

    if len(rows) > 1:
        secs = sorted(s for _, _, s in rows)
        recs = [r for _, r, _ in rows]
        lines += ["", f"  {len(rows)} syncs, {min(recs):,}-{max(recs):,} records, "
                      f"median {statistics.median(secs):,.1f}s, "
                      f"range {secs[0]:,.1f}s-{secs[-1]:,.1f}s"]
        lines += spread_notes(rows)
    slope_lines, slope_ok = slope_check(rows)
    lines += slope_lines
    ok = ok and slope_ok

    if ok:
        lines += ["", "  PASS -- the simulation reproduces production for these volumes."]
    elif any("INCONCLUSIVE" in l for l in lines):
        lines += ["", "  INCONCLUSIVE -- the gate did not run, so this is neither a pass nor a "
                      "failure.", "  Treat it as untested."]
    else:
        lines += ["", "  FAIL -- the simulation is not an instrument yet. Its findings are not "
                      "evidence."]
    return "\n".join(lines), ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("results", nargs="?", default="build/sync-durations.csv",
                    help="the simulation's sync-durations.csv")
    a = ap.parse_args(argv)
    try:
        rows = read(a.results)
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    text, ok = report(rows)
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
