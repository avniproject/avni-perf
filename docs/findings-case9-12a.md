# Case 9 / 12a: the data path saturates on app CPU, with the database at a fifth of its capacity

**12 October 2026.** `2026-10-12T02-07-36Z-case9-12a-cf77819`. A stress ramp from **200 to 3,000
syncs/hour over 45 minutes**, ten tenants, realistic mix, **`PUSH=off`**, against `pilot-day-180`.
Warmed first. 1,200 syncs injected; all completed or aborted; the run broke, which is what case 9
is for.

**The question this ramp existed to answer was not "where is the knee" but "which resource names
it".** Case 1 had already found a knee and named the app server's 2 vCPU — but its organisation
holds no field data, so `ReadIOPS` was **0.0 throughout** and it saturated on JSON serialisation of
config with nothing read from disk. Every other case pulls 10,800 to 43,300 records out of 6.9M
rows. A data-path ramp confirming "it is CPU again" was a finding to be established, not assumed.

## It is CPU again, and now that is evidence

| IST | app CPU | RDS CPU | ReadIOPS | ReadLatency ms | connections |
|---|---|---|---|---|---|
| 07:37 | 6.8 | 6.9 | 0.0 | 0.00 | 5 |
| 07:47 | 40.7 | 15.9 | 28.8 | 0.61 | 7 |
| 07:52 | 71.2 | 18.1 | 24.5 | 0.61 | 11 |
| 07:57 | 64.6 | 16.7 | 50.1 | 0.62 | 9 |
| 08:02 | **97.8** | 24.8 | 121.9 | 0.60 | 30 |
| 08:07 | **99.2** | 22.6 | 190.5 | 0.56 | 85 |
| 08:17 | **99.2** | 20.8 | 169.0 | 0.60 | 98 |
| 08:23 | **99.2** | 20.6 | **312.4** | 0.61 | 98 |
| 08:32 | **99.1** | 16.9 | 29.0 | 0.58 | 98 |
| 08:34 | 38.8 | 13.2 | 17.5 | 0.57 | 9 |

**The app server pinned at 99.0–99.3% for thirty minutes.** RDS peaked at 24.8% and spent the
saturated period between 15.7% and 22.6%.

**`ReadIOPS` moved, and that is the point.** It reached **312** against case 1's 0.0, so this ramp
genuinely exercised the disk path case 1 could not. **And `ReadLatency` never left 0.50–0.78 ms.**
The reads happened and cost nothing. Storage is not the constraint; neither is database CPU.

**Connections climbed to 98 and pegged there** — the symptom `execution-plan.md` warned would
present as the cause, as it did in case 1's cold run. The evidence that it is downstream: if the
pool were binding, the database behind it would be busy. It sat at a fifth of its capacity.

## It is request work, not garbage collection

**The obvious alternative explanation had to be excluded, because a JVM thrashing GC also reads
99% CPU** — and the two imply opposite remedies. More vCPU is the wrong relief if the real
constraint is allocation against a fixed heap.

New Relic has been attached as a javaagent on every run (`roles/newrelic`, `-Xms2560m -Xmx5120m`,
heap matched to production deliberately so GC behaviour transfers). Its CPU series agrees with
CloudWatch to a tenth of a percent, which is a useful independent check on the figure above.

| IST | heap avg MB | heap peak MB | of 5,120 | G1 Old Gen | Eden | app CPU |
|---|---|---|---|---|---|---|
| 07:35–08:00 | ~930 | ~1,680 | 33% | ~2,082 | ~780 | 8.6 → 93.4 |
| 08:05 | 2,570 | 4,914 | 96% | 3,385 | 432 | 99.3 |
| 08:15 | 2,912 | 4,858 | 95% | 3,741 | 326 | 99.2 |
| 08:25 | 3,108 | 5,023 | **98%** | **3,814** | 354 | 99.4 |
| 08:35 | 1,086 | 1,794 | 35% | 2,113 | 806 | 0.1 |

**Heap peak went from 33% to 98% of max at exactly the moment CPU pinned, Old Gen grew 83% and
Eden more than halved.** On its own that looks like a collector in trouble — G1 shrinking the young
generation to keep pace while promoting heavily is what pressure looks like.

**It was not. Measured GC time during the slow-response period was 1 to 1.4 seconds per minute,
most of it Old Gen** — about 2% of wall clock, and under 2.5% of a 2 vCPU budget. A JVM saturating
on collection would show tens of seconds per minute.

**So the 99% is request work.** The heap behaviour is G1 coping with a large live set rather than
failing: at ~113 devices in flight, each holding a 1,000-record page mid-serialisation, gigabytes
of short-lived data is the expected shape. It collected it for 2% of the CPU.

**Worth carrying forward as headroom rather than a finding**: Old Gen reached 3,814 MB of a
5,120 MB ceiling, 75%, while GC stayed cheap. That is comfortable now and is the number to watch if
concurrency rises or `PAGE_SIZE` grows, because the margin is finite and the collector's cost is
not linear in it.

**The GC figure is not in NRQL.** The agent publishes `apm.service.java.memory.pool` and the heap
gauges but no GC *time* — 45 metric names, none GC-related — so it was read from New Relic's JVM
page rather than queried. Anyone reproducing this should expect to do the same.

## What broke, and how

| | |
|---|---|
| requests | 21,607, of which **116 failed (0.54%)** |
| | 63 timeouts to one ALB address, 52 to the other, **1 × HTTP 502** |
| mean / p50 / p95 / p99 | 17,378 / 5,539 / 53,318 / 59,056 ms |
| max | **60,001 ms — the client's own ceiling** |
| sync duration p50 / p95 | 260.1 / 749.7 s (1,084 syncs recorded) |

**It stopped answering rather than falling over.** 115 of 116 failures are the injector's 60-second
timeout; exactly one request got a 502. Nothing crashed, nothing refused a connection, and the
database never complained. The degradation is latency all the way to the client's patience.

The run failed its own `MAX_FAILED_PERCENT` gate of 0.05% and `update-run-log.sh` filed the caveat
without being asked — **read its throughput and latency as a run that broke**, not as a measurement
of capacity.

## The knee

**Roughly 1,160 to 1,290 syncs/hour.** 1,200 syncs were retired between 07:37:33 and ~08:33, which
is 1,286/hour gross; 115 of those aborted on a failed page, so the rate of syncs that completed
properly is nearer 1,163/hour. App CPU crossed 90% between 07:57 and 08:02, where the ramp was
demanding 1,413 and 1,724 syncs/hour respectively.

Against the other measured ceilings:

| run | workload | syncs/hour | rps | app CPU |
|---|---|---|---|---|
| case 1, warm burst | config only, no field data | — | **50** | 83–99% |
| case 11 burst, 9 Oct | realistic mix, **push on** | **775** | 18.5 | 99.1% |
| **12a** | realistic mix, **push off** | **~1,160–1,290** | **6.2** | 99.0–99.3% |

**Every one of these saturates the same 2 vCPU at a wildly different request rate**, which is the
useful generalisation: *requests per second is not a capacity number for this server.* Case 1's
config requests are cheap and it managed 50 rps; 12a's paged data requests are expensive and it
managed 6.2. Push requests are cheap too — `Media uploadUrl` alone was 39% of every request in a
pushing run — which is why case 11's burst shows a *higher* rps than 12a while retiring *fewer*
syncs per hour. **Syncs per hour is the unit that compares; rps is not.**

## What this does not say

**One app server, 2 vCPU.** The ceiling is a property of this instance and configuration. Whether
the application scales horizontally is a separate question, and
`avni-server-multi-replica-blockers` says it currently does not.

**ETL is off**, so these figures describe sync against a database with nothing else on it.

**Push is off.** The write path — WAL, lock contention, autovacuum — is untested here by design;
12c turns it on. The pair is what isolates it, and the gap between 775 and ~1,200 syncs/hour is the
first measurement of what pushing costs.

**The database was never pressed.** 12b exists precisely because of this: every sync a full pull
rather than an incremental slice moves bytes rather than request count, which is the one shape that
might make RDS, the buffer cache or `ReadIOPS` bind before the app tier does.
