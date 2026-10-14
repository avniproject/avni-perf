# New Relic: what is instrumented, what expires, and how to read it after it has

The server under test runs the New Relic Java agent on every run. It is the only view of what
happens *inside* a request — the Gatling side sees a duration and a status code, and cannot
distinguish a request that waited on the database from one that spent its time in the JVM.

**Its most important property is that most of it expires in eight days.** This document is mostly
about that.

## What is attached

| | |
|---|---|
| app name | `avni-loadtest` |
| account / region | 8563864 / **EU** (`api.eu.newrelic.com`, not `api.newrelic.com`) |
| attachment | javaagent, `roles/newrelic` in `avni-infra` |
| heap | `-Xms2560m -Xmx5120m`, matched to production so GC behaviour transfers |
| reporting since | **29 Sep 2026 06:05 UTC** |

Its CPU series agrees with CloudWatch to a tenth of a percent, which is a useful independent check
on anything read from either.

**Distributed tracing is off** (`distributed_tracing.enabled: "false"` in every environment), so
there is no `Span` data and no cross-service view. Everything below is single-service.

**Transaction traces are cut at `apdex_f`**, about 2 s. A healthy run produces none — but 462 exist,
left by the runs that were not healthy (12a, case 11 run 1, the 15-minute burst). They are the only
whole-trace breakdowns there are.

## Retention, which is the thing to plan around

| event type | volume, 14 Oct 2026 | retained |
|---|---|---|
| `Transaction` | ~847k | **8 days** |
| `Metric` | ~2.55M | since 29 Sep, far longer |
| `SqlTrace` | ~2,360 | 8 days |
| `TransactionTrace` | 462 | 8 days |
| `TransactionError` / `ErrorTrace` | 53 / 23 | 8 days |

Volumes are as of that date and move in both directions — runs add to the head while retention
takes the tail — so a count quoted in a finding will not match a count taken later. `manifest.json`
is what records which events were actually captured.

**The boundary slides by the minute.** Queried at 10:48 UTC on 14 Oct, the earliest `Transaction`
was 6 Oct 10:48 UTC — eight days to the minute, every minute.

**This is not recoverable by re-running anything.** The environment that produced a run is
destroyed after it and the dataset is reloaded between blocks, so an expired hour is not a
measurement that can be taken again; it is a measurement that no longer exists. Case 2's
`Transaction` data expired on the morning of 14 Oct, before anyone thought to keep it.

> It was briefly read as an instrumentation gap — "the agent was not attached for cases 1 and 2" —
> and a licence-key explanation was written and committed on that reading. It was wrong, and
> `findings-case3.md` records the correction. **An absence at the retention boundary is retention
> until proven otherwise.**

## Backing it up

```
export NEW_RELIC_API_KEY=NRAK-...          # a user key; an NRIQ- ingest key returns 401
make newrelic_export ACCOUNT=8563864       # add S3=1 to sync to the artefacts bucket
```

Writes gzipped JSONL to `nr-backup/`, one file per event type per UTC hour
(`Transaction/2026-10-09/08.jsonl.gz`), which makes it resumable, incremental and sliceable by run.
`nr-backup/` is gitignored; the bucket is its home.

**Run it weekly at minimum, and after any run whose numbers matter.** Hours already complete in
`manifest.json` are skipped, so a repeat export costs only what is new.

**The hour in progress is never exported.** It is still being written, so `count(*)` and the fetch
disagree — and writing it while marking it complete would make the next run *skip* it, losing
whatever arrived afterwards. It is picked up whole on the following run. This was found by the
guard rather than by reasoning: a re-export during Block B returned 1,179 rows against a count of
1,132 taken moments earlier.

### The guard, which is the reason it is a tool and not a query

**NRQL caps a raw event query at 5,000 rows and truncates in silence.** A naive export would hold a
prefix of each hour, read as complete, and be undetectable once retention had passed — the same
shape as the feeder bug, and with the same property that nothing downstream looks wrong.

So every window is counted first and exported second, and the two are asserted equal. Windows over
the cap are bisected until each piece fits, and the children must sum to the parent. Anything short
is written to `manifest.json` with its reason and the exit code is non-zero. **Nothing is reported
as backed up on the strength of a query that returned.**

First full run, 14 Oct 2026: 850,054 events across five types, 33 MB, 1,608 queries, **159 hours,
zero shortfalls**, every hour's written count equal to its `count(*)`.

### `Metric` is in the defaults but was not in the first pass

That run narrowed `--event-types` to the five that expire in eight days. `Metric` is ~2.5M events,
roughly forty minutes, and is **not expiring** — so it was left for the same trip as the S3 sync
rather than delaying the perishable half.

**That decision is recorded in the manifest, which is the point.** `requested` lists what an
invocation asked for and `eventTypes` accumulates across invocations, so a type with no directory
reads as `never requested` rather than as an ambiguity:

```json
"requested": ["Transaction", "TransactionError", "TransactionTrace", "SqlTrace", "ErrorTrace"],
"eventTypes": { "Metric": { "status": "never requested", "events": 0 }, ... }
```

Without it, `Metric`'s absence is indistinguishable from a type that was asked for and came back
empty, or one whose export failed — and a reader months later has no way to tell which. A later
narrow export does not downgrade what a wider one recorded.

### What a backed-up event holds

28 attributes, including everything these findings are built on: `duration`, `databaseDuration`,
`databaseCallCount`, `name`, `error`, `http.statusCode`, `request.uri`, `host`, `timestamp`.

## Reading it back

```
make newrelic_query                        # list runs and their resolved windows
make newrelic_query RUN=case3
```

```
2026-10-07T06-15-54Z-case3-eb5e4b3
window 2026-10-07 06:15Z -> 08:35Z (140 min, incl. 20 min tail)

transaction                                              n   err    mean     p50     p95   db ms   calls  ms/call
WebTransaction/SpringController/encounter (GET)      2,004     0   278.8   299.8   330.7    38.3    28.3     1.35
WebTransaction/SpringController/ping (GET)             559     0     3.7     3.7     4.4     0.9     3.0     0.30
WebTransaction/SpringController/v2/syncDetails (POST)  120     0   117.7   125.0   150.7    50.3   114.6     0.44
```

That 278.8 is the figure `findings-case3.md` quotes from the live account, reproduced from files
with no key and no account. Other flags: `--facet host`, `--where "r['error']"`,
`--event-type SqlTrace`, `--since/--until` for a window that is not a run, `--csv`.

### The event types are not interchangeable

Each names its transaction differently, and a wrong facet yields a single `(absent)` row rather
than an error — a table that is empty without saying why. The tool picks per type; override with
`--facet`.

| event type | facets on | measures |
|---|---|---|
| `Transaction` | `name` | `duration`, `databaseDuration` / `databaseCallCount` |
| `TransactionTrace` | `path` | `duration` |
| `SqlTrace` | `databaseMetricName` | `totalCallTime` / `callCount`, plus the `sql` itself |
| `TransactionError` | `transactionName` | `error.class`, `error.message`, `http.statusCode` |
| `ErrorTrace` | `error.class` | `message`, `request.uri` |

`SqlTrace` measures a statement rather than a request, so database-time-per-call falls out of its
own fields. On case 11 run 1:

```
Datastore/statement/Postgres/encounter/select     105    803.7 ms/call
Datastore/statement/Postgres/individual/select     78    711.0 ms/call
Datastore/statement/Postgres/gender/select         46    750.1 ms/call
```

That last row is `DummyInterceptor.postHandle`'s `genderRepository.findAll()`, captured on the way
past — **the interceptor cost that `findings-case9-12a.md` reached by reading code is in the data.**

For anything beyond a facet, the files are ordinary JSONL and DuckDB reads them in place:

```sql
SELECT name, count(*) AS n,
       avg(duration) * 1000 AS ms,
       avg(databaseDuration) / avg(databaseCallCount) * 1000 AS ms_per_call
FROM read_json_auto('nr-backup/Transaction/**/*.jsonl.gz', union_by_name = true)
WHERE timestamp BETWEEN 1791526554000 AND 1791533754000
GROUP BY name ORDER BY n DESC;
```

### Runs whose `Transaction` data has already gone

`Metric` timeslices survive, and carry response time and throughput per endpoint — no per-request
attributes, so no database split, but enough for a cost comparison. This is all that remains of
cases 1 and 2:

```sql
SELECT count(*) AS n, average(newrelic.timeslice.value) * 1000 AS ms
FROM Metric WHERE appName = 'avni-loadtest'
AND metricTimesliceName = 'WebTransaction/SpringController/encounter (GET)'
SINCE '2026-10-06 05:38:00+0000' UNTIL '2026-10-06 09:38:00+0000'
```

**The two sources agree.** On case 3, whose `Transaction` data still exists, `Metric` gives
278.799 ms at n=2,003 against `Transaction`'s 278.8 at n=2,004 — which is what licenses reading an
expired run from `Metric` at all.

### What cannot be done

**The data cannot be put back into New Relic.** The Event API rejects timestamps more than ~24 h
old, so a re-import would land with today's clock and a fabricated history. The files are the
record; New Relic is not somewhere it returns to.

## Using it: the measures, and what each one separates

A run's Gatling report says a request took 278.8 ms. These are the questions that go past that.

**Where the time goes — facet by transaction name.** Which endpoints a sync actually spends its
time in, and how many of each it makes. Case 3: 38.6 requests per sync, of which `encounter (GET)`
is 2,004 of 2,873, and the per-request overhead is therefore paid 38.6 times.

**More queries, or slower queries — `databaseDuration / databaseCallCount`.** The single most
useful measure here, because it separates two explanations that a total cannot. **Hold the call
count constant and a move in ms-per-call is the database getting slower, not the application asking
for more.** Cases 5 → 6 moved +25.5% at identical call counts, which is how co-tenant presence was
measured at all.

**Drift — the same facet across a soak, hour by hour.** Case 10 held flat for nine hours, which is
a result: no leak, no cache decay, no residue accumulation. A null is only publishable because the
measure is calibrated enough to have shown a change.

**A/B over consecutive runs.** The case 11 pair (A–E) ran back to back on one box; comparing them
on ms-per-call rather than on wall-clock removes most of what differed between them.

**Failures — `TransactionError`, and the gap to Gatling's count.** These do not agree, and the
disagreement is the finding. Gatling recorded **0.54% of 21,491 requests failed in 12a, about 116**;
New Relic holds **one** server-side error in that window. A client-side timeout is a Gatling failure
and not a server error — the server did not reject those requests, it was too slow and the client
gave up, which is what `findings-case9-12a.md` describes as queue saturation. **Read the two
together: Gatling says what the device experienced, New Relic says whether the server ever knew.**

There are 53 `TransactionError` events in the whole account and 46 fall outside every run window.
Classes present: `DataAccessResourceFailureException` (16), `JpaSystemException` (12),
`CannotCreateTransactionException` (8), `IOException` (8).

### Not all of it is a run

**The account carries substantial traffic that no scenario produced.** Of 462 `TransactionTrace`
events, **254 fall outside every run window, and 173 of those are `importZipJob`** — co-tenant
bundle imports, up to 189.2 s each, which matches the ~183 s measured for one `large-pull-heavy`
provision in [`dataset-provenance.md`](dataset-provenance.md).

This is why a facet without a window misleads: `importZipJob` dominates any unbounded "slowest
transactions" view, and it is provisioning rather than anything a device does. **Always scope to a
run**, which `--run` does and the New Relic UI's default time picker does not.

### Two ways to compare the wrong things

**Different datasets.** Case 2 ran on `states-day-180` (2 tenants, 2.3M rows), case 3 on
`pilot-day-180` (10 tenants, 6.9M rows). Reading 184 ms against 278.8 ms and concluding something
about supervisors conflates cohort with dataset — a mistake made and corrected in
`findings-case3.md`. **Check `run-log.md`'s dataset column before comparing two runs.**

**Different windows.** A window is inferred, and a wrong one prints a table that looks entirely
reasonable. `newrelic-query.py` takes the arrival window from `run-log.md`, **not** from
`run-log-detail.md`'s `injection` line — that line carries configured defaults and reports
`120min @ 140/h, ramp 33640 s` against case 1 bursts that lasted fifteen seconds. The first version
read it and produced eleven-hour windows for a 45-minute run. Windows are also bounded by the next
run's start, since back-to-back runs share a box. **The window used is always printed; read it.**

## Keys

NerdGraph needs a **user key** (`NRAK-`). An ingest/query key (`NRIQ-`) returns 401. Keys belong in
the environment, never in the repository — `make newrelic_export` reads `NEW_RELIC_API_KEY` and
refuses anything that is not a user key, with the reason.

## Open threads this data can answer

* **`SqlTrace`, 2,359 events from 8 Oct.** Slow statements captured server-side, which is a direct
  line on the `scopeBasedSyncService` individual-selects question that
  [`findings-case9-12a.md`](findings-case9-12a.md) leaves open, rather than reading the code.
* **The 462 `TransactionTrace` events** are whole-request breakdowns of the stressed runs — the
  only ones there are, since healthy runs stay under `apdex_f`.
* **Case 2 re-run on the pilot.** The 184 ms / 274.5 ms gap is confounded by cohort today; one run
  on the pilot isolates whether a bigger database is what costs it.
