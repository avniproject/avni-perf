# Case 1 — findings, 5 October 2026

Case 1 is the training cohort: a trainer says "sync now" and a hundred devices, all empty, pull
the same reference data at once. Six runs on 5 Oct 2026 swept the arrival window from 15 minutes
down to 15 seconds and located the knee. Four further runs the same afternoon reproduced the two
harshest windows: two against a just-restarted server, which is its own finding below, and two
against a warm one that **reproduced the morning's numbers** — 56.58 rps against 56.58, p95 6,741
against 6,768. Artefacts and the per-run table are in [`run-log.md`](run-log.md); each run's
settings and environment in [`run-log-detail.md`](run-log-detail.md).

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
| p95 ms | 202 | 196 | 222 | 376 | 2,242 | 6,768 |
| p99 ms | 297 | 330 | 437 | 868 | 4,014 | 9,013 |
| mean ms | 45 | 42 | 50 | 74 | 417 | 1,254 |
| **requests in flight** | 0.2 | 1.0 | 1.7 | 3.2 | 21.9 | 71.0 |
| devices in flight | ~1 † | 5.5 | 8.4 | 11.8 | **36.0** ‡ | **80.2** ‡ |
| per-sync duration s | — | **10.5** | **10.8** | **11.8** | **31.0** ‡ | **60.9** ‡ |
| failures | 0 | 0 | 0 | 0 | 0 | 0 |

† Derived, not measured. `sync-durations.csv` was only archived from the 90 s run onwards
(9bfb8dc), so for the 15 min run the sync duration comes from wall time minus the arrival window.
`run-log.md` leaves that cell empty rather than deriving it; the derivation is kept here because
this is where it can be shown. The three measured runs agree with it exactly — 5.5, 8.4, 11.8 in
both documents.

‡ Measured, but from the **re-run** of that window at 12:01 and 12:02, not from the 09:43 and 09:53
runs the rest of the column describes. Those two predate `sync-durations.csv`. The substitution is
honest for the 15 s window, which the re-run reproduced to within 0.4% on every other figure, and
is the best available for 60 s, which came back 4.7% slower — see the reproduction note below.

**The derivation these two cells replace was wrong at one window and right at the other.** Wall time
minus the arrival window gave ~61 s at 15 s against a measured 60.9, and ~22 s at 60 s against a
measured 31.0 — low by 41%. It fails where some devices finish before the last ones arrive, which
is exactly the 60 s case. Treat a derived sync duration as an upper-bound-shaped guess, not a
number; this is why the column is now populated from the file.

**Percentiles are Gatling's OK column, matching `run-log.md`.** Worth stating because the console
summary prints Total and OK side by side and they are not the same number: 2,223 against 2,242 at
60 s, and 641 against 868 for p99 at 90 s — a 35% gap. Every run had zero failures, so the two
cover an identical population; they diverge because Gatling keeps separate histograms and the
bucket width grows with magnitude, which is why they agree exactly at 202 ms and not at all at
2 s. An earlier revision of this document quoted Total while the generated log quoted OK, which is
how the two came to disagree.

Every run issued the same 4,300 requests from the same 100 users against the same dataset. Only
the arrival window differed.

**The fall-off is abrupt.** From 180 s to 90 s the system tracks demand within 10% and latency
barely moves — p95 of 196, 222, 376 ms against 202 ms on an effectively idle baseline. Then one
step to 60 s raises demand 50% and **p95 jumps 6x**, 376 to 2,242 ms, while throughput gains 22%.
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
| 60 s ‡ | 30,957 ms | 31,774 | 40,168 | 40,831 |
| 15 s ‡ | 60,923 ms | 61,425 | 64,019 | 65,223 |

**A full case-1 sync costs about 10.5 seconds uncontended**, stretching 12% by 90 s. The profile
banner's "~N in flight at a 6s reference-data sync" therefore understates device concurrency by
roughly two: at 90 s it prints ~7 where the measured figure is 11.8. Six seconds is a fair estimate
of *server* time within a sync; it is not the sync.

The distribution is tight below the knee — p95 within 5% of the median at 180, 120 and 90 s — so
those are not means hiding a tail. At 60 s it spreads to 26% (31.8 s median, 40.2 s p95), which is
the queue sorting the cohort into early and late arrivals, and at 15 s it tightens again to 4%
because every device is uniformly stuck. Tightness at the two ends means opposite things: below the
knee nobody waits, above it everybody does.

**The duty cycle is measured too**, and it reconciles the two concurrency figures. Requests in
flight over devices in flight gives the share of a sync spent awaiting a response: 17% at 180 s,
20% at 120 s, 27% at 90 s, 75% at 60 s and 88% at 15 s. Below the knee a device is mostly in its
modelled storage pause; above it, mostly waiting on the server. That shift is saturation seen from
the device's side.

`sync-durations.csv` carries `serverMs` and `pausedMs` per sync, which reaches the same place by a
route that shares no arithmetic with it: 72% of the sync is server time at 60 s and 86% at 15 s,
against the 75% and 88% above. `pausedMs` is 8,685 ms in both, as it must be — the storage model is
a function of records pulled, and every run pulls the same ones. Two independent derivations within
three points is the reason to trust either.

## A restarted server delivers a third of its warm throughput

The runs at 11:37 and 11:41 were started seven minutes after the environment came back from a
stop/start. They are listed under "Runs that are not measurements" in `run-log.md` — out of the
table, because a row beside comparable runs reads as comparable — and each carries a
`provenance-correction.json` in its own prefix recording what it asserted and what was true. They
are not comparable to anything above:

| 60 s window | cold | warm, 20 min later | this morning |
|---|---|---|---|
| achieved rps | 18.43 | 50.00 | 52.44 |
| p95 ms | 25,635 | 2,767 | 2,242 |
| per-sync s | 182.3 | 31.0 | — |
| failures | 9 | 0 | 0 |

At the 15 s window it is 30.94 against 56.58 rps, and p95 14,214 against 6,741.

**A third of the throughput, nine times the p95 of its own warm re-run, and the first failures
this environment has produced**: nine requests hit the 60 s client timeout, and because a failed request ends that
user's chain, 108 of the 4,300 were never issued. Same host, same instance class, same parameter
group, same dataset, same harness commit — `gitSha d9eac3e`, `gitDirty false` on both.

The app server's JVM started at **11:34:14**. The first run began at **11:37:03** — two minutes and
49 seconds later.

What rules out the alternatives, all at 1-minute resolution:

* **Not the database.** RDS CPU 14-33%, `ReadIOPS` 0.0 and `ReadLatency` 0.0 throughout — the
  buffer cache had already refilled before the runs started, so whatever was cold was not there.
  Connections pegged at exactly 100 for four minutes where the morning's harshest run reached
  95-96: the application pool fully exhausted, which is a consequence of slow requests rather than
  a cause, since `max_connections` is in the hundreds either way.
* **Not the injector.** 3-22% CPU across 4 vCPU, load average 0.00.
* **Not the shape of the work.** `serverMs` is 181 s of the 190 s sync. The cost is server wait,
  not the modelled storage pause, which is 8,685 ms in every run on both sides of the comparison.
* **The ceiling is not what differs; what the CPU buys is.** The cold runs sat at 99.19-99.22%.
  The warm 60 s run peaked at 83% while achieving 2.7x the throughput, and the warm 15 s run
  reached the same 99% as its cold counterpart for nearly twice the work.

Two signs pointed at warm-up rather than damage before the re-run settled it: within the cold sweep
the *second* run beat the first by 67% despite four times the arrival rate, and twenty minutes and
two saturating runs later the same two windows returned 50.00 and 56.58 rps.

**This morning's gentle 15-minute run was an accidental warm-up.** It pushed 4,300 requests through
at 4.77 rps an hour before the 09:43 run, which is why the morning sweep never met this. A warm-up
belongs in the protocol rather than in the luck of the ordering — and the two cold runs record
`cachePolicy: warm-incidental-no-reset`, which is simply wrong. It was not a default: `build.gradle`
defaults the field to `unrecorded`, and that value appears nowhere in either repository, so it was
passed explicitly on all ten runs of the day including the two it was false for. That is the worse
version of the problem — an unset field announces itself, an asserted one does not — and it is why
the fix is a discarded warm-up pass in `prepare-run.sh` step 6 rather than a better default. The
field exists to make this distinguishable; it can only do that if what it says was done.

**In production, this is a deploy.** Every avni-server deploy restarts the JVM, and a cohort
syncing in the first minutes after one meets the cold curve rather than the warm one: at 100
devices over a minute, a 26-second p95 and the first timeouts. That is not a test artefact, it is
a property of the thing being deployed — and it argues for draining or warming a new instance
before it takes sync traffic.

## Why the app server, and not the other two

Three independent measurements agree, which is what makes this a finding rather than a guess.

**App server CPU reached 99.25%** during the morning's 15-second-burst run — an `m6g.large`, 2
vCPU, 8 GiB, fixed-performance. At the 1-minute resolution now enabled, the clearest sustained
curve comes from the cold runs, which were long enough to fill whole buckets: 99.19, 99.19, 97.38
and 99.22 across six consecutive minutes. The warm runs finish in 92 and 103 seconds, so their
load straddles bucket boundaries and reads as 83% and 65%. **1-minute buckets are still marginal
for a 90-second run** — below that, the injector's own timings are the only honest source.

**The database was not working hard.** RDS CPU peaked at 36%. `pg_stat_statements` was reset
immediately before the run, and every statement came back between 0.03 ms and 1.3 ms mean. Total
database execution time was roughly 41 seconds against 4,300 × 1,254 ms ≈ **5,392 seconds** of
cumulative client wait — under 1%. There is no slow query to find here.

**And the database was not small.** Verified against the live instance after the runs: **1,002,900
individuals and 3,610,652 encounters**, plus 66 indexes across the four big tables — the same count
prod carries, up from 39 before the 5 Oct parity work. Most of that volume belongs to orgs 10 and
11 (`states-day-180`, state-1 and state-2) rather than to the org 3 cohort being synced — though
the per-organisation split has not actually been measured, only inferred from the relative size of
the datasets loaded. Index depth, table size and the buffer cache are shared regardless, so
"the database has headroom" is a
stronger claim than it first reads: 36% CPU with zero read IOPS was achieved *at* that size, not
at a toy one. `program_enrolment` and `program_encounter` are empty database-wide, which is why the
program entities pull nothing.

`max_connections` is **829** and `pending_restart` is false on every parameter, so the 100 that
`DatabaseConnections` pegged at during the cold runs was the application pool with 729 connections
of headroom unused — the pool, not the server, is the limit worth tuning.

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
* **No co-tenant load — but co-tenant _data_ is present.** `enable_etl = false`, and the ETL host,
  export/import jobs and webapp are absent (#112 F5.4, deferred). They share the instance, the pool
  and the IOPS budget in production, so **every number here is optimistic by an unmeasured margin**.
  The *data* of other organisations is there, though — see the million individuals above — so what
  is missing is contention for CPU, connections and IOPS, not a realistically sized table.
* **Cache state was incidental**, not warm-from-reload: the environment had been restarted and
  then variously queried. Recorded as `warm-incidental-no-reset` on each run — accurately for the
  six morning runs and the two warm re-runs, wrongly for the two cold ones, where the label is
  just the unset default. The cold-start section is the measurement of how much this matters.
* **The first run is not a cohort measurement.** Its 15-minute window spread 100 arrivals one
  every nine seconds, and a sync takes ~10.5 s, so barely more than one device was ever in flight.
  Its comfortable 202 ms p95 is the per-sync cost and says nothing about a herd. The harness has
  since renamed `BURST_MINUTES` to `BURST_SECONDS` and defaulted it to 60 for this reason.
* **The 180 s run is marginally faster than the idle baseline** — p95 196 vs 202 ms, mean 42 vs 45.
  That is cache warmth from six runs in succession, not a real effect, and it is why `CACHE_POLICY`
  is recorded per run. Treat the two as equal. The cold runs later the same day put a size on that
  warmth: it is worth a factor of three, not a few percent.

## Before quoting any of this

**Detailed monitoring is now on** (avni-infra `d2f44e1`), so the figures above are 1-minute
averages and not 5-minute maxima. An earlier revision of this section asked for exactly that before
anyone quoted the saturation as a shape, and it is why the cold-start finding could be told apart
from a regression within the hour.

**The same window twice gave 52.44 and 50.00 rps, and p95 2,242 against 2,767.** Throughput
reproduces to 4.7% and p95 to 23%, on an idle single-tenant environment with nothing else running.
p95 at the knee is a steep function of queue depth, so quote it as "roughly 2-3 s at a 60 s
window", not as a four-digit figure. The 15 s window, further onto the plateau, reproduced to 0.4%.

**The archived context was checked against the live database, and it holds.** `stats.json` matches
to the row — 1,002,900 individuals and 3,610,652 encounters, both program tables empty.
`parity-report.md` is borne out by the 66-index count. `pg_settings.csv` agrees with `pg_settings`,
and every parameter reports `pending_restart = false`, with `max_connections` at 829.

That is a confirmation after the fact rather than a property of the method, and the distinction
still matters: the context directory is staged by hand, so all ten runs carried byte-identical
files because they were staged once, not because anything re-checked them. They happened to be
right. `tools/verify-live-env.sql` is the deliberate version of this check — static parameters
actually in effect, and row counts broken out by organisation, which `stats.json` cannot give
because it counts database-wide.

## What to do next

* **Narrow the knee to 60-90 s** if a sharper number is wanted. 75 s gives 57.3 rps of demand,
  between the 90 s run that keeps up and the 60 s one that does not; one run halves the remaining
  interval. Worth it only if the question is "what is the smallest window that works" rather than
  "does a minute work" — it does not.
* **`app_instance_class` moves the ceiling.** The database peaked at 36% CPU with every statement
  under 1.3 ms; the app server hit 99.25%. A run at the next size up would say whether throughput
  scales with vCPU or whether something else takes over.
* **Put a warm-up run in the protocol.** One gentle window — the 15-minute profile pushes all
  4,300 requests at 4.77 rps — before anything measured, and `CACHE_POLICY` set deliberately on
  every run rather than left to its default.
* **Then add the co-tenants** (F5.4). Everything above is a quiet system; production is not. The
  knee will move left.

The 300 s window an earlier revision suggested is not worth running: 180 s already keeps up with
95% of demand at idle-baseline latency, so 300 s would only confirm that less load is easier.
