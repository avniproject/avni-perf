# Run log

Generated from `s3://avni-loadtest-936573213727/artefacts/` by `tools/update-run-log.sh` (`make run_log`) — last refreshed 2026-10-21 15:11 IST.

**Do not edit by hand.** Rewritten wholesale on every run of that script. The artefacts prefix is append-only by IAM, so S3 is the source of truth and this is a view of it. An edit here is lost on the next refresh; a run missing from this table means its upload did not happen, not that the log is stale.

**Times are IST; run ids are UTC.** The id is the identifier and keeps the `Z` it was minted with — `...T11-37-03Z...` is the 17:07 row. Dates are converted with the time, so anything before 18:30 UTC lands on the same IST day but a late-evening run will not.

Artefacts are **not** copied into the repo. Each run directory holds Gatling's `simulation.log`, the HTML report and `run-metadata.json`, plus the environment context captured at run time — `parity-report.md`, `pg_settings.csv`, `stats.json` — and `sync-durations.csv`, one row per completed sync. Those are what make a number interpretable once the environment that produced it has been destroyed. The bucket is private and the report's ~250 objects only render together, so each run also carries a single `<run-id>.zip` of the whole directory; the detail page links it. Download, unzip, open `index.html`.

**`app CPU s` is application CPU over the run's window, from New Relic's `apm.service.cpu.usertime`, which is absolute seconds rather than a percentage.** It is cached in `docs/cpu-per-sync.json` by `tools/cpu-per-sync.py` so this log can be regenerated without New Relic access; a run missing from the cache shows a dash. **`CPU s/sync` is an attribution, not a measurement** -- whole-server CPU divided by the run's syncs, so it carries the health checks and anything else on the box, and it spans the ramp and tail where CPU is low and syncs still count. Read it for capacity, where CPU seconds are additive and wall clock is not; the per-run detail splits it by cohort and by full against incremental.

Findings drawn from these runs are written up separately, by hand, in `findings-case1.md` and its siblings — this file is the index, not the analysis.

| run | date (IST) | scenario | profile | users | arrival window | ~requests in flight | ~devices in flight | requests | failed | p95 ms | full sync p95 s | rps | app CPU s | CPU s/sync |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [`2026-10-05T08-38-47Z-case1-f76d110`](run-log-detail.md#2026-10-05t08-38-47z-case1-f76d110) | 2026-10-05 14:08 | case1 | burst | 100 | 15min | ~0.2 | — | 4300 | 0.0% | 202 | — | 4.77 | 135 | — |
| [`2026-10-05T09-43-14Z-case1-e47afd5`](run-log-detail.md#2026-10-05t09-43-14z-case1-e47afd5) | 2026-10-05 15:13 | case1 | burst | 100 | 60s | ~22 | — | 4300 | 0.0% | 2242 | — | 52.44 | 50 | — |
| [`2026-10-05T09-53-13Z-case1-burst15-e47afd5`](run-log-detail.md#2026-10-05t09-53-13z-case1-burst15-e47afd5) | 2026-10-05 15:23 | case1 | burst | 100 | 15s | ~71 | — | 4300 | 0.0% | 6768 | — | 56.58 | 123 | — |
| [`2026-10-05T10-28-06Z-case1-burst90-d9eac3e`](run-log-detail.md#2026-10-05t10-28-06z-case1-burst90-d9eac3e) | 2026-10-05 15:58 | case1 | burst | 100 | 90s | ~3.2 | ~11.8 | 4300 | 0.0% | 376 | 12.4 | 43 | 13 | 0.13 |
| [`2026-10-05T10-30-01Z-case1-burst120-d9eac3e`](run-log-detail.md#2026-10-05t10-30-01z-case1-burst120-d9eac3e) | 2026-10-05 16:00 | case1 | burst | 100 | 120s | ~1.7 | ~8.4 | 4300 | 0.0% | 222 | 11.2 | 33.33 | 19 | 0.19 |
| [`2026-10-05T10-32-25Z-case1-burst180-d9eac3e`](run-log-detail.md#2026-10-05t10-32-25z-case1-burst180-d9eac3e) | 2026-10-05 16:02 | case1 | burst | 100 | 180s | ~1.0 | ~5.5 | 4300 | 0.0% | 196 | 10.7 | 22.75 | 146 | 1.46 |
| [`2026-10-05T12-01-03Z-case1-burst60-warm-d9eac3e`](run-log-detail.md#2026-10-05t12-01-03z-case1-burst60-warm-d9eac3e) | 2026-10-05 17:31 | case1 | burst | 100 | 60s | ~27 | ~36 | 4300 | 0.0% | 2767 | 40.2 | 50 | 34 | 0.34 |
| [`2026-10-05T12-02-47Z-case1-burst15-warm-d9eac3e`](run-log-detail.md#2026-10-05t12-02-47z-case1-burst15-warm-d9eac3e) | 2026-10-05 17:32 | case1 | burst | 100 | 15s | ~71 | ~80 | 4300 | 0.0% | 6741 | 64.0 | 56.58 | 274 | 2.74 |
| [`2026-10-06T04-40-26Z-case1-burst900-e7a130d`](run-log-detail.md#2026-10-06t04-40-26z-case1-burst900-e7a130d) | 2026-10-06 10:10 | case1 | burst | 100 | 900s | ~0.2 | ~1.2 | 4300 | 0.0% | 200 | 10.8 | 4.77 | 93 | 0.93 |
| [`2026-10-06T05-16-44Z-case1-burst75-e7a130d`](run-log-detail.md#2026-10-06t05-16-44z-case1-burst75-e7a130d) | 2026-10-06 10:46 | case1 | burst | 100 | 75s | ~8.8 | ~18.4 | 4300 | 0.0% | 918 | 18.4 | 49.43 | 190 | 1.90 |
| [`2026-10-06T05-38-32Z-case2-e7a130d`](run-log-detail.md#2026-10-06t05-38-32z-case2-e7a130d) | 2026-10-06 11:08 | case2 | steady | 500 | 240min @ 42/h | ~0.0 | ~0.7 | 2846 | 0.0% | 288 | 80.4 | 0.2 | 702 | 4.21 |
| [`2026-10-06T09-50-36Z-case14-4c7b807`](run-log-detail.md#2026-10-06t09-50-36z-case14-4c7b807) | 2026-10-06 15:20 | case14 | steady | 501 | 90min @ 42/h | ~0.1 | ~0.9 | 2898 | 0.0% | 272 | 80.2 | 0.54 | 267 | 4.24 |
| [`2026-10-07T06-15-54Z-case3-eb5e4b3`](run-log-detail.md#2026-10-07t06-15-54z-case3-eb5e4b3) | 2026-10-07 11:45 | case3 | steady | 60 | 120min @ 30/h | ~0.1 | ~1.4 | 2314 | 0.0% | 333 | 223.4 | 0.32 | 490 | 8.17 |
| [`2026-10-08T06-17-46Z-case4-d484f18`](run-log-detail.md#2026-10-08t06-17-46z-case4-d484f18) | 2026-10-08 11:47 | case4 | steady | 561 | 240min @ 47/h | ~0.1 | ~1.0 | 3587 | 0.0% | 322 | 223.6 | 0.25 | 792 | 4.23 |
| [`2026-10-08T12-04-15Z-case5-d484f18`](run-log-detail.md#2026-10-08t12-04-15z-case5-d484f18) | 2026-10-08 17:34 | case5 | steady | 1682 | 120min @ 140/h | ~0.2 | ~2.8 | 5390 | 0.0% | 329 | 223.9 | 0.74 | 1,576 | 5.63 |
| [`2026-10-08T14-05-56Z-case11-run1-d484f18`](run-log-detail.md#2026-10-08t14-05-56z-case11-run1-d484f18) | 2026-10-08 19:35 | case11 | steady | 1682 | 60min @ 1682/h | ~414 | ~435 | 143211 | 0.04% | 41912 | 3747.0 | 22.27 | 8,060 | 4.94 |
| [`2026-10-09T04-28-45Z-case11-pairA-d484f18`](run-log-detail.md#2026-10-09t04-28-45z-case11-paira-d484f18) | 2026-10-09 09:58 | case11 | steady | 550 | 60min @ 550/h | ~1.0 | ~31 | 48408 | 0.0% | 342 | 455.5 | 12.14 | 2,194 | 3.99 |
| [`2026-10-09T05-37-25Z-case11-pairB-d484f18`](run-log-detail.md#2026-10-09t05-37-25z-case11-pairb-d484f18) | 2026-10-09 11:07 | case11 | steady | 550 | 60min @ 550/h | ~1.0 | ~30 | 47456 | 0.0% | 367 | 316.2 | 11.88 | 2,620 | 4.76 |
| [`2026-10-09T06-55-55Z-case11-pairC-cf77819`](run-log-detail.md#2026-10-09t06-55-55z-case11-pairc-cf77819) | 2026-10-09 12:25 | case11 | steady | 550 | 60min @ 550/h | ~1.0 | ~31 | 46489 | 0.0% | 327 | 389.8 | 12.13 | 2,622 | 4.77 |
| [`2026-10-09T08-00-22Z-case11-pairD-cf77819`](run-log-detail.md#2026-10-09t08-00-22z-case11-paird-cf77819) | 2026-10-09 13:30 | case11 | steady | 550 | 60min @ 550/h | ~1.1 | ~31 | 47544 | 0.0% | 364 | 300.7 | 11.88 | 3,285 | 5.97 |
| [`2026-10-09T09-17-04Z-case11-pairE-cf77819`](run-log-detail.md#2026-10-09t09-17-04z-case11-paire-cf77819) | 2026-10-09 14:47 | case11 | steady | 550 | 60min @ 550/h | ~0.9 | ~12.8 | 12960 | 0.0% | 424 | 227.2 | 3.45 | 1,904 | 3.46 |
| [`2026-10-09T11-27-35Z-case11-burst15-400-cf77819`](run-log-detail.md#2026-10-09t11-27-35z-case11-burst15-400-cf77819) | 2026-10-09 16:57 | case11 | steady | 400 | 15min @ 1600/h | ~79 | ~123 | 35842 | 0.0% | 19610 | 888.0 | 18.47 | 1,729 | 4.32 |
| [`2026-10-09T14-21-29Z-case10-soak-cf77819`](run-log-detail.md#2026-10-09t14-21-29z-case10-soak-cf77819) | 2026-10-09 19:51 | case10 | steady | 561 | 720min @ 47/h | ~0.1 | ~3.0 | 50098 | 0.0% | 290 | 548.7 | 1.16 | 3,005 | 5.36 |
| [`2026-10-12T02-07-36Z-case9-12a-cf77819`](run-log-detail.md#2026-10-12t02-07-36z-case9-12a-cf77819) | 2026-10-12 07:37 | case9 | stress | 1682 | 45min @ 200/h | ~107 | ~113 | 21491 | 0.54% | 52876 | 1284.2 | 6.23 | 4,411 | 4.07 |
| [`2026-10-12T03-43-44Z-case9-12b-cf77819`](run-log-detail.md#2026-10-12t03-43-44z-case9-12b-cf77819) | 2026-10-12 09:13 | case9 | stress | 1682 | 45min @ 50/h | ~1.0 | ~11.3 | 16041 | 0.0% | 489 | 229.3 | 5.82 | 1,507 | 4.74 |
| [`2026-10-12T04-55-23Z-case9-12b-rerun-cf77819`](run-log-detail.md#2026-10-12t04-55-23z-case9-12b-rerun-cf77819) | 2026-10-12 10:25 | case9 | stress | 1682 | 40min @ 200/h | ~169 | ~171 | 40241 | 0.24% | 48514 | 1450.4 | 11.4 | 5,486 | 7.14 |
| [`2026-10-12T06-01-23Z-case9-12c-cf77819`](run-log-detail.md#2026-10-12t06-01-23z-case9-12c-cf77819) | 2026-10-12 11:31 | case9 | stress | 1682 | 45min @ 200/h | ~235 | ~274 | 102891 | 0.01% | 33454 | 2123.9 | 20.46 | 5,894 | 4.95 |
| [`2026-10-14T04-26-19Z-case6-cf77819`](run-log-detail.md#2026-10-14t04-26-19z-case6-cf77819) | 2026-10-14 09:56 | case6 | steady | 1682 | 120min @ 140/h | ~0.2 | ~2.8 | 5237 | 0.0% | 333 | 81.9 | 0.72 | 1,078 | 3.85 |
| [`2026-10-14T09-19-33Z-case7-33396d9`](run-log-detail.md#2026-10-14t09-19-33z-case7-33396d9) | 2026-10-14 14:49 | case7 | steady | 1682 | 120min @ 140/h | ~1.0 | ~7.6 | 61683 | 0.0% | 323 | 82.7 | 8.53 | 3,741 | 2.01 |
| [`2026-10-15T04-01-52Z-case12-c2a0e76`](run-log-detail.md#2026-10-15t04-01-52z-case12-c2a0e76) | 2026-10-15 09:31 | case12 | steady | 1682 | 60min @ 1682/h | ~5.5 | ~36 | 31409 | 0.0% | 1709 | 254.9 | 8.52 | 6,152 | 3.66 |
| [`2026-10-15T05-33-35Z-case13-c2a0e76`](run-log-detail.md#2026-10-15t05-33-35z-case13-c2a0e76) | 2026-10-15 11:03 | case13 | steady | 1682 | 60min @ 1682/h | ~388 | ~313 | 51727 | 1.22% | 55919 | 2031.6 | 12.06 | 8,298 | 4.52 |
| [`2026-10-15T09-47-54Z-case8-day60-c2a0e76`](run-log-detail.md#2026-10-15t09-47-54z-case8-day60-c2a0e76) | 2026-10-15 15:17 | case8 | steady | 561 | 120min @ 47/h | ~0.0 | ~0.3 | 1504 | 0.0% | 263 | — | 0.21 | 145 | 1.55 |
| [`2026-10-16T04-54-41Z-case8-day-120-c2a0e76`](run-log-detail.md#2026-10-16t04-54-41z-case8-day-120-c2a0e76) | 2026-10-16 10:24 | case8 | steady | 561 | 120min @ 47/h | ~0.0 | ~0.7 | 1624 | 0.0% | 302 | — | 0.23 | 280 | 2.98 |
| [`2026-10-16T09-06-38Z-case8-day-365-c2a0e76`](run-log-detail.md#2026-10-16t09-06-38z-case8-day-365-c2a0e76) | 2026-10-16 14:36 | case8 | steady | 561 | 120min @ 47/h | ~0.1 | ~1.9 | 3112 | 0.0% | 337 | — | 0.43 | 694 | 7.38 |
| [`2026-10-19T05-06-40Z-case3-span20-c2a0e76`](run-log-detail.md#2026-10-19t05-06-40z-case3-span20-c2a0e76) | 2026-10-19 10:36 | case3 | steady | 25 | 120min @ 30/h | ~0.2 | ~3.3 | 5053 | 0.0% | 357 | — | 0.67 | 1,233 | 20.55 |
| [`2026-10-19T07-14-41Z-case4-span20-c2a0e76`](run-log-detail.md#2026-10-19t07-14-41z-case4-span20-c2a0e76) | 2026-10-19 12:44 | case4 | steady | 526 | 240min @ 44/h | ~0.1 | ~0.9 | 3436 | 0.0% | 336 | 80.5 | 0.24 | 702 | 4.01 |
| [`2026-10-19T11-15-25Z-case5-span20-c2a0e76`](run-log-detail.md#2026-10-19t11-15-25z-case5-span20-c2a0e76) | 2026-10-19 16:45 | case5 | steady | 1580 | 120min @ 132/h | ~0.2 | ~2.7 | 5120 | 0.0% | 348 | 80.9 | 0.68 | 998 | 3.79 |
| [`2026-10-21T04-10-50Z-case13-m6g.large-c2a0e76`](run-log-detail.md#2026-10-21t04-10-50z-case13-m6glarge-c2a0e76) | 2026-10-21 09:40 | case13 | steady | 1682 | 60min @ 1682/h | ~398 | ~359 | 50848 | 0.91% | 56293 | 2082.5 | 11.94 | 8,403 | 4.19 |
| [`2026-10-21T05-43-20Z-case13-m6g.xlarge-c2a0e76`](run-log-detail.md#2026-10-21t05-43-20z-case13-m6gxlarge-c2a0e76) | 2026-10-21 11:13 | case13 | steady | 1682 | 60min @ 1682/h | ~3.3 | ~38 | 57386 | 0.0% | 434 | 84.2 | 15.57 | 7,743 | 3.13 |
| [`2026-10-21T06-58-37Z-media-hour-m6g.xlarge-c2a0e76`](run-log-detail.md#2026-10-21t06-58-37z-media-hour-m6gxlarge-c2a0e76) | 2026-10-21 12:28 | media-hour-m6g.xlarge | steady | 1500 | 60min @ 1500/h | ~5.0 | ~162 | 415082 | 0.0% | 503 | 1878.4 | 49.43 | 11,542 | 5.04 |

Per-run settings and environment are in [`run-log-detail.md`](run-log-detail.md), linked from each run id in the table.

## Runs that are not measurements

Kept rather than deleted — these are the evidence for a finding of their own — but out of the table above, because a row beside comparable runs reads as comparable:

| run | date (IST) | arrival window | rps | p95 ms | why it is not a measurement |
|---|---|---|---|---|---|
| [`2026-10-05T11-37-03Z-case1-burst60-d9eac3e`](run-log-detail.md#2026-10-05t11-37-03z-case1-burst60-d9eac3e) | 2026-10-05 17:07 | 60s | 18.43 | 25635 | started 2 minutes 49 seconds after the app server's JVM, which costs roughly two thirds of throughput |
| [`2026-10-05T11-41-10Z-case1-burst15-d9eac3e`](run-log-detail.md#2026-10-05t11-41-10z-case1-burst15-d9eac3e) | 2026-10-05 17:11 | 15s | 30.94 | 14214 | started 6 minutes 56 seconds after the app server's JVM, which costs roughly two thirds of throughput |
| [`2026-10-06T04-55-47Z-case1-burst75-e7a130d`](run-log-detail.md#2026-10-06t04-55-47z-case1-burst75-e7a130d) | 2026-10-06 10:25 | 75s | 39.48 | 402 | the database credential had rotated and the app server held the old one, so every new pooled connection failed with HTTP 500 |
| [`2026-10-07T08-38-32Z-case4-eb5e4b3`](run-log-detail.md#2026-10-07t08-38-32z-case4-eb5e4b3) | 2026-10-07 14:08 | 240min @ 47/h | 0.22 | 287 | the feeder listed all 501 field workers before the first supervisor at row 502, and `circular()` reached only 187 rows in four hours, so this sampled one role and re-measured case 2 rather than case 4's mix — 60.8 s mean and 10,838 records against case 2's 60.8 s and 10,831, serverMs 6% in both. Case 4 needs re-running against the proportionally ordered feeder |
| [`2026-10-08T11-32-36Z-case5-d484f18`](run-log-detail.md#2026-10-08t11-32-36z-case5-d484f18) | 2026-10-08 17:02 | — | — | — | killed ~40s after launch and never reached archiveRun, so it has no metadata and no summary; superseded by the 17:34 run |

Each carries a `provenance-correction.json` in its own prefix with the evidence, the cause and what it was recorded as. The runs' own `run-metadata.json` is left exactly as written.

## Caveats on the runs above

Listed rather than left blank, because a blank column reads as a measurement and not as a missing one:

- `2026-10-05T08-38-47Z-case1-f76d110` — harness commit was recorded as `unknown`; **corrected to `f76d110`** by `provenance-correction.json` in the same prefix. The run's own metadata is left as written — see that file for the basis and the cause
- `2026-10-05T12-01-03Z-case1-burst60-warm-d9eac3e` — recorded no `AUTOVACUUM` — so it cannot be compared with a run that differs in it
- `2026-10-05T12-02-47Z-case1-burst15-warm-d9eac3e` — recorded no `AUTOVACUUM` — so it cannot be compared with a run that differs in it
- `2026-10-12T02-07-36Z-case9-12a-cf77819` — **failed 0.54% of requests against its own `MAX_FAILED_PERCENT` gate of 0.05%** — Gatling asserted and failed at the time. Read its throughput and latency as a run that broke, not as a point on a curve
- `2026-10-12T04-55-23Z-case9-12b-rerun-cf77819` — **failed 0.24% of requests against its own `MAX_FAILED_PERCENT` gate of 0.05%** — Gatling asserted and failed at the time. Read its throughput and latency as a run that broke, not as a point on a curve
- `2026-10-15T05-33-35Z-case13-c2a0e76` — **failed 1.22% of requests against its own `MAX_FAILED_PERCENT` gate of 0.05%** — Gatling asserted and failed at the time. Read its throughput and latency as a run that broke, not as a point on a curve
- `2026-10-21T04-10-50Z-case13-m6g.large-c2a0e76` — **failed 0.91% of requests against its own `MAX_FAILED_PERCENT` gate of 0.05%** — Gatling asserted and failed at the time. Read its throughput and latency as a run that broke, not as a point on a curve
