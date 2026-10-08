# Case 4 — findings, 8 October 2026

Case 4 is the realistic case: one state tenant, both roles, at the rate they
actually sync. The plan calls it "the baseline everything else is read against".

One run, `2026-10-08T06-17-46Z-case4-d484f18`, 11:47–15:48 IST, 187 syncs from
561 users on `pilot-day-180`'s `state-1`. An earlier attempt on 7 Oct is in
`run-log.md` under "Runs that are not measurements" — it drew 187 field workers
and no supervisors, because the feeder listed all 501 field workers before the
first supervisor at row 502 and `circular()` never reached them. The feeder is
ordered in proportion now.

## The answer

**The roles compose. The mix is the sum of its parts.**

| role | n | mean | p50 | p95 | records | `serverMs` |
|---|---|---|---|---|---|---|
| field worker | 167 | **60.8 s** | 60.6 | 61.0 | 10,829 | 6% |
| supervisor | 20 | **184.2 s** | 182.1 | 223.6 | 32,904 | 6% |

Supervisors were 10.7% of syncs against the feeder's 10.7% — the sample matched
the population.

Request level: 3,587 requests, **zero failures**, mean 229 ms, p95 322, p99 398,
max 532, 0.25 rps.

## Nothing interferes with anything

| | measured alone | measured in the mix | ms/record |
|---|---|---|---|
| field worker | case 2: 60.8 s / 10,831 | 60.8 s / 10,829 | 5.61 → 5.61 |
| supervisor | case 3: 169.7 s / 30,246 | 184.2 s / 32,904 | 5.61 → 5.60 |

A field worker's sync is **identical** to case 2's, to within a rounding error on
records. A supervisor's looks 8.5% slower until the record count is read: they
pulled 8.8% more, because 20 supervisors drawn at random have a different
catchment-size distribution from the 60 that case 3 drove. Per record the two
agree to two decimal places.

**So per-record cost is 5.6 ms across both roles, isolated or mixed.** That is
the useful constant from this case: the cases can be composed arithmetically,
and a mixed workload does not need measuring separately from its parts — at this
load. The server sat at 2–5% CPU with the connection pool flat at 10 all four
hours, so there was nothing for the roles to contend over. Whether composition
still holds near the knee is unmeasured, and case 9 is the case that would say.

## What a user waits for is still their own device

`serverMs` is 6% for both roles, which now makes five cases in a row at 6–7%
across a tenfold range of sync cost. The supervisor's 184 s is about 11 s of
server and 173 s of device.

**And D7 has since measured that device time** ([`findings-d7.md`](findings-d7.md)).
The `pausedMs` here is modelled at SQLite's rate. On Realm the same work costs
roughly four times as much to persist, so these figures hold for a SQLite fleet
and understate a Realm one:

| | here (modelled) | Realm, implied |
|---|---|---|
| field worker | 60.8 s | ~180 s |
| supervisor | 184.2 s | ~9 min |

## What this does not measure

* **No push.** `PUSH` is off throughout, and case 3's warning applies to the 60
  supervisors here too: `pushScale` defaults to 1 against a field worker's twenty
  encounters a day, so a supervisor would push like one. Quote the pull numbers.
* **No program data.** `program_enrolment` and `program_encounter` are 0 rows
  database-wide against a recipe specifying `enrolment_rate: 0.22`.
* **No co-tenants, one tenant, one run.** Cases 5 to 7 are what add tenancy.
* **An idle server.** 0.25 rps against a ceiling case 1 crossed at ~50. This
  measures what the work costs, not what the system can take.

## What to do next

* **Case 5** adds the other nine tenants, which is the first test of whether
  anything changes when the tables are shared.
* **Quote per-record, not per-sync**, where the audience cares about a different
  catchment size: 5.6 ms/record composes, 184 s does not.
* **Settle the storage engine** before quoting any of this to anyone outside the
  exercise — it is a factor of three on every number above.
