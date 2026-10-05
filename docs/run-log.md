# Run log

Generated from `s3://avni-loadtest-936573213727/artefacts/` by `tools/update-run-log.sh` (`make run_log`) — last refreshed 2026-10-05 09:07 UTC.

**Do not edit by hand.** Rewritten wholesale on every run of that script. The artefacts prefix is append-only by IAM, so S3 is the source of truth and this is a view of it. An edit here is lost on the next refresh; a run missing from this table means its upload did not happen, not that the log is stale.

Artefacts are **not** copied into the repo. Each run directory holds Gatling's `simulation.log`, the HTML report and `run-metadata.json`, plus the environment context captured at run time — `parity-report.md`, `pg_settings.csv`, `stats.json`. Those are what make a number interpretable once the environment that produced it has been destroyed.

| run | date | scenario | profile | users | mode | requests | failed | p95 ms | rps |
|---|---|---|---|---|---|---|---|---|---|
| [`2026-10-05T08-38-47Z-case1-f76d110`](s3://avni-loadtest-936573213727/artefacts/2026-10-05T08-38-47Z-case1-f76d110/) | 2026-10-05 08:38 | case1 | burst | 100 | full | 4300 | 0.0% | 202 | 4.77 |

## Caveats on the runs above

Listed rather than left blank, because a blank column reads as a measurement and not as a missing one:

- `2026-10-05T08-38-47Z-case1-f76d110` — harness commit was recorded as `unknown`; **corrected to `f76d110`** by `provenance-correction.json` in the same prefix. The run's own metadata is left as written — see that file for the basis and the cause

## Detail

### `2026-10-05T08-38-47Z-case1-f76d110`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T08-38-47Z-case1-f76d110/`

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 19 / 202 / 297 / 716 |
| mean ms | 45 |
| mean throughput rps | 4.77 |
| harness commit | `f76d1103e56c8da0078b4d3aa2097a00acaf8c14` — **corrected**, the run recorded `unknown` |
| tree dirty | False — **corrected**, the run recorded `True` |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.69 / 1.12 |
| est. sync overhead s | 0.12 |
| injection | profile burst, 100 users, burst 15 min, ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| cache policy | warm-incidental-no-reset |
| autovacuum | on |
