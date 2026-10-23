# The vertical scale sweep: more vCPU is the relief, and now it is measured

**21 October 2026.** Every finding in this campaign names the application server's CPU as the
constraint — [case 1](findings-case1.md), [9/12a](findings-case9-12a.md),
[11-burst](findings-case11-burst.md), [12](findings-case12.md), [13](findings-case13.md) — and
every one of them concludes that **more vCPU is the relief**. That conclusion was an *inference*
from five runs where CPU saturated and the database did not. **Nobody had added a vCPU and
watched.** This is that test.

**It holds, and not marginally.** The run that broke the 2 vCPU server is comfortable on 4.

| | 2 vCPU — `m6g.large` | 4 vCPU — `m6g.xlarge` |
|---|---|---|
| run | `2026-10-21T04-10-50Z-case13-m6g.large-c2a0e76` | `2026-10-21T05-43-20Z-case13-m6g.xlarge-c2a0e76` |
| result | **BUILD FAILED**, 1h 11m 14s | **BUILD SUCCESSFUL**, 1h 1m 42s |
| requests | 51,315 | 57,386 |
| **failed** | **467 (0.91%)** | **0** |
| mean throughput | 12.05 rps | **15.57 rps** |
| response p50 | 38,782 ms | **169 ms** |
| response p95 | 56,714 ms | **434 ms** |
| response p99 | 59,819 ms | 615 ms |
| max | 60,007 ms — the client's timeout | 5,895 ms |
| under 800 ms | **5.15%** | **99.6%** |
| app CPU | 94–99%, pinned | **49–55%** |
| RDS CPU | 32–38% | 38–42% |

## What changed, and what did not

**Only the instance type.** Same bed — `pilot-day-180` at span 8.4 with all 513 co-tenants, loaded
and verified the day before and re-verified this morning after an overnight stop. Same feeder
(`case5-users-pilot.csv`, 1,682 users), same 1,682 syncs/hour for 60 minutes, same co-tenant load
at 792/h with seed 42, same `PUSH=off`, same 900-second warm-up discarded before each run. **Heap
stayed pinned at `-Xmx5120m`** against the xlarge's 15 GiB, so the extra RAM is deliberately
unused, and the connection pool stayed at 100.

The resize went **through tofu**, in place — `~ instance_type` with no replacement — and the host
really restarted: uptime of one minute and a JVM 75 seconds old when the warm-up began.

## p95 fell by a factor of 131, which is the finding

**56,714 ms to 434 ms.** The 2 vCPU server was not slow; it was collapsing. Its p50 of 38.8 seconds
and its max of exactly 60,007 ms — the client's own timeout — describe a queue, not a service. At
4 vCPU the same offered load produces a p99 of 615 ms.

**Throughput rose 29%, and that understates the change.** The workload is fixed at 1,682 syncs per
hour, so the ceiling is the *offered* load rather than the server's capacity: at 2 vCPU the server
could not keep up and shed work into timeouts; at 4 vCPU it keeps up with CPU to spare. The honest
measure of headroom is **99% → 54%**, not the rps delta. It also finished **ten minutes sooner**,
because there was no backlog left to drain.

## The constraint has moved toward the database

RDS went from 32–38% to 38–42% — it is doing more work per second now that the application is not
throttling it. **The gap between the tiers narrowed from about 65 points to about 13.**

> **This makes 8 vCPU the interesting next point, not an obvious one.** Extrapolating, the app
> would sit near 27% while RDS climbs further, and the database could become the binding constraint
> for the first time in this campaign — four earlier runs failed to make it bind
> ([12b](findings-case9-12b.md)). That would be a new finding either way. **The injector is
> `m6g.xlarge` with 4 vCPU and would need watching or resizing**, or the harness becomes the limit.

## Saturation costs CPU, not only latency

**Added 21 Oct 2026, from `tools/cpu-per-sync.py`.** The throughput comparison understates the
change because the workload is fixed at 1,682 syncs/hour. CPU seconds do not have that problem —
they are additive, and they say something the rate cannot.

| | syncs | app CPU s | **CPU s per sync** |
|---|---|---|---|
| 2 vCPU `m6g.large` | 2,007 | 8,403 | **4.19** |
| 4 vCPU `m6g.xlarge` | 2,474 | 7,743 | **3.13** |

**The larger server completed 23% more syncs on 8% less total CPU — 25% less CPU per sync.**

The same work got *cheaper*. A collapsing server spends CPU on work that never completes: the 467
failed requests, the queueing, the context switching, and the responses it finished computing for
clients that had already timed out at 60,007 ms. None of that reaches a user and all of it is
paid for.

> **Read the denominator honestly.** This is CPU over **completed** syncs, while the numerator
> includes the CPU spent on everything that failed. That is the right way to express "what it cost
> to get this work done", and it is **not** "what a sync intrinsically costs" — the two diverge
> exactly when a server is collapsing, which is the case here. The 3.13 figure is the better
> estimate of the intrinsic cost, because almost nothing was wasted.

**Which is why the gain is larger than 29%.** Throughput rose by that much against a fixed offered
load; headroom went 99% to 54%; and the work itself became a quarter cheaper. The three are
different measures of the same move and the first is the least informative.

## What the 2 vCPU saturation was made of

Both row 19 runs' per-segment timeslices were captured from New Relic on 22 Oct
(`nr-backup/timeslices/case13-m6g.large`, `case13-m6g.xlarge`), beside row 21's
(`case13-2vcpu-B-no-interceptor`, the same box with the interceptor removed). Whole-run seconds;
syncs recorded 2,007 / 2,474 / 2,474.

| | 2 vCPU, control | 4 vCPU | 2 vCPU, no interceptor |
|---|---|---|---|
| **CPU/User Time** | **8,403** | 7,743 | 6,358 |
| per sync | 4.19 | 3.13 | 2.57 |
| **GC, young + old + concurrent** (collector s) | **519 + 34 + 2.5 = 555** | 18 | 53 |
| heap used, mean / peak MB | 2,778 / 5,096 | 1,073 / 1,796 | 1,042 / 1,977 |
| request time, all transactions (wall) | **738,180** | 12,571 | 28,038 |
| `doFilter` (wall) | **723,869** — 98% of all request time | 1,710 | 2,733 |
| `Spring/HandlerInterceptor` (wall) | 45,331 | 1,221 | 243 |
| database, all statements (wall) | 48,703 | 4,425 | 7,625 |
| `gender/select` calls | 108,247 | 133,175 | 4,862 |
| thread **blocked** events (monitor contention) | **48,865** | 571 | 2,811 |
| thread **waited** events | **240,061** | 69,663 | 68,533 |

**Garbage collection is a quarter to a half of the gap.** The control collected for 555 seconds
against 18 on the 4 vCPU run — thirty times more — with the old generation collecting at all only
on the control, whose heap sat at 2,778 MB mean and 5,096 of 5,120 MB peak. G1's young collections
are parallel, so on 2 vCPU that is roughly 555–1,100 CPU seconds of the 2,127 that separate 4.19
from 3.13 per sync. The rest is what a starved box does: 48,865 monitor-blocked events against
571, 240,000 waits against 70,000, and 467 requests that ran to a 60-second timeout doing work
nobody received.

**Where a saturated server queues: the authentication filter.** Of the control's 738,180 seconds
of request wall time, **723,869 — 98% — were inside `AuthenticationFilter`**, the first thing
every request meets; on 4 vCPU the same filter took 1,710 seconds for more requests. **A filter wraps the controller, so this is only a finding because timeslice segment values are exclusive time** — the filter's own, not what it encloses; an inclusive measure would read ~100% on both runs, and 14% on 4 vCPU is the proof. A pooled-connection checkout is not a child segment, so a thread waiting for a connection inside the filter is charged to the filter. The filter
resolves the user and switches role before the controller runs, which takes a pooled connection,
and the thread states say what the queue was made of: the waits are the pool, the blocks are a
monitor somewhere on that path. **RDS's own `DatabaseConnections` confirms it** (added 23 Oct):
the control held a **mean of 93 and a peak of 100** — the pool's maximum — for the hour, where the
media hour at 98% database CPU peaked at 58, and rows 24 and 25 at 5,000 users run on 20–35. The
pool was the queue: starved of CPU, requests held connections longer, the pool ran dry, and every
new request waited in the filter for one. A larger pool would move that queue, not remove it.
Every statement's wall time inflated ten to fifteen times at
identical call counts while RDS sat at 31% — the database was not slow, the threads were not being
scheduled. This is the first time the campaign has had a *place* for the cliff rather than a
level, and it is the same filter whose role-switching `areas-to-investigate.md` already ranks as
10.7% of every database call.

The 2 vCPU run with the interceptor removed is the control's box with 25% less CPU per sync: GC
back to 53 seconds, heap peak 1,977 MB, blocked events 2,811, request time 28,038 — a box that is
busy, not drowning.

## What this does not establish

* **n = 1 at each size.** The effect is far larger than the harness's known run-to-run variance —
  the one case that was repeated differed by 5% in throughput and 23% in p95 — but it is one run.
* **The xlarge has twice the RAM.** The heap is pinned, so the JVM cannot use it, but the **OS page
  cache can**, and nothing here separates that from the extra cores. A `c6g.xlarge` (4 vCPU, 8 GiB)
  would isolate it.
* **Warm-up was the same shape, not the same relative load.** 900 seconds of 100 devices is less
  work for a 4 vCPU box than a 2 vCPU one, so "equally warm" is an assumption. With an effect this
  size it is not a plausible explanation, but it is not controlled.
* **This is sync only**, like every other run here: production also carries the web app, the API
  and bulk imports, and shares its database with avni-etl and Metabase.

## What it means for the recommendation

**The campaign's headline advice survives contact with a test.** "App CPU is the constraint, more
vCPU is the relief, a bigger database is not" is now measured rather than inferred, and the relief
is large enough to turn a broken run into an uneventful one.

**It also bounds the advice.** Doubling the cores moved the constraint most of the way to the
database; doubling again may well arrive there. Capacity planning past 4 vCPU should assume the
database becomes the next thing to size, and
[`areas-to-investigate.md`](areas-to-investigate.md)'s code-level items — `DummyInterceptor` at
12.6% of request time, the N+1 `individual` selects at 11.18% — remain the cheaper lever, because
they raise the ceiling without moving the constraint anywhere.
