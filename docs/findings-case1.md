# Case 1 — findings, 5 October 2026

Case 1 is the training cohort: a trainer says "sync now" and a hundred devices, all empty, pull
the same reference data at once. Three runs on 5 Oct 2026 swept the arrival window and found the
limit. Artefacts and the per-run table are in [`run-log.md`](run-log.md).

## The answer

**The environment saturates at about 55 requests per second, and the app server's 2 vCPU is what
names it.** Not the database, not the injector.

| arrival window | 15 min | 60 s | 15 s |
|---|---|---|---|
| devices arriving per second | 0.11 | 1.67 | 6.67 |
| **requests in flight** (rps x mean) | **0.2** | **22** | **71** |
| devices in flight (derived) | ~1 | ~27 | ~80 |
| p50 ms | 19 | 152 | 486 |
| p95 ms | 202 | 2,242 | 6,768 |
| p99 ms | 297 | 4,014 | 9,013 |
| max ms | 716 | 5,860 | 16,195 |
| mean ms | 45 | 417 | 1,254 |
| throughput rps | 4.77 | 52.44 | 56.58 |
| failures | 0 | 0 | 0 |

**Two concurrency figures, because they answer different questions.** Requests in flight is the
server's mean queue depth and is exact: `rps x mean response`, no assumed durations. It is what p95
responds to, and it is the mechanism. Devices in flight is the scenario's narrative — how much of
the cohort is mid-sync — and it is derived rather than measured: wall time minus the arrival window
gives the sync duration (~22 s and ~61 s against ~6 s unloaded), and `users x duration / wall` gives
the count. The two differ by a device's duty cycle: it issues ~43 requests in sequence with a
modelled storage pause between them, so it is not in flight continuously. The derivation checks
out against the measurement both ways — 27 devices at 80% request-time predicts 21.6 requests
against 21.9 measured; 80 at 88% predicts 70.4 against 71.0.

Earlier revisions of this document read `~10` and `~40` devices. That came from
`users / window x 6.0` — Little's law against the *unloaded* sync — which understates concurrency
exactly where contention makes it interesting. `update-run-log.sh` now reports the measured
request depth instead.

Every run issued the same 4,300 requests from the same 100 users against the same dataset. Only
the arrival window differed.

**Quadrupling the arrival rate — 1.67 to 6.67 devices a second — bought 8% more throughput and
tripled p95.** That is queueing past a knee, not work being done: beyond saturation, added load
converts into latency rather than throughput. Concurrency itself rose ~3x (27 to 80 devices, 22 to
71 requests), not 4x, because the cohort is finite: at ~80 of 100 devices mid-sync there is little
left to recruit.

**The knee is below the 60-second run, not between it and the 15-second one.** Demand in requests
is `requests per device x arrival rate`, which needs no assumption about how long a sync takes:

| arrival window | demand rps | achieved rps | keeping up |
|---|---|---|---|
| 15 min | 4.78 | 4.77 | **99.8%** |
| 60 s | 71.7 | 52.44 | **73.1%** |
| 15 s | 286.7 | 56.58 | **19.7%** |

At 60 seconds the environment is already 27% short of demand, so that run is past the knee rather
than below it. Both measured points above 1.67 devices a second sit on the plateau.

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
  every nine seconds, which at a ~6-second sync is one device at a time. Its comfortable 202 ms
  p95 is the per-sync cost, and it says nothing about a herd. The harness has since renamed
  `BURST_MINUTES` to `BURST_SECONDS` and defaulted it to 60 for this reason.

## Before quoting any of this

**Enable EC2 detailed monitoring.** Basic monitoring reports 5-minute buckets, so the 99.25% is
the maximum sample inside the window rather than a sustained curve. The claim "the app server
saturated" is sound — 99.25% cannot happen without it — but the *shape* of the saturation is
unreadable at that granularity, and a knee is a shape.

## What to do next

* **`app_instance_class` is the variable that moves this.** The database has headroom; the app
  server does not. A run at the next size up would say whether throughput scales with vCPU or
  whether something else takes over as the constraint.
* **Fill in the curve with *longer* windows, not shorter ones.** `BURST_SECONDS` of 120, 180 and
  300 give 0.83, 0.56 and 0.33 devices a second — demand of 35.8, 23.9 and 14.3 rps, which is the
  interval the knee is in. 30 and 20 would give 3.33 and 5.0 a second, both above the 60-second
  run and both on the plateau: two more points confirming a ceiling already measured twice.
* **Then add the co-tenants** (F5.4). Everything above is a quiet system, and production is not
  one.
