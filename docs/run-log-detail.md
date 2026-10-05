# Run log — detail

Generated from `s3://avni-loadtest-936573213727/artefacts/` by `tools/update-run-log.sh` (`make run_log`) — last refreshed 2026-10-05 11:24 UTC.

**Do not edit by hand.** Rewritten wholesale on every run of that script, as [`run-log.md`](run-log.md) is. That file is the index and carries the results table and any caveats; this one records what each run was configured with and what environment it met, which is what makes a number interpretable once the environment is gone.

## `2026-10-05T08-38-47Z-case1-f76d110`

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
| injection | profile burst, 100 users arriving over 180s, ~1.0 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration | not archived — predates sync-durations.csv (5 Oct 2026) |
| cache policy | warm-incidental-no-reset |
| autovacuum | on |

## `2026-10-05T09-43-14Z-case1-e47afd5`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T09-43-14Z-case1-e47afd5/`

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 152 / 2242 / 4014 / 5860 |
| mean ms | 417 |
| mean throughput rps | 52.44 |
| harness commit | e47afd506861852fe2d7372627434f45cfbce95c (run id says `e47afd5`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.26 / 0.51 |
| est. sync overhead s | 0.06 |
| injection | profile burst, 100 users arriving over 180s, ~1.0 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration | not archived — predates sync-durations.csv (5 Oct 2026) |
| cache policy | warm-incidental-no-reset |
| autovacuum | on |

## `2026-10-05T09-53-13Z-case1-burst15-e47afd5`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T09-53-13Z-case1-burst15-e47afd5/`

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 486 / 6768 / 9013 / 16195 |
| mean ms | 1254 |
| mean throughput rps | 56.58 |
| harness commit | e47afd506861852fe2d7372627434f45cfbce95c (run id says `e47afd5`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.23 / 0.27 |
| est. sync overhead s | 0.03 |
| injection | profile burst, 100 users arriving over 180s, ~1.0 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration | not archived — predates sync-durations.csv (5 Oct 2026) |
| cache policy | warm-incidental-no-reset |
| autovacuum | on |

## `2026-10-05T10-28-06Z-case1-burst90-d9eac3e`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T10-28-06Z-case1-burst90-d9eac3e/`

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 31 / 376 / 868 / 1157 |
| mean ms | 74 |
| mean throughput rps | 43 |
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.23 / 0.34 |
| est. sync overhead s | 0.04 |
| injection | profile burst, 100 users arriving over 180s, ~1.0 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 11.8 / 11.8 / 12.4 (100 syncs) |
| cache policy | warm-incidental-no-reset |
| autovacuum | on |

## `2026-10-05T10-30-01Z-case1-burst120-d9eac3e`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T10-30-01Z-case1-burst120-d9eac3e/`

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 21 / 222 / 437 / 644 |
| mean ms | 50 |
| mean throughput rps | 33.33 |
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.26 / 0.28 |
| est. sync overhead s | 0.03 |
| injection | profile burst, 100 users arriving over 180s, ~1.0 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 10.8 / 10.8 / 11.2 (100 syncs) |
| cache policy | warm-incidental-no-reset |
| autovacuum | on |

## `2026-10-05T10-32-25Z-case1-burst180-d9eac3e`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T10-32-25Z-case1-burst180-d9eac3e/`

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 19 / 196 / 330 / 597 |
| mean ms | 42 |
| mean throughput rps | 22.75 |
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.58 / 0.66 |
| est. sync overhead s | 0.07 |
| injection | profile burst, 100 users arriving over 180s, ~1.0 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 10.4 / 10.5 / 10.7 (100 syncs) |
| cache policy | warm-incidental-no-reset |
| autovacuum | on |
