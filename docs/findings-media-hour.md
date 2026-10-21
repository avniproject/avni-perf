# Findings: the media-heavy hour

**Run** `2026-10-21T06-58-37Z-media-hour-m6g.xlarge-c2a0e76` — row 20 of the
[execution plan](execution-plan.md). The scenario was sized in advance in
[`scenario-tanuh-media-hour.md`](scenario-tanuh-media-hour.md), and that document asked for four
numbers to be scored against its predictions. They are scored below, including the one it got wrong.

**One sentence.** The hour that worried us holds on 4 vCPU with zero failures, and the server is
about 2% of what a field worker waits for — the other 98% is the device uploading and storing, and
no amount of server would change it.

## What ran

| | |
|---|---|
| customers | 1,500 syncs over a 1 h window, `case5-users-pilot.csv`, push on, 8 media files per encounter |
| co-tenants | 792 syncs/h from `co-tenant-users.csv`, push on, media at the platform's 0.2306 per encounter |
| media model | `pause`: `uploadUrl` is called, the S3 PUT is replaced by a 4 s pause (500 KB at 125 KB/s) |
| app server | `m6g.xlarge`, 4 vCPU, heap pinned at 5120m, pool 100, New Relic attached, no profiler |
| full syncs | 25 of 2,292 (16 customer, 9 co-tenant), the random draw |
| wall time | **2 h 20 m** for a 1 h injection — see *The tail* |

## Headline

| | |
|---|---|
| requests | **415,082, 0 failed** |
| response time p50 / p95 / p99 / max | 32 / 503 / 1,427 / 17,711 ms |
| under 800 ms | 98.05% |
| mean throughput | 49.4 rps over the whole 2 h 20 m; **~90 rps during the hour** (the drain is one device at a time) |
| customer requests per sync | **249.6**, of which **196.8 are `uploadUrl`** (79%) |
| co-tenant requests per sync | 51.4 |

`uploadUrl` is 71% of every request the server answered. It returns a signed URL in ~40 ms and
touches nothing heavy, which is how the server sustained 90 rps on a request mix that case 1 put
past the 2 vCPU knee: **the requests are different requests.**

## The sync-time breakdown — what a device actually waits for

This is the number the run exists to give. Per completed customer sync, from
`sync-durations.csv` joined to the server's own request log for the media count:

| per customer sync (n = 1,500) | mean | p50 | p95 | max |
|---|---|---|---|---|
| **duration** | **886 s** | **749 s** | 1,657 s | 4,825 s |
| media files | 197 | **160** | 368 | 1,184 |
| upload wait, files × 4 s | 787 s | 640 s | 1,472 s | 4,736 s |
| storage pause (the D7 model) | 78 s | 67 s | 200 s | 210 s |
| **server + queue** | **21 s** | **18 s** | 43 s | 87 s |
| records pulled | 15,752 | 13,778 | 41,042 | 43,356 |

**Share of a customer's total sync time: upload 88.9%, storage pause 8.8%, server 2.3%.**

So a median field worker waits **12.5 minutes**, of which **10.7 is their own uplink**, 67 s is
their device writing records, and **18 s is everything the server did, queueing included**. The
server+queue figure held at 18 s median even with app CPU in the high eighties, which is the
measurement that says the box was busy without being the thing anyone was waiting on.

The split by feeder cohort is uniform — `state-` and `ngo-` users differ by under 5% on every row
— so this is the push model, not a property of some users.

Co-tenants are the opposite shape and worth stating for contrast: 33.5 s median, of which the
storage pause is 62%, server 26%, upload 12%. Their media rate is 0.23 per encounter.

### The instrument caveat, which affects every media-bearing run

`serverMs` in `sync-durations.csv` is `durationMs − pausedMs`, and `pausedMs` accumulates **only
the storage pause**. The media pause (`.pause(mediaTransfer())`, `AvniSyncSimulation` ~2529) is
never added to it. **So `serverMs` as recorded includes the entire upload wait**: 808 s mean for
this run against a true 21 s — a 39× overstatement of server cost. Any reading of `serverMs` from
a run with `PUSH_MEDIA_PER_ENCOUNTER > 0` is wrong by the upload wait until the harness records
the media pause separately. The figures above subtract it using the per-user `uploadUrl` count
from `chs.log`; the raw column is left as the harness wrote it.

## The tail: why one hour took 2 h 20 m

The harness uploads a sync's whole media backlog **first and serially**, then posts the records.
The encounter draw is p50 20 / p95 45 / max 150 per sync, and at 8 files each that is
160 / 360 / 1,200 files, or 10.7 / 24 / 80 minutes of upload before the first record moves.

| media files per user, from the server log | users |
|---|---|
| 1–8 | 56 (co-tenants) |
| 25–80 | 245 |
| 81–240 | 865 |
| 241–800 | 385 |
| **over 800** | **20** — 100+ encounters, 53–80 min of upload each |

The last user injected, at 13:28:23, drew ~144 encounters, made 1,152 `uploadUrl` calls at exactly
4.0 s intervals with nothing else in between, and finished at 14:49. The server was at 1–2% CPU
for the last 50 minutes of that. **Nothing was stuck**; the drain was 20 devices each working
through an hour of serialized upload, and the run's wall time for any media run is
*injection window + max-encounters × files-per-encounter × 4 s*.

63 customer syncs exceeded 30 minutes, 16 exceeded an hour.

## Scoring the scenario document

| predicted | measured | verdict |
|---|---|---|
| ~215 requests per customer sync | **249.6** | 16% over. The prediction used the median encounter count (20 → 160 files); the draw's mean is 24.6 → 197 files. The document flagged exactly this: *"20 encounters a day is the customer's median, so p95 syncs push more"* |
| 160 media files per sync | **p50 160**, mean 197 | the median landed exactly |
| ~5.96 CPU s per customer sync | *pending `make cpu_per_sync`* | |
| ~10,300 CPU s for the hour | *pending* | |
| app CPU 61–68% on 4 vCPU | **85–90% observed during the hour** (CloudWatch, 5-min means); the cached figure follows | **materially over the prediction** — see below |
| whether RDS moved | **RDS 80–85% during the hour**, against 38–42% in the 4 vCPU case 13 run | **it moved a lot** |

The CPU rows are filled from `tools/cpu-per-sync.py`, which needs a New Relic user key and runs
before `make run_log`.

**The miss that matters.** Both tiers sat 20–25 points above the estimate. The arithmetic priced
`uploadUrl` at ~8 ms of CPU, *inferred*, and multiplied it by 127 extra calls per sync; the run
made 197 per sync, not 160, and RDS went to 80–85% on a request the model treated as nearly free.
The document said the inferred `uploadUrl` cost was *"the single largest lever here and the one
input nobody measured"*, and asked for one more run to measure it — the scenario at the default
media rate against this one, `ΔCPU ÷ Δ(uploadUrl calls)`. That run is now the obvious next
measurement, because at 80–85% RDS **the database is the next constraint**, and it is being driven
there by the cheapest request in the mix.

## What this settles, and what it does not

- **4 vCPU holds the hour** — 0 failures, p95 503 ms — but with less headroom than estimated, and
  RDS closer to its ceiling than the app server is to its own.
- **The server is not what a field worker waits for.** 2.3% of sync time. The product problem
  this scenario exposes is a quarter-hour sync on a 1 Mbps uplink, and it is a client problem:
  uploading concurrently, uploading in the background, or uploading less.
- **It is a model.** 8 files/encounter × a p50-20 draw × a serial 125 KB/s uplink is the harness's
  rendering of the customer's bundle. If the real device uploads concurrently, or the real bundle
  is lighter, the upload wait scales down proportionally; the server numbers do not change.
- **Not settled:** what `uploadUrl` costs the database. One paired run answers it.
