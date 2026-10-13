"""Install a generated co-tenant dataset's user file as the co-tenant feeder.

    python3 tools/co-tenant-feeder.py /tmp/co-tenants-day-180

**The copy is trivial; the checks are the point.** Cases 7 and 13 draw co-tenant syncs weighted by
`CoTenantLoad`'s measured concentration -- rank 1 takes 16% of production's device sync, the top 16
take 84% -- and the weighting is resolved per row from `organisationUUID`. A feeder without that
column collapses every row into one organisation, every draw takes rank 1, and the run reproduces
the request *rate* with a uniform working set, which is the behaviour the concentration exists to
correct. The simulation refuses that outright now, but it refuses at run time, after a dataset is
loaded and an environment is held. This refuses at copy time.

`deployment.feeder_csv` writes the column, so the dataset's own `sync-users.csv` is the feeder.
Nothing transforms it -- unlike the case feeders, which are slices of one tenant and have to be
cut. Every co-tenant row is wanted.
"""
from __future__ import annotations

import csv
import shutil
import sys
from collections import Counter
from pathlib import Path

DEST = Path(__file__).resolve().parents[1] / "src/gatling/resources/co-tenant-users.csv"


def check(src: Path) -> list[str]:
    with src.open() as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames or []
        rows = list(reader)
    problems = []
    if "organisationUUID" not in fields:
        problems.append("no organisationUUID column -- the concentration cannot be resolved, and "
                        "every row would draw rank 1")
    if "userName" not in fields:
        problems.append("no userName column, which CoTenantLoad.key() reads as a row's identity")
    if any(r.get("password|token") for r in rows):
        problems.append("carries credentials in password|token; feeders are read by anyone with "
                        "the repository")
    orgs = Counter(r.get("organisationUUID") for r in rows)
    if len(orgs) < 2:
        problems.append(f"{len(rows)} rows across {len(orgs)} organisation(s) -- a single-tenant "
                        f"file makes the draw uniform, which is what this replaces")
    return problems, rows, orgs


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    root = Path(argv[0])
    src = root / "sync-users.csv" if root.is_dir() else root
    if not src.is_file():
        print(f"error: no sync-users.csv at {src}. Point this at the generated co-tenant dataset "
              f"directory.", file=sys.stderr)
        return 2

    problems, rows, orgs = check(src)
    if problems:
        print(f"error: {src} is not usable as a co-tenant feeder:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 2

    shutil.copyfile(src, DEST)
    top = orgs.most_common(3)
    print(f"{src} -> {DEST.relative_to(Path(__file__).resolve().parents[1])}")
    print(f"  {len(rows):,} users across {len(orgs):,} organisations")
    print(f"  largest three: " + ", ".join(f"{o} ({n})" for o, n in top))
    # Stated because the rank that matters is assigned from this file, not from the recipe:
    # CoTenantLoad.ranks() orders organisations by how many users each holds.
    print(f"  rank 1 will be {top[0][0]}, which takes 16.0% of the co-tenant draw")
    print(f"\n  Cases 7 and 13 read it as CO_TENANT_USERS. Commit it with the recipe's "
          f"organisation ids: the ranks above are assigned from this file, so a feeder "
          f"whose organisations do not match the recipe is worse than none.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
