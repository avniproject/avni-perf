# Load Tests for Avni Sync
`./gradlew gatlingRun`

## Configurations

### Users

`src/gatling/resources/sync-users.csv` holds the users the simulation drives. It is **not tracked** —
copy the example and edit:

```
cp src/gatling/resources/sync-users-example.csv src/gatling/resources/sync-users.csv
```

The csv expects the following columns:
- `userName`
- `lastModifiedDateTime`
- `password` — only under `AUTH_MODE=cognito`
- `token` — only under `AUTH_MODE=cognito`; skips minting if supplied
- `pushScale` — optional, default 1. Multiplies this user's push volume, so one file can carry
  field workers creating twenty encounters a day alongside supervisors creating almost none

`co-tenant-users.csv` has the same shape and is only read under `CO_TENANTS=on` — see
[Co-tenants](#co-tenants). Also untracked.

### Authentication

`AUTH_MODE` selects how the simulation identifies users. Default is `none`.

| Mode | How | Use it for |
|---|---|---|
| `none` *(default)* | Sends only the `USER-NAME` header. No credentials, no AWS access, no expiry. Requires the target server to run with `AVNI_IDP_TYPE=none` | Everything, and the only option for runs longer than an hour |
| `cognito` | Mints a token per user via `AdminInitiateAuth` and sends `AUTH-TOKEN`. Needs AWS developer credentials on the machine running the simulation, plus `COGNITO_CLIENT_ID` and `COGNITO_USER_POOL_ID` | Short runs against a Cognito environment — staging, prerelease — and measuring what the `none` path omits |

```
./gradlew gatlingRun -DAUTH_MODE=cognito \
  -DCOGNITO_CLIENT_ID=... -DCOGNITO_USER_POOL_ID=...
```

Both identifiers are required under `cognito` and have no defaults — a default would silently point
a run at whichever environment was hardcoded rather than the one under test.

> **`cognito` has no token refresh.** Tokens expire after an hour by default, so runs longer than that
> will fail partway. Use `none` for soak testing.

> **A server running `AVNI_IDP_TYPE=none` must not be publicly reachable.** Anyone who can reach it is
> authenticated as whatever username they send.

Running both modes against the same environment gives the per-request cost of token verification —
see [the sync simulation plan](docs/sync-simulation-plan.md), section B.

### Sync window

`SYNC_MODE` sets how far back each entity's `loadedSince` reaches, which is what decides whether the
server takes the full-sync path or the incremental one. Default is `csv`.

| Mode | Window | Use it for |
|---|---|---|
| `full` | 1900 for every entity | A first sync, or a device after a reset. The heaviest case |
| `incremental` | `now − INCREMENTAL_SINCE_HOURS` (default 24) for every entity | A simple, uniform incremental run |
| `csv` | Whatever the user file carries | Replaying a specific state |
| `realistic` | Per entity, spread as production's own gaps are | The faithful case |

**`realistic` is the one that matches production.** Q2 measured the gap between a user's syncs at a
median of 16 minutes but a 75th percentile of 12.5 hours — two behaviours, not one with spread.
Every entity gets its own draw from that distribution, so a single user's entities span minutes to
days, which is what a real device looks like: reference data last pulled when the configuration
changed, transactional data a few minutes ago.

Uniform timestamps are the thing to avoid. `loadedSince` feeds the per-row queries behind
`syncDetails`, so one value across every entity produces uniform selectivity — a query plan
production never runs. Draws are derived from the user and entity name rather than randomised, so a
run reproduces.

**The window only bites once the bootstrap has run.** The simulation asks the server what each user
tracks — one `POST /v2/syncDetails` with `[]` per user, cached — because the server matches on
entity name *and* type uuid. Without it every typed entity falls through to the server's 1900
default and full-syncs whatever the mode says, which is most of the sync volume. The run warns on
the console if it ever builds a body without one.

### Client-side storage cost

The simulation pauses after each page to stand in for the time a device spends parsing and
persisting it. `STORAGE_MODEL=weighted` (default) computes that as

```
MS_PER_PAGE + records x entity tier x BASE_MS_PER_RECORD
```

**Both terms are needed — they dominate in different places.** The crossover is at 19 records a
page. Below it the fixed term is most of the cost, and 98% of production's syncs are down there;
above it the per-record term takes over, and that is where the heavy syncs live. Drop the per-record
term and a full heavy page is understated 159x; drop the per-page term and a 3-record page is
understated 7x.

Three tiers, assigned by the entity generator so a new entity arrives with one: **0.2x** for flat
lookup rows, **1.0x** for configuration and light transactional, **3.0x** for the
observation-bearing four. A page of subjects therefore costs fifteen times a page of genders, which
one uniform constant could not express.

Defaults are **174 ms a page** and **9.19 ms a record**, both derived from production: a sync is 81
requests over 14.1 seconds, and anchoring the intercept there makes the marginal term fall out
consistently across bands at 8.8 to 9.2 ms.

> **Both are calibration starting points, not measurements.** `MS_PER_PAGE` should be 174 minus the
> server's own median response, since the simulation genuinely incurs that part. F7 fits both by
> matching a simulated sync against production's `14.1s + 8.85ms x records`.

> **`STORAGE_MODEL=zero` is not a neutral fallback.** Removing the pause lets a virtual user fire
> its 81 requests back to back, bounded only by the server — at a 20 ms response that is **9x a real
> device's request rate**, and 17x at 10 ms. It is a deliberate over-drive for saturation runs. Used
> by accident it manufactures contention that cannot occur.
>
> The per-page term is what shapes load: a real device issues one request every 174 ms, and on a LAN
> the round trip vanishes. Without it the simulation runs about four times too fast per user.

### Environment variables
Can be overridden using `./gradlew gatlingRun -DBASE_URL=` etc.

`BASE_URL` default https://perf.avniproject.org

`USER_COUNT` defaults to number of rows in resources/sync-users.csv

`RAMP_PERIOD` defaults to number of rows in resources/sync-users.csv * 20 — `PROFILE=ramp` only

`PROFILE` `ramp` (default), `steady`, `burst`, `stress` or `smoke` — see below

`SYNC_WINDOW_HOURS` default 12; hours over which a day's syncs arrive

`SYNCS_PER_HOUR` defaults to `USER_COUNT / SYNC_WINDOW_HOURS`

`DURATION_MINUTES` default 120 — `steady` and `stress`

`BURST_MINUTES` default 15 — `burst` only

`STRESS_TO_SYNCS_PER_HOUR` defaults to ten times the starting rate — `stress` only

`PAGE_SIZE` defaults to 1000, matching the client

`NOW` defaults to current time at start of simulation

`SYNC_MODE` one of `full`, `incremental`, `csv`, `realistic` — see above. Default `csv`

`INCREMENTAL_SINCE_HOURS` defaults to 24, used by `SYNC_MODE=incremental`

`STRUCTURAL_CHECK` `true` asserts zero failures, for H5's gate on a generated dataset

`MAX_FAILED_PERCENT` error budget for a load run, default 0.05 — the customer's figure

`MAX_P95_MS` asserts the 95th percentile when set. Production's light-band figure is 80,000

`STORAGE_MODEL` `weighted` (default) or `zero` — see above

`BASE_MS_PER_RECORD` defaults to 9.19 — see above

`MS_PER_PAGE` defaults to 174 — see above

`PUSH` `true` includes the upload path. **Default false** — see below

`PUSH_PROFILE` `customer` (default) or `production` — see below

`PUSH_ENCOUNTER_MODEL` `program` (default) or `general` — which table the customer's
encounters land on

`CO_TENANTS` `true` adds production's other organisations as a second syncing population — see below

`CO_TENANT_SYNCS_PER_HOUR` default 792, Q4's busiest recorded hour

`CO_TENANT_SECONDS` how long to sustain that rate, defaults to `RAMP_PERIOD`

`CO_TENANT_USERS` their user file, default `co-tenant-users.csv`

`CO_TENANT_MEDIA_PER_ENCOUNTER` default 0.0214, production-wide rather than the customer's bundle

`PUSH_INDIVIDUALS` / `PUSH_ENROLMENTS` / `PUSH_PROGRAM_ENCOUNTERS` / `PUSH_ENCOUNTERS` override one
entity's distribution, as `probability:[min:]p50:p95:max:mean`

`PUSH_OBSERVATION_MULTIPLE` harvested observation sets per pushed record, default 1

`PUSH_MEDIA_PER_ENCOUNTER` media files each encounter queues, default 1.42; `0` disables media

`MEDIA_MODEL` `pause` (default) charges the upload time; `none` charges nothing — see below

`MEDIA_FILE_KB` default 500, matching the client's 1280x960 quality-1 capture

`MEDIA_UPLOAD_KBPS` device upload bandwidth, default 125 (about 1 Mbps)

`PUSH_SEED_SIZE` rows harvested per entity when seeding a device, default 20

`PUSH_ALLOW_UNSAFE_TARGET` `true` lifts the protected-host guard

## Injection profiles

`PROFILE` sets the arrival shape. **Arrival rate is derived, not configured** — one sync per user
per day over `SYNC_WINDOW_HOURS` — so 500 workers over twelve hours is 42 an hour.

| Profile | Shape | For |
|---|---|---|
| `ramp` **(default)** | every user in the file syncs once, then exits | the H5 structural check |
| `steady` | constant arrival for `DURATION_MINUTES` | most test cases |
| `burst` | `USER_COUNT` devices arriving over `BURST_MINUTES` | a training cohort |
| `stress` | rate climbing to `STRESS_TO_SYNCS_PER_HOUR` | finding the knee |
| `smoke` | one sync | CI |

> **The default is the wrong shape for a load run, deliberately.** `ramp` gives each virtual user
> one sync and then exits, so it cannot express "42 syncs an hour for four hours" — which is how
> every test case is specified. It is kept as the default because it is what runs today and what
> the structural check needs: H5 has to touch **every** user in the file, and a rate-based profile
> syncs a sample, so an unreadable row belonging to a user it never reached would pass silently.
> The run warns if `STRUCTURAL_CHECK` is set with any other profile.

Injection is open in every profile: a sync is a short visit, not a session, so the server sees a
rate. A closed model would hold in-flight syncs constant, which is the one thing that has to be
free to move when the server slows down.

`SYNC_WINDOW_HOURS=1` compresses a day's syncs into one hour — the single property separating the
clustered test cases from the spread ones.

## The push path

`PUSH=on` adds the upload half of a sync: the records a device queued since it last synced, posted
before it asks the server what changed — the order `dataServerSync` uses.

**There is no bulk endpoint.** The client posts one record per request and waits for each, so a
device with twenty queued encounters makes twenty sequential round trips, each through the full
filter chain and its own transaction. That is the load: request count, not payload size.

> **Push writes, and that is why it is off by default.** A run with `PUSH=on` changes the database
> it just measured. The next run is not the same experiment, and the dataset's H5 verdict no longer
> describes what is in the tables. Budget a restore between runs.
>
> The cost of the default running the other way: **a green run without `PUSH=on` is not evidence
> the write path holds**, because write contention, lock waits and index maintenance cannot appear
> in it at all. The startup banner says which of the two you are getting.

A short deny list refuses the protected hosts outright. Pushed subjects and encounters cannot be
told apart from field data afterwards.

**References are harvested, not configured.** Four page-0 reads per user collect the subject type,
address, enrolments and real observation sets that pushed records point at — so the push path works
against a generated dataset, a restored dump or a hand-built org without a shared list of UUIDs.
Observations are reused verbatim from real rows, because insert cost here is dominated by GIN
maintenance over the `observations` jsonb.

A device with nothing to reference pushes nothing and fails nothing, so the run prints how many
devices were only partially seeded and what they lacked. Read a run with a high count as a floor.

**Each sync draws twice per entity**: whether it pushes that entity at all, and if so how many.
`PUSH_PROFILE` picks which workload those draws describe.

**`customer` (the default)** — the deployment this exercise exists to size, from the customer's
stated 20 encounters per field worker per day.

| Entity | Pushed in | min | p50 | p95 | max | Per sync |
|---|---|---|---|---|---|---|
| ProgramEncounter | every sync | 8 | **20** | 45 | 150 | 24.0 |
| Individual | 59.6% | 1 | 1 | 13 | 174 | 1.98 |
| ProgramEnrolment | 33.2% | 1 | 1 | 15 | 349 | 1.33 |

The level is the customer's; **the spread is a modelling choice** — their one number read as the
median, p95 at 45, floor at 8. `-DPUSH_PROGRAM_ENCOUNTERS=1.0:20:20:20:20` restores a flat twenty
if the literal reading is preferred. No customer figure exists for registrations or enrolments, so
those borrow production's shape.

> **`PUSH_ENCOUNTER_MODEL` decides which table the twenty a day land on, and it will change.**
> The customer's programme design is work in progress: the bundle they export today has no live
> programs — every mapping is a general `Encounter` on one `Patient` subject type — while the
> design this exercise was scoped against is an NCD programme with ten encounter types.
>
> `program` (default) follows the design. `general` follows the current export, moving the volume
> to `Encounter` and dropping enrolments. Same volume either way; what changes is whether the
> write path touches `program_encounter` behind a `program_enrolment` parent or `encounter`
> hanging straight off the subject — different sync strategies, indexes and join depth.

**`production`** — Q17's measurement of the platform as it stands, over 105,718 syncs.

| Entity | Pushed in | p50 | p95 | max | Per sync |
|---|---|---|---|---|---|
| ProgramEncounter | 28.7% of syncs | 3 | 33 | 323 | 2.38 |
| Individual | 59.6% | 1 | 13 | 174 | 1.98 |
| ProgramEnrolment | 33.2% | 1 | 15 | 349 | 1.33 |
| Encounter | 21.1% | 1 | 13 | 479 | 0.83 |

**35% of real syncs push nothing at all**, which is what the probabilities encode. A sync that
pushes anything averages 14.3 records; over all syncs it is 9.3 — against the customer profile's
27.3.

> **Reference, and the co-tenant setting.** Use `production` for the co-tenant traffic in cases 7
> and 13, where the platform's existing organisations load the server alongside the customer's.
> Never for the customer's own cases: it understates them roughly tenfold.

Override either with `probability:p50:p95:max:mean` or `probability:min:p50:p95:max:mean`, e.g.
`-DPUSH_PROGRAM_ENCOUNTERS=1.0:8:20:45:150:24`. A probability of 0 disables the entity.

Per-user variation comes from an optional `pushScale` column in the user file: a supervisor pulls a
wide catchment but creates few records, so case 3 wants a value well under 1.

**`ChecklistItem` and `AttendanceRecord` are deliberately not modelled.** They are 20% of what
production pushes and by far the burstiest — maxima of 4,790 and 750 records in one sync, minutes
of uninterrupted POSTing from a single device — but the organisations in scope do not use them. A
future extension if this is ever pointed at one that does.

## Media

Every queued media file costs one `GET /media/uploadUrl` against the server and one PUT straight to
S3. `MediaQueueService` sends them **one at a time, and drains the whole queue before the first
record is pushed** — `PARALLEL_UPLOAD_COUNT` is 1, despite the chunking around it.

**Set the rate from the deployment's bundle, not from the default.** `survey.py BUNDLE
--media-repeats N` reports files per filled form, per form type. A platform-wide average is the
wrong base rate for any one implementation: production sits at 0.02 files per encounter across 986
organisations, while the customer's screening bundle reaches **16 on a single encounter**.

Two structural details drive that, and a flat count of media form elements misses both. Images sit
inside **repeatable question groups** — one is named *"Take photos of all lesions and 1 photo
without lesion"* — so a single form element produces one file per repeat. And elements carrying
`editable: false` are the app's own display copies of images another element already uploaded;
counting them doubles every image.

**The bytes are not transferred, but the time is charged.** S3 serves the objects directly, so a
PUT from the injector would measure the injector's own network — an in-region pipe that moves
500 KB in tens of milliseconds where a field device on rural 3G takes four seconds. Neither the
server's load nor the device's timing. So `MEDIA_MODEL=pause` spends the elapsed time and skips the
request, the same trade `STORAGE_MODEL=weighted` makes for parse-and-persist.

| `MEDIA_UPLOAD_KBPS` | ~ | 31 files | Sync duration |
|---|---|---|---|
| 40 | 0.3 Mbps | 388 s | 402 s |
| 125 (default) | 1 Mbps | 125 s | 139 s |
| 375 | 3 Mbps | 42 s | 56 s |
| 1250 | 10 Mbps | 12 s | 26 s |

That is the *conservative* row of the encounter mix — a uniform one. Where the image-heavy
encounter type is the common one, multiply by up to eleven.

> **This inflates sync duration without adding server load.** During the transfer the device asks
> avni-server for nothing, so *syncs in progress* rises several-fold while *server requests in
> flight* does not move. Sweep `MEDIA_UPLOAD_KBPS` rather than trusting one value — it is the
> largest single lever on how long a media-bearing sync takes, and it says nothing about the
> server.

`MEDIA_MODEL=none` restores the old behaviour of charging nothing. The startup banner says which
you have, because a run that skips the time starts its data push sooner than any real device could.

## Co-tenants

`CO_TENANTS=on` runs a second population alongside the customer's: production's other
organisations, **syncing** rather than merely present. That distinction is the whole difference
between test cases 6 and 7, and it separates a structural cost from a contention one.

- **Case 6** — the co-tenant dataset loaded, `CO_TENANTS` off. What their *presence* costs: RLS
  selectivity, planner statistics, table and index size.
- **Case 7** — the same dataset, `CO_TENANTS=on`. What their *activity* costs on top: connection
  pool, CPU, IO.

The difference between those two runs is the pair of numbers the hosting decision needs.

They arrive at a fixed rate rather than as a user count, because co-tenant load exists to occupy
the pool and the CPU — how many distinct accounts produce it does not change what the server feels.
They also push on the `production` profile and production's media rate, not the customer's: a
co-tenant pushes 6.5 records across a third of its syncs and almost never photographs anything.

> **Every request is named with its population's prefix**, so `Customer · Individual` and
> `Co-tenant · Individual` are separate rows in the report. Case 7 asks what the customer's sync
> costs *while* the platform is busy; pooling both into one distribution answers a different
> question, and the answer would move with the mix rather than with the server.
>
> `forAll()` asserts the error budget per request name, so the two are independent there.
> **`MAX_P95_MS` is not** — it uses `global()` and pools them. With co-tenants running, read the
> customer's p95 off the `Customer · ` rows. The run warns about this at startup.

Their user file is separate and untracked, the same as `sync-users.csv`:

```
cp src/gatling/resources/co-tenant-users-example.csv src/gatling/resources/co-tenant-users.csv
```

## Run archiving

Every `gatlingRun` writes `run-metadata.json` next to the report's `simulation.log`, recording what
produced the run: simulation commit (and whether the tree was dirty), target, injection profile,
entity table source, dataset and server build.

Two of those cannot be discovered and must be passed, or they are recorded as `unrecorded`:

```
./gradlew gatlingRun -DDATASET_ID=... -DSERVER_BUILD=...
```

A `simulation.log` with no provenance cannot be compared with anything, which is the whole point of
keeping it.
