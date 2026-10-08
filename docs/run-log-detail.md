# Run log — detail

Generated from `s3://avni-loadtest-936573213727/artefacts/` by `tools/update-run-log.sh` (`make run_log`) — last refreshed 2026-10-08 19:41 IST.

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
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.69 / 1.12 |
| est. sync overhead s | 0.12 |
| injection | profile burst, 100 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.26 / 0.51 |
| est. sync overhead s | 0.06 |
| injection | profile burst, 100 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.23 / 0.27 |
| est. sync overhead s | 0.03 |
| injection | profile burst, 100 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.23 / 0.34 |
| est. sync overhead s | 0.04 |
| injection | profile burst, 100 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.26 / 0.28 |
| est. sync overhead s | 0.03 |
| injection | profile burst, 100 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.58 / 0.66 |
| est. sync overhead s | 0.07 |
| injection | profile burst, 100 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.24 / 0.3 |
| est. sync overhead s | 0.03 |
| injection | profile burst, 100 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.58 / 0.62 |
| est. sync overhead s | 0.07 |
| injection | profile burst, 100 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.27 / 0.29 |
| est. sync overhead s | 0.03 |
| injection | profile burst, 100 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| harness commit | d9eac3e96fd977bec20fa837d18d6e29ab86e17b (run id says `d9eac3e`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.59 / 0.66 |
| est. sync overhead s | 0.07 |
| injection | profile burst, 100 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| harness commit | e7a130d9d13507142b1d9ec1a8c34e894c79dc72 (run id says `e7a130d`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.38 / 0.4 |
| est. sync overhead s | 0.04 |
| injection | profile burst, 100 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| harness commit | e7a130d9d13507142b1d9ec1a8c34e894c79dc72 (run id says `e7a130d`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.71 / 4.08 |
| est. sync overhead s | 0.45 |
| injection | profile burst, 100 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| harness commit | e7a130d9d13507142b1d9ec1a8c34e894c79dc72 (run id says `e7a130d`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | tanuh-small-v2 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.7 / 0.76 |
| est. sync overhead s | 0.08 |
| injection | profile burst, 100 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 2000 s |
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
| harness commit | e7a130d9d13507142b1d9ec1a8c34e894c79dc72 (run id says `e7a130d`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | states-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.72 / 0.74 |
| est. sync overhead s | 0.08 |
| injection | profile steady, 500 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 10020 s |
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
| harness commit | 4c7b807737e887f2d33311086d00a1a787018dd8 (run id says `4c7b807`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | states-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.71 / 0.76 |
| est. sync overhead s | 0.08 |
| injection | profile steady, 501 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 10020 s |
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
| harness commit | eb5e4b3596e90d1e48bae50186dc4bace0d4ea8c (run id says `eb5e4b3`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.38 / 0.4 |
| est. sync overhead s | 0.04 |
| injection | profile steady, 60 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 1200 s |
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
| harness commit | eb5e4b3596e90d1e48bae50186dc4bace0d4ea8c (run id says `eb5e4b3`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.7 / 0.75 |
| est. sync overhead s | 0.08 |
| injection | profile steady, 561 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 11220 s |
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
| harness commit | d484f18e1c8666dee40f981d162390061e3c91f6 (run id says `d484f18`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.6 / 0.68 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 561 users arriving over 120min @ 140/h, ~0.2 requests in flight (rps x mean), ramp 11220 s |
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
