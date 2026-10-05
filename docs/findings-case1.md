# Case 1 — findings, 5 October 2026

Case 1 is the training cohort: a trainer says "sync now" and a hundred devices, all empty, pull
the same reference data at once. Three runs on 5 Oct 2026 swept the arrival window and found the
limit. Artefacts and the per-run table are in [`run-log.md`](run-log.md).

## The answer

**The environment saturates at about 55 requests per second, and the app server's 2 vCPU is what
names it.** Not the database, not the injector.

| ~devices in flight | 1 | 10 | 40 |
|---|---|---|---|
| arrival window | 15 min | 60 s | 15 s |
| p50 ms | 19 | 152 | 488 |
| p95 ms | 202 | 2,223 | 6,745 |
| p99 ms | 297 | 3,974 | 8,773 |
| max ms | 716 | 5,860 | 16,195 |
| mean ms | 45 | 417 | 1,254 |
| throughput rps | 4.77 | 52.44 | 56.58 |
| failures | 0 | 0 | 0 |

Every run issued the same 4,300 requests from the same 100 users against the same dataset. Only
the arrival window differed.

**Going from ~10 to ~40 devices — four times the concurrency — bought 8% more throughput and
tripled p95.** That is queueing past a knee, not work being done: beyond saturation, added
concurrency converts into latency rather than throughput. The knee is between 10 and 40.

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
* **Fill in the curve between 10 and 40** devices — `BURST_SECONDS` of 30 and 20 — to locate the
  knee rather than bracket it.
* **Then add the co-tenants** (F5.4). Everything above is a quiet system, and production is not
  one.
