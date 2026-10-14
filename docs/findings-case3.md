# Case 3 — findings, 7 October 2026

Case 3 is the supervisor: 60 of them on `pilot-day-180`'s `state-1`, each covering a Taluka rather
than a village. It runs at a driven rate because at the establishment's own rhythm a two-hour run
collects ten syncs, which is a data point rather than a distribution.

One run, `2026-10-07T06-15-54Z-case3-eb5e4b3`, 11:45-13:46 IST, 60 syncs. Artefacts in
[`run-log.md`](run-log.md). Times IST, run ids UTC.

## The answer

**A supervisor's sync costs 170 seconds and pulls 30,000 records — about 2.8× a field worker's.**

| | case 3 supervisor | case 2 field worker | case 14 field worker, full |
|---|---|---|---|
| syncs | 60 | 167 | 63 |
| duration mean | **169.7 s** | 60.8 s | 80.1 s |
| p50 / p95 | 182.0 / 183.5 | 60.7 / 62.0 | 80.1 / 80.2 |
| min / max | **121.0 / 223.4** | — | 79.9 / 80.6 |
| records pulled | **30,246** | 10,831 | 15,732 |
| `serverMs` | **10.0 s — 6%** | 6% | 7% |

Request level: 2,314 requests, **zero failures**, mean 255 ms, p95 333, p99 376, max 428, 0.32 rps.
App server ~4.7% CPU, database connections flat at 10 throughout.

The ratio is the point. A supervisor is not a heavier field worker by a little — the catchment is a
Taluka, so it holds several villages' populations, and the sync scales with it.

## This is the first case with a real spread

Records pulled range from **21,556 to 43,288**, a factor of two across 60 supervisors, and duration
from 121.0 s to 223.4 s.

That matters because case 14's distribution was not a distribution: every one of its 63 syncs pulled
exactly 15,732 records, because `beneficiaries_per_village` is a constant and all 167 villages are
identical. Supervision is where the generator stops being uniform — Talukas hold different numbers
of villages, so the span lands differently on each supervisor, and the result is a spread that comes
from the shape of the hierarchy rather than from an accident of modelling.

**So case 3 is the one case so far whose tail means something.** The worst supervisor waits 223
seconds against the median's 182 — 23% longer, from catchment size alone.

## Still 6% server, as everywhere else

`serverMs` is 10.0 s of the 169.7 s sync. Across three cases now — 6% for case 2's field workers, 7%
for case 14's full syncs, 6% here — the proportion barely moves while the absolute sync cost varies
nearly threefold.

That consistency is itself the finding: **what a user waits for is their own device writing what it
pulled**, and that holds across roles and across sync modes. A supervisor waiting 170 seconds is
waiting 160 of them on local storage. Server-side work is not what makes any of these slow.

**D7 has since measured that local storage** ([`findings-d7.md`](findings-d7.md)) and the modelled
pause is engine-dependent. The largest supervisor's sync, modelled here at 223 s, took 159.5 s on
SQLite and **537.1 s on Realm** — nine minutes. The conclusion above holds in both cases and gets
stronger on Realm, where 490 of those 537 seconds are the device writing.

## A supervisor costs more requests, at the same cost each — added 14 Oct 2026

*From New Relic, needing no environment.* The 2.8× record count could be 2.8× the queries or 2.8×
the bytes per query. It is **2.3× the requests, each costing the same**.

| | requests/sync | records/sync | `encounter (GET)` per request |
|---|---|---|---|
| **case 3, supervisors**, `pilot-day-180` | **38.6** | **30,246** | **278.8 ms** |
| case 5, mixed cohort, `pilot-day-180` | — | — | 274.5 ms |
| case 6, mixed cohort, `pilot-day-180` + co-tenants | — | — | 276.5 ms |

**Per-request cost does not depend on who is syncing.** A supervisor cohort and a
field-worker-dominated one cost the same per request on the same dataset. Records scale 2.79× and
requests 2.26×; the shortfall between those is the fixed per-sync traffic — `syncDetails`,
`resetSyncs`, telemetry — which does not grow with records.

> **Case 2 is not the comparison, though it looks like it should be.** It reads 184.2 ms per
> request against case 3's 278.8 — but case 2 ran on `states-day-180`, two tenants, before the
> pilot was loaded. Cohort and dataset move together there, so the 51% gap cannot be attributed to
> either. The cohort claim above rests on case 3 against case 5, which share `pilot-day-180`.
> The 2.26× *request count* is still read against case 2, which is sound: pages per sync
> follow from records and `PAGE_SIZE`, neither of which the dataset swap changes. It is the
> millisecond cost of a page that is not transferable.
>
> **That gap is worth its own look.** 184.2 ms on a two-tenant, 2.3M-row database against 274.5 ms
> on a ten-tenant, 6.9M-row one is the same family of effect as case 6's co-tenant finding, at a
> much larger magnitude. It is not established here — the cohorts differ too — but Block A's
> planned re-run of case 2 on the pilot would isolate it exactly.

### Which is an argument about `PAGE_SIZE`

**The per-request overhead is paid per page.** `AuthenticationFilter`'s own code is 5.62% of a
request and `DummyInterceptor.postHandle` another 5.57% — about 31 ms of the 278.8 — and a
supervisor pays it **38.6 times per sync**. Roughly **1.2 seconds per sync of pure per-request
cost**, before a single record is read.

That is the strongest argument yet for page size mattering, and it cuts the opposite way from the
usual concern. D8 notes the client ships `pageSize: 1000` while the simulation once defaulted to
100; these runs used 1000, matching the client. Going *larger* would amortise the fixed cost across
more records. Going smaller multiplies it.

It also means the two interceptor costs found in case 9/12a are not a flat 11% tax on a sync —
they are 11% of each of 38.6 requests, and a supervisor pays nearly four times what the arithmetic
on one request suggests.

## What New Relic can and cannot reach — added 14 Oct 2026, corrected the same day

**`Transaction` events are retained for 8 days; `Metric` for far longer.** At the time of writing
the earliest `Transaction` was 6 Oct 10:33 UTC, exactly eight days and eight minutes before the
query — a sliding retention boundary, not a fact about the runs.

**It was briefly recorded here as an instrumentation gap, and that was wrong.** `Metric` shows
141,568 events on 5 October, so the agent was attached and reporting during case 1, and a
licence-key explanation written on the earlier reading has been removed rather than left standing.

What follows for analysis:

* **Request-level detail — `databaseDuration`, `databaseCallCount`, per-transaction attributes —
  ages out after 8 days.** Anything needing it must be taken within the week, and the breakdowns in
  [`findings-case9-12a.md`](findings-case9-12a.md) and [`findings-case6.md`](findings-case6.md)
  were taken inside that window.
* **Timeslice metrics survive**, so response time and throughput per endpoint remain available for
  every run including cases 1 and 2 — which is how the 184.2 ms above was read.
* **So the split that matters most is the perishable one.** Database versus application time at
  constant call count, the measure that distinguished case 6 from case 10 and the case 11 pair,
  comes from `Transaction`. For any run whose delta matters, take it within the week or it is gone.

### Which is now backed up rather than raced

`tools/newrelic-export.py` (`make newrelic_export ACCOUNT=...`) copies the raw events out to
gzipped JSONL, one file per UTC hour, and syncs them to the artefacts bucket beside the run
directories. **Run it weekly at least.** The environment that produced a run is destroyed after
it, so an hour that ages out cannot be re-measured by repeating anything — it is simply gone.

The guard is the reason it is a tool rather than a query. NRQL caps a raw event query at 5,000
rows and **truncates without saying so**, which would make a backup a silent prefix of each hour
— the same shape as the feeder bug, and undetectable later for exactly the same reason. So every
window is counted first, exported second, and the two asserted equal; windows above the cap are
bisected until each piece fits and the children must sum to the parent. Anything short is written
into `manifest.json` and exits non-zero.

[`newrelic.md`](newrelic.md) is the reference for all of this — what is attached, each retention
tier, the measures worth taking and the two ways to compare the wrong things.

`tools/newrelic-query.py` (`make newrelic_query RUN=case3`) reads it back. It resolves a run to
its UTC window and facets by transaction name, reporting duration, the database split and **database
time per call** — which is to say, every New Relic figure quoted in these findings can be
re-derived from the files, with no account, no key and no retention window. Ad-hoc work beyond that
needs nothing special either: the files are gzipped JSONL, and DuckDB reads the whole set in place
with `read_json_auto('nr-backup/Transaction/**/*.jsonl.gz', union_by_name=true)`.

> **Run windows come from `run-log.md`, not from `run-log-detail.md`'s `injection` line.** That
> line carries the configured defaults rather than what ran — it reports `120min @ 140/h, ramp
> 33640 s` against case 1 bursts that lasted fifteen seconds. The first version of the query tool
> read it and produced eleven-hour windows for a 45-minute run; the figures it printed looked
> entirely reasonable. A window is also bounded by the next run's start, because back-to-back runs
> share a box and a generous tail would otherwise blend two of them.

**Three things found when it was first run, each its own small correction:**

* `Metric` reaches back to **29 Sep 06:05 UTC**, four minutes after the corrected licence key
  landed in SSM — so the agent has reported since the hour it was provisioned, and the 41-minute
  v1 window touched no run. That is the coverage question closed from the other side.
* **462 `TransactionTrace` events exist.** The note that `transaction_threshold: apdex_f` means no
  traces from healthy runs is right about healthy runs and wrong as a statement about the account:
  the stressed ones — 12a, case 11 run 1, the 15-minute burst — cleared the threshold and left
  whole-trace breakdowns behind.
* **2,357 `SqlTrace` events**, from 8 Oct 14:13 onward. Slow statements captured server-side, which
  is a direct line on the `scopeBasedSyncService` individual-selects thread that
  [`findings-case9-12a.md`](findings-case9-12a.md) leaves open — and the first place to look when
  it is picked up.

## What this does not measure

* **Push, and the push numbers would be wrong if it did.** The simulation scales a user's write
  volume by `pushScale`, which defaults to 1 against a *field worker's* twenty encounters a day. A
  supervisor covers a wide catchment and records almost nothing, so every supervisor here would push
  like a field worker. Nothing has measured the real figure — the platform-wide distributions do not
  split by role — so it is left at 1 rather than guessed. **Quote case 3's pull numbers; do not quote
  its push numbers.** The same bias sits in case 4 at a tenth to a twentieth of the weight, where
  supervisors are 60 of 561 users.
* **No program data.** `program_enrolment` and `program_encounter` are 0 rows database-wide against a
  recipe specifying `enrolment_rate: 0.22`. A real supervisor's sync is larger than 30,246 records.
* **A driven rate, not a natural one.** `SYNCS_PER_HOUR=30` against a derived 5. The case measures
  per-sync cost, so this is sound — but 0.32 rps says nothing about what 60 supervisors cost a
  system, because they would never arrive this fast.
* **One state tenant, one run**, on a box doing nothing else.

## What to do next

* **Case 4** puts supervisors and field workers together on one tenant, which is the realistic mix
  and the first case where the two interact.
* **Measure a supervisor's real write volume** before case 3 is quoted for anything but pulls.
* **Load the program data**, which is now the largest known gap between every case measured so far
  and the sync a real user performs.
