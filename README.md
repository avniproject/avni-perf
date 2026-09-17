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

### Environment variables
Can be overridden using `./gradlew gatlingRun -DBASE_URL=` etc.

`BASE_URL` default https://perf.avniproject.org

`USER_COUNT` defaults to number of rows in resources/sync-users.csv

`RAMP_PERIOD` defaults to number of rows in resources/sync-users.csv * 20

`PAGE_SIZE` defaults to 100

`NOW` defaults to current time at start of simulation

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
