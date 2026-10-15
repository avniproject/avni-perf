# Case 8: the growth curve. Point one of three — day 60

**15 October 2026.** `2026-10-15T09-47-54Z-case8-day60-c2a0e76`. Case 4's workload — 561 users,
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
