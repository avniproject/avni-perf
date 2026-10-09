# Run log

Generated from `s3://avni-loadtest-936573213727/artefacts/` by `tools/update-run-log.sh` (`make run_log`) — last refreshed 2026-10-09 12:17 IST.

**Do not edit by hand.** Rewritten wholesale on every run of that script. The artefacts prefix is append-only by IAM, so S3 is the source of truth and this is a view of it. An edit here is lost on the next refresh; a run missing from this table means its upload did not happen, not that the log is stale.

**Times are IST; run ids are UTC.** The id is the identifier and keeps the `Z` it was minted with — `...T11-37-03Z...` is the 17:07 row. Dates are converted with the time, so anything before 18:30 UTC lands on the same IST day but a late-evening run will not.

Artefacts are **not** copied into the repo. Each run directory holds Gatling's `simulation.log`, the HTML report and `run-metadata.json`, plus the environment context captured at run time — `parity-report.md`, `pg_settings.csv`, `stats.json` — and `sync-durations.csv`, one row per completed sync. Those are what make a number interpretable once the environment that produced it has been destroyed.

Findings drawn from these runs are written up separately, by hand, in `findings-case1.md` and its siblings — this file is the index, not the analysis.

| run | date (IST) | scenario | profile | users | arrival window | ~requests in flight | ~devices in flight | requests | failed | p95 ms | full sync p95 s | rps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [`2026-10-05T08-38-47Z-case1-f76d110`](run-log-detail.md#2026-10-05t08-38-47z-case1-f76d110) | 2026-10-05 14:08 | case1 | burst | 100 | 15min | ~0.2 | — | 4300 | 0.0% | 202 | — | 4.77 |
| [`2026-10-05T09-43-14Z-case1-e47afd5`](run-log-detail.md#2026-10-05t09-43-14z-case1-e47afd5) | 2026-10-05 15:13 | case1 | burst | 100 | 60s | ~22 | — | 4300 | 0.0% | 2242 | — | 52.44 |
| [`2026-10-05T09-53-13Z-case1-burst15-e47afd5`](run-log-detail.md#2026-10-05t09-53-13z-case1-burst15-e47afd5) | 2026-10-05 15:23 | case1 | burst | 100 | 15s | ~71 | — | 4300 | 0.0% | 6768 | — | 56.58 |
| [`2026-10-05T10-28-06Z-case1-burst90-d9eac3e`](run-log-detail.md#2026-10-05t10-28-06z-case1-burst90-d9eac3e) | 2026-10-05 15:58 | case1 | burst | 100 | 90s | ~3.2 | ~11.8 | 4300 | 0.0% | 376 | 12.4 | 43 |
| [`2026-10-05T10-30-01Z-case1-burst120-d9eac3e`](run-log-detail.md#2026-10-05t10-30-01z-case1-burst120-d9eac3e) | 2026-10-05 16:00 | case1 | burst | 100 | 120s | ~1.7 | ~8.4 | 4300 | 0.0% | 222 | 11.2 | 33.33 |
| [`2026-10-05T10-32-25Z-case1-burst180-d9eac3e`](run-log-detail.md#2026-10-05t10-32-25z-case1-burst180-d9eac3e) | 2026-10-05 16:02 | case1 | burst | 100 | 180s | ~1.0 | ~5.5 | 4300 | 0.0% | 196 | 10.7 | 22.75 |
| [`2026-10-05T12-01-03Z-case1-burst60-warm-d9eac3e`](run-log-detail.md#2026-10-05t12-01-03z-case1-burst60-warm-d9eac3e) | 2026-10-05 17:31 | case1 | burst | 100 | 60s | ~27 | ~36 | 4300 | 0.0% | 2767 | 40.2 | 50 |
| [`2026-10-05T12-02-47Z-case1-burst15-warm-d9eac3e`](run-log-detail.md#2026-10-05t12-02-47z-case1-burst15-warm-d9eac3e) | 2026-10-05 17:32 | case1 | burst | 100 | 15s | ~71 | ~80 | 4300 | 0.0% | 6741 | 64.0 | 56.58 |
| [`2026-10-06T04-40-26Z-case1-burst900-e7a130d`](run-log-detail.md#2026-10-06t04-40-26z-case1-burst900-e7a130d) | 2026-10-06 10:10 | case1 | burst | 100 | 900s | ~0.2 | ~1.2 | 4300 | 0.0% | 200 | 10.8 | 4.77 |
| [`2026-10-06T05-16-44Z-case1-burst75-e7a130d`](run-log-detail.md#2026-10-06t05-16-44z-case1-burst75-e7a130d) | 2026-10-06 10:46 | case1 | burst | 100 | 75s | ~8.8 | ~18.4 | 4300 | 0.0% | 918 | 18.4 | 49.43 |
| [`2026-10-06T05-38-32Z-case2-e7a130d`](run-log-detail.md#2026-10-06t05-38-32z-case2-e7a130d) | 2026-10-06 11:08 | case2 | steady | 500 | 240min @ 42/h | ~0.0 | ~0.7 | 2846 | 0.0% | 288 | 80.4 | 0.2 |
| [`2026-10-06T09-50-36Z-case14-4c7b807`](run-log-detail.md#2026-10-06t09-50-36z-case14-4c7b807) | 2026-10-06 15:20 | case14 | steady | 501 | 90min @ 42/h | ~0.1 | ~0.9 | 2898 | 0.0% | 272 | 80.2 | 0.54 |
| [`2026-10-07T06-15-54Z-case3-eb5e4b3`](run-log-detail.md#2026-10-07t06-15-54z-case3-eb5e4b3) | 2026-10-07 11:45 | case3 | steady | 60 | 120min @ 30/h | ~0.1 | ~1.4 | 2314 | 0.0% | 333 | 223.4 | 0.32 |
| [`2026-10-08T06-17-46Z-case4-d484f18`](run-log-detail.md#2026-10-08t06-17-46z-case4-d484f18) | 2026-10-08 11:47 | case4 | steady | 561 | 240min @ 47/h | ~0.1 | ~1.0 | 3587 | 0.0% | 322 | 223.6 | 0.25 |
| [`2026-10-08T12-04-15Z-case5-d484f18`](run-log-detail.md#2026-10-08t12-04-15z-case5-d484f18) | 2026-10-08 17:34 | case5 | steady | 1682 | 120min @ 140/h | ~0.2 | ~2.8 | 5390 | 0.0% | 329 | 223.9 | 0.74 |
| [`2026-10-08T14-05-56Z-case11-run1-d484f18`](run-log-detail.md#2026-10-08t14-05-56z-case11-run1-d484f18) | 2026-10-08 19:35 | case11 | steady | 1682 | 60min @ 1682/h | ~414 | ~435 | 143211 | 0.04% | 41912 | 3747.0 | 22.27 |
| [`2026-10-09T04-28-45Z-case11-pairA-d484f18`](run-log-detail.md#2026-10-09t04-28-45z-case11-paira-d484f18) | 2026-10-09 09:58 | case11 | steady | 550 | 60min @ 550/h | ~1.0 | ~31 | 48408 | 0.0% | 342 | 455.5 | 12.14 |
| [`2026-10-09T05-37-25Z-case11-pairB-d484f18`](run-log-detail.md#2026-10-09t05-37-25z-case11-pairb-d484f18) | 2026-10-09 11:07 | case11 | steady | 550 | 60min @ 550/h | ~1.0 | ~30 | 47456 | 0.0% | 367 | 316.2 | 11.88 |

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
