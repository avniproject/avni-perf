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

`MAX_FAILED_PERCENT` error budget for a load run, default 1.0

`MAX_P95_MS` asserts the 95th percentile when set. Production's light-band figure is 80,000

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
