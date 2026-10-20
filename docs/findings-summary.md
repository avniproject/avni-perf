# What the load tests found

**Complete as of 19 October 2026 — 42 runs, 18 findings documents, one page.** Each claim links to
the case that carries the evidence; nothing here is new, and where a finding has been corrected the
correction is what appears.

## The one-line answer

**The application server's CPU is the constraint, the database never is, and under the sync
pattern production actually has, neither matters.** What turns a comfortable system into a broken
one is not volume, tenancy or history — it is **everybody syncing at once**.

## 1. The constraint has a name, and it is app CPU

Established independently five times — [case 1](findings-case1.md),
[9/12a](findings-case9-12a.md), [11-burst](findings-case11-burst.md),
[12](findings-case12.md), [13](findings-case13.md).

At 99% application CPU the database sits at **a fifth of its capacity**. The write path does not
bind either ([12c](findings-case9-12c.md)); push costs the database about ten percentage points of
CPU and nothing else. **More vCPU is the relief; a bigger database is not.**

The knee sits between **57 and 72 requests per second** of demand. 100 devices arriving over 75
seconds is workable; over 60 seconds is not.

## 2. Steady state is free. The herd is the problem

An ordinary hour — 500 field workers on production's own rhythm — costs **~2.1% CPU, flat**
([case 2](findings-case2.md)). The same box is near saturation in case 1's 75-second burst.

**This is the finding everything else qualifies.**

## 3. The device does the work, not the server

`serverMs` is **6–7% of a sync's wall time** in every case. Halving server time moves an 80-second
sync to 77 seconds.

Which makes [D7](findings-d7.md) the largest user-facing finding in the set: storage cost was
*modelled*, and the model is SQLite's number. On Realm it is **3.7–4.1× optimistic**, so a
**supervisor on Realm waits nine minutes** for one sync. Every duration published here is right for
a SQLite fleet and understates a Realm one by about three times.

**Server optimisation is a capacity argument, not a latency one.** It raises how many devices can
sync at once; it does not make a sync feel faster.

> **Every run here is sync and nothing else**, so this understates how contended the server is.
> Production also carries the web app, the API and bulk imports, and shares its database with
> avni-etl and Metabase — so a share measured against sync-only load does not transfer to it.

## 4. Who syncs matters; how they are mixed does not

A supervisor covers a Taluka, so the sync scales with the catchment: **2.8× the records, 2.3× the
requests, at the same cost per request** ([case 3](findings-case3.md)). Roles then compose linearly
— a mixed cohort is the sum of its parts, to the percentage point ([case 4](findings-case4.md)).

Widening the catchment scales the sync and almost nothing else ([Block A′](findings-span20.md)):
**2.38× the subjects per supervisor gives 2.33–2.44× the records, 2.34× the duration, and about +5%
server time per record.** Field workers, whom the span does not touch, hold at **1.00×** — a control
measured on the same server at the same moment.

A full sync is **not** the expensive outlier it was taken for: an incremental sync pulls 69% of
what a full one pulls ([case 2](findings-case2.md), [case 14](findings-case14.md)).

## 5. Co-tenants: presence is free, activity is not

| | per-record cost |
|---|---|
| 513 co-tenants present, idle ([case 6](findings-case6.md)) | **+0.3%** — noise |
| 513 co-tenants syncing at production's busiest recorded hour ([case 7](findings-case7.md)) | **+18%** |

6.25 M more rows and 513 more organisations in the database change nothing measurable. Their
*traffic* does. And because server time is ~7% of a sync, **the server works 18% harder per record
while the device finishes about one percent later.**

## 6. Volume is linear, however it arrives, and there is no knee

Two independent inputs, the same answer:

| input | scaled by | records per sync | per-record cost |
|---|---|---|---|
| **history** — day 60 → 365 ([case 8](findings-case8.md)) | ×6.08 | **×6.08** | falls 10%, then flat |
| **catchment** — span 8.4 → 20 ([Block A′](findings-span20.md)) | ×2.38 | **×2.33–2.44** | **+5%** |

**No knee in either.** Deeper history and wider catchments are different inputs and the server
answers both the same way: proportionally more rows at an almost unchanged cost each.

The cost lands on the device, not the server. History: a median sync goes from **21 seconds to over
two minutes**. Span: a supervisor goes from **3.0 minutes to 7.1**, 94% of it the modelled storage
pause. **Both are product questions about tooling, not server questions.**

Twelve hours of sustained load drifts in nothing — no leak, no cache decay, no residue
([case 10](findings-case10.md)).

## 7. Clustering is what breaks it

The twelve-hour working day is an assumption about behaviour, not a property of the system. Compress
the same syncs into one hour and concurrency rises twelvefold.

* [Case 12](findings-case12.md) — compression costs **170% per record**, and the app server is the
  constraint for the fourth time.
* [Case 13](findings-case13.md) — **the first run to break.** Adding 47% more load *removed* 38% of
  the throughput: 21.0 Mrec/h at 81% CPU, 13.0 Mrec/h at 95.5%.

> **A ceiling measured on a saturated server is not the ceiling.** 12.85 Mrec/h was read as a limit;
> it is what a *broken* server achieves. The healthy system is about **60% higher**. Capacity
> planning off the saturated figure understates by that much.

## 8. A headline statistic reversed the direction of what it described

At span 8.4 a supervisor is ~10.4% of syncs, so their sync sits **above** p95. At span 20 they are
~4.2%, so it sits **below**. Cases 4 and 5 therefore show **sync p95 falling from 182 s to 80 s
while every single supervisor sync got slower** — 75,000 records against 32,000
([Block A′](findings-span20.md)).

**The percentile moved because the cohort's composition changed, not because anything got faster.**
Splitting by role recovers the truth. The same trap is why case 4 re-measured case 2 before the
feeder ordering was fixed, and why `devices in flight` was 3× high for a year of runs. **Read mixed
cohorts by role, or do not read them.**

## Suggestions for other runs

**Work needing the environment**, ordered by what the findings leave open rather than by cost.

**1. Locate the clustering knee.** [Cases 12](findings-case12.md) and [13](findings-case13.md)
bracket it — 21.0 Mrec/h at 81% CPU, 13.0 at 95.5% — and neither sits on it. Bisect at roughly
1.15×, 1.3× and 1.45× case 12's load. **Three hours, and it is the number capacity planning
needs**; today the only two figures available are "fine" and "collapsed".

**2. Vertical scale sweep, 2 → 4 → 8 vCPU.** "App CPU is the constraint, more vCPU is the relief"
is the most-repeated finding in the set (§1) and **has never been tested** — it is an inference
from five runs where CPU saturated and the database did not. Re-run case 13 on larger instances. If
throughput does not scale, there is a second constraint nobody has found, and that matters more
than any tuning.

**3. Program data for the customer cohort.** `program_enrolment` and `program_encounter` are 0
rows **in the ten pilot tenants** where the recipe specifies 0.22 enrolment. The co-tenants do have
them — 2.41 M rows — so this is a gap in what the measured syncs pull, not a table the server has
never touched. Worse than "smaller": `ProgramEncounter` is production's **largest table**
and carries the **highest measured storage rate** in `StorageProfiles` — 8.44 ms/record against
`Encounter`'s 6.14. The missing entity is the expensive one. Regenerate and re-run cases 5 and 13.

**4. Media density.** Media push is already exercised — `media/uploadUrl` was the highest-count
endpoint in case 11 pair C at 18,269 calls. What is untested is **rate**: these runs carry
production's platform-wide 0.02 files per encounter, while the customer's screening bundle reaches
**16 on a single encounter**. Run case 11 or 13 with `--media-repeats` from that bundle. This
multiplies request count, not just device wall-clock.

**5. Varied catchment sizes.** The generator gives every village identical volume, so case 14's 63
full syncs pulled *exactly* 15,732 records each. The mean is sound and the spread is an artefact —
and "what does the **worst** catchment cost" is the question operations asks.

**6. Validate the server fixes against the run that broke.** After areas 1–3 above, re-run
[case 13](findings-case13.md). It is the only run that actually failed, so it is the only one that
can show the knee moving.

**7. Two confound-closers.** **Case 2 on the pilot** — the only case never run on the common
dataset, which is why its 184 ms against case 5's 274.5 cannot be attributed to database size
rather than cohort ([case 3](findings-case3.md)). And **repeats**: most cases are n=1, and the one
case that was repeated differed by **5% in throughput and 23% in p95**.

**8. Extend D7.** The storage constants rest on **one handset, four syncs, both engines in low
power mode** — and §3 makes them the largest user-facing finding in the set, since they decide
every published duration by a factor of three. More devices, not in low power mode, both engines.

### Considered and not recommended

* **A wider span sweep.** [Block A′](findings-span20.md) found simple proportionality at every
  point, so 8.4 → 20 interpolates rather than needing its own runs.
* **Anything further on the database.** Four independent runs failed to make it bind.
* **A `MEDIA_UPLOAD_KBPS` sweep as a capacity test.** It is the largest lever on media-bearing sync
  duration — 26 s to 402 s across the documented range — but during the transfer the device asks
  avni-server for nothing. It belongs with [D7](findings-d7.md) as device experience, not here.

## The write path is not measured, and it is not cheap

**Everything above measures sync, which is read-dominated.** "The database never binds" is a
statement about reads. Bulk insert behaves differently, and 20 Oct 2026's reload of the co-tenant
bed made that concrete:

* **Every insert into an audited table fires `audit_table_trigger`**, which inserts into or updates
  `audit` — **89,330,284 rows and 11 GB** on the rig by 20 Oct. Suppressing it was worth about
  **5x** on bulk load. Nothing resets that table, so this cost has been rising all campaign.
* **A per-row trigger or constraint lookup depends on an index nobody would think to keep.**
  Dropping the secondary indexes made `program_encounter` **350x slower** — 13 rows/s against
  4,570 — because the lookup degrades to a sequential scan over a growing table.
* **Loading a child table inside a transaction that already holds ~700k new rows costs ~100x per
  row.** 413,320 rows did not finish in 33 minutes; the same copy took 31 seconds once each table
  committed on its own.

None of this changes a sync finding. It bears on **imports, bulk operations and any future reset**,
and it is the kind of per-request work [`areas-to-investigate.md`](areas-to-investigate.md) is
built around — except on the write side, which that document does not cover. Details and the
measurements are in [`execution-plan.md`](execution-plan.md) under *The 20 Oct 2026 reload*.

## Areas to investigate

**Code-level work, needing no environment**, all of one shape: work the server does on every
request that nothing downstream needs. Six of them, ranked, with evidence and fixes in
**[`areas-to-investigate.md`](areas-to-investigate.md)**.

**82% of request time is Java, 17% is the database**, so the largest single item is
`DummyInterceptor` at **12.6% of request time** — 96% of all interceptor time, and more than every
database fix combined. Next are the N+1 lazy `individual` selects at **11.18%** and
`AuthenticationFilter` at **5.62%**, and **a supervisor pays all of them 38.6 times per sync**,
which is also the argument for raising `PAGE_SIZE` rather than lowering it.

Ranking by *database calls* misleads here: `syncDetails` owns 32% of them and 2.7% of request
time.

> **None of this makes a sync faster.** Database time is ~15% of a request and `serverMs` is 6–7%
> of a sync. These raise the saturation ceiling — which is where the system actually fails (§7).

## What is not measured

Limits on the numbers above. Each is closed by a run in the section above, by number.

* **No program data in the measured cohort** — `program_enrolment` and `program_encounter` are
  **0 rows across the ten pilot tenants**, where the recipe specifies 0.22 enrolment, so **every
  customer sync measured here is smaller than a real one** and the entity missing is the most
  expensive one. (3)

  **Not "0 rows database-wide", which this said until 20 Oct 2026 and which is wrong.** The 513
  co-tenants carry **560,523 enrolments and 1,845,829 program encounters** — 2.41 M rows, 38% of
  their data, and more program encounters than ordinary ones. So the program path is resident and
  co-tenant syncs read it in [case 7](findings-case7.md) and [case 13](findings-case13.md); what is
  untested is a *customer* sync that pulls it. The pilot's `program_*.tsv` files are empty by
  generation, not by teardown — they carry the sha256 of the empty string. The earlier wording
  dated from Block C, which had emptied the co-tenants, and generalised a true statement about that
  moment into a false one about the dataset. (3)
* **Media density is production's platform-wide rate**, not the customer's: 0.02 files per
  encounter against **16 on a single encounter** in the screening bundle. Media push itself is
  measured; what `MEDIA_MODEL=pause` skips is the S3 PUT, deliberately, and media *pull* is on
  demand rather than part of a sync. (4)
* **Uniform catchments** — every village holds identical volume, so the mean is sound and **the
  tail is an artefact**. (5)
* **The storage constants are one device, four syncs** ([D7](findings-d7.md)), and they scale every
  duration published here. (8)
