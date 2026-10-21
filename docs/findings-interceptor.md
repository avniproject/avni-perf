# Findings: removing `DummyInterceptor`

Rows 21 and 22 of the [execution plan](execution-plan.md). The case for removal is in
[`dummy-interceptor.md`](dummy-interceptor.md); the card is avniproject/avni-server#1097. These runs
price it.

**One sentence.** On the box where case 13 fell off the cliff, removing one class registration keeps
it on: 467 failures become none, a 39-second median request becomes 295 ms, and the server does the
same work with its queue flat the whole hour.

## The arms

| | control | test |
|---|---|---|
| jar | `avni-server-17.3.0-SNAPSHOT.jar` | `avni-server-17.3-2c0215679-NO-INTERCEPTOR.jar` |
| sha256 | `73d458d2…` | `13a896c9…` |
| build | `origin/17.3` @ `2c0215679` | the same commit, registration removed from `SyncConfiguration` and `ApiConfiguration` |
| run | row 19's `2026-10-21T04-10-50Z-case13-m6g.large` | `2026-10-21T09-56-40Z-case13-2vcpu-B-no-interceptor` |

Same day, same `m6g.large`, same `pilot-day-180`, same feeder and rate (1,682 customers over the
hour, co-tenants at 792/h, seed 42), push off, New Relic attached, no profiler, 900 s warm-up
discarded before each. The runner verified the arm from the sha256 of the deployed jar, not from
its argument, and the run's metadata records `serverBuild 2c0215679-no-interceptor`.

**The control was not re-run, deliberately.** Between the two runs the media-hour run pushed
~36,000 encounters and ~3,000 individuals into the customer orgs — about 1.7% on the dataset, and
in the direction that makes the test arm look *worse*. The box was resized to `m6g.xlarge` and
back, which a 900 s warm-up erases. Against an expected effect of ~12% that is noise, and the
result is not close.

## Row 21: case 13 at 2 vCPU

### Headline

| | control | no interceptor |
|---|---|---|
| result | **BUILD FAILED** | **BUILD SUCCESSFUL**, 1 h 2 m |
| requests | 51,315 | 61,181 (+19%) |
| failed | **467** (0.91%) | **0** |
| p50 / p95 / max | 38,782 / 56,714 / 60,007 ms | 295 / 1,441 / 10,372 ms |
| under 800 ms | 5.15% | 82.98% |
| mean throughput | 12.05 rps | 16.5 rps (+37%) |
| syncs recorded | 2,007 of 2,474 | 2,474 of 2,474 |

### The queue, minute by minute

What decided this was visible at +15 minutes, forty minutes before the control's failures peaked.
From both runs' console logs at matched elapsed time, customer scenario
(`tools/compare-trajectory.py`):

```
              customer done   active   requests    KO   req/min
 +5 min  control      79        64      3,965      0      789
         test        104        39      4,710      0      941
+10 min  control     146       137      7,409      0      689
         test        245        38     10,085      0    1,075
+15 min  control     222       201     10,550      0      628
         test        374        49     15,131      0    1,009
+20 min  control     303       261     13,711      3      632   ← first failures
         test        526        38     20,262      0    1,026
+30 min  control     506       338     20,098     55      648
         test        805        39     30,526      0    1,030
+45 min  control     956       308     31,097    279      751
         test      1,227        37     45,818      0
+55 min  control   1,236       309     38,927    404      776
         test      1,511        34     56,045      0
```

**`active` is the whole result.** The control's climbs from +5 and never recovers — that is the
queue, and it is visible fifteen minutes before the first KO. The test arm's sits at 34–49 for the
entire hour: syncs complete as fast as they arrive.

### What the throughput numbers mean, and do not

The control served **628–648 requests/min in its clean window** (+10 to +30, before failures) with
the queue climbing. Its later 750–800/min is inflated by the failures themselves: a request that
times out completes quickly and counts.

The test arm's **~1,030/min is the offered load, not a ceiling** — 1,682 + 792 syncs/h at their
request counts comes to about that, and active is flat, so it served what arrived. Where its
ceiling is, this run cannot say.

**A 12.6% per-request saving moved the knee by at least 47%, and that is the cliff rather than a
contradiction.** Past the knee what you measure is collapsed throughput — queueing, thread-pool
contention, the heap pinned at 5,096 of 5,120 MB — not capacity. Removing an eighth of the work
per request put the same offered load under the knee, where the server gives its whole capacity.
In control-request-equivalents the test arm is doing ~0.874 × 1,030 ≈ 900/min of the old build's
work and holding; the old build fell over at 1,030. **The old build's knee is between ~900 and
~1,030 requests/min on 2 vCPU**, consistent with case 12 passing at 81% CPU and case 13 breaking
at 47% more load.

### Per sync

Same work, from `sync-durations.csv` — records per customer sync p50 10,778 against 10,881:

| customer sync | control | no interceptor |
|---|---|---|
| duration p50 / p95 | 751 / 838 s | 70 / 203 s |
| `serverMs` p50 / p95 | 693 / 780 s | 9.3 / 31.6 s |

Push is off, so `serverMs` carries no media wait here; the 74× is queueing. A field worker who
waited twelve and a half minutes on the control waited seventy seconds on the test build, most of
that the modelled storage pause.

### CPU

From New Relic `apm.service.cpu.usertime` via `tools/cpu-per-sync.py`. The test arm's window ends
at 10:59:40Z, eight seconds into row 22's launch and after its own last request; the control's is
the standard injection + 20 minutes, which its failing drain needed.

| | control | no interceptor | |
|---|---|---|---|
| app CPU seconds | 8,403 | **6,358** | **−24%** |
| syncs | 2,007 recorded (467 failed) | 2,474, all | |
| CPU s per sync | 4.19 | **2.57** | −39% per recorded sync; −24% per injected |
| app CPU, mean / peak | 86% / 99% | 84% / 99% | |
| RDS CPU, mean / peak | 31% / 43% | 39% / 48% | more work reaching the database |
| heap peak | 5,096 of 5,120 MB | 1,977 MB | |
| per customer sync, mean / p50 / p95 | — | 2.96 / 2.15 / 7.32 | `serverMs`-weighted, clean here: push is off |
| per co-tenant sync, mean / p50 | — | 1.74 / 1.34 | **case 7 measured 1.68 independently** |

**The prediction was ~3.7 and the measurement is 2.57, and the gap is the control's saturation
waste.** 12.6% was the interceptor's share of request time on a *healthy* server; the control was
not healthy, and its 8,403 s include queueing, GC against a full heap and 467 requests that ran to
a 60 s timeout. That is why the case 13 delta cannot be read as the interceptor's own cost, and why
row 22 — both arms healthy, same work — is the measurement for that number.

The test arm sits at 84% mean app CPU with 99% peaks: **it is not far from its own knee**. The
removal bought the margin that case 13 needed on 2 vCPU, not a large one.

## Row 22: case 12 at 2 vCPU

_pending — launched 16:29 IST without a warm-up, directly after row 21's drain, with
`CACHE_POLICY=warm-from-preceding-run` recorded._

## What this settles

- **The binary question, yes.** Removing `DummyInterceptor` takes case 13 off the cliff on the
  hardware that broke.
- **The knee of the old build**, bounded for the first time: 900–1,030 req/min on 2 vCPU.
- **Not settled by row 21:** the clean size of the saving in CPU seconds. The control's 4.19 s/sync
  includes saturation waste, so the case 13 delta overstates the interceptor's own cost. Row 22 is
  the measurement for that.
