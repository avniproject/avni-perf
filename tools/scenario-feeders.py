"""Split the generated user file into one feeder per test case.

    python3 tools/scenario-feeders.py src/gatling/resources/sync-users.csv

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
"""
from __future__ import annotations

import csv
import sys
from collections import OrderedDict
from pathlib import Path


def slices(rows: list[dict]) -> "OrderedDict[str, list[dict]]":
    orgs = list(OrderedDict.fromkeys(r["organisationUUID"] for r in rows))
    first = orgs[0]
    one_tenant = [r for r in rows if r["organisationUUID"] == first]
    out: "OrderedDict[str, list[dict]]" = OrderedDict()
    out["case2-users.csv"] = [r for r in one_tenant if r["role"] == "field_worker"]
    out["case3-users.csv"] = [r for r in one_tenant if r["role"] == "supervisor"]
    out["case4-users.csv"] = one_tenant
    if len(orgs) >= 10:
        out["case5-users.csv"] = rows
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    src = Path(argv[0])
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
    print(f"{src}: {len(rows):,} users across {len(orgs)} tenant(s)")
    for name, subset in slices(rows).items():
        path = src.parent / name
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(subset)
        print(f"  {name:<20} {len(subset):>6,} users")
    if len(orgs) < 10:
        print(f"\n  cases 5, 9 and 11 need the ten-tenant deployment; this input has {len(orgs)}, "
              f"so no case5-users.csv was written.")
    print("\n  run a case with -DSYNC_USERS=<file>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
