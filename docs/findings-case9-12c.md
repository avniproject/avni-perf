# Case 9 / 12c: the write path does not bind either, and the ceiling is confirmed

**12 October 2026.** `2026-10-12T06-01-23Z-case9-12c-cf77819`. **12a's ramp exactly** — 200 to
3,000 syncs/hour over 45 minutes, realistic mix, ten tenants, `pilot-day-180` — with `PUSH=on`.
Nothing else differs, so the pair isolates the write path. 1,200 syncs, all completed.

*Throughout, **Mrec/h** means millions of records per hour: the rows the server serialises and
returns across all concurrent syncs, which is the `records` column of `sync-durations.csv`.*

## The write path is visible and does not bind

| | 12a (`PUSH=off`) | 12c (`PUSH=on`) |
|---|---|---|
| app CPU at saturation | 99.0–99.3% | **99.1%, held 55 minutes** |
| RDS CPU | 16–25% | **23–33%** |
| WriteIOPS | — | 45–64 |
| WriteLatency | — | 0.81–2.63 ms |
| connections | 98, pegged | 98, pegged |

**Push costs the database about ten percentage points of CPU and nothing else.** WAL, lock
contention and autovacuum are all exercised — WriteIOPS up to 64, write latency occasionally
touching 2.6 ms — and none of it binds. The app server pinned at 99.1% for fifty-five minutes while
RDS sat at a third of capacity.

With 12b having shown the same for reads, **every storage path has now been measured and none is
the constraint on this deployment.**

## It failed less than the run without push

| | 12a | 12c |
|---|---|---|
| requests | 21,607 | **102,900** |
| failed | **116 (0.54%)** | **9 (0.009%)** |
| of which timeouts | 115 | **0** |
| mean / p95 | 17,378 / 53,318 ms | 11,470 / 33,124 ms |

**The pushing run did more total work and broke less.** 12a produced 115 sixty-second client
timeouts; 12c produced none, and its nine failures were all HTTP 502.

The likely reason is request granularity. A pushing sync issues many small requests — `media/uploadUrl`
alone was 47% of 12c's transactions at 2.7 s each — so the queue drains in smaller units and fewer
individual requests sit past the client's 60-second ceiling. The same total work, cut finer, crosses
fewer deadlines. **That is a property of the request mix, not evidence that pushing is cheap.**

## The ceiling, now across six runs

| run | mode | push | in flight | syncs/h | **Mrec/h at 99% CPU** |
|---|---|---|---|---|---|
| 12b full (first) | full | off | 18 | 424 | 12.33 *(from 55%)* |
| 12a | realistic | off | 113 | 1,161 | 12.78 |
| 12b full (rerun) | full | off | 171 | 838 | 13.43 |
| case 11 run 1, 8 Oct | realistic | **on** | 435 | 776 | 10.70 |
| case 11 burst, 9 Oct | realistic | **on** | 123 | 800 | 11.28 |
| **12c** | realistic | **on** | 689 | 861 | **11.97** |

**12.85 Mrec/h without push; 11.32 with. A push penalty of about 12%.**

The groups do not overlap. This holds across two sync modes, four injection shapes, concurrency from
**18 to 884 devices in flight**, three days and two harness builds.

**12c was predicted at ~11.0 and came in at 11.97** — inside the pushing band but at its top. Call
the model supported rather than confirmed to the decimal: the pushing group spreads 10.70–11.97,
wider than the non-pushing group's 12.33–13.43, so push cost varies with something not yet
identified.

## What the server is actually doing

Measured rather than inferred, from New Relic for 12a's saturated window:

| | share of request time |
|---|---|
| database | **5.1%** (0.998 s of 19.585 s) |
| garbage collection | ~2% (1–1.4 s per minute) |
| **application work** | **~93%** |

Under saturation the database's share *falls* — it is 26% of a 161 ms request when unsaturated and
5% of a 19.6 s request when saturated. **That is the opposite of connection starvation**, which
would grow the database-attributed share as threads queued to acquire a connection. Tomcat's pool
parks waiting threads on locks rather than spinning, so a thread waiting for a connection burns no
CPU; 99% CPU means the server is computing.

What it computes is records into JSON, at **0.46 ms of server time per record** — identical in
realistic and full modes. The 2 vCPU retires ~12.8M records/hour because that is how fast it turns
rows into response bodies.

## Consequences

**Capacity planning belongs in records, not devices or syncs.**

    records_per_sync x syncs_per_hour  <=  ~12.8M on this instance, ~11.3M when pushing

Syncs per hour ranged 424 to 1,161 across these runs while the record ceiling held. Device count is
not a capacity question; the rows those devices collectively ask for, and how tightly the demand
clusters, is.

**The relief that follows is the app tier**, since app CPU is the named resource and the work is
serialisation. Raising the pool alongside it is sensible — at 100 it will likely become the next
constraint once CPU is relieved — but raising it alone would do nothing, as the first 12b run
demonstrates: 10–12 connections, never near the limit, and the same normalised ceiling.

**Anything that reduces per-record serialisation cost moves the ceiling directly.** That is a code
question rather than a sizing one, and it is where Phase 5 should look after the instance size.

## Residue

12c pushed **30,984 rows — 28,393 encounters and 2,591 individuals — 25.8 per sync**. A fifth
independent measurement of the push rate beside 25.72, 25.48, 26.9 and 27.3; all within 7%.

The dataset now stands at **113,854 rows of residue, 1.649%** above the 9 October reload baseline.
Still inside the 5% threshold for small-delta findings, and Block B's reset clears it.
