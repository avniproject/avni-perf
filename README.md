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

`RAMP_PERIOD` defaults to number of rows in resources/sync-users.csv * 20

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

`PUSH_INDIVIDUALS` / `PUSH_ENROLMENTS` / `PUSH_PROGRAM_ENCOUNTERS` / `PUSH_ENCOUNTERS` records
queued per sync, default 1 / 1 / 20 / 2

`PUSH_OBSERVATION_MULTIPLE` harvested observation sets per pushed record, default 1

`PUSH_ENCOUNTERS_PER_MEDIA_FILE` default 50; `0` disables the presigned-URL calls

`PUSH_SEED_SIZE` rows harvested per entity when seeding a device, default 20

`PUSH_ALLOW_UNSAFE_TARGET` `true` lifts the protected-host guard

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

**Volumes are provisional.** 20 program encounters per sync is arithmetic from the customer's "20
encounters per worker per day", not measurement — Q17 in
[production-measurement-queries.md](docs/production-measurement-queries.md) replaces it. Per-user
variation comes from an optional `pushScale` column in the user file: a supervisor pulls a wide
catchment but creates few records, so case 3 wants a value well under 1.

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
