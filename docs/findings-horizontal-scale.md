# Horizontal scale: copies split evenly and cost nothing extra — what it takes to run them

**4–6 November 2026, execution-plan rows 32–36.** Every run before row 33 had one avni-server.
[`findings-vertical-scale.md`](findings-vertical-scale.md) showed that more vCPU on that one server is
the relief; nobody had measured whether **more servers** are. These runs put two, three and four copies
of the 18.3 release candidate behind the load balancer and compared them with one copy of the same
total size.

**They are.** Load splits evenly at every count, a copy costs nothing measurable per sync, and latency
falls with the utilisation of each copy, not with how many there are. Scaling out the app tier is what
finally made the database the constraint (row 34), and it is how 50,000 syncs an hour was reached
(row 36). **These are sync-only runs: they say what scaling out would buy, not that avni-server can
run as several copies in production today** — see [what this does not establish](#what-this-does-not-establish).

| row | app copies | app vCPU | database | load, syncs an hour | completed | req/s | app CPU per copy | p95 | CPU s / sync | failures |
|---|---|---|---|---|---|---|---|---|---|---|
| 31 | 1 × `m6g.4xlarge` | 16 | 16 vCPU | 27,500 | 27,482 | 265 | ~91% at steady | 420 ms | 1.85 | 0 |
| **33** | **2 × `m6g.4xlarge`** | 32 | 16 | 27,500 | 27,428 | 267 | 44, 46% at steady | **208 ms** | **1.76** | 0 |
| 34 | 2 × `m6g.4xlarge` | 32 | 16 | 43,000 | 42,959 | 403 | 71, 72% at steady | 241 ms | 1.83 | 0 |
| **35** | **1 × `m6g.8xlarge`** | 32 | 16 | 43,000 | 42,976 | 403 | 73% at steady | 257 ms | **1.87** | 0 |
| **35** | **4 × `m6g.2xlarge`** | 32 | 16 | 43,000 | 42,959 | 402 | 70, 70, 70, 71% at steady | 260 ms | **1.81** | 0 |
| 36 | 3 × `m6g.4xlarge` | 48 | 32 | 50,000 | 49,960 | 464 | 55, 54, 54% at steady | 212 ms | 1.79 | 0 |

"Completed" and "req/s" are the steady part of each hour from the chains' Gatling ticks; "at steady" CPU
is CloudWatch over the same part. Runs and their links are in [`case-index.md`](case-index.md).

## What changed, and what did not

**Only the number and size of app copies, and in row 36 the database.** Everything else is row 31's:
the release candidate (`946553685`, sha `1315739b…` verified on every copy before every run), the
`pilot-day-180-10k` dataset reloaded fresh before each run, the customer's ten-a-day push with 8 media
files per encounter and batched upload URLs, co-tenants at 792 an hour, a discarded 900-second warm-up
through the load balancer immediately before each measured hour.

- **Each copy is configured identically**: heap pinned at `-Xmx5120m`, a 100-connection pool, New Relic
  reporting as the one application `avni-loadtest` so its timeslices sum across copies, 1-minute
  CloudWatch. A new copy is created by avni-infra's `app_instance_count` and configured by the same
  playbook as the first (row 32).
- **The load balancer** forwards every request to one target group: **round robin, no stickiness**,
  cross-zone on, no slow start, health check `/ping` every 30 s. A device's requests within one sync are
  spread across copies, not pinned to one.
- **Rows 33–36 are n = 1 each.** The comparisons rest on differences larger than the run-to-run spread
  one shape produced across rows 31 and 33 (1.76–1.85 CPU s per sync).

## The split is even at every count

Mean CPU per copy over each run's window (CloudWatch, the cpu-per-sync window: injection plus its tail):

| run | copies | mean CPU per copy | peak per copy |
|---|---|---|---|
| row 33, 27,500 an hour | 2 | 35.0, 36.7% | 49.9, 49.5% |
| row 34 steady, 43,000 | 2 | 47.3, 48.2% | 76.0, 77.7% |
| row 35, 43,000 | 4 | 47.5, 47.5, 47.5, 47.9% | 74.0–75.6% |
| row 36 steady, 50,000 | 3 | 40.7, 40.8, 41.3% | 57.6–58.9% |
| row 36 ramp to 70,000 | 3 | 46.1, 46.3, 46.9% | 77.6–78.2% |

**No copy ran more than two points from the others in any run**, and at the 15-minute readings during
the steady hours the spread was 0–2 points. Round robin per request is enough: with 4,000–6,000 syncs
in flight, each made of ~35 requests of very different cost, the expensive ones average out across
copies within seconds. An uneven split would have been a finding in itself; there is none.

## A copy costs nothing extra per sync

At the same 32 app vCPU and the same 43,000 syncs an hour (row 35):

| shape | CPU s per sync (New Relic) | EC2 CPU seconds, summed | app heap, mean / peak |
|---|---|---|---|
| 1 × `m6g.8xlarge` | **1.87** | 84,048 | 1,317 / 2,621 MB |
| 2 × `m6g.4xlarge` | **1.83** | 78,845 | 1,335 / 2,332 MB |
| 4 × `m6g.2xlarge` | **1.81** | 82,253 | 1,284 / 2,401 MB |

The three sit inside the 1.76–1.87 that rows 31–36 produced across every shape. **Each copy's fixed
costs — its own JVM, JIT compilation, GC, agent, caches and pool — are not visible at these loads**, and
neither is any economy from one large heap. Row 33 says the same from the other side: the same load as
row 31 on two copies instead of one cost 1.76 against 1.85.

**Heap is not what a copy is sized by.** Every healthy run, at any copy count, averaged 1.25–1.39 GB and
peaked at 2.3–2.6 GB of the pinned 5,120 MB — including the single `m6g.8xlarge` carrying all 43,000 syncs
an hour. The heap pin that keeps results comparable is generous for every shape measured.

## Latency follows each copy's utilisation, not the count

**Row 33 halved p95 (420 → 208 ms) at the same throughput** as row 31. Not because two servers are faster
than one, but because each ran at ~45% instead of ~91%: row 31's 1.1× hour sat at the edge of its knee,
where requests queue for CPU and for connections, and two copies removed that queue.

At equal utilisation the count barely matters. At 32 vCPU and ~61–63% per copy (row 35) p95 was 241 ms
on two copies, 257 on one and 260 on four. The ~20 ms is inside what one shape varies by, and it points
nowhere consistent: neither "fewer, larger" nor "more, smaller" wins.

## The pool: why one large copy is the exception

Each copy has its own 100-connection pool. **One copy carries all the concurrency in that one pool**, and
on the single `m6g.8xlarge` at 43,000 an hour it peaked at its cap of 100 (mean 84) — the only shape to
touch it at that load. Two copies held ~42 each, four ~27 each (counted as open connections to port 5432
on each host; the Tomcat JDBC pool reports no gauge to New Relic).

- **A single large server needs its pool raised with its size.** At 48 vCPU in one JVM the pool would bind
  before the CPU does — the same shape as row 31, where the pool pinned behind a saturated CPU, but here
  ahead of it. Several copies avoid this without changing a setting.
- **The database's connections follow copies × what each needs**: ~84 on one or two copies, ~109 on four,
  ~120–157 on three at 66,000 an hour. All far below the RAM-scaled `max_connections` of these classes.
  At the database's limit (row 34) both 100-connection pools were full — 200 connections — because the
  database, not the pools, was slow.
- **For production**: the pool size per copy can stay at 100 while copies are added; it is the
  single-large-server path that needs it changed.

## What scaling out exposed: the database's limit, and linear costs

With the app tier no longer the limit, rows 34 and 36 measured the database for the first time.

- **One 16-vCPU database tops out at ~48,000–49,000 syncs an hour** (~470–490 req/s). At saturation it ran
  98–99% with every connection of both pools taken, and app CPU *fell* as requests waited for it. Disk was
  never the limit — write IOPS ≤1,023 of 3,000.
- **A 32-vCPU database carries 50,000 at 47%**, and the ramp to 70,000 found no knee: ~66,000 completed
  an hour with app 73% and database 59%.
- **Both tiers' costs are linear in syncs and independent of instance size or count**: the database
  ~0.30 vCPU and the app ~0.53 vCPU per 1,000 syncs an hour, from 27,500 to 70,000. Sizing is arithmetic.

Details are in [`findings-summary.md` §11](findings-summary.md#11-scaling-out-and-what-50000-syncs-an-hour-needs)
and the execution plan's [row 34](execution-plan.md#row-34-results) and [row 36](execution-plan.md#row-36-results) results.

## Two CPU measures agree until the knee, then diverge

The run log carries app CPU two ways: New Relic's JVM user time, summed across copies, and EC2's
utilisation × vCPU × window, summed across hosts.

| run | New Relic, CPU s | EC2, CPU s | EC2 against New Relic |
|---|---|---|---|
| row 33 | 49,720 | 51,624 | +3.8% |
| row 34 steady 0.9× | 80,149 | 78,845 | −1.6% |
| row 35, 1 × 8xlarge | 81,987 | 84,048 | +2.5% |
| row 35, 4 × 2xlarge | 79,451 | 82,253 | +3.5% |
| row 36 steady | 91,072 | 93,131 | +2.3% |
| row 36 ramp | 110,168 | 108,320 | −1.7% |
| **row 34 ramp (saturated)** | 144,155 | **208,092** | **+44%** |
| **row 34 steady 1.1× (saturated)** | 43,513 | **68,299** | **+57%** |

**Below the knee they agree within ±4%**, which validates both: summing New Relic across copies is
right, and the EC2 figure needs no correction for the agent or the OS. **Past it they part by half**:
the host burns CPU that the JVM's user time does not count. Which part is unmeasured; the likely ones
are system time on thousands of waiting connections and GC under a heap that grew to ~4 GB (peaks of
3.9 and 4.1 GB, against ≤2.6 GB in every healthy run). So **CPU per
sync from an overloaded run is not comparable** in either measure, and the two disagreeing is itself a
sign a run went past its knee.

## Running several copies: what the campaign learned

None of this is a performance finding; all of it is what made the runs work, and most of it applies to
running copies anywhere.

- **Start copies one at a time.** Each copy applies pending Flyway migrations at start-up. The playbook
  configures with `serial: 1` and `env-teardown.sh start-apps` starts each copy only after the previous
  one answers `/ping`. Concurrent starts are untested; with the same jar and no pending migration they
  would only validate, but the serial start costs ~30 seconds a copy.
- **A new copy takes ~6 minutes** from `tofu apply` to serving: create, then base, security, JDK, New
  Relic and the app. An existing stopped copy starts and serves in ~30 seconds.
- **A copy is unhealthy for its first health checks.** Two consecutive `/ping` passes 30 s apart are
  needed, so a new or restarted target is out of rotation for ~1 minute after it serves. A readiness
  check must wait for the load balancer's verdict, not the copy's own `/ping`.
- **AWS can refuse capacity for one copy.** `m6g.4xlarge` start was refused once with
  `InsufficientInstanceCapacity` (5 Nov) and succeeded on a retry 60 seconds later; the start command
  retries ten times.
- **Copies can stay stopped while the database is reset.** From row 34 the dataset reload ran from the
  injector, with every copy stopped through its ~80 minutes, and the copies started afterwards. Each
  measured run therefore begins on a cold JVM; the 900-second warm-up through the load balancer brings
  every copy up together (each at 1–2% CPU during it, which is why a warm-up check can only compare
  copies, never test an absolute floor).
- **Logs are per copy.** Each copy writes its own server log; a scale-in deletes a host and its logs with
  it, so every copy's logs were archived after each run — only the files new since the last archive.
- **The tofu default is one copy.** With three in place, a plain `tofu apply` without
  `-var app_instance_count=3` would delete two of them. The campaign's resize helper passes the count.

## Routing

Round robin balances request counts, not cost, and avni's sync requests vary widely in cost. It still
balanced to within two points because each copy sees thousands of requests a minute. **Least outstanding
requests** — which sends each request to the copy with the fewest in flight — would matter if one copy
were slower than the others: a smaller instance among larger ones, a copy pausing for GC, or a copy just
started. It was not measured; both are available to production, and for unequal copies it is the safer
default.

## What this does not establish

- **That avni-server can run as several copies in production.** It cannot today. Its second-level cache
  keeps users, catchments, locations and concepts for 24 hours, so an admin edit on one copy is invisible
  to the others; start-up recovery of bulk uploads and timed jobs (Glific, storage clean-up) run on every
  copy; locks around Metabase setup, identifier ranges and user prefixes are in-memory; job queues are per
  copy; and a rules server is expected on the same host. **A sync-only load exercises none of these**, so
  they neither failed nor were tested. These runs measure what scaling out would buy once they are fixed.
- **Anything about writes, uploads, exports or admin traffic across copies.** Sync pushes are the only
  writes measured.
- **More than four copies, or copies of unequal size.**
- **Pool sizes other than 100.** The single-large-copy limit is inferred from its pool reaching the cap,
  not from raising it.
- **Loss of a copy mid-run.** No copy was stopped under load; failover behaviour is unmeasured.
- **Repeatability.** Each shape ran once.

## What it means for the recommendation

- **Scale the app tier by whichever is easier to operate** — size and count cost the same per sync. Prefer
  several copies: they keep the per-copy pool at its default, scale in finer steps, and lose less when one
  fails. Avoid one very large copy unless its pool is raised with it.
- **Size each tier from its own linear cost**: ~0.53 app vCPU and ~0.30 database vCPU per 1,000 syncs an
  hour, divided by the utilisation wanted. For 50,000 an hour that is ~48 app vCPU (3 × `m6g.4xlarge` or
  6 × `m6g.2xlarge`) and a 32-vCPU database, measured at ~55% and ~47% (row 36).
- **Fix the multi-copy blockers before relying on any of it.** Until then the single-server figures apply:
  ~25,000 syncs an hour on 16 + 16 ([§10](findings-summary.md#10-where-it-breaks-with-the-fixes-in)),
  scaling upward with the server's size the same way (row 35's single 32-vCPU copy held 43,000).
