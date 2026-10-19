# The supervisor span: what doubling the catchment costs

**Block A′, 19 October 2026.** Blocks A, B and C all ran on `pilot-day-180` at a supervisor span of
**8.4** — Q13's measured establishment, 60 supervisors per state tenant, 8,400 subjects each. This
block repeats the span-sensitive cases on `pilot-day-180-span20`: **20** workers per supervisor,
the high end of the specified range, 25 supervisors each covering 20,000 subjects.

**The span is a dataset, not a flag.** It sets how many supervisors exist and how wide each
catchment is — users, catchments and their address mappings, all structural rows — so a run cannot
switch between them. Both datasets carry the same population (1,506,000 individuals) and the same
volume (6,896,792 rows against 6,896,276, 0.007% apart). Only the shape of the supervisory layer
differs.

**Only cases 3, 4 and 5 repeat**, because they are the ones whose cohort the span defines.

---

## Case 3 — supervisors alone

`2026-10-19T05-06-40Z-case3-span20-c2a0e76`. 25 supervisors, driven at 30 syncs/hour for 120
minutes, `PUSH=off`, no co-tenant activity. **60 syncs, 5,053 requests, zero failures, every
request under 800 ms** (p95 357 ms, max 588 ms).

Against Block A's case 3 — `2026-10-07T06-15-54Z-case3-eb5e4b3`, the same 60 syncs at the same 30
syncs/hour, differing only in the cohort the dataset defines:

| | span 8.4 | span 20 | ratio |
|---|---|---|---|
| subjects per supervisor | 8,400 | 20,000 | **2.38×** |
| **records per sync** | 32,334 | **75,446** | **2.33×** |
| sync duration p50 | 182.0 s | **425.8 s** | 2.34× |
| sync duration p95 | 183.4 s | 426.3 s | 2.32× |
| modelled pause p50 | 171.2 s | 399.5 s | 2.33× |
| server ms per sync p50 | 10,739 | 26,302 | 2.45× |
| **server ms per record** | **0.3312** | **0.3493** | **1.05×** |

### Records track the catchment, and duration tracks the records

**2.33× the records for 2.38× the subjects**, and **2.34× the duration for 2.33× the records.**
Both relationships hold to within about two percent, which is the same one-for-one scaling case 8
found against dataset depth — there, records per sync tracked encounters ×6.08 for ×6.08. Widening
the catchment and deepening the history are different inputs, and the server responds to both the
same way: by returning proportionally more rows at an almost unchanged cost each.

### Per record it is 5.5% dearer, and that is the whole span effect

0.3312 → 0.3493 ms. **The full-sync draw does not explain it**: Block A's run happened to include
one full sync in sixty and this one none, and recomputing over incremental syncs alone gives the
same +5.5% to four decimal places. That matters because the harness is not reproducible by design
and a one-in-sixty difference in the draw is exactly the kind of thing that usually has to be
argued away — here it cannot be, because excluding it changes nothing.

**About 0.3 points of the 5.5% is not the span at all.** Block A ran with no co-tenant
organisations in the database; these 513 exist now, emptied of transactional data by Block C's
reset, and [case 6](findings-case6.md) measured their presence at +0.3% per record. That leaves
roughly **+5.2% attributable to the span**, and it is the only confound the two runs carry.

### What a supervisor actually experiences

**A median sync goes from 3.0 minutes to 7.1.** That is the finding a reader acts on, and like
case 8's it is the device's rather than the server's: 93.9% of the 425.8 s is `pausedMs`, the
modelled client-side storage pause, against 26.3 s of server time. The server was never under
pressure — four devices in flight throughout, 0.67 rps, every request under 800 ms.

> **Case 3's rate is deliberately unreal and its throughput means nothing.** Twenty-five
> supervisors syncing once a day produce ten syncs in two hours, so the case is driven at 30/h to
> gather samples. Its durations and per-record costs are sound; its rps is not a measurement of
> anything. Cases 4 and 5 run at the real derived rate and carry the load question.

> **Quote the pull numbers, not the push numbers.** `PUSH=off` here, but the standing caveat
> stands: the simulation scales push volume by a `pushScale` whose default is a *field worker's*
> twenty encounters a day, which a supervisor covering 20,000 subjects certainly does not write.

## Cases 4 and 5

Pending — case 4 launched 12:44 on 19 Oct, case 5 after it, both against this same load with no
reset between them, mirroring Block A.
