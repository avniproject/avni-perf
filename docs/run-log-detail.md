# Run log — detail

Generated from `s3://avni-loadtest-936573213727/artefacts/` by `tools/update-run-log.sh` (`make run_log`) — last refreshed 2026-10-30 04:05 IST.

**Do not edit by hand.** Rewritten wholesale on every run of that script, as [`run-log.md`](run-log.md) is. That file is the index and carries the results table and any caveats; this one records what each run was configured with and what environment it met, which is what makes a number interpretable once the environment is gone.

## `2026-10-05T08-38-47Z-case1-f76d110`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T08-38-47Z-case1-f76d110/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-05T08-38-47Z-case1-f76d110/2026-10-05T08-38-47Z-case1-f76d110.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-05T08-38-47Z-case1-f76d110/2026-10-05T08-38-47Z-case1-f76d110.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 19 / 202 / 297 / 716 |
| mean ms | 45 |
| mean throughput rps | 4.77 |
| app CPU seconds | 135 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T09-43-14Z-case1-e47afd5/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-05T09-43-14Z-case1-e47afd5/2026-10-05T09-43-14Z-case1-e47afd5.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-05T09-43-14Z-case1-e47afd5/2026-10-05T09-43-14Z-case1-e47afd5.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 152 / 2242 / 4014 / 5860 |
| mean ms | 417 |
| mean throughput rps | 52.44 |
| app CPU seconds | 50 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T09-53-13Z-case1-burst15-e47afd5/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-05T09-53-13Z-case1-burst15-e47afd5/2026-10-05T09-53-13Z-case1-burst15-e47afd5.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-05T09-53-13Z-case1-burst15-e47afd5/2026-10-05T09-53-13Z-case1-burst15-e47afd5.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 486 / 6768 / 9013 / 16195 |
| mean ms | 1254 |
| mean throughput rps | 56.58 |
| app CPU seconds | 123 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T10-28-06Z-case1-burst90-d9eac3e/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-05T10-28-06Z-case1-burst90-d9eac3e/2026-10-05T10-28-06Z-case1-burst90-d9eac3e.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-05T10-28-06Z-case1-burst90-d9eac3e/2026-10-05T10-28-06Z-case1-burst90-d9eac3e.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 31 / 376 / 868 / 1157 |
| mean ms | 74 |
| mean throughput rps | 43 |
| app CPU seconds | 13 |
| app CPU s per sync | 0.13 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T10-30-01Z-case1-burst120-d9eac3e/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-05T10-30-01Z-case1-burst120-d9eac3e/2026-10-05T10-30-01Z-case1-burst120-d9eac3e.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-05T10-30-01Z-case1-burst120-d9eac3e/2026-10-05T10-30-01Z-case1-burst120-d9eac3e.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 21 / 222 / 437 / 644 |
| mean ms | 50 |
| mean throughput rps | 33.33 |
| app CPU seconds | 19 |
| app CPU s per sync | 0.19 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T10-32-25Z-case1-burst180-d9eac3e/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-05T10-32-25Z-case1-burst180-d9eac3e/2026-10-05T10-32-25Z-case1-burst180-d9eac3e.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-05T10-32-25Z-case1-burst180-d9eac3e/2026-10-05T10-32-25Z-case1-burst180-d9eac3e.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 19 / 196 / 330 / 597 |
| mean ms | 42 |
| mean throughput rps | 22.75 |
| app CPU seconds | 146 |
| app CPU s per sync | 1.46 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T11-37-03Z-case1-burst60-d9eac3e/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-05T11-37-03Z-case1-burst60-d9eac3e/2026-10-05T11-37-03Z-case1-burst60-d9eac3e.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-05T11-37-03Z-case1-burst60-d9eac3e/2026-10-05T11-37-03Z-case1-burst60-d9eac3e.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 4183 |
| failed | 9 (0.21%) |
| response time p50 / p95 / p99 / max ms | 1143 / 25635 / 34970 / 51788 |
| mean ms | 4083 |
| mean throughput rps | 18.43 |
| app CPU seconds | 85 |
| app CPU s per sync | 0.93 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T11-41-10Z-case1-burst15-d9eac3e/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-05T11-41-10Z-case1-burst15-d9eac3e/2026-10-05T11-41-10Z-case1-burst15-d9eac3e.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-05T11-41-10Z-case1-burst15-d9eac3e/2026-10-05T11-41-10Z-case1-burst15-d9eac3e.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 1020 / 14214 / 20225 / 27018 |
| mean ms | 2693 |
| mean throughput rps | 30.94 |
| app CPU seconds | 292 |
| app CPU s per sync | 2.92 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T12-01-03Z-case1-burst60-warm-d9eac3e/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-05T12-01-03Z-case1-burst60-warm-d9eac3e/2026-10-05T12-01-03Z-case1-burst60-warm-d9eac3e.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-05T12-01-03Z-case1-burst60-warm-d9eac3e/2026-10-05T12-01-03Z-case1-burst60-warm-d9eac3e.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 207 / 2767 / 5326 / 6728 |
| mean ms | 539 |
| mean throughput rps | 50 |
| app CPU seconds | 34 |
| app CPU s per sync | 0.34 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-05T12-02-47Z-case1-burst15-warm-d9eac3e/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-05T12-02-47Z-case1-burst15-warm-d9eac3e/2026-10-05T12-02-47Z-case1-burst15-warm-d9eac3e.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-05T12-02-47Z-case1-burst15-warm-d9eac3e/2026-10-05T12-02-47Z-case1-burst15-warm-d9eac3e.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 499 / 6741 / 9834 / 17959 |
| mean ms | 1253 |
| mean throughput rps | 56.58 |
| app CPU seconds | 274 |
| app CPU s per sync | 2.74 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-06T04-40-26Z-case1-burst900-e7a130d/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-06T04-40-26Z-case1-burst900-e7a130d/2026-10-06T04-40-26Z-case1-burst900-e7a130d.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-06T04-40-26Z-case1-burst900-e7a130d/2026-10-06T04-40-26Z-case1-burst900-e7a130d.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 24 / 200 / 363 / 705 |
| mean ms | 48 |
| mean throughput rps | 4.77 |
| app CPU seconds | 93 |
| app CPU s per sync | 0.93 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-06T04-55-47Z-case1-burst75-e7a130d/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-06T04-55-47Z-case1-burst75-e7a130d/2026-10-06T04-55-47Z-case1-burst75-e7a130d.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-06T04-55-47Z-case1-burst75-e7a130d/2026-10-06T04-55-47Z-case1-burst75-e7a130d.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 3356 |
| failed | 40 (1.18%) |
| response time p50 / p95 / p99 / max ms | 34 / 402 / 750 / 1118 |
| mean ms | 83 |
| mean throughput rps | 39.48 |
| app CPU seconds | 159 |
| app CPU s per sync | 2.56 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-06T05-16-44Z-case1-burst75-e7a130d/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-06T05-16-44Z-case1-burst75-e7a130d/2026-10-06T05-16-44Z-case1-burst75-e7a130d.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-06T05-16-44Z-case1-burst75-e7a130d/2026-10-06T05-16-44Z-case1-burst75-e7a130d.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 4300 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 74 / 918 / 1426 / 1919 |
| mean ms | 178 |
| mean throughput rps | 49.43 |
| app CPU seconds | 190 |
| app CPU s per sync | 1.90 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-06T05-38-32Z-case2-e7a130d/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-06T05-38-32Z-case2-e7a130d/2026-10-06T05-38-32Z-case2-e7a130d.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-06T05-38-32Z-case2-e7a130d/2026-10-06T05-38-32Z-case2-e7a130d.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 2846 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 251 / 288 / 533 / 611 |
| mean ms | 209 |
| mean throughput rps | 0.2 |
| app CPU seconds | 702 |
| app CPU s per sync | 4.21 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-06T09-50-36Z-case14-4c7b807/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-06T09-50-36Z-case14-4c7b807/2026-10-06T09-50-36Z-case14-4c7b807.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-06T09-50-36Z-case14-4c7b807/2026-10-06T09-50-36Z-case14-4c7b807.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 2898 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 44 / 272 / 311 / 772 |
| mean ms | 117 |
| mean throughput rps | 0.54 |
| app CPU seconds | 267 |
| app CPU s per sync | 4.24 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-07T06-15-54Z-case3-eb5e4b3/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-07T06-15-54Z-case3-eb5e4b3/2026-10-07T06-15-54Z-case3-eb5e4b3.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-07T06-15-54Z-case3-eb5e4b3/2026-10-07T06-15-54Z-case3-eb5e4b3.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 2314 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 294 / 333 / 376 / 428 |
| mean ms | 255 |
| mean throughput rps | 0.32 |
| app CPU seconds | 490 |
| app CPU s per sync | 8.17 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-07T08-38-32Z-case4-eb5e4b3/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-07T08-38-32Z-case4-eb5e4b3/2026-10-07T08-38-32Z-case4-eb5e4b3.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-07T08-38-32Z-case4-eb5e4b3/2026-10-07T08-38-32Z-case4-eb5e4b3.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 3107 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 259 / 287 / 301 / 623 |
| mean ms | 212 |
| mean throughput rps | 0.22 |
| app CPU seconds | 37 |
| app CPU s per sync | 0.20 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-08T06-17-46Z-case4-d484f18/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-08T06-17-46Z-case4-d484f18/2026-10-08T06-17-46Z-case4-d484f18.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-08T06-17-46Z-case4-d484f18/2026-10-08T06-17-46Z-case4-d484f18.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 3587 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 265 / 322 / 387 / 532 |
| mean ms | 229 |
| mean throughput rps | 0.25 |
| app CPU seconds | 792 |
| app CPU s per sync | 4.23 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-08T11-32-36Z-case5-d484f18/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-08T11-32-36Z-case5-d484f18/2026-10-08T11-32-36Z-case5-d484f18.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-08T11-32-36Z-case5-d484f18/2026-10-08T11-32-36Z-case5-d484f18.zip .`; unzip and open `index.html`.

| | |
|---|---|

## `2026-10-08T12-04-15Z-case5-d484f18`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-08T12-04-15Z-case5-d484f18/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-08T12-04-15Z-case5-d484f18/2026-10-08T12-04-15Z-case5-d484f18.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-08T12-04-15Z-case5-d484f18/2026-10-08T12-04-15Z-case5-d484f18.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 5390 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 268 / 329 / 367 / 523 |
| mean ms | 228 |
| mean throughput rps | 0.74 |
| app CPU seconds | 1,576 |
| app CPU s per sync | 5.63 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-08T14-05-56Z-case11-run1-d484f18/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-08T14-05-56Z-case11-run1-d484f18/2026-10-08T14-05-56Z-case11-run1-d484f18.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-08T14-05-56Z-case11-run1-d484f18/2026-10-08T14-05-56Z-case11-run1-d484f18.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 143211 |
| failed | 53 (0.04%) |
| response time p50 / p95 / p99 / max ms | 18771 / 41912 / 51544 / 59909 |
| mean ms | 18568 |
| mean throughput rps | 22.27 |
| app CPU seconds | 8,060 |
| app CPU s per sync | 4.94 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T04-28-45Z-case11-pairA-d484f18/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-09T04-28-45Z-case11-pairA-d484f18/2026-10-09T04-28-45Z-case11-pairA-d484f18.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-09T04-28-45Z-case11-pairA-d484f18/2026-10-09T04-28-45Z-case11-pairA-d484f18.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 48408 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 28 / 342 / 1222 / 2469 |
| mean ms | 83 |
| mean throughput rps | 12.14 |
| app CPU seconds | 2,194 |
| app CPU s per sync | 3.99 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T05-37-25Z-case11-pairB-d484f18/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-09T05-37-25Z-case11-pairB-d484f18/2026-10-09T05-37-25Z-case11-pairB-d484f18.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-09T05-37-25Z-case11-pairB-d484f18/2026-10-09T05-37-25Z-case11-pairB-d484f18.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 47456 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 28 / 367 / 710 / 916 |
| mean ms | 84 |
| mean throughput rps | 11.88 |
| app CPU seconds | 2,620 |
| app CPU s per sync | 4.76 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T06-55-55Z-case11-pairC-cf77819/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-09T06-55-55Z-case11-pairC-cf77819/2026-10-09T06-55-55Z-case11-pairC-cf77819.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-09T06-55-55Z-case11-pairC-cf77819/2026-10-09T06-55-55Z-case11-pairC-cf77819.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 46489 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 28 / 327 / 527 / 1137 |
| mean ms | 81 |
| mean throughput rps | 12.13 |
| app CPU seconds | 2,622 |
| app CPU s per sync | 4.77 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T08-00-22Z-case11-pairD-cf77819/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-09T08-00-22Z-case11-pairD-cf77819/2026-10-09T08-00-22Z-case11-pairD-cf77819.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-09T08-00-22Z-case11-pairD-cf77819/2026-10-09T08-00-22Z-case11-pairD-cf77819.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 47544 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 28 / 364 / 685 / 2144 |
| mean ms | 90 |
| mean throughput rps | 11.88 |
| app CPU seconds | 3,285 |
| app CPU s per sync | 5.97 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T09-17-04Z-case11-pairE-cf77819/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-09T09-17-04Z-case11-pairE-cf77819/2026-10-09T09-17-04Z-case11-pairE-cf77819.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-09T09-17-04Z-case11-pairE-cf77819/2026-10-09T09-17-04Z-case11-pairE-cf77819.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 12960 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 284 / 424 / 610 / 1369 |
| mean ms | 253 |
| mean throughput rps | 3.45 |
| app CPU seconds | 1,904 |
| app CPU s per sync | 3.46 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T11-27-35Z-case11-burst15-400-cf77819/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-09T11-27-35Z-case11-burst15-400-cf77819/2026-10-09T11-27-35Z-case11-burst15-400-cf77819.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-09T11-27-35Z-case11-burst15-400-cf77819/2026-10-09T11-27-35Z-case11-burst15-400-cf77819.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 35842 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 2082 / 19610 / 23226 / 30570 |
| mean ms | 4294 |
| mean throughput rps | 18.47 |
| app CPU seconds | 1,729 |
| app CPU s per sync | 4.32 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-09T14-21-29Z-case10-soak-cf77819/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-09T14-21-29Z-case10-soak-cf77819/2026-10-09T14-21-29Z-case10-soak-cf77819.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-09T14-21-29Z-case10-soak-cf77819/2026-10-09T14-21-29Z-case10-soak-cf77819.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 50098 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 29 / 290 / 325 / 2103 |
| mean ms | 72 |
| mean throughput rps | 1.16 |
| app CPU seconds | 3,005 |
| app CPU s per sync | 5.36 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-12T02-07-36Z-case9-12a-cf77819/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-12T02-07-36Z-case9-12a-cf77819/2026-10-12T02-07-36Z-case9-12a-cf77819.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-12T02-07-36Z-case9-12a-cf77819/2026-10-12T02-07-36Z-case9-12a-cf77819.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 21491 |
| failed | 116 (0.54%) |
| response time p50 / p95 / p99 / max ms | 5129 / 52876 / 57940 / 59992 |
| mean ms | 17151 |
| mean throughput rps | 6.23 |
| app CPU seconds | 4,411 |
| app CPU s per sync | 4.07 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-12T03-43-44Z-case9-12b-cf77819/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-12T03-43-44Z-case9-12b-cf77819/2026-10-12T03-43-44Z-case9-12b-cf77819.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-12T03-43-44Z-case9-12b-cf77819/2026-10-12T03-43-44Z-case9-12b-cf77819.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 16041 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 88 / 489 / 769 / 1384 |
| mean ms | 167 |
| mean throughput rps | 5.82 |
| app CPU seconds | 1,507 |
| app CPU s per sync | 4.74 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-12T04-55-23Z-case9-12b-rerun-cf77819/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-12T04-55-23Z-case9-12b-rerun-cf77819/2026-10-12T04-55-23Z-case9-12b-rerun-cf77819.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-12T04-55-23Z-case9-12b-rerun-cf77819/2026-10-12T04-55-23Z-case9-12b-rerun-cf77819.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 40241 |
| failed | 98 (0.24%) |
| response time p50 / p95 / p99 / max ms | 6112 / 48514 / 54197 / 59988 |
| mean ms | 14810 |
| mean throughput rps | 11.4 |
| app CPU seconds | 5,486 |
| app CPU s per sync | 7.14 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-12T06-01-23Z-case9-12c-cf77819/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-12T06-01-23Z-case9-12c-cf77819/2026-10-12T06-01-23Z-case9-12c-cf77819.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-12T06-01-23Z-case9-12c-cf77819/2026-10-12T06-01-23Z-case9-12c-cf77819.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 102891 |
| failed | 9 (0.01%) |
| response time p50 / p95 / p99 / max ms | 8464 / 33454 / 41619 / 52693 |
| mean ms | 11470 |
| mean throughput rps | 20.46 |
| app CPU seconds | 5,894 |
| app CPU s per sync | 4.95 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-14T04-26-19Z-case6-cf77819/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-14T04-26-19Z-case6-cf77819/2026-10-14T04-26-19Z-case6-cf77819.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-14T04-26-19Z-case6-cf77819/2026-10-14T04-26-19Z-case6-cf77819.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 5237 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 263 / 333 / 549 / 3730 |
| mean ms | 238 |
| mean throughput rps | 0.72 |
| app CPU seconds | 1,078 |
| app CPU s per sync | 3.85 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-14T09-19-33Z-case7-33396d9/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-14T09-19-33Z-case7-33396d9/2026-10-14T09-19-33Z-case7-33396d9.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-14T09-19-33Z-case7-33396d9/2026-10-14T09-19-33Z-case7-33396d9.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 61683 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 79 / 323 / 623 / 3895 |
| mean ms | 115 |
| mean throughput rps | 8.53 |
| app CPU seconds | 3,741 |
| app CPU s per sync | 2.01 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-15T04-01-52Z-case12-c2a0e76/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-15T04-01-52Z-case12-c2a0e76/2026-10-15T04-01-52Z-case12-c2a0e76.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-15T04-01-52Z-case12-c2a0e76/2026-10-15T04-01-52Z-case12-c2a0e76.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 31409 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 498 / 1709 / 2207 / 4314 |
| mean ms | 641 |
| mean throughput rps | 8.52 |
| app CPU seconds | 6,152 |
| app CPU s per sync | 3.66 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-15T05-33-35Z-case13-c2a0e76/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-15T05-33-35Z-case13-c2a0e76/2026-10-15T05-33-35Z-case13-c2a0e76.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-15T05-33-35Z-case13-c2a0e76/2026-10-15T05-33-35Z-case13-c2a0e76.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 51727 |
| failed | 640 (1.22%) |
| response time p50 / p95 / p99 / max ms | 37484 / 55919 / 58692 / 59998 |
| mean ms | 32170 |
| mean throughput rps | 12.06 |
| app CPU seconds | 8,298 |
| app CPU s per sync | 4.52 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-15T09-47-54Z-case8-day60-c2a0e76/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-15T09-47-54Z-case8-day60-c2a0e76/2026-10-15T09-47-54Z-case8-day60-c2a0e76.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-15T09-47-54Z-case8-day60-c2a0e76/2026-10-15T09-47-54Z-case8-day60-c2a0e76.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 1504 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 103 / 263 / 292 / 399 |
| mean ms | 111 |
| mean throughput rps | 0.21 |
| app CPU seconds | 145 |
| app CPU s per sync | 1.55 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-16T04-54-41Z-case8-day-120-c2a0e76/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-16T04-54-41Z-case8-day-120-c2a0e76/2026-10-16T04-54-41Z-case8-day-120-c2a0e76.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-16T04-54-41Z-case8-day-120-c2a0e76/2026-10-16T04-54-41Z-case8-day-120-c2a0e76.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 1624 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 184 / 302 / 341 / 573 |
| mean ms | 177 |
| mean throughput rps | 0.23 |
| app CPU seconds | 280 |
| app CPU s per sync | 2.98 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-16T09-06-38Z-case8-day-365-c2a0e76/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-16T09-06-38Z-case8-day-365-c2a0e76/2026-10-16T09-06-38Z-case8-day-365-c2a0e76.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-16T09-06-38Z-case8-day-365-c2a0e76/2026-10-16T09-06-38Z-case8-day-365-c2a0e76.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 3112 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 271 / 337 / 831 / 1416 |
| mean ms | 257 |
| mean throughput rps | 0.43 |
| app CPU seconds | 694 |
| app CPU s per sync | 7.38 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-19T05-06-40Z-case3-span20-c2a0e76/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-19T05-06-40Z-case3-span20-c2a0e76/2026-10-19T05-06-40Z-case3-span20-c2a0e76.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-19T05-06-40Z-case3-span20-c2a0e76/2026-10-19T05-06-40Z-case3-span20-c2a0e76.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 5053 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 327 / 357 / 388 / 588 |
| mean ms | 294 |
| mean throughput rps | 0.67 |
| app CPU seconds | 1,233 |
| app CPU s per sync | 20.55 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-19T07-14-41Z-case4-span20-c2a0e76/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-19T07-14-41Z-case4-span20-c2a0e76/2026-10-19T07-14-41Z-case4-span20-c2a0e76.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-19T07-14-41Z-case4-span20-c2a0e76/2026-10-19T07-14-41Z-case4-span20-c2a0e76.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 3436 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 263 / 336 / 360 / 536 |
| mean ms | 232 |
| mean throughput rps | 0.24 |
| app CPU seconds | 702 |
| app CPU s per sync | 4.01 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-19T11-15-25Z-case5-span20-c2a0e76/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-19T11-15-25Z-case5-span20-c2a0e76/2026-10-19T11-15-25Z-case5-span20-c2a0e76.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-19T11-15-25Z-case5-span20-c2a0e76/2026-10-19T11-15-25Z-case5-span20-c2a0e76.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 5120 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 267 / 348 / 379 / 1660 |
| mean ms | 238 |
| mean throughput rps | 0.68 |
| app CPU seconds | 998 |
| app CPU s per sync | 3.79 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-21T04-10-50Z-case13-m6g.large-c2a0e76/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-21T04-10-50Z-case13-m6g.large-c2a0e76/2026-10-21T04-10-50Z-case13-m6g.large-c2a0e76.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-21T04-10-50Z-case13-m6g.large-c2a0e76/2026-10-21T04-10-50Z-case13-m6g.large-c2a0e76.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 50848 |
| failed | 467 (0.91%) |
| response time p50 / p95 / p99 / max ms | 38689 / 56293 / 58755 / 60001 |
| mean ms | 33299 |
| mean throughput rps | 11.94 |
| app CPU seconds | 8,403 |
| app CPU | 86% mean, peak 99% |
| app heap | 2,778 MB mean, peak 5,096 of 5,120 MB max |
| RDS CPU | 31% mean, peak 43% |
| RDS memory | 1,151 MB freeable at its lowest, swap peak 2 MB |
| app CPU s per sync | 4.19 |
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

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-21T05-43-20Z-case13-m6g.xlarge-c2a0e76/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-21T05-43-20Z-case13-m6g.xlarge-c2a0e76/2026-10-21T05-43-20Z-case13-m6g.xlarge-c2a0e76.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-21T05-43-20Z-case13-m6g.xlarge-c2a0e76/2026-10-21T05-43-20Z-case13-m6g.xlarge-c2a0e76.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 57386 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 169 / 434 / 615 / 5895 |
| mean ms | 215 |
| mean throughput rps | 15.57 |
| app CPU seconds | 7,743 |
| app CPU | 42% mean, peak 71% |
| app heap | 1,073 MB mean, peak 1,796 of 5,120 MB max |
| RDS CPU | 33% mean, peak 48% |
| RDS memory | 4,302 MB freeable at its lowest, swap peak 2 MB |
| app CPU s per sync | 3.13 |
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

## `2026-10-21T06-58-37Z-media-hour-m6g.xlarge-c2a0e76`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-21T06-58-37Z-media-hour-m6g.xlarge-c2a0e76/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-21T06-58-37Z-media-hour-m6g.xlarge-c2a0e76/2026-10-21T06-58-37Z-media-hour-m6g.xlarge-c2a0e76.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-21T06-58-37Z-media-hour-m6g.xlarge-c2a0e76/2026-10-21T06-58-37Z-media-hour-m6g.xlarge-c2a0e76.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 415082 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 32 / 503 / 1427 / 17711 |
| mean ms | 101 |
| mean throughput rps | 49.43 |
| app CPU seconds | 11,542 |
| app CPU | 62% mean, peak 94% |
| app heap | 1,164 MB mean, peak 2,092 of 5,120 MB max |
| RDS CPU | 62% mean, peak 98% |
| RDS memory | 3,362 MB freeable at its lowest, swap peak 6 MB |
| app CPU s per sync | 5.04 |
| app CPU s per **customer** sync | 7.69 (792 co-tenant syncs excluded from the denominator, their CPU included) |
| app CPU s per incremental sync p50 / p95 | 3.85 / 13.16 (n=2267) |
| app CPU s per full sync p50 / p95 | 5.58 / 15.74 (n=25) |
| harness commit | c2a0e76417d3ac980bb476d835e9b132df7c8a92 (run id says `c2a0e76`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 17.3.0-SNAPSHOT |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.41 / 0.66 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 1500 users arriving over 60min @ 1500/h, ~5.0 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 491.2 / 593.9 / 1471.9 (2292 syncs) |
| full syncs p50 / p95 s | 666.4 / 1878.4 (25 of 2292, recorded) |
| cache policy | warm-from-case13-m6g.xlarge |
| autovacuum | on |

## `2026-10-21T09-56-40Z-case13-2vcpu-B-no-interceptor-f038788`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-21T09-56-40Z-case13-2vcpu-B-no-interceptor-f038788/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-21T09-56-40Z-case13-2vcpu-B-no-interceptor-f038788/2026-10-21T09-56-40Z-case13-2vcpu-B-no-interceptor-f038788.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-21T09-56-40Z-case13-2vcpu-B-no-interceptor-f038788/2026-10-21T09-56-40Z-case13-2vcpu-B-no-interceptor-f038788.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 61181 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 295 / 1440 / 2441 / 10372 |
| mean ms | 463 |
| mean throughput rps | 16.5 |
| app CPU seconds | 6,358 |
| app CPU | 84% mean, peak 99% |
| app heap | 1,042 MB mean, peak 1,977 of 5,120 MB max |
| RDS CPU | 39% mean, peak 48% |
| RDS memory | 3,926 MB freeable at its lowest, swap peak 6 MB |
| app CPU s per sync | 2.57 |
| app CPU s per **customer** sync | 3.78 (792 co-tenant syncs excluded from the denominator, their CPU included) |
| app CPU s per incremental sync p50 / p95 | 1.86 / 6.74 (n=2448) |
| app CPU s per full sync p50 / p95 | 5.02 / 16.75 (n=26) |
| harness commit | f038788ffc86f00170921f81aacf4a2c4d44da27 (run id says `f038788`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 2c0215679-no-interceptor |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.68 / 0.72 |
| est. sync overhead s | 0.08 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~7.6 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / True |
| sync duration p50 / mean / p95 s | 64.8 / 66.8 / 196.7 (2474 syncs) |
| full syncs p50 / p95 s | 93.8 / 255.7 (26 of 2474, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.large |
| autovacuum | on |

## `2026-10-21T10-59-35Z-case12-2vcpu-B-no-interceptor-f038788`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-21T10-59-35Z-case12-2vcpu-B-no-interceptor-f038788/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-21T10-59-35Z-case12-2vcpu-B-no-interceptor-f038788/2026-10-21T10-59-35Z-case12-2vcpu-B-no-interceptor-f038788.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-21T10-59-35Z-case12-2vcpu-B-no-interceptor-f038788/2026-10-21T10-59-35Z-case12-2vcpu-B-no-interceptor-f038788.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 33709 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 283 / 748 / 1087 / 1806 |
| mean ms | 325 |
| mean throughput rps | 9.1 |
| app CPU seconds | 4,999 |
| app CPU | 65% mean, peak 85% |
| app heap | 1,285 MB mean, peak 2,070 of 5,120 MB max |
| RDS CPU | 25% mean, peak 34% |
| RDS memory | 4,261 MB freeable at its lowest, swap peak 6 MB |
| app CPU s per sync | 2.97 |
| app CPU s per **customer** sync | 2.97 (0 co-tenant syncs excluded from the denominator, their CPU included) |
| app CPU s per incremental sync p50 / p95 | 2.42 / 7.84 (n=1670) |
| app CPU s per full sync p50 / p95 | 4.36 / 5.40 (n=12) |
| harness commit | f038788ffc86f00170921f81aacf4a2c4d44da27 (run id says `f038788`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 2c0215679-no-interceptor |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.37 / 0.43 |
| est. sync overhead s | 0.05 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~3.0 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 63.2 / 78.6 / 188.2 (1682 syncs) |
| full syncs p50 / p95 s | 84.7 / 157.5 (12 of 1682, recorded) |
| cache policy | warm-from-preceding-run-m6g.large |
| autovacuum | on |

## `2026-10-21T12-27-12Z-case15-redrawn-m6g.xlarge-40f08e2`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-21T12-27-12Z-case15-redrawn-m6g.xlarge-40f08e2/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-21T12-27-12Z-case15-redrawn-m6g.xlarge-40f08e2/2026-10-21T12-27-12Z-case15-redrawn-m6g.xlarge-40f08e2.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-21T12-27-12Z-case15-redrawn-m6g.xlarge-40f08e2/2026-10-21T12-27-12Z-case15-redrawn-m6g.xlarge-40f08e2.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 327307 |
| failed | 2 (0.0%) |
| response time p50 / p95 / p99 / max ms | 28 / 426 / 796 / 9557 |
| mean ms | 90 |
| mean throughput rps | 68.17 |
| app CPU seconds | 10,714 |
| app CPU | 54% mean, peak 89% |
| app heap | 1,101 MB mean, peak 1,938 of 5,120 MB max |
| RDS CPU | 52% mean, peak 81% |
| RDS memory | 3,772 MB freeable at its lowest, swap peak 6 MB |
| app CPU s per sync | 4.68 |
| app CPU s per **customer** sync | 7.14 (790 co-tenant syncs excluded from the denominator, their CPU included) |
| app CPU s per incremental sync p50 / p95 | 4.72 / 11.30 (n=2266) |
| app CPU s per full sync p50 / p95 | 7.86 / 13.21 (n=24) |
| harness commit | 40f08e2552038bdf0d9c928e0c519f4c57f84b8c (run id says `40f08e2`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 2c0215679 |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.37 / 0.47 |
| est. sync overhead s | 0.05 |
| injection | profile steady, 1500 users arriving over 60min @ 1500/h, ~6.1 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot-nosuppush.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 465.2 / 453.1 / 1026.8 (2290 syncs) |
| full syncs p50 / p95 s | 735.1 / 1185.2 (24 of 2290, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.xlarge |
| autovacuum | on |

## `2026-10-23T04-39-55Z-case15-tenaday-m6g.xlarge-23a4e48`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-23T04-39-55Z-case15-tenaday-m6g.xlarge-23a4e48/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-23T04-39-55Z-case15-tenaday-m6g.xlarge-23a4e48/2026-10-23T04-39-55Z-case15-tenaday-m6g.xlarge-23a4e48.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-23T04-39-55Z-case15-tenaday-m6g.xlarge-23a4e48/2026-10-23T04-39-55Z-case15-tenaday-m6g.xlarge-23a4e48.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 203439 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 34 / 446 / 774 / 9670 |
| mean ms | 110 |
| mean throughput rps | 47.69 |
| app CPU seconds | 9,284 |
| app CPU | 53% mean, peak 81% |
| app heap | 1,079 MB mean, peak 1,896 of 5,120 MB max |
| RDS CPU | 54% mean, peak 79% |
| RDS memory | 3,855 MB freeable at its lowest, swap peak 1 MB |
| app CPU s per sync | 4.05 |
| harness commit | 23a4e48769bf0a74bc1cfad4923f07a9632c7a9e (run id says `23a4e48`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 2c0215679 |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.39 / 0.42 |
| est. sync overhead s | 0.05 |
| injection | profile steady, 1500 users arriving over 60min @ 1500/h, ~5.2 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot-nosuppush.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 267.7 / 257.5 / 529.4 (2292 syncs) |
| full syncs p50 / p95 s | 248.4 / 538.7 (26 of 2292, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.xlarge |
| autovacuum | on |

## `2026-10-23T08-29-29Z-case15-5k-m6g.2xlarge-23a4e48`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-23T08-29-29Z-case15-5k-m6g.2xlarge-23a4e48/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-23T08-29-29Z-case15-5k-m6g.2xlarge-23a4e48/2026-10-23T08-29-29Z-case15-5k-m6g.2xlarge-23a4e48.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-23T08-29-29Z-case15-5k-m6g.2xlarge-23a4e48/2026-10-23T08-29-29Z-case15-5k-m6g.2xlarge-23a4e48.zip .`; unzip and open `index.html`.

| | |
|---|---|
| harness commit | 23a4e48769bf0a74bc1cfad4923f07a9632c7a9e (run id says `23a4e48`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 2c0215679 |
| dataset | pilot-day-180-5k |
| injector | — (—, java —, — cpu, heap — MB) |
| injector RTT min / median ms | — / — |
| est. sync overhead s | — |
| injection | profile —, — users arriving over —, ~— requests in flight (rps x mean), ramp — s |
| sync | mode —, feeder — (— rows), auth —, page — |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | — / — |
| sync duration p50 / mean / p95 s | 11.5 / 11.5 / 11.7 (100 syncs) |
| full syncs p50 / p95 s | 11.5 / 11.7 (100 of 100, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.2xlarge |
| autovacuum | on |

## `2026-10-23T08-54-23Z-case15-5k-m6g.2xlarge-1aa819b`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-23T08-54-23Z-case15-5k-m6g.2xlarge-1aa819b/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-23T08-54-23Z-case15-5k-m6g.2xlarge-1aa819b/2026-10-23T08-54-23Z-case15-5k-m6g.2xlarge-1aa819b.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-23T08-54-23Z-case15-5k-m6g.2xlarge-1aa819b/2026-10-23T08-54-23Z-case15-5k-m6g.2xlarge-1aa819b.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 573457 |
| failed | 1 (0.0%) |
| response time p50 / p95 / p99 / max ms | 12 / 234 / 363 / 3560 |
| mean ms | 55 |
| mean throughput rps | 135.38 |
| app CPU seconds | 18,536 |
| app CPU | 54% mean, peak 76% |
| app heap | 1,176 MB mean, peak 2,134 of 5,120 MB max |
| RDS CPU | 27% mean, peak 38% |
| RDS memory | 20,601 MB freeable at its lowest, no swap |
| app CPU s per sync | 3.20 |
| harness commit | 1aa819b70eaa0f43700f849e8b064f052b75344a (run id says `1aa819b`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 2c0215679 |
| dataset | pilot-day-180-5k |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.67 / 0.78 |
| est. sync overhead s | 0.09 |
| injection | profile steady, 5000 users arriving over 60min @ 5000/h, ~7.4 requests in flight (rps x mean), ramp 111800 s |
| sync | mode realistic, feeder case5-users-pilot-5k-nosuppush.csv (5590 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 300.4 / 294.2 / 525.1 (5791 syncs) |
| full syncs p50 / p95 s | 310.4 / 536.8 (56 of 5791, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.2xlarge |
| autovacuum | on |

## `2026-10-23T12-09-02Z-case15-10k-m6g.4xlarge-1aa819b`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-23T12-09-02Z-case15-10k-m6g.4xlarge-1aa819b/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-23T12-09-02Z-case15-10k-m6g.4xlarge-1aa819b/2026-10-23T12-09-02Z-case15-10k-m6g.4xlarge-1aa819b.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-23T12-09-02Z-case15-10k-m6g.4xlarge-1aa819b/2026-10-23T12-09-02Z-case15-10k-m6g.4xlarge-1aa819b.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 1107301 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 10 / 231 / 351 / 1349 |
| mean ms | 50 |
| mean throughput rps | 263.77 |
| app CPU seconds | 35,564 |
| app CPU | 51% mean, peak 70% |
| app heap | 1,220 MB mean, peak 2,285 of 5,120 MB max |
| RDS CPU | 24% mean, peak 33% |
| RDS memory | 42,731 MB freeable at its lowest, no swap |
| app CPU s per sync | 3.30 |
| harness commit | 1aa819b70eaa0f43700f849e8b064f052b75344a (run id says `1aa819b`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 2c0215679 |
| dataset | pilot-day-180-10k |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 4 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.36 / 0.39 |
| est. sync overhead s | 0.04 |
| injection | profile steady, 10000 users arriving over 60min @ 10000/h, ~13.2 requests in flight (rps x mean), ramp 223280 s |
| sync | mode realistic, feeder case5-users-pilot-10k-nosuppush.csv (11164 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 321.0 / 312.7 / 525.0 (10792 syncs) |
| full syncs p50 / p95 s | 310.6 / 535.7 (96 of 10792, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.4xlarge |
| autovacuum | on |

## `2026-10-27T06-53-54Z-case12-anchorA-v18.1-r1-1806f72`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-27T06-53-54Z-case12-anchorA-v18.1-r1-1806f72/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-27T06-53-54Z-case12-anchorA-v18.1-r1-1806f72/2026-10-27T06-53-54Z-case12-anchorA-v18.1-r1-1806f72.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-27T06-53-54Z-case12-anchorA-v18.1-r1-1806f72/2026-10-27T06-53-54Z-case12-anchorA-v18.1-r1-1806f72.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 31469 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 820 / 2433 / 2990 / 4175 |
| mean ms | 983 |
| mean throughput rps | 8.53 |
| app CPU seconds | 6,654 |
| app CPU | 86% mean, peak 99% |
| app heap | 1,048 MB mean, peak 1,850 of 5,120 MB max |
| RDS CPU | 26% mean, peak 31% |
| RDS memory | 3,906 MB freeable at its lowest, swap peak 1 MB |
| app CPU s per sync | 3.96 |
| harness commit | 1806f72f039a73b36a2b131bba675f05db415dbe (run id says `1806f72`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 789092feb |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.58 / 0.6 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~8.4 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 70.2 / 86.1 / 216.0 (1682 syncs) |
| full syncs p50 / p95 s | 102.9 / 268.6 (21 of 1682, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.large |
| autovacuum | on |

## `2026-10-27T08-18-41Z-case12-anchorA-v18.1-r2-1806f72`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-27T08-18-41Z-case12-anchorA-v18.1-r2-1806f72/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-27T08-18-41Z-case12-anchorA-v18.1-r2-1806f72/2026-10-27T08-18-41Z-case12-anchorA-v18.1-r2-1806f72.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-27T08-18-41Z-case12-anchorA-v18.1-r2-1806f72/2026-10-27T08-18-41Z-case12-anchorA-v18.1-r2-1806f72.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 31259 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 630 / 1905 / 2341 / 3411 |
| mean ms | 772 |
| mean throughput rps | 8.48 |
| app CPU seconds | 6,449 |
| app CPU | 84% mean, peak 99% |
| app heap | 1,095 MB mean, peak 1,882 of 5,120 MB max |
| RDS CPU | 25% mean, peak 32% |
| RDS memory | 4,049 MB freeable at its lowest, swap peak 1 MB |
| app CPU s per sync | 3.83 |
| harness commit | 1806f72f039a73b36a2b131bba675f05db415dbe (run id says `1806f72`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 789092feb |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.29 / 0.34 |
| est. sync overhead s | 0.04 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~6.5 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 67.5 / 82.1 / 208.3 (1682 syncs) |
| full syncs p50 / p95 s | 98.2 / 271.7 (14 of 1682, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.large |
| autovacuum | on |

## `2026-10-27T09-46-42Z-case12-anchorA-v17.3-drift-r1-1806f72`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-27T09-46-42Z-case12-anchorA-v17.3-drift-r1-1806f72/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-27T09-46-42Z-case12-anchorA-v17.3-drift-r1-1806f72/2026-10-27T09-46-42Z-case12-anchorA-v17.3-drift-r1-1806f72.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-27T09-46-42Z-case12-anchorA-v17.3-drift-r1-1806f72/2026-10-27T09-46-42Z-case12-anchorA-v17.3-drift-r1-1806f72.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 31259 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 704 / 2219 / 2793 / 3616 |
| mean ms | 875 |
| mean throughput rps | 8.47 |
| app CPU seconds | 6,592 |
| app CPU | 86% mean, peak 99% |
| app heap | 1,050 MB mean, peak 1,808 of 5,120 MB max |
| RDS CPU | 25% mean, peak 31% |
| RDS memory | 3,962 MB freeable at its lowest, swap peak 1 MB |
| app CPU s per sync | 3.92 |
| harness commit | 1806f72f039a73b36a2b131bba675f05db415dbe (run id says `1806f72`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 2c0215679 |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.58 / 0.61 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~7.4 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 68.7 / 83.9 / 213.3 (1682 syncs) |
| full syncs p50 / p95 s | 102.4 / 278.5 (14 of 1682, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.large |
| autovacuum | on |

## `2026-10-27T11-14-57Z-case15-tenaday-anchorB-v18.1-r1-1806f72`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-27T11-14-57Z-case15-tenaday-anchorB-v18.1-r1-1806f72/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-27T11-14-57Z-case15-tenaday-anchorB-v18.1-r1-1806f72/2026-10-27T11-14-57Z-case15-tenaday-anchorB-v18.1-r1-1806f72.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-27T11-14-57Z-case15-tenaday-anchorB-v18.1-r1-1806f72/2026-10-27T11-14-57Z-case15-tenaday-anchorB-v18.1-r1-1806f72.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 204123 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 34 / 449 / 751 / 11652 |
| mean ms | 111 |
| mean throughput rps | 48.35 |
| app CPU seconds | 9,821 |
| app CPU | 56% mean, peak 85% |
| app heap | 1,090 MB mean, peak 1,947 of 5,120 MB max |
| RDS CPU | 52% mean, peak 77% |
| RDS memory | 3,839 MB freeable at its lowest, swap peak 3 MB |
| app CPU s per sync | 4.28 |
| harness commit | 1806f72f039a73b36a2b131bba675f05db415dbe (run id says `1806f72`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 789092feb |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.59 / 0.65 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 1500 users arriving over 60min @ 1500/h, ~5.4 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot-nosuppush.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 267.8 / 259.5 / 554.2 (2292 syncs) |
| full syncs p50 / p95 s | 142.2 / 538.9 (25 of 2292, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.xlarge |
| autovacuum | on |

## `2026-10-27T14-06-07Z-case15-tenaday-anchorB-v18.1-r2-1806f72`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-27T14-06-07Z-case15-tenaday-anchorB-v18.1-r2-1806f72/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-27T14-06-07Z-case15-tenaday-anchorB-v18.1-r2-1806f72/2026-10-27T14-06-07Z-case15-tenaday-anchorB-v18.1-r2-1806f72.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-27T14-06-07Z-case15-tenaday-anchorB-v18.1-r2-1806f72/2026-10-27T14-06-07Z-case15-tenaday-anchorB-v18.1-r2-1806f72.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 203771 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 33 / 449 / 712 / 9640 |
| mean ms | 108 |
| mean throughput rps | 47.13 |
| app CPU seconds | 9,735 |
| app CPU | 56% mean, peak 90% |
| app heap | 1,334 MB mean, peak 2,177 of 5,120 MB max |
| RDS CPU | 50% mean, peak 77% |
| RDS memory | 3,830 MB freeable at its lowest, swap peak 4 MB |
| app CPU s per sync | 4.25 |
| harness commit | 1806f72f039a73b36a2b131bba675f05db415dbe (run id says `1806f72`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 789092feb |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.23 / 0.32 |
| est. sync overhead s | 0.04 |
| injection | profile steady, 1500 users arriving over 60min @ 1500/h, ~5.1 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot-nosuppush.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 266.9 / 257.2 / 543.2 (2292 syncs) |
| full syncs p50 / p95 s | 280.6 / 531.5 (25 of 2292, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.xlarge |
| autovacuum | on |

## `2026-10-28T05-55-38Z-case12-anchorA-fix1097-r1-1806f72`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-28T05-55-38Z-case12-anchorA-fix1097-r1-1806f72/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-28T05-55-38Z-case12-anchorA-fix1097-r1-1806f72/2026-10-28T05-55-38Z-case12-anchorA-fix1097-r1-1806f72.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-28T05-55-38Z-case12-anchorA-fix1097-r1-1806f72/2026-10-28T05-55-38Z-case12-anchorA-fix1097-r1-1806f72.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 31406 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 286 / 715 / 1380 / 3522 |
| mean ms | 329 |
| mean throughput rps | 8.52 |
| app CPU seconds | 4,842 |
| app CPU | 64% mean, peak 84% |
| app heap | 985 MB mean, peak 1,767 of 5,120 MB max |
| RDS CPU | 25% mean, peak 32% |
| RDS memory | 4,244 MB freeable at its lowest, swap peak 1 MB |
| app CPU s per sync | 2.88 |
| harness commit | 1806f72f039a73b36a2b131bba675f05db415dbe (run id says `1806f72`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 5ed93de7c |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.3 / 0.85 |
| est. sync overhead s | 0.09 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~2.8 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 61.5 / 74.1 / 185.5 (1682 syncs) |
| full syncs p50 / p95 s | 83.7 / 233.2 (19 of 1682, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.large |
| autovacuum | on |

## `2026-10-28T07-24-38Z-case12-anchorA-fix1098-r1-1806f72`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-28T07-24-38Z-case12-anchorA-fix1098-r1-1806f72/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-28T07-24-38Z-case12-anchorA-fix1098-r1-1806f72/2026-10-28T07-24-38Z-case12-anchorA-fix1098-r1-1806f72.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-28T07-24-38Z-case12-anchorA-fix1098-r1-1806f72/2026-10-28T07-24-38Z-case12-anchorA-fix1098-r1-1806f72.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 31316 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 694 / 2163 / 2696 / 3825 |
| mean ms | 847 |
| mean throughput rps | 8.49 |
| app CPU seconds | 6,558 |
| app CPU | 85% mean, peak 99% |
| app heap | 1,004 MB mean, peak 1,798 of 5,120 MB max |
| RDS CPU | 26% mean, peak 30% |
| RDS memory | 3,965 MB freeable at its lowest, swap peak 1 MB |
| app CPU s per sync | 3.90 |
| harness commit | 1806f72f039a73b36a2b131bba675f05db415dbe (run id says `1806f72`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 3fb5046f7 |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.25 / 0.4 |
| est. sync overhead s | 0.04 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~7.2 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 68.2 / 83.5 / 212.6 (1682 syncs) |
| full syncs p50 / p95 s | 96.4 / 264.2 (16 of 1682, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.large |
| autovacuum | on |

## `2026-10-28T08-54-30Z-case15-tenaday-anchorB-fix1097-r1-1806f72`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-28T08-54-30Z-case15-tenaday-anchorB-fix1097-r1-1806f72/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-28T08-54-30Z-case15-tenaday-anchorB-fix1097-r1-1806f72/2026-10-28T08-54-30Z-case15-tenaday-anchorB-fix1097-r1-1806f72.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-28T08-54-30Z-case15-tenaday-anchorB-fix1097-r1-1806f72/2026-10-28T08-54-30Z-case15-tenaday-anchorB-fix1097-r1-1806f72.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 205007 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 27 / 306 / 459 / 8169 |
| mean ms | 79 |
| mean throughput rps | 48.66 |
| app CPU seconds | 7,435 |
| app CPU | 43% mean, peak 65% |
| app heap | 1,040 MB mean, peak 1,906 of 5,120 MB max |
| RDS CPU | 48% mean, peak 71% |
| RDS memory | 3,934 MB freeable at its lowest, swap peak 3 MB |
| app CPU s per sync | 3.24 |
| harness commit | 1806f72f039a73b36a2b131bba675f05db415dbe (run id says `1806f72`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 5ed93de7c |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.58 / 0.62 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 1500 users arriving over 60min @ 1500/h, ~3.8 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot-nosuppush.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 264.7 / 257.9 / 552.7 (2292 syncs) |
| full syncs p50 / p95 s | 275.3 / 437.8 (23 of 2292, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.xlarge |
| autovacuum | on |

## `2026-10-28T11-47-36Z-case15-tenaday-anchorB-fix1098-r1-1806f72`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-28T11-47-36Z-case15-tenaday-anchorB-fix1098-r1-1806f72/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-28T11-47-36Z-case15-tenaday-anchorB-fix1098-r1-1806f72/2026-10-28T11-47-36Z-case15-tenaday-anchorB-fix1098-r1-1806f72.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-28T11-47-36Z-case15-tenaday-anchorB-fix1098-r1-1806f72/2026-10-28T11-47-36Z-case15-tenaday-anchorB-fix1098-r1-1806f72.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 202302 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 31 / 445 / 755 / 7868 |
| mean ms | 108 |
| mean throughput rps | 48.58 |
| app CPU seconds | 9,732 |
| app CPU | 56% mean, peak 80% |
| app heap | 1,062 MB mean, peak 1,942 of 5,120 MB max |
| RDS CPU | 51% mean, peak 71% |
| RDS memory | 3,849 MB freeable at its lowest, swap peak 4 MB |
| app CPU s per sync | 4.25 |
| harness commit | 1806f72f039a73b36a2b131bba675f05db415dbe (run id says `1806f72`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 3fb5046f7 |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.55 / 0.64 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 1500 users arriving over 60min @ 1500/h, ~5.2 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot-nosuppush.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 267.6 / 257.3 / 545.8 (2292 syncs) |
| full syncs p50 / p95 s | 248.5 / 406.7 (21 of 2292, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.xlarge |
| autovacuum | on |

## `2026-10-28T14-38-32Z-case15-tenaday-anchorB-fix1100-batch50-r1-7205831`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-28T14-38-32Z-case15-tenaday-anchorB-fix1100-batch50-r1-7205831/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-28T14-38-32Z-case15-tenaday-anchorB-fix1100-batch50-r1-7205831/2026-10-28T14-38-32Z-case15-tenaday-anchorB-fix1100-batch50-r1-7205831.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-28T14-38-32Z-case15-tenaday-anchorB-fix1100-batch50-r1-7205831/2026-10-28T14-38-32Z-case15-tenaday-anchorB-fix1100-batch50-r1-7205831.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 97189 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 122 / 494 / 743 / 7881 |
| mean ms | 193 |
| mean throughput rps | 23.7 |
| app CPU seconds | 9,167 |
| app CPU | 52% mean, peak 78% |
| app heap | 1,045 MB mean, peak 1,872 of 5,120 MB max |
| RDS CPU | 47% mean, peak 67% |
| RDS memory | 4,044 MB freeable at its lowest, swap peak 4 MB |
| app CPU s per sync | 4.00 |
| harness commit | 72058313ae0a9034e46c4188f0bb9475cd11da46 (run id says `7205831`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 99373a2b8 |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.6 / 0.63 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 1500 users arriving over 60min @ 1500/h, ~4.6 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot-nosuppush.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 265.5 / 250.5 / 523.7 (2292 syncs) |
| full syncs p50 / p95 s | 275.4 / 532.8 (25 of 2292, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.xlarge |
| autovacuum | on |

## `2026-10-29T04-10-05Z-case12-anchorA-fix1103-r1-7205831`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-29T04-10-05Z-case12-anchorA-fix1103-r1-7205831/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-29T04-10-05Z-case12-anchorA-fix1103-r1-7205831/2026-10-29T04-10-05Z-case12-anchorA-fix1103-r1-7205831.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-29T04-10-05Z-case12-anchorA-fix1103-r1-7205831/2026-10-29T04-10-05Z-case12-anchorA-fix1103-r1-7205831.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 31193 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 208 / 417 / 588 / 1872 |
| mean ms | 219 |
| mean throughput rps | 8.47 |
| app CPU seconds | 3,876 |
| app CPU | 51% mean, peak 69% |
| app heap | 989 MB mean, peak 1,734 of 5,120 MB max |
| RDS CPU | 21% mean, peak 26% |
| RDS memory | 4,343 MB freeable at its lowest, swap peak 1 MB |
| app CPU s per sync | 2.30 |
| harness commit | 72058313ae0a9034e46c4188f0bb9475cd11da46 (run id says `7205831`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | b4c611977 |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.6 / 0.64 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~1.9 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 60.2 / 72.0 / 180.7 (1682 syncs) |
| full syncs p50 / p95 s | 82.0 / 225.7 (12 of 1682, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.large |
| autovacuum | on |

## `2026-10-29T05-47-37Z-case15-tenaday-anchorB-fix1103-r1-7205831`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-29T05-47-37Z-case15-tenaday-anchorB-fix1103-r1-7205831/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-29T05-47-37Z-case15-tenaday-anchorB-fix1103-r1-7205831/2026-10-29T05-47-37Z-case15-tenaday-anchorB-fix1103-r1-7205831.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-29T05-47-37Z-case15-tenaday-anchorB-fix1103-r1-7205831/2026-10-29T05-47-37Z-case15-tenaday-anchorB-fix1103-r1-7205831.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 204044 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 29 / 293 / 443 / 8214 |
| mean ms | 80 |
| mean throughput rps | 49.55 |
| app CPU seconds | 7,434 |
| app CPU | 44% mean, peak 68% |
| app heap | 1,068 MB mean, peak 1,926 of 5,120 MB max |
| RDS CPU | 48% mean, peak 69% |
| RDS memory | 3,898 MB freeable at its lowest, swap peak 3 MB |
| app CPU s per sync | 3.24 |
| harness commit | 72058313ae0a9034e46c4188f0bb9475cd11da46 (run id says `7205831`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | b4c611977 |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.62 / 0.64 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 1500 users arriving over 60min @ 1500/h, ~4.0 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot-nosuppush.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 264.9 / 257.4 / 552.5 (2292 syncs) |
| full syncs p50 / p95 s | 275.1 / 695.3 (18 of 2292, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.xlarge |
| autovacuum | on |

## `2026-10-29T09-21-16Z-case12-anchorA-fix1098b-r1-7205831`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-29T09-21-16Z-case12-anchorA-fix1098b-r1-7205831/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-29T09-21-16Z-case12-anchorA-fix1098b-r1-7205831/2026-10-29T09-21-16Z-case12-anchorA-fix1098b-r1-7205831.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-29T09-21-16Z-case12-anchorA-fix1098b-r1-7205831/2026-10-29T09-21-16Z-case12-anchorA-fix1098b-r1-7205831.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 31289 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 671 / 2107 / 2600 / 3931 |
| mean ms | 829 |
| mean throughput rps | 8.48 |
| app CPU seconds | 6,518 |
| app CPU | 72% mean, peak 99% |
| app heap | 1,096 MB mean, peak 1,815 of 5,120 MB max |
| RDS CPU | 21% mean, peak 29% |
| RDS memory | 4,085 MB freeable at its lowest, swap peak 4 MB |
| app CPU s per sync | 3.88 |
| harness commit | 72058313ae0a9034e46c4188f0bb9475cd11da46 (run id says `7205831`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 041438efe |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.58 / 0.65 |
| est. sync overhead s | 0.07 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~7.0 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 68.2 / 83.2 / 211.0 (1682 syncs) |
| full syncs p50 / p95 s | 101.6 / 254.1 (15 of 1682, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.large |
| autovacuum | on |

## `2026-10-29T12-03-22Z-case15-tenaday-anchorB-fix1098b-r1-7205831`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-29T12-03-22Z-case15-tenaday-anchorB-fix1098b-r1-7205831/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-29T12-03-22Z-case15-tenaday-anchorB-fix1098b-r1-7205831/2026-10-29T12-03-22Z-case15-tenaday-anchorB-fix1098b-r1-7205831.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-29T12-03-22Z-case15-tenaday-anchorB-fix1098b-r1-7205831/2026-10-29T12-03-22Z-case15-tenaday-anchorB-fix1098b-r1-7205831.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 202058 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 29 / 427 / 711 / 8569 |
| mean ms | 103 |
| mean throughput rps | 48.63 |
| app CPU seconds | 9,594 |
| app CPU | 55% mean, peak 86% |
| app heap | 1,060 MB mean, peak 1,924 of 5,120 MB max |
| RDS CPU | 48% mean, peak 71% |
| RDS memory | 3,906 MB freeable at its lowest, swap peak 4 MB |
| app CPU s per sync | 4.19 |
| harness commit | 72058313ae0a9034e46c4188f0bb9475cd11da46 (run id says `7205831`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 041438efe |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.23 / 0.31 |
| est. sync overhead s | 0.03 |
| injection | profile steady, 1500 users arriving over 60min @ 1500/h, ~5.0 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot-nosuppush.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 266.4 / 254.7 / 526.1 (2292 syncs) |
| full syncs p50 / p95 s | 245.7 / 502.8 (30 of 2292, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.xlarge |
| autovacuum | on |

## `2026-10-29T15-07-09Z-case12-anchorA-rc18.3-r1-7205831`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-29T15-07-09Z-case12-anchorA-rc18.3-r1-7205831/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-29T15-07-09Z-case12-anchorA-rc18.3-r1-7205831/2026-10-29T15-07-09Z-case12-anchorA-rc18.3-r1-7205831.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-29T15-07-09Z-case12-anchorA-rc18.3-r1-7205831/2026-10-29T15-07-09Z-case12-anchorA-rc18.3-r1-7205831.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 31265 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 174 / 332 / 489 / 1848 |
| mean ms | 180 |
| mean throughput rps | 8.49 |
| app CPU seconds | 3,270 |
| app CPU | 43% mean, peak 56% |
| app heap | 947 MB mean, peak 1,732 of 5,120 MB max |
| RDS CPU | 20% mean, peak 25% |
| RDS memory | 4,402 MB freeable at its lowest, swap peak 4 MB |
| app CPU s per sync | 1.94 |
| harness commit | 72058313ae0a9034e46c4188f0bb9475cd11da46 (run id says `7205831`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 946553685 |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.31 / 0.42 |
| est. sync overhead s | 0.05 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~1.5 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / False |
| sync duration p50 / mean / p95 s | 59.6 / 71.3 / 179.1 (1682 syncs) |
| full syncs p50 / p95 s | 80.9 / 224.4 (14 of 1682, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.large |
| autovacuum | on |

## `2026-10-29T16-27-09Z-case13-anchorC-rc18.3-r1-7205831`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-29T16-27-09Z-case13-anchorC-rc18.3-r1-7205831/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-29T16-27-09Z-case13-anchorC-rc18.3-r1-7205831/2026-10-29T16-27-09Z-case13-anchorC-rc18.3-r1-7205831.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-29T16-27-09Z-case13-anchorC-rc18.3-r1-7205831/2026-10-29T16-27-09Z-case13-anchorC-rc18.3-r1-7205831.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 58912 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 159 / 396 / 597 / 6090 |
| mean ms | 174 |
| mean throughput rps | 16 |
| app CPU seconds | 4,412 |
| app CPU | 58% mean, peak 73% |
| app heap | 1,049 MB mean, peak 1,848 of 5,120 MB max |
| RDS CPU | 36% mean, peak 43% |
| RDS memory | 4,299 MB freeable at its lowest, swap peak 4 MB |
| app CPU s per sync | 1.78 |
| harness commit | 72058313ae0a9034e46c4188f0bb9475cd11da46 (run id says `7205831`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 946553685 |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.28 / 0.3 |
| est. sync overhead s | 0.03 |
| injection | profile steady, 1682 users arriving over 60min @ 1682/h, ~2.8 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | False / True |
| sync duration p50 / mean / p95 s | 59.8 / 57.2 / 179.8 (2474 syncs) |
| full syncs p50 / p95 s | 81.2 / 83.7 (33 of 2474, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.large |
| autovacuum | on |

## `2026-10-29T19-03-39Z-case15-tenaday-anchorB-rc18.3-batch50-r1-7205831`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-29T19-03-39Z-case15-tenaday-anchorB-rc18.3-batch50-r1-7205831/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-29T19-03-39Z-case15-tenaday-anchorB-rc18.3-batch50-r1-7205831/2026-10-29T19-03-39Z-case15-tenaday-anchorB-rc18.3-batch50-r1-7205831.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-29T19-03-39Z-case15-tenaday-anchorB-rc18.3-batch50-r1-7205831/2026-10-29T19-03-39Z-case15-tenaday-anchorB-rc18.3-batch50-r1-7205831.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 96803 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 76 / 248 / 388 / 6942 |
| mean ms | 109 |
| mean throughput rps | 23.42 |
| app CPU seconds | 5,219 |
| app CPU | 30% mean, peak 44% |
| app heap | 1,036 MB mean, peak 1,860 of 5,120 MB max |
| RDS CPU | 40% mean, peak 59% |
| RDS memory | 4,282 MB freeable at its lowest, swap peak 4 MB |
| app CPU s per sync | 2.28 |
| harness commit | 72058313ae0a9034e46c4188f0bb9475cd11da46 (run id says `7205831`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 946553685 |
| dataset | pilot-day-180 |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.27 / 0.31 |
| est. sync overhead s | 0.03 |
| injection | profile steady, 1500 users arriving over 60min @ 1500/h, ~2.6 requests in flight (rps x mean), ramp 33640 s |
| sync | mode realistic, feeder case5-users-pilot-nosuppush.csv (1682 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 262.5 / 249.1 / 539.6 (2292 syncs) |
| full syncs p50 / p95 s | 271.9 / 529.2 (22 of 2292, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.xlarge |
| autovacuum | on |

## `2026-10-29T21-16-32Z-case15-5k-anchorD-rc18.3-batch50-r1-7205831`

Artefacts: `s3://avni-loadtest-936573213727/artefacts/2026-10-29T21-16-32Z-case15-5k-anchorD-rc18.3-batch50-r1-7205831/` — [download the run as one zip](https://ap-south-1.console.aws.amazon.com/s3/object/avni-loadtest-936573213727?region=ap-south-1&prefix=artefacts/2026-10-29T21-16-32Z-case15-5k-anchorD-rc18.3-batch50-r1-7205831/2026-10-29T21-16-32Z-case15-5k-anchorD-rc18.3-batch50-r1-7205831.zip) from the AWS console (load-test account), or `aws s3 cp s3://avni-loadtest-936573213727/artefacts/2026-10-29T21-16-32Z-case15-5k-anchorD-rc18.3-batch50-r1-7205831/2026-10-29T21-16-32Z-case15-5k-anchorD-rc18.3-batch50-r1-7205831.zip .`; unzip and open `index.html`.

| | |
|---|---|
| requests (ok) | 224688 |
| failed | 0 (0.0%) |
| response time p50 / p95 / p99 / max ms | 68 / 205 / 247 / 2714 |
| mean ms | 81 |
| mean throughput rps | 53.13 |
| app CPU seconds | 10,485 |
| app CPU | 31% mean, peak 42% |
| app heap | 1,146 MB mean, peak 2,037 of 5,120 MB max |
| RDS CPU | 21% mean, peak 29% |
| RDS memory | 20,898 MB freeable at its lowest, swap peak 0 MB |
| app CPU s per sync | 1.81 |
| harness commit | 72058313ae0a9034e46c4188f0bb9475cd11da46 (run id says `7205831`) |
| tree dirty | False |
| target | https://loadtest.avniproject.org |
| server build | 946553685 |
| dataset | pilot-day-180-5k |
| injector | i-041afc7c6e0761195 (Linux aarch64, java 17.0.20.1, 2 cpu, heap 1024 MB) |
| injector RTT min / median ms | 0.23 / 0.29 |
| est. sync overhead s | 0.03 |
| injection | profile steady, 5000 users arriving over 60min @ 5000/h, ~4.3 requests in flight (rps x mean), ramp 111800 s |
| sync | mode realistic, feeder case5-users-pilot-5k-nosuppush.csv (5590 rows), auth none, page 1000 |
| entities | 75 pulled of 79 (openchs-models@1.33.81) |
| push / co-tenants | True / True |
| sync duration p50 / mean / p95 s | 298.1 / 292.2 / 522.4 (5792 syncs) |
| full syncs p50 / p95 s | 340.0 / 500.6 (63 of 5792, recorded) |
| cache policy | warm-after-discarded-warmup-m6g.2xlarge |
| autovacuum | on |
