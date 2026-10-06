# Case 2 — findings, 6 October 2026

Case 2 is the ordinary hour: 500 field workers on `states-day-180`, each syncing on production's
own rhythm, held for four hours. The execution plan calls it "the common case and the baseline
everything else is read against", and that is what it delivers — a number for what a quiet system
costs, against which every heavier case can be read.

One run, `2026-10-06T05-38-32Z-case2-e7a130d`, 11:08-15:08 IST. Settings and artefacts in
[`run-log.md`](run-log.md); per-run detail in [`run-log-detail.md`](run-log-detail.md). Times are
IST, run ids UTC.

## The answer

**An ordinary hour costs the server almost nothing.**

| | case 2 |
|---|---|
| syncs collected | 167 over 4 h (42/h, as specified) |
| requests | 2,846 |
| failures | **0** |
| mean / p95 / p99 request | 209 / 288 / 533 ms |
| max request | 611 ms |
| throughput | 0.2 rps |
| app server CPU | **~2.1%**, flat across all eight 30-minute buckets |
| database connections | **10**, constant — the pool never grew |

For contrast, case 1's 75 s burst put the same `m6g.large` near saturation at 49.43 rps and pegged
the connection pool at its 100 ceiling. Case 2 does not register. **The steady state is not the
problem; the herd is.**

## The expensive sync is not the rare one

This is the result worth carrying forward, and it was not what the case was expected to show.

`SYNC_MODE=realistic` draws a full sync for 1% of syncs. It drew 2 of 167 — 1.2%, as designed. But
the other 165 are not cheap:

| | n | records pulled | mean duration | p50 | p95 |
|---|---|---|---|---|---|
| full | 2 | 15,732 | 80.2 s | 80.4 | 80.4 |
| incremental | 165 | **10,831** | **60.8 s** | 60.7 | 62.0 |

**An incremental sync pulls 69% of what a full one pulls and takes 76% as long.** The intuition
behind the 1% — that full syncs are the expensive outlier and everything else is a cheap delta —
does not hold on this data.

The reason is in the harness rather than the server. `realistic` does not use one window: it draws
a per-`(user, entity)` gap from production's measured distribution of *gaps between syncs*,
interpolated in log space because the range spans four orders of magnitude. That distribution is
heavy-tailed — real devices often have not synced for weeks — so a typical "incremental" sync is
catching up on a long gap, not on a day.

**So case 14 is measuring the top of a continuum, not a separate regime.** It should be read that
way: the gap between 60.8 s and 80.2 s is what being fully behind costs over being ordinarily
behind, and it is small.

## The device does the work, not the server

Across all 167 syncs, **`serverMs` is 6% of `durationMs`** — 7% for the full syncs, 6% for the
incremental ones. The remaining 94% is the modelled storage pause: the device writing what it
pulled.

That reframes a sync's cost. A 61-second sync is not 61 seconds of server; it is about 3.7 seconds
of server and about 57 seconds of the device writing to local storage. Halving server time would
move a sync from 61 s to 59 s.

It also explains a figure the harness prints and should not be quoted here. The banner says
"~0.16 in flight at production's 14.1s median"; the run-log reports **~2.1 devices in flight**,
measured. The banner is not wrong about the arrival rate — it is using a 14.1 s median against
syncs that actually took 61 s. The measured figure is the one in the table.

## What this does not measure

* **No push.** `PUSH` is off, so this is read-path only. A field worker's day includes writes.
* **No program data.** `syncDetails` served 40 items across 29 entity names — `Individual` present,
  `Encounter` in 12 slices, so the field-data path is genuinely exercised. But `program_enrolment`
  and `program_encounter` are **0 rows database-wide**, where the recipe specifies an enrolment
  rate of 0.22 and a program-encounter share of 0.59. A real field worker pulls those too, so the
  sync measured here is smaller than the one they perform.
* **No co-tenants.** Single tenant on a quiet box (#112 F5.4, deferred).
* **One run.** Case 1 needed a repeat to show that two runs of the same window differ by 5% in
  throughput and 23% in p95. Nothing here has been repeated.

## What to do next

* **Re-read the 1% full-sync assumption** across cases 2 to 7. If an incremental sync already pulls
  69% of a full one, the full-sync share is not the lever it was taken for, and case 14's result
  should be compared against case 2's incremental figure rather than against nothing.
* **Load the program data.** The zero enrolments are the largest known gap between this measurement
  and a field worker's real sync, and the recipe already specifies the rates.
* **Then add push, and then the co-tenants.** In that order: push is part of the same device's hour,
  co-tenants are a different system.
