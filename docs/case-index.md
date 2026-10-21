# Case index: what each case is, what ran, and what it found

> **CPU s/sync is whole-server CPU over the run's syncs** — an attribution, not a per-sync
> measurement. It compares well across healthy runs and badly across saturated ones, and badly for
> any run mixing co-tenant and customer syncs; see the run log's header.

## At a glance

| case | what it tests | runs | findings |
|---|---|---|---|
| [**1**](#case-1) | Training cohort | 10 | [`findings-case1.md`](findings-case1.md) |
| [**2**](#case-2) | Field worker steady state | 1 | [`findings-case2.md`](findings-case2.md) |
| [**14**](#case-14) | Re-enrolled device | 1 | [`findings-case14.md`](findings-case14.md) |
| [**3**](#case-3) | Supervisor steady state | 2 | [`findings-case3.md`](findings-case3.md), [`findings-span20.md`](findings-span20.md) |
| [**4**](#case-4) | Combined | 2 | [`findings-case4.md`](findings-case4.md), [`findings-span20.md`](findings-span20.md) |
| [**5**](#case-5) | Separate infrastructure | 2 | none of its own — written up in [6](findings-case6.md), [12](findings-case12.md) and [13](findings-case13.md) |
| [**6**](#case-6) | Shared — co-tenant data | 1 | [`findings-case6.md`](findings-case6.md) |
| [**7**](#case-7) | Shared — co-tenant load | 1 | [`findings-case7.md`](findings-case7.md) |
| [**8**](#case-8) | Growth | 3 | [`findings-case8.md`](findings-case8.md) |
| [**9**](#case-9) | Stress ramp | 4 | [`12a`](findings-case9-12a.md), [`12b`](findings-case9-12b.md), [`12c`](findings-case9-12c.md) |
| [**10**](#case-10) | Soak | 1 | [`findings-case10.md`](findings-case10.md) |
| [**11**](#case-11) | Clustered — separate | 7 | [`pair`](findings-case11-pair.md), [`15-min burst`](findings-case11-burst.md); run 1 has none |
| [**12**](#case-12) | Clustered — co-tenant data | 2 | [`findings-case12.md`](findings-case12.md); row 22 → [`findings-interceptor.md`](findings-interceptor.md) |
| [**13**](#case-13) | Clustered — co-tenant load | 4 | [`findings-case13.md`](findings-case13.md), [`findings-vertical-scale.md`](findings-vertical-scale.md), [`findings-interceptor.md`](findings-interceptor.md) |
| [**15**](#case-15) | Clustered — co-tenant load, media push | 1 + 1 pending | [`findings-clustered-media-push.md`](findings-clustered-media-push.md) |
| — | D7: client storage, on a real device | 4 device syncs, no server run | [`findings-d7.md`](findings-d7.md) |

<a id="case-1"></a>
## Case 1 — Training cohort

100 field workers' first login inside a short window; config only, no field data. Reference-data and `syncDetails` cost, swept across arrival windows.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-05 08:38`](run-log-detail.md#2026-10-05t08-38-47z-case1-f76d110) | 15 min window | tanuh-small-v2 | — | 0.0% | 202 | — |
| [`2026-10-05 09:43`](run-log-detail.md#2026-10-05t09-43-14z-case1-e47afd5) | 60 s window | tanuh-small-v2 | — | 0.0% | 2242 | — |
| [`2026-10-05 09:53`](run-log-detail.md#2026-10-05t09-53-13z-case1-burst15-e47afd5) | 15 s window | tanuh-small-v2 | — | 0.0% | 6768 | — |
| [`2026-10-05 10:28`](run-log-detail.md#2026-10-05t10-28-06z-case1-burst90-d9eac3e) | 90 s window | tanuh-small-v2 | 100 | 0.0% | 376 | 0.13 |
| [`2026-10-05 10:30`](run-log-detail.md#2026-10-05t10-30-01z-case1-burst120-d9eac3e) | 120 s window | tanuh-small-v2 | 100 | 0.0% | 222 | 0.19 |
| [`2026-10-05 10:32`](run-log-detail.md#2026-10-05t10-32-25z-case1-burst180-d9eac3e) | 180 s window | tanuh-small-v2 | 100 | 0.0% | 196 | 1.46 |
| [`2026-10-05 11:37`](run-log-detail.md#2026-10-05t11-37-03z-case1-burst60-d9eac3e) | 60 s, cold server | tanuh-small-v2 | — | — | — | **not a measurement** — started 2 minutes 49 seconds after the app server's JVM, which costs roughly two thirds of throughput |
| [`2026-10-05 11:41`](run-log-detail.md#2026-10-05t11-41-10z-case1-burst15-d9eac3e) | 15 s, cold server | tanuh-small-v2 | — | — | — | **not a measurement** — started 6 minutes 56 seconds after the app server's JVM, which costs roughly two thirds of throughput |
| [`2026-10-05 12:01`](run-log-detail.md#2026-10-05t12-01-03z-case1-burst60-warm-d9eac3e) | 60 s, warm | tanuh-small-v2 | 100 | 0.0% | 2767 | 0.34 |
| [`2026-10-05 12:02`](run-log-detail.md#2026-10-05t12-02-47z-case1-burst15-warm-d9eac3e) | 15 s, warm | tanuh-small-v2 | 100 | 0.0% | 6741 | 2.74 |
| [`2026-10-06 04:40`](run-log-detail.md#2026-10-06t04-40-26z-case1-burst900-e7a130d) | 900 s window | tanuh-small-v2 | 100 | 0.0% | 200 | 0.93 |
| [`2026-10-06 04:55`](run-log-detail.md#2026-10-06t04-55-47z-case1-burst75-e7a130d) | 75 s window | tanuh-small-v2 | — | — | — | **not a measurement** — the database credential had rotated and the app server held the old one, so every new pooled connection failed with HTTP 500 |
| [`2026-10-06 05:16`](run-log-detail.md#2026-10-06t05-16-44z-case1-burst75-e7a130d) | 75 s window, re-run | tanuh-small-v2 | 100 | 0.0% | 918 | 1.90 |

**Findings:** [`findings-case1.md`](findings-case1.md)

**100 devices arriving over 75 s or more is workable; 60 s is not.** The knee sits between 57 and 72 requests per second of demand, and the app server's 2 vCPU names it — not the database. A cold server gave a third of the throughput and the only failures, so later ramps warm up first; three cold runs are excluded for that reason or for an expired database credential.

<a id="case-2"></a>
## Case 2 — Field worker steady state

501 field workers, one state, production's own rhythm, 4 h.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-06 05:38`](run-log-detail.md#2026-10-06t05-38-32z-case2-e7a130d) | 500 field workers, 4 h | states-day-180 | 167 | 0.0% | 288 | 4.21 |

**Findings:** [`findings-case2.md`](findings-case2.md)

**An ordinary hour costs the server almost nothing** — ~2% CPU, flat. An incremental sync pulls 69% of what a full one does, so the 1% full-sync share is not the lever it looks like. Ran on `states-day-180`, the one case never repeated on the pilot dataset.

<a id="case-14"></a>
## Case 14 — Re-enrolled device

Case 2's cohort with every sync a full pull, 90 min.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-06 09:50`](run-log-detail.md#2026-10-06t09-50-36z-case14-4c7b807) | every sync full, 90 min | states-day-180 | 63 | 0.0% | 272 | 4.24 |

**Findings:** [`findings-case14.md`](findings-case14.md)

**A full sync costs 80 s, and 5.4 of them are the server's.** Every one of 63 syncs pulled exactly 15,732 records — an artefact of uniform catchments, so quote the mean, not the spread.

<a id="case-3"></a>
## Case 3 — Supervisor steady state

Supervisors alone, driven at 30/h for 2 h; the span (workers per supervisor) is a dataset, so it is swept by reloading.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-07 06:15`](run-log-detail.md#2026-10-07t06-15-54z-case3-eb5e4b3) | span 8.4, 60 supervisors | pilot-day-180 | 60 | 0.0% | 333 | 8.17 |
| [`2026-10-19 05:06`](run-log-detail.md#2026-10-19t05-06-40z-case3-span20-c2a0e76) | **span 20**, 25 supervisors | pilot-day-180-span20 | 60 | 0.0% | 357 | 20.55 |

**Findings:** [`findings-case3.md`](findings-case3.md), [`findings-span20.md`](findings-span20.md)

**A supervisor's sync pulls ~2.8× a field worker's records at the same cost per request**; it costs ~8.2 CPU s against ~4.2. At **span 20** records rise 2.33× for 2.38× the subjects, server cost per record ~5% more, and a median supervisor waits 7.1 minutes against 3.0 — almost all device time.

<a id="case-4"></a>
## Case 4 — Combined

Field workers and supervisors together, one state, 4 h.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-07 08:38`](run-log-detail.md#2026-10-07t08-38-32z-case4-eb5e4b3) | first attempt | pilot-day-180 | — | — | — | **not a measurement** — the feeder listed all 501 field workers before the first supervisor at row 502, and `circular()` reached only 187 rows in four hours, so this sampled one role and re-measured case … |
| [`2026-10-08 06:17`](run-log-detail.md#2026-10-08t06-17-46z-case4-d484f18) | span 8.4, interleaved feeder | pilot-day-180 | 187 | 0.0% | 322 | 4.23 |
| [`2026-10-19 07:14`](run-log-detail.md#2026-10-19t07-14-41z-case4-span20-c2a0e76) | **span 20** | pilot-day-180-span20 | 175 | 0.0% | 336 | 4.01 |

**Findings:** [`findings-case4.md`](findings-case4.md), [`findings-span20.md`](findings-span20.md)

**The roles compose — the mix is the sum of its parts.** The first attempt only ever reached field workers because of feeder order and re-measured case 2; the interleaved feeder fixed it. At span 20 the field workers hold at 1.00× and serve as a control, and p95 *falls* 182 s → 80 s purely because supervisors become a smaller share — composition, not speed.

<a id="case-5"></a>
## Case 5 — Separate infrastructure

Ten tenants, the customer's own load with nobody else's data present, 2 h. The baseline cases 6, 12 and 13 are read against.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-08 11:32`](run-log-detail.md#2026-10-08t11-32-36z-case5-d484f18) | first attempt | — | — | — | — | **not a measurement** — killed ~40s after launch and never reached archiveRun, so it has no metadata and no summary; superseded by the 17:34 run |
| [`2026-10-08 12:04`](run-log-detail.md#2026-10-08t12-04-15z-case5-d484f18) | span 8.4 | pilot-day-180 | 280 | 0.0% | 329 | 5.63 |
| [`2026-10-19 11:15`](run-log-detail.md#2026-10-19t11-15-25z-case5-span20-c2a0e76) | **span 20** | pilot-day-180-span20 | 263 | 0.0% | 348 | 3.79 |

**Findings:** none of its own — written up in [6](findings-case6.md), [12](findings-case12.md) and [13](findings-case13.md)

280 syncs, 0 failed, ~5.6 CPU s per sync. The comparison point for co-tenant presence, activity and compression.

<a id="case-6"></a>
## Case 6 — Shared — co-tenant data

Case 5 with 513 production-shaped organisations present in the database but syncing nothing.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-14 04:26`](run-log-detail.md#2026-10-14t04-26-19z-case6-cf77819) | case 5 + 513 co-tenants present, idle | pilot-day-180 | 280 | 0.0% | 333 | 3.85 |

**Findings:** [`findings-case6.md`](findings-case6.md)

**The presence of 513 co-tenants costs 0.3% per record** — noise end to end, though database time per call rose 25.5% at identical call counts.

<a id="case-7"></a>
## Case 7 — Shared — co-tenant load

Case 6 with the co-tenants syncing at 792/h, production's busiest recorded hour.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-14 09:19`](run-log-detail.md#2026-10-14t09-19-33z-case7-33396d9) | case 6 + co-tenants syncing at 792/h | pilot-day-180 | 1864 | 0.0% | 323 | 2.01 |

**Findings:** [`findings-case7.md`](findings-case7.md)

**Their activity costs 18% per record where their presence cost 0.3%.** Server time is ~7% of a sync, so the device finishes about 1% later. Its CPU per sync, 2.01, mixes 280 customer syncs with 1,584 small co-tenant ones and should not be read raw.

<a id="case-8"></a>
## Case 8 — Growth

Case 4's cohort at day 60, 120 and 365 of history; day 180 is case 4 itself.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-15 09:47`](run-log-detail.md#2026-10-15t09-47-54z-case8-day60-c2a0e76) | day 60 | pilot-day-60 | 94 | 0.0% | 263 | 1.55 |
| [`2026-10-16 04:54`](run-log-detail.md#2026-10-16t04-54-41z-case8-day-120-c2a0e76) | day 120 | pilot-day-120 | 94 | 0.0% | 302 | 2.98 |
| [`2026-10-16 09:06`](run-log-detail.md#2026-10-16t09-06-38z-case8-day-365-c2a0e76) | day 365 | pilot-day-365 | 94 | 0.0% | 337 | 7.38 |

**Findings:** [`findings-case8.md`](findings-case8.md)

**No knee at six times the history.** Records per sync track dataset depth one-for-one, per-record server cost falls then flattens, and CPU per sync runs 1.55 → 2.98 → 4.23 → 7.38 across days 60, 120, 180 and 365. What grows is the device's wait: a median sync goes 21 s → 122 s.

<a id="case-9"></a>
## Case 9 — Stress ramp

Ten tenants, arrivals ramped until something breaks; three ramps, each varying one dimension so a different answer would name a different resource.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-12 02:07`](run-log-detail.md#2026-10-12t02-07-36z-case9-12a-cf77819) | **12a** — ramp, realistic mix, push off | pilot-day-180 | 1084 | 0.54% | 52876 | 4.07 |
| [`2026-10-12 03:43`](run-log-detail.md#2026-10-12t03-43-44z-case9-12b-cf77819) | **12b** — ramp, every sync full (sized wrong) | pilot-day-180 | 318 | 0.0% | 489 | 4.74 |
| [`2026-10-12 04:55`](run-log-detail.md#2026-10-12t04-55-23z-case9-12b-rerun-cf77819) | **12b re-run** — every sync full, resized | pilot-day-180 | 768 | 0.24% | 48514 | 7.14 |
| [`2026-10-12 06:01`](run-log-detail.md#2026-10-12t06-01-23z-case9-12c-cf77819) | **12c** — ramp, push on | pilot-day-180 | 1191 | 0.01% | 33454 | 4.95 |

**Findings:** [`12a`](findings-case9-12a.md), [`12b`](findings-case9-12b.md), [`12c`](findings-case9-12c.md)

**12a**: app CPU pinned at 99% with RDS at 16–25%, knee ~1,160–1,290 syncs/h. **12b**: even with every sync a full pull the database cannot be made to bind; the ceiling is records per hour. **12c**: the write path does not bind either. The ~12.85 Mrec/h 'ceiling' was later shown by case 13 to be a saturated server's throughput, not a maximum.

<a id="case-10"></a>
## Case 10 — Soak

Case 4's load sustained for 12 h overnight, push on.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-09 14:21`](run-log-detail.md#2026-10-09t14-21-29z-case10-soak-cf77819) | case 4's load, 12 h, push on | pilot-day-180 | 561 | 0.0% | 290 | 5.36 |

**Findings:** [`findings-case10.md`](findings-case10.md)

**Twelve hours changed nothing** — 50,098 requests, 0 failed, no drift at the endpoint, in the JVM or per record.

<a id="case-11"></a>
## Case 11 — Clustered — separate

Case 5's day compressed into one hour; then a five-run back-to-back pair to validate running in blocks; then a 15-minute window.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-08 14:05`](run-log-detail.md#2026-10-08t14-05-56z-case11-run1-d484f18) | **run 1** — full 1,682 in 1 h, push on | pilot-day-180 | 1630 | 0.04% | 41912 | 4.94 |
| [`2026-10-09 04:28`](run-log-detail.md#2026-10-09t04-28-45z-case11-paira-d484f18) | **pair A** — 550/h, push on | pilot-day-180 | 550 | 0.0% | 342 | 3.99 |
| [`2026-10-09 05:37`](run-log-detail.md#2026-10-09t05-37-25z-case11-pairb-d484f18) | **pair B** — A again, no reset | pilot-day-180 | 550 | 0.0% | 367 | 4.76 |
| [`2026-10-09 06:55`](run-log-detail.md#2026-10-09t06-55-55z-case11-pairc-cf77819) | **pair C** — 550/h, push on | pilot-day-180 | 550 | 0.0% | 327 | 4.77 |
| [`2026-10-09 08:00`](run-log-detail.md#2026-10-09t08-00-22z-case11-paird-cf77819) | **pair D** — C again, no reset | pilot-day-180 | 550 | 0.0% | 364 | 5.97 |
| [`2026-10-09 09:17`](run-log-detail.md#2026-10-09t09-17-04z-case11-paire-cf77819) | **pair E** — push **off**, control | pilot-day-180 | 550 | 0.0% | 424 | 3.46 |
| [`2026-10-09 11:27`](run-log-detail.md#2026-10-09t11-27-35z-case11-burst15-400-cf77819) | **15-min window**, 400 users | pilot-day-180 | 400 | 0.0% | 19610 | 4.32 |

**Findings:** [`pair`](findings-case11-pair.md), [`15-min burst`](findings-case11-burst.md); run 1 has none

**Run 1**: the full 1,682 in an hour saturated (p95 41.9 s). **The pair** could not resolve drift because the harness is not reproducible run to run; the block strategy was settled another way. **The 15-minute burst** saturates on app CPU at 18.5 rps, not the database.

<a id="case-12"></a>
## Case 12 — Clustered — co-tenant data

Case 6 compressed into one hour: ~6.6 devices in flight against 0.55.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-15 04:01`](run-log-detail.md#2026-10-15t04-01-52z-case12-c2a0e76) | case 6 compressed to 1 h | pilot-day-180 | 1682 | 0.0% | 1709 | 3.66 |
| [`2026-10-21 10:59`](run-log-detail.md#2026-10-21t10-59-35z-case12-2vcpu-b-no-interceptor-f038788) | **2 vCPU, `DummyInterceptor` removed** (row 22); on row 20's residue, so a lower bound | pilot-day-180 | 1682 | 0.0% | 748 | 2.97 |

**Findings:** [`findings-case12.md`](findings-case12.md); row 22 → [`findings-interceptor.md`](findings-interceptor.md)

**The same work twelve times denser costs 170% more server time per record** — contention, not extra work — and takes app CPU to 81%, healthy. 0 failed. **With `DummyInterceptor` removed the same hour costs 19% less CPU**: 6,152 → 4,999 s, 3.66 → 2.97 per sync, `serverMs` p50 8.7 → 5.2 s, app CPU 81% → 65%, on a healthy server both times — the clean size of the saving that case 13 could not give.

<a id="case-13"></a>
## Case 13 — Clustered — co-tenant load

Case 7 compressed into one hour: ~9.7 in flight, three times production's peak. Re-run on larger instances, and now with `DummyInterceptor` removed.

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-15 05:33`](run-log-detail.md#2026-10-15t05-33-35z-case13-c2a0e76) | case 7 compressed to 1 h, 2 vCPU | pilot-day-180 | 1834 | 1.22% | 55919 | 4.52 |
| [`2026-10-21 04:10`](run-log-detail.md#2026-10-21t04-10-50z-case13-m6glarge-c2a0e76) | **2 vCPU** — sweep control | pilot-day-180 | 2007 | 0.91% | 56293 | 4.19 |
| [`2026-10-21 05:43`](run-log-detail.md#2026-10-21t05-43-20z-case13-m6gxlarge-c2a0e76) | **4 vCPU** | pilot-day-180 | 2474 | 0.0% | 434 | 3.13 |
| [`2026-10-21 09:56`](run-log-detail.md#2026-10-21t09-56-40z-case13-2vcpu-b-no-interceptor-f038788) | **2 vCPU, `DummyInterceptor` removed** (row 21); on row 20's residue by choice | pilot-day-180 | 2474 | 0.0% | 1440 | 2.57 |

**Findings:** [`findings-case13.md`](findings-case13.md), [`findings-vertical-scale.md`](findings-vertical-scale.md), [`findings-interceptor.md`](findings-interceptor.md)

**The first run to break**: 1.22% failed, and 47% more load *removed* 38% of the throughput. **On 4 vCPU it is uneventful** — 0 failures, p95 from ~56 s to 434 ms, CPU per sync 4.19 → 3.13, because a collapsing server spends CPU on work that never completes. The constraint moved toward the database: RDS 33% → 41%. **And on 2 vCPU with `DummyInterceptor` removed it stays on the cliff's safe side** — 467 failures become none, a 39 s median request becomes 295 ms, and CPU per sync falls 4.19 → 2.57, on a dataset carrying row 20's residue.

<a id="case-15"></a>
## Case 15 — Clustered — co-tenant load, media push

Case 13's shape — clustered into one hour, co-tenants syncing — with push on and **8 media files per encounter**: 1,500 workers over 1 h on 4 vCPU. Sized in advance in [`scenario-clustered-media-push.md`](scenario-clustered-media-push.md).

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-21 06:58`](run-log-detail.md#2026-10-21t06-58-37z-media-hour-m6gxlarge-c2a0e76) | 1,500 over 1 h, push on, 8 files/encounter, co-tenants, 4 vCPU | pilot-day-180 | 2292 | 0.0% | 503 | 5.04 |
| *row 23 — planned* | supervisors push nothing, `CUSTOMER_PUSH_DRAW=v2`; on row 20's residue | | | | | |

**Findings:** [`findings-clustered-media-push.md`](findings-clustered-media-push.md)

**It holds, and the server is 2% of it.** A median sync is 12.5 minutes, 10.7 of them the device uploading. App CPU landed inside the estimate; **RDS went to a 98.5% peak**, driven by `uploadUrl`. The 2 h 20 m drain came from the old encounter draw's tail, since replaced; supervisors were also pushing, which row 23 removes.

## D7 — client storage

Not a server run: four syncs on one real handset, two users per storage engine, against
`pilot-day-180`. **The storage model is sound in shape and wrong in magnitude** — SQLite's
2.22–2.53 ms per record is close to the model, Realm's 10.18–11.37 is 3.7–4.1× above it, so every
duration in the tables above is right for a SQLite fleet and understates a Realm one about
threefold. [`findings-d7.md`](findings-d7.md)

## Beyond the cases

* [`areas-to-investigate.md`](areas-to-investigate.md) — code-level costs the runs point at, ranked
* [`dummy-interceptor.md`](dummy-interceptor.md) — the largest of them, and rows 21–22's evidence
* [`what-a-simulated-sync-does.md`](what-a-simulated-sync-does.md) — what one virtual user does
* [`newrelic.md`](newrelic.md) — what the server-side instrumentation holds and how to read it back
