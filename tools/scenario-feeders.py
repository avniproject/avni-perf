"""Split the generated user file into one feeder per test case.

    python3 tools/scenario-feeders.py src/gatling/resources/sync-users.csv
    python3 tools/scenario-feeders.py /tmp/pilot-day-180-span20/sync-users.csv --variant span20

**Why the generated file is not itself a case's feeder.** `generate.py` writes every user of every
tenant in the deployment -- for `states-day-180` that is 1,082 across two organisations. Cases 2, 3
and 4 are each *one state tenant*, and case 3 is its supervisors alone. Pointing a run at the whole
file drives a case that is not in the plan: the run completes, the report looks ordinary, and the
number belongs to nothing. `SYNC_USERS` names the slice per run; this writes the slices.

**The rules are the scenario table, in code.** See docs/test-scenarios.md:

    case 1   a bootstrap cohort in an organisation with no field data -- not sliced from here,
             see bootstrap_user.py --count
    case 2   one state tenant, field workers           (the common case)
    case 3   one state tenant, supervisors alone       (driven above its natural rate)
    case 4   one state tenant, both                    (the realistic case)
    case 8   case 4's users against other growth points
    case 10  case 4's users, sustained
    case 5,  every tenant -- needs the ten-tenant deployment. Written only when the input has
    9, 11    ten, because a two-tenant file under that name is the same trap one layer down.

**--variant exists because the supervisor span is a second dataset, not a flag.** Block A runs
cases 3 to 5 on `pilot-day-180` (span 8.4) and Block A' repeats them on `pilot-day-180-span20`.
Both are ten-tenant pilots, so both split to the same four names -- and the slices differ: case 3
is 60 users at span 8.4 and 25 at span 20. A run that picked up the wrong one would complete and
report 25 users as the measured point. `--variant span20` writes `case3-users-span20.csv` instead.

**Forgetting it is the case that actually bites**, so it is not only a flag. Writing a slice over
an existing file whose contents differ is refused; `--force` is there for when that is meant.
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from collections import OrderedDict
from pathlib import Path

# The csv module's own default. Named because the overwrite check renders a slice and compares it
# with the file on disk, and a mismatched line terminator would make every comparison differ.
LINE_TERMINATOR = "\r\n"

VARIANT = re.compile(r"[a-z0-9][a-z0-9-]*\Z")


def interleave(rows: list[dict]) -> list[dict]:
    """Order rows so that *any prefix* holds each tenant and role in its full proportion.

    **A run consumes a prefix, not the file.** `circular()` walks in order so no user is skipped
    and none runs twice before the others -- but `generate.py` emits tenant by tenant and role by
    role, so the file arrives in blocks. When a case performs fewer syncs than the feeder has
    rows, the roles and tenants it reaches become a function of file order.

    That is not hypothetical. Case 4 ran 187 syncs against 501 field workers followed by 60
    supervisors and never reached row 502, so "one state tenant, both" measured field workers and
    returned case 2's numbers to three significant figures -- 60.8 s, 10,838 records against
    10,831, serverMs 6% in both. Case 5 is worse: 281 syncs against a file that opens with 561
    rows of one tenant would have reached one of ten tenants and no supervisors at all, and case 5
    is the separate-hosting baseline cases 6 and 7 are read against.

    **Each row is placed at its fractional position within its own stratum** -- the k-th of n
    becomes (k + 0.5) / n -- and the file is sorted on that. A stratum holding 10% of the
    population then appears at roughly every tenth row, so a prefix of any length carries it at
    10%. Ties resolve on the stratum key, so the order is deterministic: the same subset syncs on
    every run, which is what makes the 5 -> 6 -> 7 deltas comparisons of co-tenant presence rather
    than of who happened to be sampled.

    Shuffling would also give a representative prefix, in expectation, and was rejected for that
    reason: it is representative on average across runs, where a delta needs the same cohort in
    both halves of the comparison.
    """
    strata: "OrderedDict[tuple, list[dict]]" = OrderedDict()
    for r in rows:
        strata.setdefault((r["organisationUUID"], r["role"]), []).append(r)
    placed = []
    for key, members in strata.items():
        n = len(members)
        for k, row in enumerate(members):
            placed.append(((k + 0.5) / n, key, row))
    placed.sort(key=lambda t: (t[0], t[1]))
    return [row for _, _, row in placed]


def slices(rows: list[dict], variant: str | None = None) -> "OrderedDict[str, list[dict]]":
    suffix = f"-{variant}" if variant else ""
    orgs = list(OrderedDict.fromkeys(r["organisationUUID"] for r in rows))
    first = orgs[0]
    one_tenant = [r for r in rows if r["organisationUUID"] == first]
    out: "OrderedDict[str, list[dict]]" = OrderedDict()
    out[f"case2-users{suffix}.csv"] = [r for r in one_tenant if r["role"] == "field_worker"]
    out[f"case3-users{suffix}.csv"] = [r for r in one_tenant if r["role"] == "supervisor"]
    out[f"case4-users{suffix}.csv"] = one_tenant
    if len(orgs) >= 10:
        out[f"case5-users{suffix}.csv"] = rows
    return OrderedDict((name, interleave(subset)) for name, subset in out.items())


def render(fields: list[str], subset: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator=LINE_TERMINATOR)
    w.writeheader()
    w.writerows(subset)
    return buf.getvalue()


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source", type=Path, help="a generated sync-users.csv")
    p.add_argument("--variant", metavar="LABEL",
                   help="suffix the slices, e.g. --variant span20 writes case3-users-span20.csv")
    p.add_argument("--force", action="store_true",
                   help="overwrite a differing slice instead of refusing")
    args = p.parse_args(argv)

    if args.variant is not None and not VARIANT.match(args.variant):
        print(f"error: --variant {args.variant!r} is not a file-name fragment; use lower-case "
              f"letters, digits and hyphens", file=sys.stderr)
        return 2

    src = args.source
    with src.open() as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames or []
        rows = list(reader)
    for required in ("organisationUUID", "role"):
        if required not in fields:
            print(f"error: {src} has no {required} column, so it cannot be split by case",
                  file=sys.stderr)
            return 2
    if any(r.get("password|token") for r in rows):
        print(f"error: {src} carries credentials; these files are committed, so refusing to split",
              file=sys.stderr)
        return 2

    orgs = list(OrderedDict.fromkeys(r["organisationUUID"] for r in rows))
    print(f"{src}: {len(rows):,} users across {len(orgs)} tenant(s)"
          + (f", variant {args.variant}" if args.variant else ""))

    # Rendered and checked before anything is written, so a refusal does not leave half the
    # slices replaced and half not.
    planned = [(src.parent / name, render(fields, subset), len(subset))
               for name, subset in slices(rows, args.variant).items()]
    if not args.force:
        clashes = [(path, text) for path, text, _ in planned
                   if path.exists() and path.open(newline="").read() != text]
        if clashes:
            print(f"\nerror: {len(clashes)} slice(s) already exist here with different contents, "
                  f"and nothing distinguishes them by name:", file=sys.stderr)
            for path, text in clashes:
                was = sum(1 for _ in path.open(newline="")) - 1
                now = text.count(LINE_TERMINATOR) - 1
                print(f"  {path.name:<28} {was:>6,} users on disk, {now:,} from this input",
                      file=sys.stderr)
            print("\n  Two datasets split to the same four names -- the supervisor spans do, and\n"
                  "  so does any pair of ten-tenant pilots. A run pointed at the survivor drives\n"
                  "  the wrong cohort and reports it as the right one.\n"
                  "\n  Pass --variant LABEL to keep both, or --force if replacing is meant.",
                  file=sys.stderr)
            return 2

    for path, text, count in planned:
        path.open("w", newline="").write(text)
        print(f"  {path.name:<28} {count:>6,} users")
    if len(orgs) < 10:
        print(f"\n  cases 5, 9 and 11 need the ten-tenant deployment; this input has {len(orgs)}, "
              f"so no case5-users{'-' + args.variant if args.variant else ''}.csv was written.")
    print("\n  run a case with -DSYNC_USERS=<file>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
