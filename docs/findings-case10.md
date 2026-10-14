# Case 10: twelve hours changed nothing, at every level that was checked

**9–10 October 2026.** `2026-10-09T14-21-29Z-case10-soak-cf77819`. Case 4's load sustained
overnight, 561 syncs and 50,098 requests, **zero failed**, p95 290 ms. The sequence row in
[`execution-plan.md`](execution-plan.md) recorded the verdict — *no measurable degradation*, a
trend of r=+0.23 across twelve hourly buckets, smaller than the hour-to-hour spread.

This records what that looked like underneath, from New Relic, **14 Oct 2026**. It needed no
environment; the run was already there.

## The busiest endpoint, hour by hour

`encounter (GET)`, hourly from 14:21 UTC:

| hour | requests | avg ms | p95 ms | db ms | db calls |
|---|---|---|---|---|---|
| 0 | 739 | 261.1 | 326.2 | 34.67 | 27.0 |
| 1 | 767 | 265.2 | 326.2 | 39.03 | 27.0 |
| 2 | 751 | 261.0 | 326.2 | 35.69 | 26.8 |
| 3 | 745 | 263.8 | 322.3 | 34.91 | 26.9 |
| 4 | 710 | 262.2 | 322.3 | 35.11 | 27.1 |
| 5 | 736 | 261.0 | 322.3 | 34.35 | 27.0 |
| 6 | 736 | 260.8 | 322.3 | 34.18 | 27.0 |
| 7 | 707 | 260.3 | 318.4 | 34.32 | 27.0 |
| 8 | 699 | 259.9 | 318.4 | 34.34 | 26.9 |

**Nothing drifts, and the direction is very slightly down.** Average duration moves 261.1 → 259.9
ms, p95 326.2 → 318.4, database time 34.67 → 34.34. Call count holds at 27.0 throughout. Every one
of those is inside the hour-to-hour spread, which is the same conclusion the sync-level trend
reached, now at the endpoint rather than in aggregate.

**The database is the part worth noting.** If overnight bloat or deferred autovacuum were costing
anything, it would appear as database time rising at a constant call count — which is exactly the
signature case 6 showed for co-tenant presence, +25.5% at 28.6 calls. Here there is no such
movement over nine hours. Whatever the soak accumulated, it did not reach the pages these queries
touch.

## The JVM did not drift either

G1 Old Gen, in two-hour buckets across the run:

```
197.5   200.7   197.8   199.2   202.3  MB
```

**+2.4% over nine hours**, and not monotonic. Concurrent GC was flat at zero. So no leak, no
promotion creep, no collector pressure building — which matters because case 9/12a found Old Gen
reaching 3,814 MB of 5,120 at saturation, and recorded that margin as *"the number to watch if
concurrency rises or `PAGE_SIZE` grows"*. A long run at case 4's load does not consume it.

## What this does not say

* **Nine hours of data, not twelve.** The run's own window was 548.7 minutes — about 9.1 hours —
  so "twelve-hour soak" names the intent rather than the run. The conclusion is unaffected; the
  duration quoted should not be.
* **One endpoint.** `encounter (GET)` is the busiest and carries most of the work, but the series
  above is not every endpoint.
* **Load was modest throughout.** Case 4's load is roughly 0.25 rps, far below the knee case 9
  located between 50 and 200 syncs/hour. This says a quiet server stays quiet for nine hours. It
  does not say a saturated one would.
* **No reset preceded it**, so standing residue is a constant offset rather than a variable — the
  finding is hour 1 against hour 9 of the same run, which is what makes that acceptable.
