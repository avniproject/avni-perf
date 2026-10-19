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

## Cases 4 and 5 — where the span disappears into the cohort

`2026-10-19T07-14-41Z-case4-span20-c2a0e76` (526 users, 44/h, 4 h, **175 syncs**) and
`2026-10-19T11-15-25Z-case5-span20-c2a0e76` (1,580 users, 132/h, 2 h, **263 syncs**). Both at the
derived rate, both `PUSH=off`, both on the same load as case 3 with **no reset between any of the
three**, mirroring Block A. 3,436 and 5,120 requests, **zero failures**.

**Read as wholes, these two runs say the span changed nothing:**

| | case 4 8.4 → 20 | case 5 8.4 → 20 |
|---|---|---|
| records per sync p50 | 10,778 → 10,778 | 10,778 → 10,778 |
| sync duration p50 | 60.6 s → 60.5 s | 60.6 s → 60.6 s |
| mean records per sync | 13,190 → 13,791 (1.05×) | 12,989 → 13,498 (1.04×) |
| server ms per record | 0.3306 → 0.3294 | 0.3365 → 0.3396 |

**That is dilution, not absence.** The span widens supervisor catchments, and supervisors are
**60 of 561 users at span 8.4 and 25 of 526 at span 20** — a tenth of the cohort falling to a
twentieth. Splitting each run by role recovers the effect, and gives something case 3 could not:
a control group measured on the same server at the same moment.

| | n | records per sync | ms per record |
|---|---|---|---|
| **case 4** field workers | 166 → 165 | 10,799 → 10,778 (**1.00×**) | 0.3287 → 0.3228 (**−1.8%**) |
| **case 4** supervisors | 19 → 8 | 32,358 → 75,446 (**2.33×**) | 0.3348 → 0.3465 (**+3.5%**) |
| **case 5** field workers | 249 → 248 | 10,775 → 10,727 (**1.00×**) | 0.3338 → 0.3315 (**−0.7%**) |
| **case 5** supervisors | 29 → 11 | 30,856 → 75,160 (**2.44×**) | 0.3437 → 0.3628 (**+5.6%**) |

### The catchment ratio reproduces three times

**2.33×, 2.33× and 2.44×** against the 2.38× ratio of 20,000 subjects to 8,400 — measured on
supervisors alone, inside a one-tenant cohort, and inside a ten-tenant one. **Field workers, whom
the span does not touch, hold at 1.00× in both runs that contain them**, to within half a percent.

### The control is what makes the per-record number honest

Supervisors cost **+5.5%, +3.5% and +5.6%** more per record across the three runs. Field workers,
who should show **zero**, moved **−1.8%** and **−0.7%**. So run-to-run variation here is on the
order of one to two points, and the defensible statement is **about +5%, give or take 1.5**, not
any single figure to three significant digits. Roughly 0.3 points of it is co-tenant presence
rather than span ([case 6](findings-case6.md)).

Supervisor counts are small at span 20 — **8 and 11 syncs** — which is the other reason not to
quote a precise figure. Case 3 exists precisely because driving supervisors alone is the only way
to get a decent sample of them.

### Do not read case 4's and case 5's p95 as an improvement

**Both show sync duration p95 falling from 182 s to 80 s, and nothing got faster.** At span 8.4 a
supervisor is ~10.4% of the syncs, so a supervisor's sync sits above the 95th percentile; at span
20 it is ~4.2%, so it sits below. **The percentile moved because the cohort's composition changed.**
Every span-20 supervisor sync is *slower* than every span-8.4 one — 75,000 records against 32,000.
This is the clearest example in the campaign of a headline statistic reversing the direction of the
thing it describes, and it is why the role split is not optional for these two runs.

---

## What the span sweep settles

**The span scales the work and barely touches the cost of it.** Widening a supervisor's catchment
by 2.38× gives 2.33–2.44× the records per sync, 2.34× the sync duration, and about 5% more server
time per record. There is no knee, no new bottleneck, and nothing that behaves differently in kind
from span 8.4.

**This is the same answer case 8 gave for history**, reached from an independent input: ×6.08 the
dataset depth gave ×6.08 the records per sync at a flat per-record cost. Volume — however it
arrives, through deeper history or wider catchments — is linear on this server, and the application
server's CPU remains the constraint only when arrivals are compressed (cases 12 and 13).

**What it costs the person holding the device**: a supervisor at span 20 waits **7.1 minutes** for
a median sync against **3.0** at span 8.4, 94% of it the modelled client-side storage pause. Field
workers are unaffected. That is a product question about supervisor tooling, not a server one.

**The sweep does not justify widening itself.** The plan reserved the right to extend the sweep if
"one span-20 result shows the span matters more than this expects". None does: every measurement
landed within a couple of percent of simple proportionality. The span can be treated as an
interpolation between 8.4 and 20 rather than a factor needing its own runs.
