# Run log — detail

Generated from `s3://avni-loadtest-936573213727/artefacts/` by `tools/update-run-log.sh` (`make run_log`) — last refreshed 2026-10-21 12:20 IST.

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
| app CPU seconds | 124 |
| harness commit | `f76d1103e56c8da0078b4d3aa2097a00acaf8c14` — **corrected**, the run recorded `unknown` |
| tree dirty | False — **corrected**, the run recorded `True` |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.69 / 1.12 |
| est. sync overhead s | 0.12 |
| injection | profile burst, 100 users arriving over 15min, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| app CPU seconds | 124 |
| harness commit | e47afd506861852fe2d7372627434f45cfbce95c (run id says `e47afd5`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.26 / 0.51 |
| est. sync overhead s | 0.06 |
| injection | profile burst, 100 users arriving over 60s, ~22 requests in flight (rps x mean), ramp 2000 s |
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
| app CPU seconds | 124 |
| harness commit | e47afd506861852fe2d7372627434f45cfbce95c (run id says `e47afd5`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.23 / 0.27 |
| est. sync overhead s | 0.03 |
| injection | profile burst, 100 users arriving over 15s, ~71 requests in flight (rps x mean), ramp 2000 s |
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
| app CPU seconds | 124 |
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.23 / 0.34 |
| est. sync overhead s | 0.04 |
| injection | profile burst, 100 users arriving over 90s, ~3.2 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 11.8 / 11.8 / 12.4 (100 syncs) |
| full syncs p50 / p95 s | 11.8 / 12.4 (100 of 100, back-calculated from SYNC_MODE=full) |
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
| app CPU seconds | 124 |
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.26 / 0.28 |
| est. sync overhead s | 0.03 |
| injection | profile burst, 100 users arriving over 120s, ~1.7 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 10.8 / 10.8 / 11.2 (100 syncs) |
| full syncs p50 / p95 s | 10.8 / 11.2 (100 of 100, back-calculated from SYNC_MODE=full) |
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
| app CPU seconds | 124 |
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.58 / 0.66 |
| est. sync overhead s | 0.07 |
| injection | profile burst, 100 users arriving over 180s, ~1.0 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 10.4 / 10.5 / 10.7 (100 syncs) |
| full syncs p50 / p95 s | 10.4 / 10.7 (100 of 100, back-calculated from SYNC_MODE=full) |
| cache policy | warm-incidental-no-reset |
| autovacuum | on |

## `2026-10-05T11-37-03Z-case1-burst60-d9eac3e`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T11-37-03Z-case1-burst60-d9eac3e/`

| | |
|---|---|
| requests (ok) | 4183 |
| failed | 9 (0.21%) |
| response time p50 / p95 / p99 / max ms | 1143 / 25635 / 34970 / 51788 |
| mean ms | 4083 |
| mean throughput rps | 18.43 |
| app CPU seconds | 124 |
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.24 / 0.3 |
| est. sync overhead s | 0.03 |
| injection | profile burst, 100 users arriving over 60s, ~75 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 186.7 / 182.3 / 199.7 (91 syncs) |
| full syncs p50 / p95 s | 186.7 / 199.7 (91 of 91, back-calculated from SYNC_MODE=full) |
| cache policy | warm-incidental-no-reset |
| autovacuum | on |

## `2026-10-05T11-41-10Z-case1-burst15-d9eac3e`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T11-41-10Z-case1-burst15-d9eac3e/`

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 1020 / 14214 / 20225 / 27018 |
| mean ms | 2693 |
| mean throughput rps | 30.94 |
| app CPU seconds | 124 |
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.58 / 0.62 |
| est. sync overhead s | 0.07 |
| injection | profile burst, 100 users arriving over 15s, ~83 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 120.6 / 120.2 / 129.8 (100 syncs) |
| full syncs p50 / p95 s | 120.6 / 129.8 (100 of 100, back-calculated from SYNC_MODE=full) |
| cache policy | warm-incidental-no-reset |
| autovacuum | on |

## `2026-10-05T12-01-03Z-case1-burst60-warm-d9eac3e`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T12-01-03Z-case1-burst60-warm-d9eac3e/`

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 207 / 2767 / 5326 / 6728 |
| mean ms | 539 |
| mean throughput rps | 50 |
| app CPU seconds | 124 |
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.27 / 0.29 |
| est. sync overhead s | 0.03 |
| injection | profile burst, 100 users arriving over 60s, ~27 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 31.8 / 31.0 / 40.2 (100 syncs) |
| full syncs p50 / p95 s | 31.8 / 40.2 (100 of 100, back-calculated from SYNC_MODE=full) |
| cache policy | warm-jvm-30min-after-two-saturating-runs |
| autovacuum | unrecorded |

## `2026-10-05T12-02-47Z-case1-burst15-warm-d9eac3e`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T12-02-47Z-case1-burst15-warm-d9eac3e/`

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 499 / 6741 / 9834 / 17959 |
| mean ms | 1253 |
| mean throughput rps | 56.58 |
| app CPU seconds | 124 |
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.59 / 0.66 |
| est. sync overhead s | 0.07 |
| injection | profile burst, 100 users arriving over 15s, ~71 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 61.4 / 60.9 / 64.0 (100 syncs) |
| full syncs p50 / p95 s | 61.4 / 64.0 (100 of 100, back-calculated from SYNC_MODE=full) |
| cache policy | warm-jvm-30min-after-two-saturating-runs |
| autovacuum | unrecorded |

## `2026-10-06T04-40-26Z-case1-burst900-e7a130d`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-06T04-40-26Z-case1-burst900-e7a130d/`

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 24 / 200 / 363 / 705 |
| mean ms | 48 |
| mean throughput rps | 4.77 |
| app CPU seconds | 124 |
| harness commit | e7a130d9d13507142b1d9ec1a8c34e894c79dc72 (run id says `e7a130d`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.38 / 0.4 |
| est. sync overhead s | 0.04 |
| injection | profile burst, 100 users arriving over 900s, ~0.2 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 10.6 / 10.7 / 10.8 (100 syncs) |
| full syncs p50 / p95 s | 10.6 / 10.8 (100 of 100, recorded) |
| cache policy | warm-idle-25min-since-discarded-warmup |
| autovacuum | on |

## `2026-10-06T04-55-47Z-case1-burst75-e7a130d`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-06T04-55-47Z-case1-burst75-e7a130d/`

| | |
|---|---|
| requests (ok) | 3356 |
| failed | 40 (1.18%) |
| response time p50 / p95 / p99 / max ms | 34 / 402 / 750 / 1118 |
| mean ms | 83 |
| mean throughput rps | 39.48 |
| app CPU seconds | 124 |
| harness commit | e7a130d9d13507142b1d9ec1a8c34e894c79dc72 (run id says `e7a130d`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.71 / 4.08 |
| est. sync overhead s | 0.45 |
| injection | profile burst, 100 users arriving over 75s, ~3.3 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 12.2 / 11.9 / 12.9 (62 syncs) |
| full syncs p50 / p95 s | 12.2 / 12.9 (62 of 62, recorded) |
| cache policy | warm-after-900s-run |
| autovacuum | on |

## `2026-10-06T05-16-44Z-case1-burst75-e7a130d`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-06T05-16-44Z-case1-burst75-e7a130d/`

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 74 / 918 / 1426 / 1919 |
| mean ms | 178 |
| mean throughput rps | 49.43 |
| app CPU seconds | 124 |
| harness commit | e7a130d9d13507142b1d9ec1a8c34e894c79dc72 (run id says `e7a130d`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.7 / 0.76 |
| est. sync overhead s | 0.08 |
| injection | profile burst, 100 users arriving over 75s, ~8.8 requests in flight (rps x mean), ramp 2000 s |
| sync | mode full, feeder case1-users.csv (100 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 16.4 / 16.0 / 18.4 (100 syncs) |
| full syncs p50 / p95 s | 16.4 / 18.4 (100 of 100, recorded) |
| cache policy | warm-after-discarded-warmup |
| autovacuum | on |

## `2026-10-06T05-38-32Z-case2-e7a130d`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-06T05-38-32Z-case2-e7a130d/`

| | |
|---|---|
| requests (ok) | 2846 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 251 / 288 / 533 / 611 |
| mean ms | 209 |
| mean throughput rps | 0.2 |
| app CPU seconds | 124 |
| harness commit | e7a130d9d13507142b1d9ec1a8c34e894c79dc72 (run id says `e7a130d`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | states-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.72 / 0.74 |
| est. sync overhead s | 0.08 |
| injection | profile steady, 500 users arriving over 240min @ 42/h, ~0.0 requests in flight (rps x mean), ramp 10020 s |
| sync | mode realistic, feeder case2-users.csv (501 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 60.7 / 61.0 / 62.0 (167 syncs) |
| full syncs p50 / p95 s | 80.4 / 80.4 (2 of 167, recorded) |
| cache policy | warm-after-case1-75s-run |
| autovacuum | on |

## `2026-10-06T09-50-36Z-case14-4c7b807`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-06T09-50-36Z-case14-4c7b807/`

| | |
|---|---|
| requests (ok) | 2898 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 44 / 272 / 311 / 772 |
| mean ms | 117 |
| mean throughput rps | 0.54 |
| app CPU seconds | 124 |
| harness commit | 4c7b807737e887f2d33311086d00a1a787018dd8 (run id says `4c7b807`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | states-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.71 / 0.76 |
| est. sync overhead s | 0.08 |
| injection | profile steady, 501 users arriving over 90min @ 42/h, ~0.1 requests in flight (rps x mean), ramp 10020 s |
| sync | mode full, feeder case2-users-states.csv (501 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 80.1 / 80.1 / 80.2 (63 syncs) |
| full syncs p50 / p95 s | 80.1 / 80.2 (63 of 63, recorded) |
| cache policy | warm-after-case2 |
| autovacuum | on |

## `2026-10-07T06-15-54Z-case3-eb5e4b3`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-07T06-15-54Z-case3-eb5e4b3/`

| | |
|---|---|
| requests (ok) | 2314 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 294 / 333 / 376 / 428 |
| mean ms | 255 |
| mean throughput rps | 0.32 |
| app CPU seconds | 124 |
| harness commit | eb5e4b3596e90d1e48bae50186dc4bace0d4ea8c (run id says `eb5e4b3`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.38 / 0.4 |
| est. sync overhead s | 0.04 |
| injection | profile steady, 60 users arriving over 120min @ 30/h, ~0.1 requests in flight (rps x mean), ramp 1200 s |
| sync | mode realistic, feeder case3-users-pilot.csv (60 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 182.0 / 169.7 / 183.5 (60 syncs) |
| full syncs p50 / p95 s | 223.4 / 223.4 (1 of 60, recorded) |
| cache policy | warm-after-discarded-warmup-15min-idle |
| autovacuum | on |

## `2026-10-07T08-38-32Z-case4-eb5e4b3`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-07T08-38-32Z-case4-eb5e4b3/`

| | |
|---|---|
| requests (ok) | 3107 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 259 / 287 / 301 / 623 |
| mean ms | 212 |
| mean throughput rps | 0.22 |
| app CPU seconds | 124 |
| harness commit | eb5e4b3596e90d1e48bae50186dc4bace0d4ea8c (run id says `eb5e4b3`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.7 / 0.75 |
| est. sync overhead s | 0.08 |
| injection | profile steady, 561 users arriving over 240min @ 47/h, ~0.0 requests in flight (rps x mean), ramp 11220 s |
| sync | mode realistic, feeder case4-users-pilot.csv (561 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 60.6 / 60.8 / 61.3 (187 syncs) |
| full syncs p50 / p95 s | 80.2 / 80.2 (1 of 187, recorded) |
| cache policy | warm-after-case3 |
| autovacuum | on |

## `2026-10-08T06-17-46Z-case4-d484f18`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-08T06-17-46Z-case4-d484f18/`

| | |
|---|---|
| requests (ok) | 3587 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 265 / 322 / 387 / 532 |
| mean ms | 229 |
| mean throughput rps | 0.25 |
| app CPU seconds | 124 |
| harness commit | d484f18e1c8666dee40f981d162390061e3c91f6 (run id says `d484f18`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.6 / 0.68 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 561 users arriving over 240min @ 47/h, ~0.1 requests in flight (rps x mean), ramp 11220 s |
| sync | mode realistic, feeder case4-users-pilot.csv (561 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 60.6 / 74.0 / 182.1 (187 syncs) |
| full syncs p50 / p95 s | 223.6 / 223.6 (2 of 187, recorded) |
| cache policy | warm-after-discarded-warmup |
| autovacuum | on |

## `2026-10-08T11-32-36Z-case5-d484f18`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-08T11-32-36Z-case5-d484f18/`

| | |
|---|---|

## `2026-10-08T12-04-15Z-case5-d484f18`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-08T12-04-15Z-case5-d484f18/`

| | |
|---|---|
| requests (ok) | 5390 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 268 / 329 / 367 / 523 |
| mean ms | 228 |
| mean throughput rps | 0.74 |
| app CPU seconds | 124 |
| harness commit | d484f18e1c8666dee40f981d162390061e3c91f6 (run id says `d484f18`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.61 / 0.66 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 1682 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 60.6 / 72.9 / 182.2 (280 syncs) |
| full syncs p50 / p95 s | 223.9 / 223.9 (2 of 280, recorded) |
| cache policy | warm-after-discarded-warmup |
| autovacuum | on |

## `2026-10-08T14-05-56Z-case11-run1-d484f18`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-08T14-05-56Z-case11-run1-d484f18/`

| | |
|---|---|
| requests (ok) | 143211 |
| failed | 53 (0.04%) |
| response time p50 / p95 / p99 / max ms | 18771 / 41912 / 51544 / 59909 |
| mean ms | 18568 |
| mean throughput rps | 22.27 |
| app CPU seconds | 124 |
| harness commit | d484f18e1c8666dee40f981d162390061e3c91f6 (run id says `d484f18`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.6 / 0.64 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~414 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / False |
| sync duration p50 / mean / p95 s | 1639.5 / 1717.0 / 3344.9 (1630 syncs) |
| full syncs p50 / p95 s | 2327.5 / 3747.0 (16 of 1630, recorded) |
| cache policy | warm-after-case5 |
| autovacuum | on |

## `2026-10-09T04-28-45Z-case11-pairA-d484f18`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T04-28-45Z-case11-pairA-d484f18/`

| | |
|---|---|
| requests (ok) | 48408 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 28 / 342 / 1222 / 2469 |
| mean ms | 83 |
| mean throughput rps | 12.14 |
| app CPU seconds | 124 |
| harness commit | d484f18e1c8666dee40f981d162390061e3c91f6 (run id says `d484f18`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.25 / 0.3 |
| est. sync overhead s | 0.03 |
| injection | profile steady, 550 users arriving over 60min @ 550/h, ~1.0 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / False |
| sync duration p50 / mean / p95 s | 196.7 / 225.1 / 416.0 (550 syncs) |
| full syncs p50 / p95 s | 165.3 / 455.5 (7 of 550, recorded) |
| cache policy | warm-from-reload |
| autovacuum | on |

## `2026-10-09T05-37-25Z-case11-pairB-d484f18`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T05-37-25Z-case11-pairB-d484f18/`

| | |
|---|---|
| requests (ok) | 47456 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 28 / 367 / 710 / 916 |
| mean ms | 84 |
| mean throughput rps | 11.88 |
| app CPU seconds | 124 |
| harness commit | d484f18e1c8666dee40f981d162390061e3c91f6 (run id says `d484f18`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.65 / 0.74 |
| est. sync overhead s | 0.08 |
| injection | profile steady, 550 users arriving over 60min @ 550/h, ~1.0 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / False |
| sync duration p50 / mean / p95 s | 198.1 / 220.8 / 395.6 (550 syncs) |
| full syncs p50 / p95 s | 255.7 / 316.2 (4 of 550, recorded) |
| cache policy | warm-from-previous-run |
| autovacuum | on |

## `2026-10-09T06-55-55Z-case11-pairC-cf77819`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T06-55-55Z-case11-pairC-cf77819/`

| | |
|---|---|
| requests (ok) | 46489 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 28 / 327 / 527 / 1137 |
| mean ms | 81 |
| mean throughput rps | 12.13 |
| app CPU seconds | 124 |
| harness commit | cf778198f71abde6af399aa036c9cf7d2797da02 (run id says `cf77819`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.59 / 0.68 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 550 users arriving over 60min @ 550/h, ~1.0 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / False |
| sync duration p50 / mean / p95 s | 195.1 / 215.6 / 367.7 (550 syncs) |
| full syncs p50 / p95 s | 243.0 / 389.8 (8 of 550, recorded) |
| cache policy | warm-from-previous-run |
| autovacuum | on |

## `2026-10-09T08-00-22Z-case11-pairD-cf77819`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T08-00-22Z-case11-pairD-cf77819/`

| | |
|---|---|
| requests (ok) | 47544 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 28 / 364 / 685 / 2144 |
| mean ms | 90 |
| mean throughput rps | 11.88 |
| app CPU seconds | 124 |
| harness commit | cf778198f71abde6af399aa036c9cf7d2797da02 (run id says `cf77819`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.24 / 0.25 |
| est. sync overhead s | 0.03 |
| injection | profile steady, 550 users arriving over 60min @ 550/h, ~1.1 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / False |
| sync duration p50 / mean / p95 s | 199.3 / 222.9 / 397.2 (550 syncs) |
| full syncs p50 / p95 s | 300.7 / 300.7 (2 of 550, recorded) |
| cache policy | warm-from-previous-run |
| autovacuum | on |

## `2026-10-09T09-17-04Z-case11-pairE-cf77819`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T09-17-04Z-case11-pairE-cf77819/`

| | |
|---|---|
| requests (ok) | 12960 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 284 / 424 / 610 / 1369 |
| mean ms | 253 |
| mean throughput rps | 3.45 |
| app CPU seconds | 124 |
| harness commit | cf778198f71abde6af399aa036c9cf7d2797da02 (run id says `cf77819`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.24 / 0.34 |
| est. sync overhead s | 0.04 |
| injection | profile steady, 550 users arriving over 60min @ 550/h, ~0.9 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 73.5 / 87.3 / 218.6 (550 syncs) |
| full syncs p50 / p95 s | 83.4 / 227.2 (3 of 550, recorded) |
| cache policy | warm-from-previous-run |
| autovacuum | on |

## `2026-10-09T11-27-35Z-case11-burst15-400-cf77819`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T11-27-35Z-case11-burst15-400-cf77819/`

| | |
|---|---|
| requests (ok) | 35842 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 2082 / 19610 / 23226 / 30570 |
| mean ms | 4294 |
| mean throughput rps | 18.47 |
| app CPU seconds | 124 |
| harness commit | cf778198f71abde6af399aa036c9cf7d2797da02 (run id says `cf77819`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.55 / 0.61 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 400 users arriving over 15min @ 1600/h, ~79 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / False |
| sync duration p50 / mean / p95 s | 593.2 / 598.0 / 1111.9 (400 syncs) |
| full syncs p50 / p95 s | 888.0 / 888.0 (2 of 400, recorded) |
| cache policy | warm-from-warmup |
| autovacuum | on |

## `2026-10-09T14-21-29Z-case10-soak-cf77819`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T14-21-29Z-case10-soak-cf77819/`

| | |
|---|---|
| requests (ok) | 50098 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 29 / 290 / 325 / 2103 |
| mean ms | 72 |
| mean throughput rps | 1.16 |
| app CPU seconds | 124 |
| harness commit | cf778198f71abde6af399aa036c9cf7d2797da02 (run id says `cf77819`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.63 / 0.69 |
| est. sync overhead s | 0.08 |
| injection | profile steady, 561 users arriving over 720min @ 47/h, ~0.1 requests in flight (rps x mean), ramp 11220 s |
| sync | mode realistic, feeder case4-users-pilot.csv (561 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / False |
| sync duration p50 / mean / p95 s | 202.0 / 228.1 / 424.2 (561 syncs) |
| full syncs p50 / p95 s | 282.8 / 548.7 (6 of 561, recorded) |
| cache policy | warm-from-warmup |
| autovacuum | on |

## `2026-10-12T02-07-36Z-case9-12a-cf77819`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-12T02-07-36Z-case9-12a-cf77819/`

| | |
|---|---|
| requests (ok) | 21491 |
| failed | 116 (0.54%) |
| response time p50 / p95 / p99 / max ms | 5129 / 52876 / 57940 / 59992 |
| mean ms | 17151 |
| mean throughput rps | 6.23 |
| app CPU seconds | 124 |
| harness commit | cf778198f71abde6af399aa036c9cf7d2797da02 (run id says `cf77819`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.25 / 0.3 |
| est. sync overhead s | 0.03 |
| injection | profile stress, 1682 users arriving over 45min @ 200/h, ~107 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 260.1 / 360.9 / 749.7 (1084 syncs) |
| full syncs p50 / p95 s | 749.7 / 1284.2 (6 of 1084, recorded) |
| cache policy | warm-from-warmup |
| autovacuum | on |

## `2026-10-12T03-43-44Z-case9-12b-cf77819`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-12T03-43-44Z-case9-12b-cf77819/`

| | |
|---|---|
| requests (ok) | 16041 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 88 / 489 / 769 / 1384 |
| mean ms | 167 |
| mean throughput rps | 5.82 |
| app CPU seconds | 124 |
| harness commit | cf778198f71abde6af399aa036c9cf7d2797da02 (run id says `cf77819`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.25 / 0.3 |
| est. sync overhead s | 0.03 |
| injection | profile stress, 1682 users arriving over 45min @ 50/h, ~1.0 requests in flight (rps x mean), ramp 33640 s |
| sync | mode full, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 84.2 / 98.0 / 229.3 (318 syncs) |
| full syncs p50 / p95 s | 84.2 / 229.3 (318 of 318, recorded) |
| cache policy | warm-from-warmup |
| autovacuum | on |

## `2026-10-12T04-55-23Z-case9-12b-rerun-cf77819`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-12T04-55-23Z-case9-12b-rerun-cf77819/`

| | |
|---|---|
| requests (ok) | 40241 |
| failed | 98 (0.24%) |
| response time p50 / p95 / p99 / max ms | 6112 / 48514 / 54197 / 59988 |
| mean ms | 14810 |
| mean throughput rps | 11.4 |
| app CPU seconds | 124 |
| harness commit | cf778198f71abde6af399aa036c9cf7d2797da02 (run id says `cf77819`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.25 / 0.26 |
| est. sync overhead s | 0.03 |
| injection | profile stress, 1682 users arriving over 40min @ 200/h, ~169 requests in flight (rps x mean), ramp 33640 s |
| sync | mode full, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 1035.9 / 787.6 / 1450.4 (768 syncs) |
| full syncs p50 / p95 s | 1035.9 / 1450.4 (768 of 768, recorded) |
| cache policy | warm-from-previous-run |
| autovacuum | on |

## `2026-10-12T06-01-23Z-case9-12c-cf77819`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-12T06-01-23Z-case9-12c-cf77819/`

| | |
|---|---|
| requests (ok) | 102891 |
| failed | 9 (0.01%) |
| response time p50 / p95 / p99 / max ms | 8464 / 33454 / 41619 / 52693 |
| mean ms | 11470 |
| mean throughput rps | 20.46 |
| app CPU seconds | 124 |
| harness commit | cf778198f71abde6af399aa036c9cf7d2797da02 (run id says `cf77819`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.59 / 0.63 |
| est. sync overhead s | 0.07 |
| injection | profile stress, 1682 users arriving over 45min @ 200/h, ~235 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / False |
| sync duration p50 / mean / p95 s | 1067.2 / 1156.2 / 2371.6 (1191 syncs) |
| full syncs p50 / p95 s | 1343.4 / 2123.9 (11 of 1191, recorded) |
| cache policy | warm-from-previous-run |
| autovacuum | on |

## `2026-10-14T04-26-19Z-case6-cf77819`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-14T04-26-19Z-case6-cf77819/`

| | |
|---|---|
| requests (ok) | 5237 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 263 / 333 / 549 / 3730 |
| mean ms | 238 |
| mean throughput rps | 0.72 |
| app CPU seconds | 124 |
| harness commit | cf778198f71abde6af399aa036c9cf7d2797da02 (run id says `cf77819`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.57 / 0.7 |
| est. sync overhead s | 0.08 |
| injection | profile steady, 1682 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 60.6 / 72.7 / 182.4 (280 syncs) |
| full syncs p50 / p95 s | 81.9 / 81.9 (2 of 280, recorded) |
| cache policy | warm-after-discarded-warmup |
| autovacuum | on |

## `2026-10-14T09-19-33Z-case7-33396d9`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-14T09-19-33Z-case7-33396d9/`

| | |
|---|---|
| requests (ok) | 61683 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 79 / 323 / 623 / 3895 |
| mean ms | 115 |
| mean throughput rps | 8.53 |
| app CPU seconds | 124 |
| harness commit | 33396d90121f2da6f7bc38271bc08c120ac77ba2 (run id says `33396d9`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.27 / 0.45 |
| est. sync overhead s | 0.05 |
| injection | profile steady, 1682 users arriving over 120min @ 140/h, ~1.0 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / True |
| sync duration p50 / mean / p95 s | 18.8 / 29.4 / 61.5 (1864 syncs) |
| full syncs p50 / p95 s | 53.0 / 82.7 (14 of 1864, recorded) |
| cache policy | warm-from-case6 |
| autovacuum | on |

## `2026-10-15T04-01-52Z-case12-c2a0e76`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-15T04-01-52Z-case12-c2a0e76/`

| | |
|---|---|
| requests (ok) | 31409 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 498 / 1709 / 2207 / 4314 |
| mean ms | 641 |
| mean throughput rps | 8.52 |
| app CPU seconds | 124 |
| harness commit | c2a0e76417d3ac980bb476d835e9b132df7c8a92 (run id says `c2a0e76`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.21 / 0.26 |
| est. sync overhead s | 0.03 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~5.5 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 65.5 / 79.8 / 201.8 (1682 syncs) |
| full syncs p50 / p95 s | 90.2 / 254.9 (19 of 1682, recorded) |
| cache policy | warm-after-discarded-warmup |
| autovacuum | on |

## `2026-10-15T05-33-35Z-case13-c2a0e76`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-15T05-33-35Z-case13-c2a0e76/`

| | |
|---|---|
| requests (ok) | 51727 |
| failed | 640 (1.22%) |
| response time p50 / p95 / p99 / max ms | 37484 / 55919 / 58692 / 59998 |
| mean ms | 32170 |
| mean throughput rps | 12.06 |
| app CPU seconds | 124 |
| harness commit | c2a0e76417d3ac980bb476d835e9b132df7c8a92 (run id says `c2a0e76`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.23 / 0.27 |
| est. sync overhead s | 0.03 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~388 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / True |
| sync duration p50 / mean / p95 s | 767.5 / 732.2 / 1414.3 (1834 syncs) |
| full syncs p50 / p95 s | 965.1 / 2031.6 (19 of 1834, recorded) |
| cache policy | warm-from-case12 |
| autovacuum | on |

## `2026-10-15T09-47-54Z-case8-day60-c2a0e76`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-15T09-47-54Z-case8-day60-c2a0e76/`

| | |
|---|---|
| requests (ok) | 1504 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 103 / 263 / 292 / 399 |
| mean ms | 111 |
| mean throughput rps | 0.21 |
| app CPU seconds | 124 |
| harness commit | c2a0e76417d3ac980bb476d835e9b132df7c8a92 (run id says `c2a0e76`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-60 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.56 / 0.59 |
| est. sync overhead s | 0.06 |
| injection | profile steady, 561 users arriving over 120min @ 47/h, ~0.0 requests in flight (rps x mean), ramp 11220 s |
| sync | mode realistic, feeder case4-users-pilot.csv (561 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 21.4 / 25.5 / 60.6 (94 syncs) |
| full syncs | none — `SYNC_MODE=realistic` produced no sync that pulled from 1900 |
| cache policy | warm-jvm-pristine-indexes |
| autovacuum | on |

## `2026-10-16T04-54-41Z-case8-day-120-c2a0e76`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-16T04-54-41Z-case8-day-120-c2a0e76/`

| | |
|---|---|
| requests (ok) | 1624 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 184 / 302 / 341 / 573 |
| mean ms | 177 |
| mean throughput rps | 0.23 |
| app CPU seconds | 124 |
| harness commit | c2a0e76417d3ac980bb476d835e9b132df7c8a92 (run id says `c2a0e76`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-120 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.26 / 0.35 |
| est. sync overhead s | 0.04 |
| injection | profile steady, 561 users arriving over 120min @ 47/h, ~0.0 requests in flight (rps x mean), ramp 11220 s |
| sync | mode realistic, feeder case4-users-pilot.csv (561 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 41.0 / 49.6 / 121.3 (94 syncs) |
| full syncs | none — `SYNC_MODE=realistic` produced no sync that pulled from 1900 |
| cache policy | warm-after-discarded-warmup |
| autovacuum | on |

## `2026-10-16T09-06-38Z-case8-day-365-c2a0e76`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-16T09-06-38Z-case8-day-365-c2a0e76/`

| | |
|---|---|
| requests (ok) | 3112 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 271 / 337 / 831 / 1416 |
| mean ms | 257 |
| mean throughput rps | 0.43 |
| app CPU seconds | 124 |
| harness commit | c2a0e76417d3ac980bb476d835e9b132df7c8a92 (run id says `c2a0e76`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-365 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.56 / 0.59 |
| est. sync overhead s | 0.06 |
| injection | profile steady, 561 users arriving over 120min @ 47/h, ~0.1 requests in flight (rps x mean), ramp 11220 s |
| sync | mode realistic, feeder case4-users-pilot.csv (561 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 122.5 / 148.9 / 369.6 (94 syncs) |
| full syncs | none — `SYNC_MODE=realistic` produced no sync that pulled from 1900 |
| cache policy | warm-after-discarded-warmup |
| autovacuum | on |

## `2026-10-19T05-06-40Z-case3-span20-c2a0e76`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-19T05-06-40Z-case3-span20-c2a0e76/`

| | |
|---|---|
| requests (ok) | 5053 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 327 / 357 / 388 / 588 |
| mean ms | 294 |
| mean throughput rps | 0.67 |
| app CPU seconds | 124 |
| harness commit | c2a0e76417d3ac980bb476d835e9b132df7c8a92 (run id says `c2a0e76`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180-span20 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.6 / 0.68 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 25 users arriving over 120min @ 30/h, ~0.2 requests in flight (rps x mean), ramp 500 s |
| sync | mode realistic, feeder case3-users-span20.csv (25 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 425.8 / 409.6 / 426.3 (60 syncs) |
| full syncs | none — `SYNC_MODE=realistic` produced no sync that pulled from 1900 |
| cache policy | warm-after-discarded-warmup |
| autovacuum | on |

## `2026-10-19T07-14-41Z-case4-span20-c2a0e76`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-19T07-14-41Z-case4-span20-c2a0e76/`

| | |
|---|---|
| requests (ok) | 3436 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 263 / 336 / 360 / 536 |
| mean ms | 232 |
| mean throughput rps | 0.24 |
| app CPU seconds | 124 |
| harness commit | c2a0e76417d3ac980bb476d835e9b132df7c8a92 (run id says `c2a0e76`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180-span20 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.24 / 0.33 |
| est. sync overhead s | 0.04 |
| injection | profile steady, 526 users arriving over 240min @ 44/h, ~0.1 requests in flight (rps x mean), ramp 10520 s |
| sync | mode realistic, feeder case4-users-span20.csv (526 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 60.5 / 77.5 / 80.5 (175 syncs) |
| full syncs p50 / p95 s | 80.5 / 80.5 (2 of 175, recorded) |
| cache policy | warm-after-case3-span20 |
| autovacuum | on |

## `2026-10-19T11-15-25Z-case5-span20-c2a0e76`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-19T11-15-25Z-case5-span20-c2a0e76/`

| | |
|---|---|
| requests (ok) | 5120 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 267 / 348 / 379 / 1660 |
| mean ms | 238 |
| mean throughput rps | 0.68 |
| app CPU seconds | 124 |
| harness commit | c2a0e76417d3ac980bb476d835e9b132df7c8a92 (run id says `c2a0e76`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180-span20 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.25 / 0.48 |
| est. sync overhead s | 0.05 |
| injection | profile steady, 1580 users arriving over 120min @ 132/h, ~0.2 requests in flight (rps x mean), ramp 31600 s |
| sync | mode realistic, feeder case5-users-span20.csv (1580 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 60.6 / 75.9 / 80.4 (263 syncs) |
| full syncs p50 / p95 s | 80.7 / 80.9 (4 of 263, recorded) |
| cache policy | warm-after-case4-span20 |
| autovacuum | on |

## `2026-10-21T04-10-50Z-case13-m6g.large-c2a0e76`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-21T04-10-50Z-case13-m6g.large-c2a0e76/`

| | |
|---|---|
| requests (ok) | 50848 |
| failed | 467 (0.91%) |
| response time p50 / p95 / p99 / max ms | 38689 / 56293 / 58755 / 60001 |
| mean ms | 33299 |
| mean throughput rps | 11.94 |
| app CPU seconds | 124 |
| harness commit | c2a0e76417d3ac980bb476d835e9b132df7c8a92 (run id says `c2a0e76`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.68 / 0.75 |
| est. sync overhead s | 0.08 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~398 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / True |
| sync duration p50 / mean / p95 s | 803.9 / 762.4 / 1397.6 (2007 syncs) |
| full syncs p50 / p95 s | 1124.3 / 2082.5 (18 of 2007, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.large |
| autovacuum | on |

## `2026-10-21T05-43-20Z-case13-m6g.xlarge-c2a0e76`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-21T05-43-20Z-case13-m6g.xlarge-c2a0e76/`

| | |
|---|---|
| requests (ok) | 57386 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 169 / 434 / 615 / 5895 |
| mean ms | 215 |
| mean throughput rps | 15.57 |
| app CPU seconds | 124 |
| harness commit | c2a0e76417d3ac980bb476d835e9b132df7c8a92 (run id says `c2a0e76`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.68 / 0.86 |
| est. sync overhead s | 0.09 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~3.3 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / True |
| sync duration p50 / mean / p95 s | 61.1 / 56.4 / 183.3 (2474 syncs) |
| full syncs p50 / p95 s | 82.7 / 84.2 (21 of 2474, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.xlarge |
| autovacuum | on |
