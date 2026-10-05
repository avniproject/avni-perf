# Case 1 — findings, 5 October 2026

Case 1 is the training cohort: a trainer says "sync now" and a hundred devices, all empty, pull
the same reference data at once. Six runs on 5 Oct 2026 swept the arrival window from 15 minutes
down to 15 seconds and located the knee. Artefacts and the per-run table are in [`run-log.md`](run-log.md); each run's settings and environment in [`run-log-detail.md`](run-log-detail.md).

## The answer

**100 devices arriving over 90 seconds or more is comfortable. 60 seconds is not.** The knee sits
between those two windows — between roughly 48 and 72 requests per second of demand — and the app
server's 2 vCPU is what names it. Not the database, not the injector.

| arrival window | 15 min | 180 s | 120 s | 90 s | 60 s | 15 s |
|---|---|---|---|---|---|---|
| devices arriving per second | 0.11 | 0.56 | 0.83 | 1.11 | 1.67 | 6.67 |
| demand rps | 4.8 | 23.9 | 35.8 | 47.8 | 71.7 | 286.7 |
| achieved rps | 4.77 | 22.75 | 33.33 | 43.00 | 52.44 | 56.58 |
| **keeping up with demand** | **100%** | **95%** | **93%** | **90%** | **73%** | **20%** |
| p95 ms | 202 | 196 | 222 | 366 | 2,223 | 6,745 |
| p99 ms | 297 | 331 | 437 | 641 | 3,974 | 8,773 |
| mean ms | 45 | 42 | 50 | 74 | 417 | 1,254 |
| **requests in flight** | 0.2 | 1.0 | 1.7 | 3.2 | 21.9 | 71.0 |
| devices in flight | ~1 | 5.5 | 8.4 | 11.8 | ~27 | ~80 |
| per-sync duration s | — | **10.5** | **10.8** | **11.8** | ~22 | ~61 |
| failures | 0 | 0 | 0 | 0 | 0 | 0 |

Every run issued the same 4,300 requests from the same 100 users against the same dataset. Only
the arrival window differed.

**The fall-off is abrupt.** From 180 s to 90 s the system tracks demand within 10% and latency
barely moves — p95 of 196, 222, 366 ms against 202 ms on an effectively idle baseline. Then one
step to 60 s raises demand 50% and **p95 jumps 6x**, 366 to 2,223 ms, while throughput gains 22%.
Requests in flight go 3.2 to 21.9: a 7x rise for a 1.5x increase in demand. That is queue growth,
not work.

**The usable ceiling is 45-50 rps, not the 55 an earlier revision reported.** 55 is what the
environment achieves while *saturated* — 52.44 at 60 s, 56.58 at 15 s — and the last 20% of
throughput costs six times the latency. The honest figure is what it sustains while still keeping
up with demand, which tops out near 43-48.

**Two concurrency figures, because they answer different questions.** Requests in flight is the
server's mean queue depth and is exact: `rps x mean response`, no assumed durations. It is what p95
responds to. Devices in flight is the scenario's narrative — how much of the cohort is mid-sync —
and for the three runs at and above 90 s it is now *measured* rather than derived, from
`sync-durations.csv`.

**Earlier revisions got the knee wrong twice.** The first put it between the 60 s and 15 s runs,
reading their flat throughput as a bracket — but 60 s was already 27% short of its own demand, so
both sat on the plateau. The second correctly moved it below 60 s without saying where. These
three runs settle it. Note the departure from linear begins *before* 90 s — a 10% shortfall is
still a shortfall — so 90 s is the left edge of the knee, not a clean pass.

## Per-sync duration is ~10.5 s, not the 6 s the harness assumes

The runs at and above 90 s are the first to archive `sync-durations.csv`, so this is measured per
sync rather than inferred from wall time:

| window | mean | p50 | p95 | max |
|---|---|---|---|---|
| 180 s | 10,468 ms | 10,447 | 10,715 | 10,840 |
| 120 s | 10,792 ms | 10,772 | 11,156 | 11,470 |
| 90 s | 11,766 ms | 11,790 | 12,315 | 12,587 |

**A full case-1 sync costs about 10.5 seconds uncontended**, stretching 12% by 90 s. The profile
banner's "~N in flight at a 6s reference-data sync" therefore understates device concurrency by
roughly two: at 90 s it prints ~7 where the measured figure is 11.8. Six seconds is a fair estimate
of *server* time within a sync; it is not the sync.

The distribution is tight — p95 within 5% of the median at every window — so these are not means
hiding a tail. Every device in the cohort has much the same experience.

**The duty cycle is measured too**, and it reconciles the two concurrency figures. Requests in
flight over devices in flight gives the share of a sync spent awaiting a response: 17% at 180 s,
20% at 120 s, 27% at 90 s, rising to ~82% and ~88% past the knee. Below the knee a device is mostly
in its modelled storage pause; above it, mostly waiting on the server. That shift is saturation
seen from the device's side.

## Why the app server, and not the other two

Three independent measurements agree, which is what makes this a finding rather than a guess.

**App server CPU reached 99.25%** during the 15-second-burst run. It is an `m6g.large` — 2 vCPU,
8 GiB, fixed-performance.

**The database was not working hard.** RDS CPU peaked at 36%. `pg_stat_statements` was reset
immediately before the run, and every statement came back between 0.03 ms and 1.3 ms mean. Total
database execution time was roughly 41 seconds against 4,300 × 1,254 ms ≈ **5,392 seconds** of
cumulative client wait — under 1%. There is no slow query to find here; at this dataset size the
database has headroom.

**The injector was idle**: load average 0.35 across 4 CPUs on an `m6g.xlarge`. Worth stating
because a saturated injector produces the same curve as a saturated server, and the two are only
distinguishable if you look. The metadata records the injector's CPU count, heap and measured RTT
for exactly this reason.

**It degrades gracefully.** Zero failures at every level, and 70% of requests stayed under 800 ms
even at ~40 devices. Nothing fell over; it queued.

## One query worth watching

The row-level-security organisation lookup —
`SELECT coalesce(array_agg(org_id), …) FROM (SELECT id AS org_id FROM public.org_ids …)` — ran
**65,578 times** for 4,300 requests, about **15 calls per request**. At 0.03 ms each it is
trivial today and nowhere near the bottleneck. It is recorded because per-request multipliers are
the things that stop being trivial, and this is the largest one in the trace by call count.

## What these numbers are not

* **No field data.** The cohort's village holds no subjects by design, so this measures the
  config and metadata sync path. A field worker's sync pulls subjects too. 75 of 79 entities were
  pulled; the subject-keyed ones were empty.
* **No push.** `PUSH` disabled, so this is read-path only.
* **No co-tenant load.** `enable_etl = false`, and the ETL host, export/import jobs and webapp are
  absent (#112 F5.4, deferred). They share the instance, the pool and the IOPS budget in
  production, so **every number here is optimistic by an unmeasured margin**.
* **Cache state was incidental**, not warm-from-reload: the environment had been restarted and
  then variously queried. Recorded as `warm-incidental-no-reset` on each run.
* **The first run is not a cohort measurement.** Its 15-minute window spread 100 arrivals one
  every nine seconds, and a sync takes ~10.5 s, so barely more than one device was ever in flight.
  Its comfortable 202 ms p95 is the per-sync cost and says nothing about a herd. The harness has
  since renamed `BURST_MINUTES` to `BURST_SECONDS` and defaulted it to 60 for this reason.
* **The 180 s run is marginally faster than the idle baseline** — p95 196 vs 202 ms, mean 42 vs 45.
  That is cache warmth from six runs in succession, not a real effect, and it is why `CACHE_POLICY`
  is recorded per run. Treat the two as equal.

## Before quoting any of this

**Enable EC2 detailed monitoring.** Basic monitoring reports 5-minute buckets, so the 99.25% is
the maximum sample inside the window rather than a sustained curve. The claim "the app server
saturated" is sound — 99.25% cannot happen without it — but the *shape* of the saturation is
unreadable at that granularity, and a knee is a shape.

## What to do next

* **Narrow the knee to 60-90 s** if a sharper number is wanted. 75 s gives 57.3 rps of demand,
  between the 90 s run that keeps up and the 60 s one that does not; one run halves the remaining
  interval. Worth it only if the question is "what is the smallest window that works" rather than
  "does a minute work" — it does not.
* **`app_instance_class` moves the ceiling.** The database peaked at 36% CPU with every statement
  under 1.3 ms; the app server hit 99.25%. A run at the next size up would say whether throughput
  scales with vCPU or whether something else takes over.
* **Enable EC2 detailed monitoring first.** The knee is a shape and 5-minute buckets cannot show
  one.
* **Then add the co-tenants** (F5.4). Everything above is a quiet system; production is not. The
  knee will move left.

The 300 s window an earlier revision suggested is not worth running: 180 s already keeps up with
95% of demand at idle-baseline latency, so 300 s would only confirm that less load is easier.
