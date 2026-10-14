# Case 6: the presence of 513 co-tenants costs 0.3% per record

**14 October 2026.** `2026-10-14T04-26-19Z-case6-cf77819`. Case 5's run, unchanged, with 513
co-tenant organisations present in the same tables and syncing nothing. 280 syncs, 5,237
requests, **zero failures**, 2 h 00 m 48 s.

The question case 6 exists to answer is what *presence* costs — RLS selectivity, planner
statistics, table and index size — as distinct from case 7, which turns the co-tenants' activity
on. The answer at this scale is **nothing measurable**.

## Normalised per record, nothing moved

Both runs pulled ~3.6 M records across 280 syncs, of which 278 were incremental. Comparing only
the incremental syncs, which is like for like:

| | case 5 (8 Oct) | case 6 | delta |
|---|---|---|---|
| syncs | 280 | 280 | — |
| full syncs | 2 | 2 | — |
| records pulled | 3,636,774 | 3,617,090 | −0.5% |
| records per sync, mean | 12,870.2 | 12,897.9 | +0.2% |
| sync duration p50 | 60.6 s | 60.6 s | −0.0% |
| sync duration p95 | 182.2 s | 182.3 s | +0.1% |
| server ms p50 | 3,577 | 3,560 | −0.5% |
| server ms p95 | 11,004 | 11,181 | +1.6% |
| **server ms per record** | **0.336** | **0.337** | **+0.3%** |

**0.3% is noise.** The database holds 513 more organisations, 6.25 M more rows and
correspondingly larger indexes, and the server spends the same time per record it returns.

## The request-level tail says something different, and it is the wrong lens

Gatling's own summary invites a worse conclusion:

| | case 5 | case 6 |
|---|---|---|
| mean | 228 ms | 238 ms |
| p50 | 268 ms | 262 ms |
| p95 | 329 ms | 333 ms |
| p99 | 367 ms | **525 ms** |
| max | 523 ms | **3,730 ms** |

p99 up 43% and a maximum seven times worse reads like a finding. It is not one. **14 requests of
5,237 exceeded 800 ms**, where case 5's slowest was 523 ms — 0.27% of the run, against sync-level
work that is identical to within half a percent. Per-record normalisation is the lens the soak
used for the same reason: raw durations move with what a sync happened to be asked for, and the
full-sync draw is random.

Those 14 requests are worth remembering rather than explaining. Planner statistics over a table
530 organisations wide, or a B-tree deep enough to cost an extra level, would both look like this
and neither is established by fourteen requests. **Case 7 is where to look**, because it puts real
load behind those organisations instead of only their rows.

## Why this comparison is readable at all

The pilot was reloaded the same morning — orgs 10–19 torn down and restored from
`pilot-day-180`, leaving the co-tenants in place. That removed **120,929 rows** of push residue
accumulated by case 11 run 1, pairs A–E and 12c. Without it a 0.3% signal would have been sitting
underneath five runs of accumulated writes with no way to separate them afterwards.

Every setting was taken from case 5's own `run-metadata.json` rather than reconstructed — steady,
1682 users, `SYNC_WINDOW_HOURS=12` giving 140 syncs/hour, 120 minutes, realistic,
`case5-users-pilot.csv`, push off, page 1000. The only difference either run records is the
measured injector RTT, 0.07 s against 0.08 s.

`FULL_SYNC_PERCENT` was left at its 1.0 default because case 5 left it there. Both runs drew
exactly 2 full syncs of 280, which is luck — the draw varies, and a pair that differed there would
not be comparable at the tail. A future paired run should consider pinning it.

## One near miss worth recording

The first attempt at this run launched against a cold JVM. `env-warmup.sh` polls `/ping` from
wherever it is invoked, the ALB admits only the injector and one office CIDR, and the operator was
on neither — so the warm-up reported "not warmed" and, because every exit in that script is 0 by
design, the run started anyway. A cold server serves about a third of warm throughput, and case 5
was warm: the run would have reported the co-tenants as catastrophically expensive. It was killed
and relaunched after the warm-up was fixed to poll from the injector. **A warm-up that cannot fail
a start must still be able to fail a measurement.**
