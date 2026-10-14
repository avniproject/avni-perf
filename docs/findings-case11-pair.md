# The case 11 pair: five runs, and why none of them measured drift

**9 October 2026.** `execution-plan.md` makes one measurement the gate on the block strategy:
run case 11 twice back to back with no reset, and if per-sync record counts and p50 agree within
noise, five resets for sixteen runs holds. Five runs were made. **None of them can answer that
question, and the reason is worth more than the answer would have been: the harness is not
reproducible by design, and a paired comparison assumes that it is.**

## The runs

All against `pilot-day-180`, reloaded and verified this morning — exact baseline counts, zero
2026-dated rows at the start. 550 users, 550 syncs/hour, one hour each, no reset between any of them.

| run | id | harness | push | requests | failed | mean | p95 | rps | full syncs |
|---|---|---|---|---|---|---|---|---|---|
| A | `2026-10-09T04-28-45Z-case11-pairA-d484f18` | d484f18 | on | 48,408 | 0 | 83 ms | 340 ms | 12.14 | 7 |
| B | `2026-10-09T05-37-25Z-case11-pairB-d484f18` | d484f18 | on | 47,456 | 0 | 84 ms | 368 ms | 11.88 | 4 |
| C | `2026-10-09T06-55-55Z-case11-pairC-cf77819` | cf77819 | on | 46,489 | 0 | 81 ms | 329 ms | 12.13 | 8 |
| D | `2026-10-09T08-00-22Z-case11-pairD-cf77819` | cf77819 | on | 47,544 | 0 | 90 ms | 384 ms | 11.88 | 2 |
| E | `2026-10-09T09-17-04Z-case11-pairE-cf77819` | cf77819 | **off** | 12,960 | 0 | 253 ms | 423 ms | 3.45 | 3 |

C, D and E ran with `-DNOW=2026-10-09T08:15:00Z`. A and B did not — see *The NOW fix* below.

## What the paired comparisons said

Joined on `userName`, which is sound: `realisticLoadedSince` derives each entity's window from
`(userName + "|" + entityName).hashCode()`, so both runs hand the same user the same window and
under the null each user's count should be identical.

| pair | mean shift | users differing | negative | exactly zero |
|---|---|---|---|---|
| A → B | **+2.69%** | 550 of 550 | 57 | 0 |
| C → D | **+8.65%** | 467 of 550 | 8 | 83 |
| D → E | **+1.63%** | 111 of 550 | 2 | 439 |

Every one is far above the ~0.32% ceiling that was pinned before the runs. None of them is drift.

## Why not

**Residue can only add, and these differences go both ways.** 57 users pulled *fewer* records in B
than in A. Whatever moved them, it was not rows that had been written.

**The effect is flat across organisations that pushed eight times different volumes.** Orgs 10 and
11 pushed 4,595 and 4,841 rows; orgs 12–19 pushed ~550. If this were residue being re-pulled, the
big orgs' users should gain ~8x as much. They gain the same:

```
org 10:  4,595 pushed -> +1,429 mean      org 15:  555 pushed -> +1,486 mean
org 11:  4,841 pushed -> +1,338 mean      org 17:  541 pushed -> +1,602 mean
```

In the small organisations each user gained **more records than the whole organisation pushed**.

**It happens with nothing written at all.** Run E pushed nothing — the only rows it created were
550 `sync_telemetry` records, confirmed by query. Restricted to the 416 users who in both D and E
read the database frozen at the pinned window end, and therefore saw byte-identical data:

```
identical  378 of 416
differing   38, every one by >1000 records, max +3,067
```

**It is not a fixed set of users.** Of the steppers in A/B, C/D and D/E, only **2** appear in all
three. The affected set is redrawn every run: 10.3% of field workers, 1.8% of supervisors.

**It is one entity, all or nothing.** Of 54 pull request names, only `Individual` moves materially
between D and E — **+188 page requests**, everything else within 5. A complete `Individual` pull for
the user traced is **3,041 records**; that user's step was **+3,129**, taking them from 11,057
(incremental) to 14,186 (their whole catchment). The step is not partial paging; the entity is
either synced in full or skipped.

## The server is not at fault

Three probes, all stable:

| probe | result |
|---|---|
| paged `Individual` pull, 12x sequential | 1,850 records / 2 pages, **12/12 identical** |
| bootstrap `syncDetails`, 20 threads x 8 | 160 responses, **one signature**, `Individual` always present |
| full walk, 16 threads x 4 | 64 walks, **all identical** |
| 40 users, two concurrent passes | **0 of 40 disagreed** |

The server returns the same answer to the same question, including under concurrency at the same
level the runs used. An earlier reading of this as a possible server defect was wrong.

## Where the variance actually comes from

**1. The full-sync draw, which is deliberate and documented.** `drawFullSync` uses
`ThreadLocalRandom`, and the comment says so plainly: *"a run is not bit-reproducible and this does
not change that … expect the count to vary run to run."* A drawn full sync sets `loadedSince` to
1900 and pulls everything. Recorded counts were 7, 4, 8, 2 and 3 across the five runs.

**This explains 5 of the 52 D/E steppers. It is real but it is not the main cause.**

**2. The other 47 are unexplained. Two candidates have been tested and both are dead.**

*The bootstrap fallback — refuted.* `syncStatusBody` falls back to an empty `entityTypeUuid` when
`userSyncStatuses` has no entry, which makes the server full-sync type-sliced entities, and that
matched the signature. It never happened: the one-shot warning *"no bootstrapped status list for
this user"* appears **zero times in all five run logs**, and every run shows
`Bootstrap sync statuses = 550 = Getting SyncDetails`. Every user bootstrapped.

*A drawn full sync — refuted for these users.* The user traced in detail is `fullSync=false` in all
five runs and still swings 10,962 to 14,186. Across the 52 D/E steppers, **47 have their high run
unflagged**.

So the mechanism for the bulk of the effect is **not known**. What is known about it:

* one entity, `Individual`, moving all-or-nothing by roughly one user's complete catchment
* a different ~10% of field workers each run, 1.8% of supervisors
* present with nothing written, and absent from every sequential and concurrent replay
* for the traced user the low values are runs C and D, which synced at or before the pinned window
  end, and the high values are A, B and E, which synced well after it — a pattern worth testing
  before anything else

**The next test should capture per-entity record counts per user**, which `sync-durations.csv` does
not carry — it has only a per-sync total. Without that, every further analysis is inference from
request counts.

## What this costs, and what to do

**A paired comparison assumes reproducibility the harness does not offer.** The artifact is ~284
records/sync against a residue signal of ~85 — 3.3x larger than what it is meant to resolve. That
is why every pair came out above the ceiling, and why two successive corrections to the
amplification model both failed: the model was being fitted to noise.

Before attempting this again:

1. **`-DFULL_SYNC_PERCENT=0`** for both runs of a pair. Removes source 1 entirely.
2. **Prove or kill the bootstrap fallback.** Log `tracked == null` per user, or assert the
   bootstrap populated the map before the sync proceeds. A run where any user silently
   full-syncs a typed entity is not comparable with one where none did.
3. Only then re-run the pair. Reload first — see *What was established* for why that still matters.

## The server-side half can be answered, and it says no drift — added 14 Oct 2026

The comparison above fails because the harness draws a different number of records per run, so
sync durations and record counts are not comparable between A and B. **Database time per call is
not subject to that.** It is a per-query measure: how long the same queries take, independent of
how many of them a given sync happened to need.

`encounter (GET)`, across all five runs:

| run | requests | avg | db | calls | **db/call** | app |
|---|---|---|---|---|---|---|
| A | 6,902 | 306.1 ms | 49.34 ms | 31.3 | **1.577 ms** | 256.8 ms |
| B | 7,071 | 295.6 | 47.79 | 31.2 | **1.532** | 247.8 |
| C | 7,381 | 294.1 | 48.52 | 31.2 | **1.556** | 245.6 |
| D | 7,485 | 322.2 | 49.39 | 31.4 | **1.575** | 272.8 |
| E | 7,028 | 318.7 | 47.14 | 31.8 | **1.483** | 271.5 |

**No trend.** `db/call` spans 1.483 to 1.577, 6.3%, and the order is A high, B low, C middle, D
high, E lowest — scatter, not drift. Call count holds at 31.2 to 31.8 throughout. Push residue
accumulated across all five runs, and case 11 run 1 alone had added 43,257 rows beforehand, yet
the database shows nothing.

### Why that is believable rather than just quiet

The same measure has now been taken three times under different conditions, and it discriminates:

| | db per call, at constant call count |
|---|---|
| case 6, 513 co-tenants present | **+25.5%** |
| case 10, nine hours of sustained load | flat, 34.67 → 34.34 ms |
| **this pair, five runs of accumulating push residue** | **no trend, 6.3% scatter** |

A measure that moved for co-tenant presence and did not move for the soak is not one that simply
fails to move. So the residue not reaching the database is a result, not an absence of
instrumentation.

### Application time does step, and it fits the explanation above

245.6 → 272.8 ms between C and D, holding into E. **Not a harness change** — C, D and E share
`cf77819`. The most likely cause is the one this document already identifies as fatal to the
paired comparison: `realistic` draws per-(user, entity) gaps from a measured distribution, so each
run pulls a different number of records, and more records is more application time. That is
consistent with the conclusion above rather than a competing explanation for it.

### What it changes

The verdict stands: **the sync-level comparison cannot answer the drift question**, for the reasons
set out above. But the question the block strategy actually rests on — does a run sitting on the
previous run's residue pay for it — now has a partial answer. **On the database side, no.** The
application side remains confounded by the record-count variation, and would need a feeder pinned
to fixed record counts to separate.

## What was established

**The residue figures are sound even though the drift question is not answered.** They were
measured directly, not inferred from the pairs:

| | rows pushed | per sync |
|---|---|---|
| case 11 run 1 (8 Oct, 1,682 syncs) | 43,257 | 25.72 |
| run C (9 Oct, 550 syncs) | 14,014 | 25.48 |

Two independent runs a day apart agree to 1%. The 8 Oct figure was itself cross-checked two ways —
a `created_date_time` filter and a delta against the baseline — which agreed to the row.

**A real harness bug was found and fixed (`cf77819`).** `NOW` is documented as *"set it to pin the
window across runs"*, but only `windowEndFor` honoured it; `realisticLoadedSince` always measured
its gap back from `Instant.now()`. Setting `NOW` pinned one end and left the other floating, so the
window **narrowed** by the time between two runs. Pinning both ends is visibly better — negatives
fell 57 → 8 and exact matches rose 0 → 439 — it simply does not reach past the larger artifact.
No run before today had ever set `NOW`, so nothing already measured changes.

**The 1,682/hour result of 8 Oct was congestion, not cost.** At 550/hour the same work on the same
dataset ran at 83 ms mean against 18,569 ms — a factor of 224 — with zero failures and devices in
flight flat at ~31 rather than ~435. Case 11's published per-sync costs describe a saturated
server and should not be read as per-device cost.
