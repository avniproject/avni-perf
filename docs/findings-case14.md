# Case 14 — findings, 6 October 2026

Case 14 is the re-enrolled device: a field worker whose phone was wiped, pulling a day-180
catchment from nothing. It exists because no other case measures that — case 1 is `SYNC_MODE=full`
but its organisation holds no field data, and cases 2 to 7 draw a full sync for 1% of syncs, which
is one or two per run.

One run, `2026-10-06T09-50-36Z-case14-4c7b807`, 15:20-16:50 IST, on `states-day-180` with
`case2-users-states.csv`. 63 syncs, **every one of them full**. Artefacts in
[`run-log.md`](run-log.md). Times IST, run ids UTC.

## The answer

**A full sync costs 80 seconds, and 5.4 of them are the server's.**

| | case 14 | case 2 full (n=2) | case 2 incremental (n=165) |
|---|---|---|---|
| syncs | 63 | 2 | 165 |
| duration mean | **80.1 s** | 80.2 s | 60.8 s |
| p50 / p95 | 80.1 / 80.2 | 80.4 / 80.4 | 60.7 / 62.0 |
| records pulled | **15,732** | 15,732 | 10,831 |
| `serverMs` | **5.4 s — 7%** | 7% | 6% |
| `pausedMs` | 74.7 s | — | — |

Request level: 2,898 requests, **zero failures**, mean 117 ms, p95 272, p99 311, max 772, 0.54 rps.
Every request completed under 800 ms. About 46 requests per sync, against case 2's 17 — the extra
pages of a full pull.

## The heaviest sync is 7% server

This is the number to carry. A wiped device re-enrolling against 180 days of data waits 80 seconds,
and **74.7 of those are its own storage writes**; 5.4 are the server. The 20-second gap between
this and case 2's ordinary sync is almost entirely extra local writing, not extra server work.

Two consequences:

* **Server-side optimisation has little leverage on what the user experiences here.** Halving
  server time moves an 80-second sync to 77 seconds.
* **The ceiling case 1 found is not the constraint for this path.** Case 14 ran at 0.54 rps and
  p95 272 ms — the server was never stretched. What makes a full sync slow is its size, not
  contention.

The caveat was that `pausedMs` is *modelled*, not measured on a device — a stated assumption that
93% of this result rested on. **D7 has since measured it** ([`findings-d7.md`](findings-d7.md)), and
the answer depends on the storage engine: the same full sync took 67.6 s on SQLite, close to the
80.1 s modelled here, and **192.1 s on Realm**. `baseMsPerRecord` turns out to be SQLite's number,
3.7× optimistic for Realm. So this figure stands for a SQLite device and understates a Realm one by
about 2.4×.

## Case 2's two-sample estimate held

`run-log.md` reports a `full sync p95 s` over full syncs only, and in every `realistic` case that is
a percentile of one or two samples — which this document's predecessor called out as a weakness.
Here 63 samples give 80.1 s against the 2 samples' 80.2 s. **The small-n figure was accurate.**

That is worth knowing, but it is not a general licence: it held because this dataset makes every
full sync identical, which the next section is about.

## The distribution is too tight to be real

Across 63 syncs: min 79.9 s, max 80.6 s, p95 within 0.1% of the median — and **every single sync
pulled exactly 15,732 records**.

That is the generator, not the system. `beneficiaries_per_village` is a constant and encounters are
spread evenly, so all 167 villages hold identical volume and every field worker's catchment is the
same size. Real catchments vary by an order of magnitude.

**So quote the mean, not the spread.** 80 seconds is a sound central estimate for a day-180
catchment of this size; the implied consistency is an artefact. A dataset with varied village sizes
would answer "what does the worst catchment cost", which is the question an operations team
actually asks, and nothing here answers it.

Case 3 since has that spread, for a different reason: supervisors cover Talukas, which hold
different numbers of villages, so its 60 syncs range from 21,556 to 43,288 records and 121 s to
223 s. See [`findings-case3.md`](findings-case3.md). The uniformity is a property of the village
layer, not of the generator everywhere.

## What this does not measure

* **No push.** A re-enrolled device has nothing local to push, so this is correct for the case —
  but it means case 14 says nothing about write load.
* **No program data.** `program_enrolment` and `program_encounter` are 0 rows database-wide, where
  the recipe specifies an enrolment rate of 0.22. A real full sync pulls those too, so 15,732
  records and 80 seconds are both **under**-estimates.
* **No co-tenants, single tenant, quiet box** (#112 F5.4, deferred).
* **One run**, not repeated.

## What to do next

* **Vary village size in the generator**, then re-run. The mean is in hand; the tail is not, and the
  tail is what determines whether anyone complains.
* **Load the program data** before quoting 80 seconds as the cost of a re-enrolment. It is the
  largest known gap between this and the real thing.
* **Measure a device's real storage write**, or at least bound it. 93% of this result is a modelled
  pause, and no measurement here constrains it.
