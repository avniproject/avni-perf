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

**It was not.** New Relic's *Garbage collection CPU time* chart for the run window (its x-axis is
UTC; 12a ran 02:07–03:04, CPU pinned 02:32–03:02) shows GC flat at **0.02–0.05 through the entire
early ramp**, erupting at **02:35** and stopping at **03:05** — the saturated window to the minute.
Peaks reach **1.2–1.4**, overwhelmingly **G1 Old Generation**, with Young Generation and Concurrent
GC as thin caps. They are tall narrow bursts returning toward zero between, not a plateau.

**Even read pessimistically that is about 2% of wall clock** and ~1.2% of a 2 vCPU budget, with the
time-average lower again. A JVM saturating on collection would show tens of seconds per minute.

**GC did rise roughly thirtyfold — 0.04 to 1.4 — and still accounts for a couple of percent.** That
is the useful shape: the collector noticed the load and absorbed it cheaply.

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

### What the server saw, and the gap between the two — added 14 Oct 2026

New Relic confirms the reading above and adds the part the injector cannot see.

| | 12a | 12b-rerun |
|---|---|---|
| transactions recorded | 21,968 | 27,557 |
| **non-200 responses** | **0** | **0** |
| server-side max duration | **45.25 s** | **38.91 s** |
| server-side p99 / p99.9 | 37.0 / 41.0 s | 31.5 / 35.0 s |

**Not one non-200, in either run.** Every request the application started, it finished, correctly.
The single 502 in the table above came from the ALB rather than from the app — consistent with
New Relic having no error to show for it.

**And the server's own maximum is 45.25 s against a client that gave up at 60.** New Relic's clock
starts when Tomcat hands a request to the application, so time spent queued in the connector ahead
of that is invisible to it and fully visible to Gatling. With 107 to 274 requests in flight against
a bounded thread pool, that queue is where the missing fifteen-plus seconds went.

Two consequences:

* **Server-side latency understates what a device experiences, and the gap grows with saturation.**
  A p99 of 37 s here is a p99 of *application time*, not of what the client waited. Any use of
  these numbers as "what the user saw" needs that said.
* **The server did work nobody received.** 21,968 transactions recorded against 21,607 requests the
  injector counted — a timed-out request still runs to completion server-side. On a box pinned at
  99% CPU, that is capacity spent producing responses that were already abandoned.

**"Broke" means too slow to be waited for, not beginning to fail.** Worth keeping the distinction:
nothing refused a connection, nothing errored, and the database never complained. It is the same
conclusion as above, now with the server's side of it.

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
useful generalisation: *requests per second is not a capacity number for this server.*

> **Superseded 12 Oct, same day.** The sentence below concludes "syncs per hour is the unit that
> compares". It is not. Across five saturating runs syncs/hour ranges 424 to 1,161 while
> **records per hour holds at ~12.8M without push and ~11.0M with it** — see
> [`findings-case9-12b.md`](findings-case9-12b.md). Records is the capacity number; syncs/hour
> merely happens to be steadier than rps. Case 1's
config requests are cheap and it managed 50 rps; 12a's paged data requests are expensive and it
managed 6.2. Push requests are cheap too — `Media uploadUrl` alone was 39% of every request in a
pushing run — which is why case 11's burst shows a *higher* rps than 12a while retiring *fewer*
syncs per hour. **Syncs per hour is the unit that compares; rps is not.**

## Where the request work goes, from New Relic — added 14 Oct 2026

The finding above names the resource and not the work. This closes half of that, read from New
Relic's transaction data for the saturated window, **02:32–03:02 UTC**.

### One endpoint is 86% of it

| endpoint | calls | avg | total |
|---|---|---|---|
| **`encounter (GET)`** | 10,154 | **22.7 s** | **230,584 s** |
| `v2/syncDetails (POST)` | 1,634 | 11.7 s | 19,100 s |
| `resetSyncs (GET)` | 817 | 8.1 s | 6,613 s |
| `syncTelemetry (POST)` | 597 | 9.4 s | 5,606 s |
| `individual (GET)` | 162 | 17.8 s | 2,889 s |

230,584 of roughly 267,000 transaction-seconds. Any optimisation that is not about `encounter`
is rounding error.

### The database is not in the picture, and that holds unsaturated

|  | avg total | database | **application** |
|---|---|---|---|
| saturated, 02:32–03:02 | 22.71 s | 0.94 s (4.1%) | **21.77 s** |
| healthy, 03:50–04:25 (12b at 50/h) | 331 ms | 60 ms (18.2%) | **271 ms** |

**The healthy figure is the one that matters.** At 99% CPU most of the 21.8 s is a request waiting
for a slice, so the saturated ratio describes the queue. Unsaturated there is no queue, and
application code is still 82% of the request. The work really is app-side.

The contrast across endpoints says the same thing from the other direction: `syncDetails` makes
**114.5** database calls and spends 60 ms in application code; `executeSearch` makes 93.9 and
spends 54 ms. `encounter` makes **31.5** and spends **270 ms** — four times the application time on
a third of the queries.

### Inside one request

A transaction trace from the saturated window, 45.25 s total. Absolute figures are inflated by
queueing; the **shares** are what to read.

| segment | share | |
|---|---|---|
| `EncounterController.getEncountersByOperatingIndividualScope` | **52.6%** | the controller node, including the service and repository beneath it |
| 9 × lazy `individual` select | 11.18% | 1.03 s of actual database time spread over 5.06 s |
| `AuthenticationFilter` own code | **5.62%** | |
| `DummyInterceptor.postHandle` | **5.57%** | |
| `PgStatement/execute` | 0.01% | 5 ms of 45.25 s |

### Two of the plan's code-read suspicions are now measured

**F2.1 — the per-borrow interceptor, 5.57% of every request.** `DummyInterceptor` runs
`genderRepository.findAll()` in a `@Transactional` block after every web request, and its own
comment says why: *"Hack. Ensure a transactional data query is made at the end of a web request so
that all dirty objects are flushed out. Somehow, changing flush mode does not seem to fix the
problem."* The `gender select` itself is 66 ms of the 2.52 s segment — **97% of it is the
transaction wrapper, not the query.** Opening a transaction borrows a pooled connection, and every
borrow pays `set role`, `set application_name` and `RESET ROLE`. F2.1 predicted exactly this from
reading the code, including that *"requests that need no database at all still pay it whenever they
are wrapped in `@Transactional`"*. Here it is, on every request.

**F2 — `AuthenticationFilter`'s own code, 5.62%.** F2 suspected the two INFO log lines per request,
including the full query string. This does not prove logging is the cost, but it prices the
filter's own work at a tenth of what the whole controller costs.

**Together ~11% of every request**, on a server that is 99% CPU-bound, and neither needs a
serialisation rewrite. A read-only sync endpoint has no dirty objects to flush, so skipping
`DummyInterceptor` for `@Transactional(readOnly = true)` requests may be safe and free — though the
comment is explicit that the obvious fix, changing flush mode, was tried and did not work, so this
wants care rather than deletion.

### What is still not known

**Serialisation has not been priced.** Jackson writes the response *after* the controller returns,
so it is a sibling of that 52.6% node and not inside it. The named segments account for roughly
two thirds of the request; the remaining third is where `writeWithMessageConverters` and the
message converter would sit, and that fragment has not been read. **So "optimise serialisation"
remains a hypothesis** — better supported than before, because the work is app-side and on one
endpoint, but not yet attributed.

**And there is no span data.** `distributed_tracing.enabled` is `"false"` in
`avni-infra`'s `configure/group_vars/loadtest_vars.yml`, as it is in every other environment, so
`Span` events do not exist and the breakdown above came from transaction traces in the UI rather
than from NRQL. Transaction traces only capture above `apdex_f`, about 2 seconds, so **there are no
traces at all from the healthy 12b window** — every trace available is of a queued request. Turning
distributed tracing on for a few minutes of 12b would give the clean segment split, at the cost of
an app restart, a re-warm, and one more way in which loadtest differs from production.

**The 9 lazy `individual` selects are unexplained.** `Encounter` carries
`@JsonIgnoreProperties({"individual"})`, so Jackson should not touch the association, yet
individuals are loaded one at a time during the request rather than with the page. Either the
scope query resolves them per row or something reaches through `getIndividual()` after the query
returns. Worth chasing: it is 11% of the request and it is the shape of an N+1.

---

## The open thread, and what to pick it up with

A chain that would explain the nine lazy `individual` selects, the size of the controller's
application time, and why `DummyInterceptor` exists at all. **It is a hypothesis.** Each link is
read from the code; none of it is measured.

### The chain

1. **`AbstractUserType.deepCopy` round-trips every `jsonb` value through Java serialisation** —
   `ObjectOutputStream` to a byte array and `ObjectInputStream` back, with the comment *"use
   serialization to create a deep copy"*. `isMutable()` returns `true`, so Hibernate calls it to
   build the dirty-checking snapshot for **every entity it loads**. A 1,000-record page therefore
   serialises and deserialises a thousand observation maps before anything reaches the response,
   with no database involved — which is the shape the trace shows.
2. **`equals` compares the live map against that reconstructed copy**, delegating to
   `HashMap.equals`. Any value that does not round-trip to an `equals`-equal instance makes the
   entity look dirty.
3. **`DummyInterceptor.postHandle` forces a flush after every web request** —
   `genderRepository.findAll()` inside `@Transactional`, by its own comment a hack *"to ensure all
   dirty objects are flushed out"*.
4. **A dirty `Encounter` at flush fires `@PreUpdate beforeUpdate()`**, which calls
   `getIndividual()` — a lazy load, one per dirty row.

### Why `readOnly = true` may not have closed it

`9e1b91a0a` — *"Make GET endpoints readonly"* — put `@Transactional(readOnly = true)` on the sync
controllers, which sets Hibernate's flush mode to MANUAL and stops **that** transaction flushing.

**`DummyInterceptor.postHandle` is plain `@Transactional`, not readOnly**, and it runs after the
controller returns, in the same request. `spring.jpa.open-in-view` is set nowhere in avni-server, so
it is Spring Boot's default of `true`: one Hibernate Session spans the whole request, and the
entities the controller loaded are still managed in it when the interceptor opens its own
read-write transaction and commits.

So the fix closed the controller's flush and left a second, writable one immediately behind it.
That is consistent with the interceptor existing at all — it was written to flush.

### Tools to pick this up with

* **`tools/read-only-sync-writes-check.sql`** — `n_tup_upd` and `pg_current_wal_lsn()` on
  `encounter`, `individual`, `program_encounter` and `program_enrolment`. Run it, make one
  `GET /encounter` as a sync user, run it again. WAL position is the second witness, because
  `n_tup_upd` comes from the stats collector and can lag; the LSN cannot be explained away. Needs a
  quiet server: anything else touching those tables lands in the same counters.
* **A sync that exercises the path**, org 10, 100 records:

  ```
  curl -H "USER-NAME: state-1-u201000001@org10" \
    "$URL/encounter?lastModifiedDateTime=1900-01-01T00:00:00.000Z&now=<now>\
&encounterTypeUuid=eb9133de-578a-44ae-a525-c1b481cf3216&page=0&size=100"
  ```

* **`org.hibernate.SQL` at DEBUG** for one short run, as the direct version: `update encounter`
  statements during a pull settle it without inference.
* **Distributed tracing**, if the segment split is wanted — `newrelic_distributed_tracing_enabled`
  is `"false"` in `avni-infra`'s `configure/group_vars/loadtest_vars.yml`, as in every environment.
  Turning it on costs an app restart and a re-warm, and makes loadtest differ from production by
  one more setting, so flip it back afterwards.

### What each outcome would mean

| | |
|---|---|
| `n_tup_upd` moves with row count | the fix is incomplete. One-line version: `readOnly = true` on `DummyInterceptor.postHandle`, or skip it when the handler's own transaction was read-only |
| updates flat, nine selects still there | entities are not dirty, `@PreUpdate` is not firing, and the lazy loads come from somewhere not yet found |
| neither | reads are reads, and what remains is `deepCopy` serialising every `jsonb` column on every loaded row to build a snapshot that `readOnly = true` then never compares — wasted CPU, not wasted I/O |

**The third is still worth something.** On a read-only endpoint that snapshot work is pure
overhead whatever the flush does, and it sits on the one endpoint that is 86% of the saturated
window.

---

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
