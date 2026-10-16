# Case 8: the growth curve, complete. No knee at six times the history

**15–16 October 2026.** Three runs on `c2a0e76` — day 60, day 120 and day 365 — plus case 4 at
day 180 as corroboration. 94 syncs each, zero failures throughout. Day 365:
`2026-10-16T09-06-38Z-case8-day-365-c2a0e76`, 3,112 requests, mean 257 ms, p95 337 ms, 98.75%
under 800 ms.

Day 60: Case 4's workload — 561 users,
46.75 syncs/hour, realistic, `case4-users-pilot.csv` — at `DURATION_MINUTES=120` on
`pilot-day-60`. 94 syncs, 1,504 requests, **zero failures**, every request under 800 ms.

Case 8 asks for the *shape* of the curve as a tenant's history deepens. This is the first of
three points measured under identical conditions; days 120 and 365 follow.

## What "growth" means here, which is not what it sounds like

| | day 60 | day 180 |
|---|---|---|
| individuals | 1,506,000 | 1,506,000 |
| encounters | 1,794,784 | 5,385,356 |

**The population is fixed and the visit history grows.** Day 180 is not a bigger tenant, it is the
same tenant 120 days later. Three times the elapsed days, three times the encounters, to within
rounding.

## The curve, complete

| incremental syncs | day 60 | day 120 | day 180* | day 365 |
|---|---|---|---|---|
| dataset encounters | 1.79 M | 3.59 M | 5.39 M | **10.92 M** |
| records per sync, mean | 4,356 | 8,714 | 10,812 | **26,506** |
| duration p50 | 21.4 s | 41.0 s | 60.6 s | **122.5 s** |
| duration p95 | 60.6 s | 121.3 s | 61.3 s | **369.5 s** |
| server ms p50 | 1,466 | 2,513 | 3,461 | **6,848** |
| **server ms per record** | **0.386** | **0.347** | **0.322** | **0.326** |

\* day 180 is case 4 from 7 October, on a different harness and index state.

Relative to day 60, at the three directly comparable points:

| | encounters | records/sync | per-record cost |
|---|---|---|---|
| day 120 | x2.00 | **x2.00** | x0.898 |
| day 365 | x6.08 | **x6.08** | x0.843 |

**Two things hold exactly, and one is the answer.**

**Records per sync tracks dataset depth one-for-one.** Twice the encounters, twice the records;
six times the encounters, six times the records — x2.00 against x2.00 and x6.08 against x6.08,
with no drift at either step. At a fixed sync cadence a device carries what accumulated since it
last synced, and that is linear in how much the tenant does.

**The per-record cost falls and then flattens**: 0.386, 0.347, 0.326. The fall is −10.2% over the
first doubling and only −6.1% more across the next tripling, settling near 0.33 ms. It is per-sync
fixed cost — authentication, `syncDetails`, the entity walk — spread over more rows, and the
spreading has nearly run its course by day 120.

**There is no knee.** Six times the history, 94 syncs, 3,112 requests, zero failures, 98.75% of
requests under 800 ms. Nothing in this range degrades.

## What does grow, and it is the device's problem

Per-record cost is the server's view. The device's view is the whole sync:

| | day 60 | day 365 |
|---|---|---|
| duration p50 | 21.4 s | **122.5 s** |
| duration p95 | 60.6 s | **369.5 s** |

**A median sync goes from 21 seconds to over two minutes, and p95 to six minutes.** That is linear
in dataset depth and it is exactly what "no knee" means: the work per record did not get worse, so
six times the records takes six times as long. A field worker returning to a tenant with a year of
history waits two minutes for a routine sync and six for an unlucky one.

Whether that is acceptable is a product question, not a performance one. The server is not the
constraint at any point on this curve.

## What "growth" means here, which is not what it sounds like

| incremental syncs | day 60 | day 120 | day 180* |
|---|---|---|---|
| syncs | 94 | 94 | 186 |
| records per sync, mean | 4,356 | 8,714 | 10,812 |
| duration p50 | 21.4 s | 41.0 s | 60.6 s |
| server ms p50 | 1,466 | 2,513 | 3,461 |
| **server ms per record** | **0.386** | **0.347** | **0.322** |

\* day 180 is case 4 from 7 October — different harness and index state, see below.

**Day 60 → day 120 is the clean comparison**, and it is −10.1% per record. Both ran on harness
`c2a0e76`, both on indexes rebuilt within the hour, both verified warm, a day apart. Nothing
differs but the dataset.

That matters because the day 60 → 180 figure below is −16.6% and *is* confounded. Two
comparisons, one of them uncontaminated, now point the same way: **the cost per record falls as
the history deepens, and the fall is getting smaller** — 0.386, 0.347, 0.322.

**Records per sync doubled exactly as the encounters doubled**: 4,356 → 8,714 is 2.00x against a
dataset ratio of 2.00x. A sync returns what changed since the device last synced, and at a fixed
sync cadence twice the history means twice the changes to carry.

The p95 duration at day 120 (121.3 s) is twice day 60's and day 180's. With 94 syncs the 95th
percentile is one of the last five values; day 180 had 186 syncs and a better-estimated tail. Read
it as noise unless day 365 repeats it.

## Day 60 against day 180, and the cost per record falls

| incremental syncs | day 60 | day 180 (case 4) | delta |
|---|---|---|---|
| syncs | 94 | 187 | — |
| records per sync, mean | 4,356 | 10,812 | +148% |
| duration p50 | 21.4 s | 60.6 s | +183% |
| duration p95 | 60.6 s | 61.3 s | +1.1% |
| server ms p50 | 1,466 | 3,461 | +136% |
| **server ms per record** | **0.386** | **0.322** | **−16.6%** |

A sync at day 180 returns 2.5x the records and takes 2.4x the server time, so the work tracks what
is returned rather than what is stored. **Per record it is 17% cheaper**, which is per-sync fixed
cost — authentication, `syncDetails`, the entity walk — amortised over more rows.

**No knee between these two points.** The curve is flat to mildly favourable, and nothing here
suggests a cliff; the two remaining points are where one would show up if it exists.

Note also that records per sync grew 2.5x while the dataset grew 3.0x. An incremental sync returns
what changed since the device last synced, not a share of the whole table, so depth reaches the
sync only through how much recent activity it implies.

## The day-180 point is not measured like the other three

This comparison is to **case 4, run on 7 October**, and four things differ:

| | case 4 | case 8 day-60 |
|---|---|---|
| harness | `eb5e4b3` | `c2a0e76` |
| duration | 240 min | 120 min |
| cache policy | `warm-after-case3` | `warm-jvm-pristine-indexes` |
| database around it | no co-tenants at all | 513 organisations resident, 105,608 catchments, indexes REINDEXed an hour earlier |

Duration normalises away per record. **Index state does not.** Case 4's indexes had accumulated
through Block A; today's were rebuilt an hour before the run, and the plan already names this as a
parity caveat — "post-load indexes are pristine; production's carry accumulated bloat." A 17%
per-record difference is comfortably inside the range that could account for.

So **the −16.6% should be read as provisional**. Days 60, 120 and 365 will be directly comparable
with each other; day 180 sits on a different footing and is corroboration rather than a measured
point. If the knee appears to fall at 180, re-run case 4's shape on `pilot-day-180` under current
conditions before believing it — a dataset swap plus two hours.

## Provenance

The reset before this run emptied the 513 co-tenants' transactional data so the growth curve is not
damped by a constant 6.25 M-row background: at day 60 that background would have been 2.5x the
customer's own encounters. Organisation 3 was left intact. 105,608 co-tenant *catchments* survive
`--scope data` by design, which is a lookup table rather than transactional volume.

Case 4's feeder was checked against the day-60 users before launch — 561 of 561 present, none
voided, all with catchments. A different dataset can carry different usernames, and a feeder that
silently matches nothing produces a run that completes and measures the wrong thing.


## One difference between the three points, recorded rather than assumed

Day 60 ran with `CACHE_POLICY=warm-jvm-pristine-indexes` — warm from the previous day's load, on a
JVM that had served cases 12 and 13. Days 120 and 365 ran `warm-after-discarded-warmup`, a
deliberate 900-second warm-up on a JVM started that morning.

All three were warm; they did not get there the same way. Day 120's warm-up was not optional: its
server had been up 38 minutes and served nothing, and a cold JVM delivers about a third of warm
throughput — which would have swamped the dataset effect entirely and produced a false knee at
day 120.
