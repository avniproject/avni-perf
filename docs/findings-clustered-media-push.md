# Findings: clustered — co-tenant load, media push

Case 13's shape — syncs clustered into one hour with co-tenants syncing — with push on and 8 media
files per encounter.

**Run** `2026-10-21T06-58-37Z-media-hour-m6g.xlarge-c2a0e76` — row 20 of the
[execution plan](execution-plan.md). The scenario was sized in advance in
[`scenario-clustered-media-push.md`](scenario-clustered-media-push.md), and that document asked for four
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

> **The draw that produced this tail has since been replaced, 21 Oct 2026.** 8 / 20 / 45 / 150 was
> a modelling choice; the customer's own figure is that a heavy day is unlikely to pass thirty
> encounters. `PushProfiles.customer()` now draws **10 / 20 / 30 / 45, mean 20** — a 45 ceiling,
> deliberately above thirty so a busy day is not undercounted. At 8 files a visit that caps a sync
> at 360 files and **24 minutes of upload**, against 1,200 and 80 here. **A rerun would drain in
> roughly the injection window plus 24 minutes, and carry about a fifth less media load** — mean
> 20 encounters against this run's 24.6. The tail above is a property of the old draw, not of the
> workload.
>
> **To reproduce this run like for like, pass `-DCUSTOMER_PUSH_DRAW=v1`**, which restores the old
> draw. `v2` is the default. Every push run records which it used as `push.customerDraw` in
> `run-metadata.json`.

## Scoring the scenario document

| predicted | measured | verdict |
|---|---|---|
| ~215 requests per customer sync | **249.6** | 16% over. The prediction used the median encounter count (20 → 160 files); the draw's mean is 24.6 → 197 files. The document flagged exactly this: *"20 encounters a day is the customer's median, so p95 syncs push more"* |
| 160 media files per sync | **p50 160**, mean 197 | the median landed exactly |
| ~5.96 CPU s per customer sync | **~6.8** — 11,542 total less the co-tenants at case 7's 1.68 s × 792, over 1,500 | 14% over, in step with the extra media calls |
| ~10,300 CPU s for the hour | **11,542** in the standard window (injection + 20 min); the drain beyond it adds ~370 | 12% over |
| app CPU 61–68% on 4 vCPU | **68.3% mean over the injection hour, peaks 93.6%** (62.4% over the 80-min window) | the mean lands at the top of the band; the peaks do not |
| whether RDS moved | **RDS 70.4% mean, 98.5% peak over the hour**, against 38–42% in the 4 vCPU case 13 run | **it moved to the ceiling** |

CPU from `tools/cpu-per-sync.py` (New Relic `apm.service.cpu.usertime`, window
`06:58:37–08:18:37Z`), utilisation from CloudWatch 5-minute means. Per-sync overall: **5.04 s**.

**The customer figure is corrected, not read off.** `cpu-per-sync.py` attributes whole-server
CPU to cohorts in proportion to `serverMs`, and `serverMs` carries the upload wait for customers
(see the caveat above) — so its raw split, 7.69 s per customer sync and 0.14 per co-tenant, hands
nearly everything to the customers. Co-tenants have never cost 0.14 s; case 7 measured 1.68. The
6.8 above subtracts them at that rate. Until the harness records the media pause, the weighted
split is wrong for every media-bearing run.

**The miss that matters is the database.** The application landed where the arithmetic said it
would; RDS did not. The estimate priced `uploadUrl` at ~8 ms of *application* CPU, inferred, and
said nothing about the database because the request was assumed to touch it lightly. 295,000 of
them in an hour took RDS from the low forties to a 70% mean and a 98.5% peak. The scenario
document called the inferred `uploadUrl` cost *"the single largest lever here and the one input
nobody measured"* and asked for one paired run — this scenario at the default media rate against
this one, `ΔCPU ÷ Δ(uploadUrl calls)`, on both tiers. That run is now the obvious next
measurement, because **the database is the next constraint**, and it is being driven there by the
cheapest-looking request in the mix.

## Row 23: the re-draw — supervisors push nothing, the customer's own spread

Row 20 overstated its own workload twice over: supervisors pushed a field worker's twenty a day,
and the encounter draw's tail (max 150) put 1,200 files on one sync. Row 23 —
`2026-10-21T12-27-12Z-case15-redrawn-m6g.xlarge` — removes both (`case5-users-pilot-nosuppush.csv`,
`CUSTOMER_PUSH_DRAW=v2`: 10 / 20 / 30 / 45) and changes nothing else: same `m6g.xlarge`, same
control jar, same co-tenants, on row 20's residue by choice. Warmed by a 900 s burst after a
resize and redeploy, where row 20 was warm from case 13.

**It landed where the plan put it.** Scored against the predictions written beforehand:

| | row 20 | predicted | **row 23** |
|---|---|---|---|
| media files, customer syncs | 295,232 | ~215,000 | **217,400** |
| users pushing media | 1,500 | 1,344 field workers | **1,344** — the 156 supervisors pushed nothing |
| files per field-worker sync | p50 160, mean 197, max 1,184 | p50 160, mean 160, max 360 | **p50 160, mean 161.8, p95 240, max 360** |
| upload wait, worst sync | 80 min | 24 min | **24 min** (25.6 min sync) |
| wall time | 2 h 20 m | ~1 h 25 m | **1 h 20 m** |
| requests | 415,082 | | 327,309, p50 28 ms, p95 426, 99.2% under 800 |
| app CPU s | 11,542 | ~10,400 | **10,714** |
| customer CPU s per sync, corrected | ~6.8 | ~6.0 | **~6.3** |
| app CPU, mean | 68% over the hour | ~61% | **~62% over the hour**, 54% over the 85-min window, peak 89% |
| **RDS, mean / peak** | **62% / 98.5%** | ~60% / ~85% if it follows `uploadUrl` | **52% / 81.4%** |

**The question was whether RDS comes off its ceiling, and it does.** 26% fewer `uploadUrl` calls
took the peak from 98.5% to 81.4% and the mean down 17%. Not one-for-one: the pulls, identical in
both runs, are the floor the database sits on, and the media calls were what spiked it. The paired
run the scenario document asked for is in effect answered by this one.

Per customer sync, from `sync-durations.csv` joined to the server's own `uploadUrl` counts:

| | field workers (1,344) | supervisors (156) | row 20, all 1,500 |
|---|---|---|---|
| duration p50 / p95 / max | 722 / 1,047 / 1,536 s | 197 / 233 / 246 s | 749 / 1,657 / 4,825 s |
| upload wait p50 | 640 s | 0 | 640 s |
| storage pause p50 | 68 s | 173 s | 67 s |
| **server + queue p50 / p95** | **13.3 / 19.7 s** | 21.4 / 30.5 s | 18.1 / 43.1 s |
| records pulled p50 | 13,844 | 32,647 | 13,778 |
| share: upload / storage / server | 89% / 9% / 2% | 0% / 89% / 11% | 89% / 9% / 2% |

No customer sync exceeded 30 minutes; row 20 had 63, and 16 over an hour. The server's share of a
field worker's wait is unchanged at 2%, and its absolute time fell 18 → 13 s at the median — less
queueing behind media calls. A supervisor's sync is now what it should be: a large pull, a long
storage pause, no upload.

**Gatling reports `BUILD FAILED`, on 2 KO in 327,309 requests.** Both are `Co-tenant → Groups`,
both from **organisation 24**, both HTTP 500 after ~30 s: `GET /groups/search/lastModified` for the
first co-tenant organisation has **failed on every call today — 4 of 4**, two of them inside row
19's control run, where they sit among its 467. No other organisation's groups call has failed.
Only a full sync reaches that endpoint for a co-tenant, which is why it surfaces at the 0.01%
level. It is a standing data defect in org 24, not load.

**New Relic names the cause.** All four `ErrorTrace`s carry the same message: `Could not write
JSON: Unable to find org.avni.server.domain.User with id 2100000117`. The query succeeds; the
response fails while being written. `Group` inherits `CHSEntity`'s `createdBy` and
`lastModifiedBy`, which serialise as usernames through a lazy `User` proxy, and resolving that
proxy is what throws. Under the organisation's database role a `users` row is visible only if the
user is in that organisation, is an admin of its account, or belongs to an organisation in an
organisation group (`V1_144__ChangeUserTableRLS.sql`). So one of org 24's groups was created or
last modified by **user 2100000117, who either does not exist or is outside what org 24's role can
see** — most likely the identity that provisioned it. Which one it is takes a query, left to be run
rather than run here:

```sql
select id, organisation_id, username, is_voided from users where id = 2100000117;
select id, name, created_by_id, last_modified_by_id from groups
 where organisation_id = 24 and 2100000117 in (created_by_id, last_modified_by_id);
```

**Fixed 23 Oct 2026.** The queries answered it: user 2100000117 does not exist, and it was org
24's bootstrap identity — every co-tenant's 18 bundle-imported user groups carry their own
provisioning user as creator (528 such ids across the 513 organisations, all still present), and
org 24's alone had been deleted. Nothing else referenced it: `user_group` carried no dangling ids,
and across every organisation the only dangling audit references in `groups` were those 18 rows.
Repointed to `admin` (user 1), which is what the three standard groups already carry;
`groups/search/lastModified` as an org 24 user then returned 200 with 22 groups in 0.1 s. The
server behaviour is still worth an issue of its own: one unreadable audit user turns a whole
metadata endpoint into a 500, which on a real device would fail every full sync for that
organisation.

The identifier generator also warned throughout — `No non-exhausted identifier assignments found`
— for customer users whose pushed individuals had exhausted their ID pools. A push-model artefact
of running the same users through many push runs, not a server fault, and worth knowing before
reading any `individual` POST latency from a media run.

## Why `uploadUrl` loads the database

**Added 22 Oct 2026, from the New Relic backup.** `uploadUrl` signs an S3 URL and its handler
makes no database call (`MediaController.generateUploadUrl`). It still costs the database **about
twelve statements every time** — 11.9 per request and 18.1 ms of database time in row 20, 12.1 and
15.7 ms in row 23, from 114,252 and 92,234 sampled `Transaction` events. At 71% of all requests,
that is most of what the database did:

| | row 20 | row 23 |
|---|---|---|
| `uploadUrl`, share of requests | 288,440 of 404,205 — **71%** | 218,170 of 327,685 — **67%** |
| **share of every statement the database executed** | **46%** | **41%** |
| share of database time | 23% | 24% |

Windows are the timeslice captures — row 20's first 80 minutes, row 23's 85 — so counts are a
little short of the run totals.

**The twelve are per-request overhead, not media.** Differencing the per-statement timeslices
between the two runs — 70,270 fewer `uploadUrl` calls, and 7,480 fewer push POSTs that account for
the remainder — gives, per `uploadUrl`, about:

| statements | from |
|---|---|
| 1 `users`, 1 `account_admin`, 1 `organisation` | authentication — `AuthService` looks up the user, checks admin status and loads the organisation, every request |
| 1 `catchment` | the user's catchment, loaded lazily during the request; sampled SQL tags it to `uploadUrl` |
| **2 `gender`** | **`DummyInterceptor`**, registered in both `ApiConfiguration` and `SyncConfiguration`, so it runs twice per request — an unfiltered `select … from gender` each time |
| ~6 session statements | `SetOrganisationJdbcInterceptor`: `set role` and `set application_name` when a connection with an organisation leaves the pool, `RESET ROLE` on every return |

The session count fits the code: the three authentication lookups run before the organisation is
known, each on its own connection, so each pays only the `RESET ROLE`; the request's own connection
pays all three. That is a reading of the code that matches the counts, not a trace.

**Removing `DummyInterceptor` takes exactly two of them off.** The same request types in rows 21
and 22, on the test jar, make **2.0 fewer database calls per GET** than in row 19's control —
`resetSyncs` 13.7 → 11.5, `programEncounter` 23.8 → 21.5, `encounter` 30.2 → 28.5 — so an
`uploadUrl` on the fixed build would cost about ten.

**This is the mechanism behind row 20's 98.5% RDS peak.** The media did not reach the database;
the per-request scaffolding of 288,000 small requests did, at nearly half of all statements. It
also says where the remaining cost sits once the interceptor goes: **the authentication lookups and
their connection resets are half of what is left**, repeated on every request a device makes. A
short-lived cache of the authenticated context per token would take an `uploadUrl` from about ten
statements to about four, and every other request down by the same six. That is an avni-server
question rather than a finding, and it is untested here.

## What this settles, and what it does not

- **4 vCPU holds the hour** — 0 failures, p95 503 ms — and the application CPU landed inside the
  estimate. **RDS did not, on row 20**: a 98.5% peak is the ceiling. **On row 23, the realistic
  version, it is 81%**: the media calls were the spike, and with the customer's own spread the
  database has headroom again — though the pulls hold it at ~52% mean regardless.
- **The server is not what a field worker waits for.** 2.3% of sync time. The product problem
  this scenario exposes is a quarter-hour sync on a 1 Mbps uplink, and it is a client problem:
  uploading concurrently, uploading in the background, or uploading less.
- **It is a model.** 8 files/encounter × a p50-20 draw × a serial 125 KB/s uplink is the harness's
  rendering of the customer's bundle. If the real device uploads concurrently, or the real bundle
  is lighter, the upload wait scales down proportionally; the server numbers do not change.
- **Settled by row 23 and the backup:** `uploadUrl` is what drove the database to its ceiling — 26% fewer calls took the peak down 17 points — while the pulls are its floor. Per call it is about twelve statements of per-request overhead, 46% of everything the database executed in row 20 ([why](#why-uploadurl-loads-the-database)).
- **Open:** org 24's groups endpoint — the cause is an unreadable audit user, 2100000117, and the query that settles which kind is above. Not the server's: the exhausted identifier pools of the load users.
