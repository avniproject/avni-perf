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
