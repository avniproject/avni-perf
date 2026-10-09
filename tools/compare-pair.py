#!/usr/bin/env python3
"""Compare two runs of the same scenario, paired by user.

    tools/compare-pair.py runA/sync-durations.csv runB/sync-durations.csv

WHY PAIRED RATHER THAN MEAN-VS-MEAN
  `realisticLoadedSince` derives each user's sync window from
  `(userName + "|" + entityName).hashCode()` -- AvniSyncSimulation.java:1665,
  "derived from the user and entity name rather than drawn at random, so a run
  reproduces". Both runs therefore hand the same user the same window, so under
  the null each user's record count is IDENTICAL, not merely close, and any
  non-zero paired difference is signal. Comparing means would throw that away
  and leave an effect of ~0.3% to be seen against between-user variance that is
  orders of magnitude larger.

  The one residual: loadedSince is *now* minus the hashed gap, so the second
  run's window slides forward by the inter-run interval. Negligible for gaps of
  days or months, material for the few drawn in hours -- those users lose an
  hour at the old end and gain the hour holding the first run's pushes. So a
  handful of non-zero diffs is expected even with no residue effect; the shape
  of the distribution is what to read, not the presence of any difference.

Thresholds are the ones pinned in docs/execution-plan.md before the runs.
"""
import csv, sys, statistics

PASS, AMBIG = 0.0010, 0.0040   # fraction, one-sided: residue can only add

def load(path):
    rows = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            u = r.get("userName", "").strip()
            if not u:
                continue
            try:
                rec = int(r["records"]); dur = int(r["durationMs"])
            except (KeyError, ValueError):
                continue
            rows.setdefault(u, (rec, dur))    # first sync per user; the feeder
    return rows                               # does not wrap at these counts

def main(a_path, b_path):
    A, B = load(a_path), load(b_path)
    common = sorted(set(A) & set(B))
    if not common:
        sys.exit("no users in common -- are these the same scenario and feeder?")

    diffs = [B[u][0] - A[u][0] for u in common]
    a_rec = [A[u][0] for u in common]
    nz = [d for d in diffs if d != 0]
    pos = [d for d in nz if d > 0]

    mean_a = statistics.mean(a_rec)
    mean_d = statistics.mean(diffs)
    frac = mean_d / mean_a if mean_a else 0.0

    print(f"run A         {a_path}   {len(A)} users")
    print(f"run B         {b_path}   {len(B)} users")
    print(f"paired        {len(common)}   (A-only {len(set(A)-set(B))}, B-only {len(set(B)-set(A))})")
    print()
    print(f"records/sync in A      mean {mean_a:,.1f}   median {statistics.median(a_rec):,.0f}")
    print(f"paired difference      mean {mean_d:+,.2f}   median {statistics.median(diffs):+,.0f}"
          f"   min {min(diffs):+,}   max {max(diffs):+,}")
    print(f"users differing        {len(nz)} of {len(common)} ({100*len(nz)/len(common):.1f}%)"
          f"   of which {len(pos)} pulled MORE in B")
    print(f"total extra records    {sum(diffs):+,}")
    print()
    print(f"mean shift             {100*frac:+.4f}%")
    print(f"  pinned bands         pass <= +0.10%   ambiguous to +0.40%   investigate above")
    if frac <= PASS:
        v = "PASS -- drift under a third of the ceiling, the block strategy holds"
    elif frac <= AMBIG:
        v = "AMBIGUOUS -- consistent with residue being re-pulled"
    else:
        v = "ABOVE THE CEILING -- the cause is not residue alone. Investigate"
    print(f"  verdict              {v}")
    print()
    print("A non-zero mean with almost every user at zero is the inter-run window slide,")
    print("not residue. Residue shows as many users each gaining a little.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
