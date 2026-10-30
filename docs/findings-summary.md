# What the load tests found

**Complete as of 19 October 2026 — 42 runs, 18 findings documents, one page.** Each claim links to
the case that carries the evidence; nothing here is new, and where a finding has been corrected the
correction is what appears.

**For which runs belong to which case**, and what each varied, see
[`case-index.md`](case-index.md).

**For what a run actually does**, see
[`what-a-simulated-sync-does.md`](what-a-simulated-sync-does.md) — one virtual user end to end,
and which parts are modelled rather than performed.

## The one-line answer

**The application server's CPU is the constraint, the database never is, and under the sync
pattern production actually has, neither matters.** What turns a comfortable system into a broken
one is not volume, tenancy or history — it is **everybody syncing at once**.

**And most of that app CPU was avoidable.** Four server fixes, measured one at a time and then
together on the 18.3 release candidate (§9), take **43–50% off the CPU of every sync** on every
anchor, a fifth to a quarter off the database, half the requests wherever media is pushed — and
the case 13 load that broke 2 vCPU now runs there at 65% with no failures.

## 1. The constraint has a name, and it is app CPU

Established independently five times — [case 1](findings-case1.md),
[9/12a](findings-case9-12a.md), [11-burst](findings-case11-burst.md),
[12](findings-case12.md), [13](findings-case13.md).

At 99% application CPU the database sits at **a fifth of its capacity**. The write path does not
bind either ([12c](findings-case9-12c.md)); push costs the database about ten percentage points of
CPU and nothing else. **More vCPU is the relief; a bigger database is not.**

**That is now tested rather than inferred** ([vertical scale sweep](findings-vertical-scale.md),
21 Oct). Case 13 — the only run that ever broke — re-run on 4 vCPU instead of 2, nothing else
changed:

| | 2 vCPU | 4 vCPU |
|---|---|---|
| failures | 467 (0.91%) | **0** |
| response p95 | 56,714 ms | **434 ms** |
| under 800 ms | 5.15% | **99.6%** |
| app CPU | 94–99% | **49–55%** |
| RDS CPU | 32–38% | 38–42% |

**The constraint moved toward the database**: the gap between the tiers fell from ~65 points to
~13, so 8 vCPU may be where the database finally binds — which four earlier runs could not make
happen.

**It does not, when the tiers are sized together** ([rows 25 and 26, 23 Oct](findings-clustered-media-push.md#row-26-10000-users-on-16-app-and-16-database-vcpu)).
The scale-out runs — the customer at ten encounters a day and 8 files each, co-tenants on —
doubled users and both tiers at once and the gap held at ~30 points:

| | 5,000 users, 8 + 8 vCPU | **10,000 users, 16 + 16 vCPU** |
|---|---|---|
| requests | 573,458 at 159 rps | **1,107,301 at 307 rps** |
| failures | 1 (a data defect, since fixed) | **0** |
| response p95 | 234 ms | **231 ms** |
| app CPU, mean | 61.6% | **58.9%** |
| RDS CPU, mean | 31.6% | **27.4%** |
| CPU s per customer sync | ~3.4 | **~3.4** |
| field-worker sync p50, of which the server | 364 s, 1.3% | **364 s, 1.3%** |

Per-sync cost is flat from 8 to 16 vCPU; the pool peaked at 44 of 100, the heap at a quarter of
its pin, the volume at 212 read IOPS. On these numbers **10,000 users at ten a day fit on 16
application vCPU at 59% — 8 would run at ~100% — and on 8 database vCPU at ~55%**; the plan's
"16 and 16" over-provisions the database, and the interceptor fix (−19%) is what would make 8
application vCPU comfortable. **Measured since (§9):** the 18.3 release candidate runs 5,000 users
on 8 + 8 at 36% app and 24% database CPU, −43% per sync — so 10,000 at ten a day fits on 8
application vCPU with room to spare.

**What the 2 vCPU saturation was made of** ([timeslices, 22 Oct](findings-vertical-scale.md)):
the broken run collected garbage for **555 seconds against 18** on 4 vCPU, with old-generation
collections only on 2 vCPU and the heap at 5,096 of 5,120 MB — a quarter to a half of the 4.19
→ 3.13 CPU s per sync gap. And **98% of its request time was the authentication filter's own
code** (exclusive time; 14% at 4 vCPU), with 48,865 monitor-blocked thread events against 571.
Every request takes a pooled connection there before any controller runs. **The cliff has a
place, not only a level** — and the release candidate removes it: case 13 on the same 2 vCPU
spends 0.7 s per sync in that filter against 292.6, with 1,152 blocked-thread events against
48,865 and no old-generation collections at all (§9).

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
| **users** — 5,000 → 10,000, both tiers doubled with them ([rows 25–26](findings-clustered-media-push.md#row-26-10000-users-on-16-app-and-16-database-vcpu)) | ×2 | unchanged, 8,400 | **unchanged**, 3.4 CPU s a sync |

**No knee in any of them.** Deeper history, wider catchments and more users are different inputs
and the server answers all three the same way: proportionally more rows at an almost unchanged
cost each — and, for users, the same cost on twice the cores.

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
* [Removing `DummyInterceptor`](findings-interceptor.md) — **takes case 13 off the cliff on the
  hardware that broke**: 467 failures → 0, p50 38,782 → 295 ms, CPU 4.19 → 2.57 s per sync; the
  queue that climbed 64 → 338 on the control held at 34–49 all hour. On case 12, healthy both
  times, the clean saving is **18.7% of application CPU**. The timeslices put the interceptor's
  segment at **11.7% of request time** — the profiler's 12.6% reproduced — with its `gender`
  query only 8% of that and the `@Transactional` boundary around it the rest. The old build's
  knee is bounded for the first time: **900–1,030 requests/min on 2 vCPU.**
* [The 18.3 release candidate](execution-plan.md#row-30-results) — **case 13 on 2 vCPU with every
  fix in**: 0 failures, p95 56,293 → **396 ms**, CPU 4.19 → **1.78 s per sync**, app 65%. Better than
  17.3 managed on *4* vCPU (434 ms, 3.13 s). The knee has moved off this hardware altogether (§9).

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

## 9. The fixes, measured

**Rows 27–30, 27–30 Oct 2026** ([execution plan](execution-plan.md#rows-27-28-results)). The
production build moved to 18.1, so the baseline was re-run on it first: **18.1 reproduces 17.3**
on both anchors with identical statement counts (row 28 ran the old jar the same day and landed
between the two 18.1 runs), and the rig had drifted 5–8% dearer since mid-October, so the
controls are the 27 Oct runs — A 3.90 ± 0.07, B 4.27 ± 0.02 CPU s per sync. Each fix was then
built on 18.3 alone and run against them; then all four together.

| fix | A — case 12, 2 + 2 vCPU | B — case 15 ten-a-day, 4 + 2 | what it removed |
|---|---|---|---|
| **#1097** `DummyInterceptor` gone | **−26%**, p95 2,433 → 715 ms | **−24%**, RDS −6 pts | two `gender` selects per request; the interceptor segment; two of three re-saves per write |
| **#1103** parent UUIDs via `@Formula` | **−41%**, p95 → 417 ms | **−24%**, RDS −6 pts | a hydrated parent entity per child row — `individual` selects −85%, GC −79% |
| **#1100** batched upload URLs (client at 50) | — | **−6%**, **RDS −11 pts**, requests 204k → 97k | 80 per-file `uploadUrl` calls per sync → 2, and their twelve statements each |
| **#1098** Joda instant equality | none | none (write IOPS −33%) | **every** re-save of telemetry and pushed entities — a correctness fix, not a capacity one |

**Together — the 18.3 release candidate:**

| anchor | CPU s per sync | p95 | app / database CPU | failures |
|---|---|---|---|---|
| **A** case 12, 2 + 2 | 3.90 → **1.94 (−50%)** | 2,433 → **332 ms** | 90 → **46%** / 27 → **21%** | 0 |
| **B** case 15, 4 + 2, batched | 4.27 → **2.28 (−47%)** | 449 → **248** | 65 → **35%** / 62 → **46%** | 0 |
| **C** case 13 on 2 + 2 — the cliff | 4.19 → **1.78** | 56,293 → **396** | 94–99 → **65%** | 467 → **0** |
| **D** 5,000 users, 8 + 8, batched | 3.20 → **1.81 (−43%)** | 234 → **205** | 63 → **36%** / 32 → **24%** | 0 |

**What it settles.**

1. **The fixes compose on different tiers, not by adding up.** #1097 and #1103 both strip
   per-row work from the same request path, so the release candidate is "#1103 plus part of
   #1097" — −50% on A, not the −67% the stand-alone figures sum to. #1100 adds on the database
   tier, and on B it is worth more combined than alone: with the parent loads gone, the
   per-request overhead it removes is a larger share of what is left.
2. **The 2 vCPU knee is gone, not moved a little.** The scenario that defined the cliff runs at
   65% of 2 vCPU with a better p95 than 17.3 managed on 4. Every capacity figure in §1 and §7 was
   measured on the old build and is now conservative by roughly half. The comparison is against the 17.3 control,
   not row 21's no-interceptor run: that one started 38 minutes after a push run and pulled its
   residue — 4,404 `GET /individual` against 116–360 for the same scenario earlier that day — so
   its CPU per sync (2.57) is inflated. **The request count of a pull is set by what was pushed
   recently, not by the build**, which is why every run in this phase starts from a reload.
3. **The gain holds at scale.** At 5,000 users on 8 + 8 the per-sync saving (−43%) matches the
   1,500-user anchors, and the pool never left 13–19 connections.
4. **The write amplification was the Joda bug, not the interceptor.** #1098 alone took every
   re-save to zero; #1097 alone left one per write. Its value is correctness and `audit`'s
   growth, not CPU.
5. **A fix's share of query time is not its share of CPU.** #1103 was ranked at ~5% from
   statement time and measured at −41%. Ranking by the profiler's request-time share, as
   `areas-to-investigate.md` does, is the better guide.

**Where the release candidate breaks** ([row 31](execution-plan.md#row-31), 30 Oct). On 16 app + 16
database vCPU, 10,000 users' worth of data and the customer's push pattern with batched upload
URLs: **~22,500 syncs an hour is comfortable** (app ~75%, p95 222 ms, pool half used),
**~27,500 is sustained at the edge** (app ~91%, p95 534.9 ms, no backlog, no failures), and above
~29,000 the server queues — throughput flat at ~265–300 requests a second, p95 growing without
bound, failures still under 0.1%. **App CPU binds; the database never passes 62%**; the connection
pool fills only once CPU saturates. Per-sync cost holds at –~1.85 CPU s right up to the
edge. **Plan on ~25,000 syncs an hour for 16 + 16** — about 1.7× what the old jar was predicted
to manage on the same hardware.

**Not measured:** #882's catchment/`users` lookups and #1057's `syncDetails` `exists` are larger
pieces with no jar yet; a client-side `Slice` endpoint (avni-client#2096) needs a harness mode.

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

**4. Media density.** **Done 21 Oct 2026 as *clustered — co-tenant load, media push*** — see suggestion 9 and
[`findings-clustered-media-push.md`](findings-clustered-media-push.md). Before it, customer push runs carried the
harness default of 1.42 files per encounter and co-tenants production's 0.23 per pushed encounter;
the customer's screening bundle reaches **16 on a single encounter**. At 8 per encounter
`uploadUrl` became 79% of customer requests and took RDS to a 98.5% peak.

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

**9. Clustered — co-tenant load, media push.** **Done 21 Oct 2026** as row 20: 1,500 workers over
an hour, push on, **8 media files per encounter**, co-tenants syncing, on 4 vCPU. Sized in advance in
[`scenario-clustered-media-push.md`](scenario-clustered-media-push.md) at ~10,300 CPU seconds; it measured
11,542, app CPU landed inside the estimate, and **RDS went to a 98.5% peak** driven by `uploadUrl` —
the database is the next constraint. 0 failures. Row 23 re-draws it with supervisors pushing nothing
and the customer's own encounter spread; **rows 24–26 (23 Oct) take it to ten encounters a day and
scale it out** — 5,000 users on 8 + 8 vCPU, then 10,000 on 16 + 16, each on a dataset generated
for it: **0 failures at 10,000, ~3.4 CPU s per customer sync at both sizes, app ~60% and database
~30% at both**, the field worker's sync 364 s at p50 with the server 1.3% of it. The plan's upper
bounds held; its "the database idles" did not — the pulls set its floor at ~30%. §1 has the table.
[`findings-clustered-media-push.md`](findings-clustered-media-push.md)

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
database fix combined. **That one is now measured, not estimated** (§7): removing it saves 18.7% of
application CPU on a healthy server and is the difference between 467 failures and none on the
one that broke. Next are the N+1 lazy `individual` selects at **11.18%** — explained 26 Oct: every sync response loads each parent entity in full to build the link to it ([§9](areas-to-investigate.md#9-sync-responses-load-each-parent-entity-in-full-to-link-a-record-to-its-parent)) and `AuthenticationFilter`
at **5.62%** — and the row 19 timeslices make the filter more than a per-call cost: **it is where a
saturated server queues**, 98% of request time in its own code at 2 vCPU, so anything that lets it
answer without a pooled connection moves the knee itself. **A supervisor pays all of them 38.6
times per sync**, which is also the argument for raising `PAGE_SIZE` rather than lowering it.

Ranking by *database calls* misleads here: `syncDetails` owns 32% of them and 2.7% of request
time.

**Two of these are now fixed and measured** (§9): the interceptor (#1097) and the parent loads
(#1103), which turned out to be the largest single item — **−41% of CPU per sync on its own**, five
times the ~5% its share of query time suggested, because the cost was hydrating an entity per
child row, not the select. `AuthenticationFilter` and `syncDetails` remain.

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
* **Media density was below the customer's until row 20** (clustered — co-tenant load, media push) — 1.42 files per encounter
  against up to **16 on a single encounter** in the screening bundle; 8 per encounter is now
  measured ([`findings-clustered-media-push.md`](findings-clustered-media-push.md)). Media push itself is
  measured; what `MEDIA_MODEL=pause` skips is the S3 PUT, deliberately, and media *pull* is on
  demand rather than part of a sync. (4)
* **Uniform catchments** — every village holds identical volume, so the mean is sound and **the
  tail is an artefact**. (5)
* **The storage constants are one device, four syncs** ([D7](findings-d7.md)), and they scale every
  duration published here. (8)
