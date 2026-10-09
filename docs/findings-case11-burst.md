# Case 11 at a 15-minute window: the data path saturates on app CPU, not the database

**9 October 2026.** `execution-plan.md` revision 2 asked for a cluster tighter than an hour — the
real analogue of a shift ending is minutes — and predicted it would land "near 35 rps, which is
where the interesting behaviour starts". **It does not reach 35 rps. It saturates first, on the
application server, at 18.5.**

Run `2026-10-09T11-27-35Z-case11-burst15-400-cf77819`. 400 users over 15 minutes — 1,600 syncs/hour,
essentially the arrival rate of 8 October's run 1, sustained for a quarter of the time so the
backlog is 400 syncs rather than 1,682. Warmed first; `PUSH=on`; `pilot-day-180`.

## The result

| | 8 Oct run 1 | pair run C | **this burst** |
|---|---|---|---|
| demanded | 1,682/h for 60 min | 550/h for 60 min | **1,600/h for 15 min** |
| syncs | 1,682 | 550 | 400 |
| devices in flight | ~435 | ~31 | ~123 |
| requests | 143,211 | 46,489 | 35,842 |
| failed | 0.04% | 0.0% | **0.0%** |
| mean response | 18,569 ms | 81 ms | 4,294 ms |
| p95 response | 41,912 ms | 327 ms | 19,610 ms |
| sync duration p50 | 1,639 s | 195 s | **593 s** |
| rps | 22.27 | 12.13 | **18.47** |

## The bottleneck is the application tier

Measured while the burst was at full queue depth:

| | app server | RDS |
|---|---|---|
| 17:04 | **99.11%** | 31.9% |
| 17:09 | **99.09%** | 27.7% |
| 17:14 | **99.09%** | 23.8% |
| 17:19 | **99.11%** | 24.4% |

**The app server is pinned at 99.1%, flat to two decimal places, while the database runs at a
quarter of its capacity.** Database connections sat at exactly 90 for the duration — the pool
ceiling, not the database's. Whatever limits sync throughput on this environment, it is not
PostgreSQL, and buying database capacity would not move it.

## Saturated throughput is reproducible, and it is the useful number

400 syncs retired between 16:57:32 and ~17:27 — **13.3 syncs/minute**. 8 October's run 1, demanded
at 1,682/hour over a full hour rather than 1,600/hour over fifteen minutes, retired **12.6 per
minute**.

**Two runs, different injection shapes, a day apart, agreeing within 6%.** That makes
**roughly 775 syncs/hour** this server's capacity against a 180-day dataset — and it is a property
of the server, not of how the cohort arrives. Demanding more than that does not raise throughput;
it lengthens the queue and nothing else.

That reconciles the three runs above exactly:

* at 550/hour the demand is **below** the ceiling, so it is met: 31 devices in flight, p95 327 ms
* at 1,600/hour for 15 minutes the demand is **2.1x** the ceiling, so a queue forms and stops
  growing when injection stops: 123 in flight, p95 19.6 s
* at 1,682/hour for 60 minutes the demand is **2.2x** the ceiling for four times as long, so the
  queue grows four times as large: 435 in flight, p95 41.9 s

Same server, same ceiling, three queue depths.

## What this corrects

**"Case 11 projects to ~8.9 rps, case 13 to ~13, against a ceiling that 100 users crossed at 50"
understates the problem.** That projection multiplied measured requests-per-sync by a demanded
arrival rate, which assumes the arrival rate is achieved. Above 775 syncs/hour it is not. Case 1
reached 50 rps pulling configuration only; the data path saturates on app CPU well below that, and
no clustered case can be expected to approach it.

**A 15-minute window does not make the burst worse per sync — it makes it shorter.** p95 fell from
41.9 s to 19.6 s against 8 October, because the backlog is smaller. The tighter window concentrates
arrivals, but the server was already past its knee at the looser one.

## What this does not say

**Zero failures at 2.1x capacity.** Nothing fell over, nothing timed out — the 60 s client ceiling
was never reached, max response was 30.6 s. The degradation is latency, not errors, which is the
benign failure mode but also the one a device user experiences as a sync that takes ten minutes:
**sync duration p50 was 593 s**.

**This is one app server.** The ceiling is a property of this instance type and this configuration.
It says nothing about whether the application scales horizontally — and
`avni-server-multi-replica-blockers` says it currently does not.

**ETL is off.** The environment runs sync against a database with nothing else on it. A real
deployment contends with a 90-minute Quartz cycle reading the same tables. The 775/hour figure is
therefore optimistic, not conservative.
