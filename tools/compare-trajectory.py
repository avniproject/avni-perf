#!/usr/bin/env python3
"""Two runs' Gatling console logs, side by side at matched elapsed minutes.

    ./tools/compare-trajectory.py <control gradle.log> <test gradle.log> [--rate]

Gatling prints a progress block every few seconds with "Ns elapsed", a per-scenario
"waiting / active / done" line and the Global request count. This takes the first block at
each 5-minute mark and prints, for the Customer scenario, done and active, plus total requests
and KO. --rate adds requests per minute over each 5-minute interval.

WHY THE CUSTOMER LINE IS NAMED, NOT THE FIRST ONE FOUND. A block carries one waiting line per
scenario, and a comparison that takes the first line it meets will compare the co-tenant
scenario of one run against the customer scenario of the other. It did, on 21 Oct 2026, and
the arrivals arithmetic (co-tenants at 792/h, customers at 1682/h) is what exposed it.

WHAT "ACTIVE" MEANS HERE. For a steady profile it is the number of syncs in flight. Flat means
the server is completing syncs as fast as they arrive; climbing without recovering is the queue
building, and is visible well before the first KO. The interceptor A/B (plan rows 21 and 22)
was decided by this column at +15 min, forty minutes before the control's failures peaked.

REQUESTS PER MINUTE IS NOT A CEILING UNLESS ACTIVE IS CLIMBING. When active is flat the server
is serving the offered load, and req/min says what was offered, not what it could do. When
active climbs, req/min is what it could do -- and it rises again as failures mount, because a
timed-out request completes fast and counts.
"""
import re, sys

MARK = 300

def parse(path, upto=7200):
    txt = open(path, errors="replace").read()
    out = {}
    for b in txt.split("=" * 80):
        m = re.search(r"(\d+)s elapsed", b)
        if not m:
            continue
        e = int(m[1]); k = e // MARK
        if k in out or e > upto:
            continue
        g = re.search(r"> Global\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)", b)
        sc = {}
        for name, w, a, d in re.findall(
                r"---- (Customer|Co-tenant) -+.*?\n.*?waiting:\s*([\d,]+)\s*/\s*active:\s*([\d,]+)\s*/\s*done:\s*([\d,]+)",
                b, re.S):
            sc[name] = (int(a.replace(",", "")), int(d.replace(",", "")))
        if g and "Customer" in sc:
            out[k] = (e, sc["Customer"], int(g[1].replace(",", "")), int(g[3].replace(",", "")))
    return out

def main(argv):
    rate = "--rate" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if len(paths) != 2:
        print(__doc__); return 2
    A, B = parse(paths[0]), parse(paths[1])
    hdr = f"{'':9s}{'cust done':>10s}{'active':>8s}{'requests':>10s}{'KO':>6s}"
    if rate:
        hdr += f"{'req/min':>9s}"
    print(hdr)
    for k in sorted(set(A) | set(B)):
        for lab, S in (("control", A), ("test", B)):
            r = S.get(k)
            if not r:
                continue
            line = f"+{r[0] // 60:2d} min {lab:8s}{r[1][1]:>7,}{r[1][0]:>8,}{r[2]:>10,}{r[3]:>6,}"
            if rate:
                p = S.get(k - 1)
                line += f"{(r[2] - p[2]) / ((r[0] - p[0]) / 60):>9,.0f}" if p else f"{'':>9s}"
            print(line)
        print()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
