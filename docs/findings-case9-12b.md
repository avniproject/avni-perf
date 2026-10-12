# Case 9 / 12b: the database cannot be made to bind, and the ceiling is records per hour

**12 October 2026.** Two runs, because the first was sized wrong.

| run | ramp | syncs | peak app CPU | outcome |
|---|---|---|---|---|
| `2026-10-12T03-43-44Z-case9-12b-cf77819` | 50 → 800/h over 45 min | 318 | **55%** | no knee, zero failures |
| `2026-10-12T04-55-23Z-case9-12b-rerun-cf77819` | 200 → 2,400/h over 40 min | 866 | **99.1%** | saturated, 0.24% failed |

Both `SYNC_MODE=full`, `PUSH=off`, ten tenants, `pilot-day-180`.

**The first ramp was sized from a number that did not mean what I thought.** 12a's six drawn full
syncs showed p50 749.7 s against 260.1 s for the run, which I read as full costing 2.9x. Those syncs
ran *during* 12a's saturation: they measured queueing. Like-for-like against 12a's own unsaturated
syncs, full costs **1.44x** — and costs it entirely in extra records, not in any per-sync penalty.

## The database was never pressed, and that is 12b's own answer

12b existed to move bytes rather than request count — the one shape that might make RDS, the buffer
cache or storage bind before the app tier. It does not, in either run:

| | first run | rerun (saturated) |
|---|---|---|
| RDS CPU | 15–18% | 23–31% |
| ReadLatency | 0.41–1.02 ms | 0.50–0.60 ms |
| ReadThroughput | 0.41–0.61 MB/s | 0.85–1.18 MB/s |
| connections | 10–12 | 98, pegged |

**Every sync pulling everything, and the database reads about one megabyte a second at
sub-millisecond latency.** The working set is comfortably resident. Storage cannot be made to bind
by this workload on this dataset, and the pool pegging at 98 in the rerun is again downstream of
slow requests rather than their cause — the database behind it sat at a quarter of its capacity.

## Server cost is linear in records, and identical across sync modes

Comparing only unsaturated syncs, so queueing is excluded from both sides:

| | records/sync | serverMs p50 | **server ms per record** |
|---|---|---|---|
| 12a realistic, first 300 | 11,186 | 5.2 s | **0.46** |
| 12b full, all 318 | 16,158 | 7.4 s | **0.46** |
| 12a realistic, last 300 (saturated) | 10,778 | 650.8 s | **60.38** |

Full syncs pull 1.44x the records and cost 1.44x the server time. **There is no full-sync penalty
beyond the rows.** And saturation inflates per-record cost **131-fold**, which is why the drawn full
syncs inside 12a looked so expensive.

## The ceiling is records per hour, across every run measured

| run | mode | push | in flight | achieved syncs/h | **Mrec/h at 99% CPU** |
|---|---|---|---|---|---|
| 12b full (first) | full | off | 18 | 424 | 12.33 *(from 55%)* |
| 12a | realistic | off | 113 | 1,161 | 12.78 |
| 12b full (rerun) | full | off | 171 | 838 | 13.43 |
| case 11 burst, 9 Oct | realistic | **on** | 123 | 800 | 11.28 |
| case 11 run 1, 8 Oct | realistic | **on** | 435 | 776 | 10.70 |

**~12.8M records/hour without push, ~11.0M with it.** Spread inside each group is under 5%; the
push penalty of about **14%** is larger than the spread and consistent across two runs.

It holds across two sync modes, four injection shapes, and concurrency from **18 to 435 devices in
flight**. Concurrency is not the binding quantity: 18 in flight and 435 in flight land on the same
ceiling once each is normalised for the CPU it actually used.

**This replaces "syncs per hour is the capacity number".** Syncs per hour ranges 424 to 1,161 across
these runs while the record ceiling holds. Capacity planning belongs in records:

    records_per_sync x syncs_per_hour  <=  ~12.8M on this instance, ~11.0M when pushing

A deployment of 1,682 devices each pulling 11,000 records once a day needs 18.5M records of
capacity a day, which this server delivers in about 1.5 hours — the constraint is how tightly that
demand clusters, not the daily total.

## Honest record of how this was got wrong twice

**The first 12b ramp was too low**, sized from a saturated measurement. Cost: one 45-minute run.

**I then proposed that concurrency, not records, was the binding quantity**, on the basis that the
first 12b reached "12.9M records/hour at 55% CPU" where 12a hit 99% at 13.4M. That figure was wrong:
I computed it from the ramp's *demanded* peak rate of 800 syncs/hour rather than its *achieved* 424.
The real figure is 6.85M, and once corrected all five runs agree on records. **Demanded is not
achieved, and in a stress ramp the difference is the entire finding.**

## What this does not say

**One app server, 2 vCPU, ETL off.** The ceiling is a property of this instance and this
configuration.

**The write path is still untested.** 12c turns push on. It now has a sharp prediction to fail:
if records are the binding quantity, 12c should saturate near **11.0M records/hour**, matching the
two pushing runs above.
