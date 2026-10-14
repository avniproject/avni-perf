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

## A supervisor costs more requests, not costlier requests — added 14 Oct 2026

*From New Relic, needing no environment.* The 2.8× record count could be 2.8× the queries or 2.8×
the bytes per query, and those imply different remedies. It is neither exactly: it is **2.3× the
requests, each costing the same**.

| | requests/sync | records/sync | per-request cost |
|---|---|---|---|
| case 2, field worker | 17.0 | 10,831 | *no New Relic data — see below* |
| **case 3, supervisor** | **38.6** | **30,246** | 278.8 ms, 28.3 db calls |
| case 5 / 6, mixed cohort | — | — | 276.4 / 276.5 ms, 28.6 calls |

**Per-request cost does not depend on who is syncing.** 278.8 ms for the supervisor run against
276.4 ms for the field-worker-dominated one, at the same ~28 database calls. Records scale 2.79×
and requests 2.26×; the shortfall between those two is the fixed per-sync traffic — `syncDetails`,
`resetSyncs`, telemetry — which does not grow with records.

### Which is an argument about `PAGE_SIZE`

**The per-request overhead is paid per page.** `AuthenticationFilter`'s own code is 5.62% of a
request and `DummyInterceptor.postHandle` another 5.57% — about 31 ms of the 278.8 — and a
supervisor pays it **38.6 times per sync**. Roughly **1.2 seconds per sync of pure per-request
cost**, before a single record is read.

That is the strongest argument yet for the page size mattering, and it cuts the opposite way from
the usual concern. D8 notes the client ships `pageSize: 1000` while the simulation once defaulted
to 100; the runs here used 1000, matching the client. Going *larger* would amortise the fixed cost
across more records. Going smaller multiplies it.

It also means the two interceptor costs found in case 9/12a are not a flat 11% tax on a sync —
they are 11% of each of 38.6 requests, and a supervisor pays nearly four times what the arithmetic
on one request suggests.

## A bound on what New Relic can answer — added 14 Oct 2026

**Case 2 has no New Relic data**, which is why the table above compares the supervisor against
case 5/6 rather than against case 2 directly.

The earliest transaction in the account is **6 October 10:33:28 UTC**. Case 1 ran on 5 October;
case 2 ran 05:38–09:38 on 6 October. Both predate it. So
[`findings-case9-12a.md`](findings-case9-12a.md)'s statement that *"New Relic has been attached as
a javaagent on every run"* is not correct, and **no retrospective New Relic analysis of cases 1 or
2 is possible**.

**The configuration was not at fault.** `avni-infra` set `newrelic_agent_enabled: "true"` for
loadtest in `e991b4b` on 15 September and wired the license key from SSM in `fa8a52b` on 29
September, and nothing has touched either since. Two operational explanations fit and the
repository cannot distinguish them: a license key absent or placeholder in SSM, which makes the
agent start, fail to authenticate and report nothing; or a connection that only succeeded later,
since the agent retries.

**The second is more likely.** First data at 10:33:28 falls *inside* case 14's window of
09:50–11:20, and case 14 recorded zero failures. An app restart mid-run would almost certainly
have produced some; an agent connecting mid-run would produce none. `/opt/newrelic/logs/newrelic_agent.log`
on the host would settle it — though `log_file_count` is 1, so there is no history if the app has
restarted since.

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
