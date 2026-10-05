# Run log

Generated from `s3://avni-loadtest-936573213727/artefacts/` by `tools/update-run-log.sh` (`make run_log`) — last refreshed 2026-10-05 13:31 UTC.

**Do not edit by hand.** Rewritten wholesale on every run of that script. The artefacts prefix is append-only by IAM, so S3 is the source of truth and this is a view of it. An edit here is lost on the next refresh; a run missing from this table means its upload did not happen, not that the log is stale.

Artefacts are **not** copied into the repo. Each run directory holds Gatling's `simulation.log`, the HTML report and `run-metadata.json`, plus the environment context captured at run time — `parity-report.md`, `pg_settings.csv`, `stats.json` — and `sync-durations.csv`, one row per completed sync. Those are what make a number interpretable once the environment that produced it has been destroyed.

Findings drawn from these runs are written up separately, by hand, in `findings-case1.md` and its siblings — this file is the index, not the analysis.

| run | date | scenario | profile | users | arrival window | ~requests in flight | ~devices in flight | requests | failed | p95 ms | rps |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [`2026-10-05T08-38-47Z-case1-f76d110`](run-log-detail.md#2026-10-05t08-38-47z-case1-f76d110) | 2026-10-05 08:38 | case1 | burst | 100 | 15min | ~0.2 | — | 4300 | 0.0% | 202 | 4.77 |
| [`2026-10-05T09-43-14Z-case1-e47afd5`](run-log-detail.md#2026-10-05t09-43-14z-case1-e47afd5) | 2026-10-05 09:43 | case1 | burst | 100 | 60s | ~22 | — | 4300 | 0.0% | 2242 | 52.44 |
| [`2026-10-05T09-53-13Z-case1-burst15-e47afd5`](run-log-detail.md#2026-10-05t09-53-13z-case1-burst15-e47afd5) | 2026-10-05 09:53 | case1-burst15 | burst | 100 | 15s | ~71 | — | 4300 | 0.0% | 6768 | 56.58 |
| [`2026-10-05T10-28-06Z-case1-burst90-d9eac3e`](run-log-detail.md#2026-10-05t10-28-06z-case1-burst90-d9eac3e) | 2026-10-05 10:28 | case1-burst90 | burst | 100 | 90s | ~3.2 | ~11.8 | 4300 | 0.0% | 376 | 43 |
| [`2026-10-05T10-30-01Z-case1-burst120-d9eac3e`](run-log-detail.md#2026-10-05t10-30-01z-case1-burst120-d9eac3e) | 2026-10-05 10:30 | case1-burst120 | burst | 100 | 120s | ~1.7 | ~8.4 | 4300 | 0.0% | 222 | 33.33 |
| [`2026-10-05T10-32-25Z-case1-burst180-d9eac3e`](run-log-detail.md#2026-10-05t10-32-25z-case1-burst180-d9eac3e) | 2026-10-05 10:32 | case1-burst180 | burst | 100 | 180s | ~1.0 | ~5.5 | 4300 | 0.0% | 196 | 22.75 |
| [`2026-10-05T11-37-03Z-case1-burst60-d9eac3e`](run-log-detail.md#2026-10-05t11-37-03z-case1-burst60-d9eac3e) | 2026-10-05 11:37 | case1-burst60 | burst | 100 | 60s | ~75 | ~80 | 4183 | 0.21% | 25635 | 18.43 |
| [`2026-10-05T11-41-10Z-case1-burst15-d9eac3e`](run-log-detail.md#2026-10-05t11-41-10z-case1-burst15-d9eac3e) | 2026-10-05 11:41 | case1-burst15 | burst | 100 | 15s | ~83 | ~86 | 4300 | 0.0% | 14214 | 30.94 |
| [`2026-10-05T12-01-03Z-case1-burst60-warm-d9eac3e`](run-log-detail.md#2026-10-05t12-01-03z-case1-burst60-warm-d9eac3e) | 2026-10-05 12:01 | case1-burst60-warm | burst | 100 | 60s | ~27 | ~36 | 4300 | 0.0% | 2767 | 50 |
| [`2026-10-05T12-02-47Z-case1-burst15-warm-d9eac3e`](run-log-detail.md#2026-10-05t12-02-47z-case1-burst15-warm-d9eac3e) | 2026-10-05 12:02 | case1-burst15-warm | burst | 100 | 15s | ~71 | ~80 | 4300 | 0.0% | 6741 | 56.58 |

Per-run settings and environment are in [`run-log-detail.md`](run-log-detail.md), linked from each run id in the table.

## Caveats on the runs above

Listed rather than left blank, because a blank column reads as a measurement and not as a missing one:

- `2026-10-05T08-38-47Z-case1-f76d110` — harness commit was recorded as `unknown`; **corrected to `f76d110`** by `provenance-correction.json` in the same prefix. The run's own metadata is left as written — see that file for the basis and the cause
- `2026-10-05T11-37-03Z-case1-burst60-d9eac3e` — **failed 0.21% of requests against its own `MAX_FAILED_PERCENT` gate of 0.05%** — Gatling asserted and failed at the time. Read its throughput and latency as a run that broke, not as a point on a curve
- `2026-10-05T11-37-03Z-case1-burst60-d9eac3e` — only **91 of 100 devices completed a sync** — the per-sync figures describe the ones that finished, and the request count is short of a full cohort by the rest
- `2026-10-05T12-01-03Z-case1-burst60-warm-d9eac3e` — recorded no `AUTOVACUUM` — so it cannot be compared with a run that differs in it
- `2026-10-05T12-02-47Z-case1-burst15-warm-d9eac3e` — recorded no `AUTOVACUUM` — so it cannot be compared with a run that differs in it
