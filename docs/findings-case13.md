# Case 13: the first run to break, and throughput fell as load rose

**15 October 2026.** `2026-10-15T05-33-35Z-case13-c2a0e76`. Case 12 with `CO_TENANTS=on` at
792 syncs/hour — **9.7 syncs in flight**, three times production's peak and the heaviest sustained
load in the suite. 52,367 requests, **640 failed (1.22%)**, `BUILD FAILED` against its own gate.
The first run in the exercise to break.

## Adding 47% more load removed 38% of the throughput

| | case 12 | case 13 |
|---|---|---|
| customer syncs **completed** | 1,682 of 1,682 | **1,165 of 1,682** (69%) |
| co-tenant syncs completed | — | 669 of 792 (84%) |
| customer records pulled | 21,647,550 | 13,369,092 (−38%) |
| **total throughput** | **21.0 Mrec/h** | **13.0 Mrec/h** |

Case 13 asks for 2,474 syncs/hour where case 12 asked for 1,682 — 47% more — and the server
returned **8.3 million fewer records**. That is not a system under strain; it is a system past its
knee, doing less work while working harder. 625 of the 640 failures are clients giving up after
60 seconds, and every one of those consumed server effort that produced nothing.

The customer bore it worse than the co-tenants — 69% of its syncs completed against their 84% —
because customer syncs are 3.5x larger and a long sync is likelier to be cut off than a short one.

## What a saturated sync looks like

| customer, incremental | case 12 | case 13 |
|---|---|---|
| records per sync | 12,805 | 11,424 |
| duration p50 | 65.5 s | **718.1 s** |
| duration p95 | 201.7 s | 839.0 s |
| server ms p50 | 8,673 | **657,589** |
| server ms per record | 0.911 | **48.787** |

A median sync took **twelve minutes**, of which eleven were spent waiting on the server. These are
queueing numbers, not work numbers: the per-record cost did not rise 53x because the work got
harder, it rose because requests sat in line. The device-side figure that stayed reassuring through
cases 7 and 12 — "+8% on sync duration" — is gone. At saturation the user feels all of it.

## It is the application server, and the database is still fine

| | case 12 | case 13 |
|---|---|---|
| **app CPU** | 81.0%, peak 92.5% | **95.5%, peak 99.2%** |
| RDS CPU | 23.8% | 35.0% |
| ReadIOPS | 125.2 | 447.2 |
| **ReadLatency** | **0.0 ms** | **0.0 ms** |
| DatabaseConnections | 15, peak 19 | **92.2, peak 100** |

Fifth independent run to put the constraint in the application server. Read latency did not move
even at 728 peak IOPS; RDS had two thirds of its CPU spare while the app server had none.

**The connection pool pegged at 100**, where case 12 used 15. `findings-case9-12b.md` established
the pool as a symptom rather than a cause — a 12b run held the same normalised ceiling on 10–12
connections — and this is consistent: connections pile up because requests are slow, not the
reverse. Worth stating because 100 pegged connections is exactly the number that invites a pool
resize, and that would not have helped.

## This reconciles case 12's open question

`findings-case12.md` recorded that case 12 sustained **21.0 Mrec/h** against the **12.85 Mrec/h**
in `findings-case9-12b.md`, and listed three candidates without choosing. Case 13 supplies a
fourth that fits better than any of them:

**12.85 Mrec/h is not a ceiling. It is the throughput of a saturated server.**

| regime | app CPU | throughput |
|---|---|---|
| below the knee (case 12) | 81% | **21.0 Mrec/h** |
| saturated (case 13) | 95.5% | **13.0 Mrec/h** |
| 12b, measured at the point of breaking | ~99% | 12.85 Mrec/h |

Case 13's 13.0 lands within 1.2% of 12b's 12.85, from a different profile on a different day. The
figure is reproducible — it is simply not the maximum. A server past its knee settles near 13
Mrec/h while one below it delivers 21, and 12a/12b measured the former because a stress ramp finds
the broken state by construction.

**Capacity statements derived from 12.85 understate the healthy system by about 60%.** The
qualification belongs wherever that number is quoted; the other three candidates in
`findings-case12.md` (fresh B-trees, ramp versus steady, record accounting) are not needed to
explain the gap, though fresh indexes may still account for part of case 12's 21.0.

## Provenance

Harness `c2a0e76`, the same as case 12, so the pair differs only in `CO_TENANTS`. Push off. Both
banner lines were checked before launch — `1682 syncs/hour for 60 min` and `792 syncs/hour for
3600s` — rather than relying on `launch-run.sh`, which asserts the customer rate only.

`BUILD FAILED` is the harness's own `MAX_FAILED_PERCENT` gate firing at 1.22%, not an error in the
run. The artefacts published normally.
