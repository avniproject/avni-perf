# Extending the Sync Simulation

Task breakdown for turning `avni-perf` from a working sync probe into an instrument capable of
finding choke points in the Avni server.

**Scope:** server-side, sync only. Client-side performance (device profiling, Maestro/Flashlight,
production RUM) is tracked separately.

**Status:** planning draft, September 2026.

---

## Where it stands

`AvniSyncSimulation` authenticates under a selectable mode, posts a full 79-entity status array to
`/v2/syncDetails`, walks every entity the response marks changed, paginates each one, and posts sync
telemetry at the end. The entity list is generated from `openchs-models` rather than hand-maintained,
and CI fails if it drifts.

That is a faithful download-sync probe, production is measured, the test cases are specified
with numbers, and a dataset generator exists that reproduces them.

**What is missing is everywhere those three meet a server.** No environment to run against, no
instrumentation on it, no write path, and no restore between runs — so **no run has yet happened
against generated data**, and the generator's own output has never been loaded. That is the next
boundary, and most of what remains sits behind it.

The table below covers the whole plan rather than just the harness. **A `Not started` cell means no
work has been done on that item at all** — the "Before" column still describes it today.

| | Before | Now |
|---|---|---|
| **Harness hygiene** | | |
| Gatling plugin | 3.9.2 | 3.15.1.3 |
| Gradle wrapper | 7.6 | 8.14 |
| Java toolchain | not declared — runs inherited the ambient JDK | 17, declared |
| Dead scaffolding | `Engine`, `Recorder`, `IDEPathHelper`, `recorder.conf` | deleted |
| Entity loop | every entity nested inside every sync detail | one chain per entity, built at startup |
| Request naming | generic | named per entity and entity type |
| Credentials | user file committed to the repo | gitignored, example file only |
| README | stale | documents both auth and sync modes |
| Run archiving | none | metadata written into each report directory |
| **Read-path fidelity** | | |
| Entity list | 64, hand-maintained in `AvniEntities.json` | 79, generated from `openchs-models`, drift-checked in CI |
| `syncDetails` body | `EmptyBody.json` — an empty array | the entities **and type uuids** the server says each user tracks, learned by bootstrapping |
| Page size | 100 | 1000, matching the client |
| Sync window | client clock, always 1900 in the committed user file | server-supplied, with `SYNC_MODE` for full / incremental / per-user / **realistic**, the last drawn per entity from Q2 |
| Auth | Cognito only | `AUTH_MODE` — username header or Cognito |
| Telemetry | none | posted like a real client, tagged so production queries exclude it |
| Reset sync | not requested at all | request modelled in the right order; no scenario needed — the storm was a defect |
| Storage pause | uniform random, 0 to a constant | per-entity weighted model at `BASE_MS_PER_RECORD`, with `STORAGE_MODEL=zero` to remove it |
| Request timeouts | Gatling defaults | **Not started — D8.4** |
| **Write path** | | |
| Push / upload | none | modelled: one POST per record in the client's own order, seeded from the deployment. `PUSH=on`, off by default |
| Media presigned URLs | none | upload signing modelled with the push (D5.1); on-demand viewing out of scope (D5.3) |
| **Workload design** | | |
| Feeder | `random()`, drawing with replacement | `circular()`, warns when oversubscribed |
| Full vs incremental | full only, every run | `SYNC_MODE`; incremental stays partial until D1 |
| Test cases | none defined | **specified with numbers**, in [test-scenarios.md](test-scenarios.md) |
| Injection profiles | one open ramp | defined as cases; **not yet implemented as Gatling profiles — E3** |
| Multi-tenant load | single organisation | **Not started — E4** |
| Co-tenant sync traffic | none | **Not started — E7**, and case 7 needs it |
| Production's tenant skew | none | built — 513 tenants and 473 rows-only organisations, reproducing Q12's skew |
| **Test data** | | |
| Dataset generation | none — runs hit whatever happened to be in the database | built: `tools/data-generator`, 195 tests · needs a target database to run against |
| User provisioning | hand-built CSV | generated with the dataset — catchments, users and a feeder spanning every tenant |
| Dataset gate (H5) | none | statistical gate built; the client half of the structural check is manual |
| Schema drift | nothing to drift against | generation refuses on any column the contract has not accounted for |
| Dataset and environment parity | none | **Not started — F5** |
| Run-to-run restore | none — nothing reset between runs | **Not started — G4 / F6** |
| **Environment** | | |
| Deploy path into the closed environment | none | **Not started — F4** |
| Environment contract | undocumented | specified in section J; **Not started** to implement |
| **Trustworthiness** | | |
| Server APM | not provisioned for a load-test environment | **Not started — F1** |
| Request-logging overhead | unmeasured | **Not started — F2** |
| Second Gatling setup | unreconciled | **Not started — F3** |
| Distributed injection | undecided | **Deferred** — one injector until F7 shows it saturating |
| Assertions | commented out | zero-failure structural gate, plus rate and p95 bounds for a load run |
| Calibration gate | none | **Not started — F7** |
| **Grounding** | | |
| Production measurement | none — every figure was an estimate | run, and [tracked per query](production-measurement-queries.md#what-has-run) · Q11 needs a client change before it can be answered |
| Success criteria | empty | measured, one row left to fill |

**The empty body row is the one that mattered most.** Posting an empty array made the server
synthesise every entity at 1900, so every run drove the full-sync path and never the incremental one
that 98% of production syncs take.

**Production is now measured.** `baseMsPerRecord`, the sync-gap distribution, peak concurrency,
catchment volumes, observation shape, tenant skew and hierarchy shape all come from the queries in
[production-measurement-queries.md](production-measurement-queries.md). The figures sit in the
sections that use them, and the Success criteria table below has one row left to fill.

The work below is of two kinds: making the simulation **faithful** to what the client actually does,
and making it **trustworthy** as a measuring instrument. Neither is optional given the goal — an
unfaithful simulation finds the wrong bottleneck, and an untrustworthy one reports the injector's
limits as the server's.

---

## Success criteria

**Partly filled; still blocks A6.** Three of the five numbers below are now measured against
production. The two that remain are not derivable from the codebase or from telemetry — they are
product decisions, and A6 cannot be implemented until someone makes them.

**What this work is for.** Finding choke points in the current server. Not capacity certification, not
regression gating — those are different exercises with different designs, and adopting either goal
later would change several decisions in this plan.

**Numbers that must be filled in before A6 can be implemented:**

| Target | Source | Value |
|---|---|---|
| p95 sync duration, light band (<5k records) | Q5 | **80.0 s** (p50 14.1 s) |
| p95 sync duration, heavy band (~47.5k records) | Q5 | p50 **1,076 s**; p95 pending re-run |
| Acceptable error rate under load | Product decision | **0.05%** |
| Concurrent-user target to design against | [test-scenarios.md](test-scenarios.md) | **1,000** workers across 8–10 tenants |
| Heaviest single device to design against | [test-scenarios.md](test-scenarios.md) | **~125,000** records — a sub-centre supervisor at year 2 |
| Peak-hour concurrency to reproduce | Q4 | **792 syncs/hour** (0.22/sec) peak; **267** distinct users; ~3 in flight |

**Every row is now filled.** The four measurable ones came from production; the acceptable error
rate is the customer's decision, taken at **0.05%** — which at 81 requests a sync permits roughly
one sync in twenty-five losing a single request, so a run that breaches it has a fault rather than
noise.

> **Concurrency is not the risk here; volume per device is** — and at the confirmed once-a-day sync
> frequency the deployment produces **under one sync in flight**, so this is emphatic rather than
> marginal. Production's busiest hour ever recorded
> saw 267 distinct users across *every* organisation and roughly **3 syncs in flight**. The customer's
> 1,000 workers is four times that user base — a real step up, but still a modest arrival rate. What
> is new is the **mix**: a thousand workers across 8–10 tenants, with supervisors carrying an order of
> magnitude more than field workers, on infrastructure also holding production's existing tenant skew.
> Per-device volume stays inside what production already carries (Q3's p99 is 264,569 rows against a
> supervisor's ~125,000 at year two), so this exercise is about concurrency and tenancy rather than
> about finding a volume ceiling — unless supervision sits above the sub-centre, which would put
> volume back at the centre.

**There is no separate incremental figure, and there cannot be one from this table.** `sync_telemetry`
does not record whether a sync ran full or incremental. The light band is the closest available proxy
and a good one — 98% of production syncs pull fewer than 5,000 records — so **"no worse than 80.0 s at
p95" is the working threshold** for the common case.

The honest default for a choke-point exercise is to derive thresholds from *today's* production
distribution and assert "no worse than current" — that is enough to detect a regression and enough to
recognise a knee, without requiring anyone to invent an SLO first. That is what the filled rows above
are: current production behaviour, not a target anyone chose.

> **Provenance.** Figures marked as measured come from three query runs against production,
> **2026-09-03** and **2026-09-17**, over a 30-day window (90 days for Q2). The second run corrected
> defects the first exposed — hour-of-day bucketing in Q4, per-sync rather than per-user counting in
> Q3, a missing schema filter in Q7, and clock-skew outliers in Q1 and Q5 — so where the two disagree,
> the later run stands.
>
> **Two caveats attach to everything here.** The queries ran against a **physical replica**, so
> `pg_stat_*` counters reflect Metabase's workload rather than sync traffic and cannot answer
> index-usage questions (Q7). And the `sync_source` exclusion literal was wrong in both runs — the real
> value is `automatic-upload-only`. A third run on **2026-09-17** applied the correct literal and the
> clock-skew bound to Q1, Q2 and Q3; all three moved by less than 1% — `baseMsPerRecord` went from
> 9.185 to 9.188 ms/record — so the earlier conclusions stand and the figures here are the corrected
> ones. Re-derive rather than trusting these indefinitely; the distributions move.

**Definition of done.** The exercise ends when the top bottlenecks have been named, attributed to a
specific resource, and either fixed or explicitly accepted with a reason. Not when a run passes.

### Measure before fixing

Reading the code has already produced several plausible suspects, listed throughout this plan. **They
are hypotheses, not findings.** Every one of them gets a cost attached before anyone changes it —
including the ones that look obviously wasteful, and including the ones where the fix is a one-line
change.

Two reasons this matters more than usual here. A cheap-looking fix applied to a suspect that turns
out to cost 0.3% burns review and deploy cycles on noise while the real bottleneck stays hidden. And
several suspects are doing **necessary work** — the organisation interceptor enforces row-level
security, `syncDetails` exists to reduce the client's request count — so the question is never "is
this expensive?" but "**is it expensive relative to what it buys?**"

That second framing is the one to carry into every measurement below.

### What the tests will answer

Here are the suspects, against the cases that will cost them. Nobody should answer these in advance
— that is what the runs are for, and an answer asserted now is the thing this exercise was built to
replace.

Worth reading in both directions. **A test case that answers no question is a run nobody needs**, and
a question with no case against it will not get answered. Laying them side by side makes either gap
visible.

| Question | Answered by | Suspect, if any |
|---|---|---|
| **Shared or separate infrastructure?** | Cases 5, 6, 7 — the deltas between them | Multi-tenancy costs scale with the platform, not with this customer: RLS selectivity, planner statistics across all tenants, `set role` on every borrow |
| **Where are the choke points?** | The whole exercise; cases 4 and 10 most directly | Storage IO is the prime suspect — 19.4 GB of indexes against 933 MB of cache, on a fixed 3,000 IOPS |
| **Does the server hold at this load at all?** | Cases 2, 3, 4 | Nothing yet. Per-device volumes sit inside what production already carries, and these cases run under one sync in flight |
| **Does volume growth show a knee?** | Case 8, across day 60/120/180/365 | Index size crossing cache residency is the shape to look for. **The only evidence this exercise gives about scale beyond the pilot** |
| **What does a supervisor's catchment cost?** | Case 3 against case 2 | Depends entirely on question 1 above |
| **Is `syncDetails`' per-row cost material?** | Cases 1 and 4, with F1/F2 attribution | Q8 found 4 of 79 entities changed at p50, so 94% of the per-row queries prove nothing changed — but the endpoint saves 75 HTTP round trips, so the question is cost *relative to what it buys* |
| **Does the organisation interceptor cost enough to matter?** | F2.1, under case 5 | Three Postgres round trips per connection borrow, plus `getMetaData()` evaluated for a TRACE log argument |
| **Does ETL contention matter?** | The contended variant of case 4 | ETL shares the same IO ceiling on a 90-minute cycle |
| **Where does it break, and which resource names it?** | Case 10, the stress ramp | Unknown by design — this is the one question with no useful prior |

**None of these blocks anything.** They are the deliverable — the
[open questions](open-questions.md) are what blocks, and they are a separate list for that reason.

---

## A. Upgrade and harness hygiene

Six minor versions behind, with several patterns that will distort results before the server is ever
the limiting factor.

**A1 — Gatling 3.9.2 → 3.15.1.3.** *Done.* Gradle wrapper 7.6 → 8.14, plugin 3.9.2 → 3.15.1.3, Java
toolchain pinned to 17 so runs do not inherit whatever JDK is ambient.

Three things broke, all outside the simulation itself:

- **`logLevel` / `logHttp` were removed from the plugin extension.** They were already inert — the
  repo ships `logback-test.xml`, and those options only applied when no logback config was present.
- **`Engine.java`, `Recorder.java`, `IDEPathHelper.java`** reference `GatlingPropertiesBuilder` and
  `RecorderPropertiesBuilder`, which are no longer on the plugin's classpath. Removed along with
  `recorder.conf` — IDE-launcher scaffolding from the original template, and runs go through
  `./gradlew gatlingRun` per the Makefile.
- Nothing else. **`AvniSyncSimulation` compiled unchanged**, and a smoke run against a dead port
  completed end to end with reports generated — so the checks, `jmesPath` usage and
  `transformWithSession` all survived six minors intact.

> **Finding for D8.4:** the smoke run showed Gatling's default request timeout is **60 seconds**. A
> page of 1000 observation-bearing rows plausibly approaches that, and a timeout firing mid-run looks
> exactly like a server failure. Set it explicitly.

> The specific breaking changes per version were not verifiable at time of writing — the upgrade guide
> pages did not render through automated fetch. Treat the list above as the areas to check, not as a
> complete migration list.

**~~A2 — Fix the token cache data race.~~** *Done in A10.1 — now a `ConcurrentHashMap`.*

**~~A3 — Stop blocking the injector event loop.~~** *Not doing — the blocking call survives only on the opt-in `AUTH_MODE=cognito` path. Acknowledged in A10.1.*

**A4 — Materialise each response body once.** *Done.* The two `checkIf` predicates each call
`response.body().string()`, so every page of every entity is turned into a String twice purely to test
for the substrings `totalPages` and `hasNext`. On large payloads this burns injector CPU and inflates
the latency being measured. Replace with a single parsed check.

**A5 — Flatten the nested entity loop.** *Done.* `foreach(entities)` wrapping `foreach(syncDetails)` with a
`doIfEquals` is at minimum 60 × 60 ≈ 3,600 in-session comparisons per virtual user per sync — and that
is a floor, not an estimate. The syncDetails list carries one entry per entity *type instance*, so
every encounter type, program and subject type adds a row (visible in `SyncDetailsBody.json`, which
already has several `Encounter` entries). For a large organisation the real figure is several times
higher. Resolve the ordered work list once in a session function, then iterate it.

**A6 — Re-enable assertions.** *Done.* `MAX_FAILED_PERCENT` bounds the error rate for a load run
and `MAX_P95_MS` the 95th percentile, asserted only when set because production's 80.0 s figure (Q5)
was not measured on a laptop against a local database. `STRUCTURAL_CHECK=true` replaces the rate with
**zero failures**, which is H5's gate on a generated dataset.

The remaining open figure is the acceptable error rate itself — a product decision, and the last
unfilled row of the Success criteria table.

**A7 — Name requests meaningfully.** *Done.* `http(entityTypeUuid)` names every reference-entity request with
the empty string, since those entities have no type UUID. Name by entity plus UUID.

**~~A8 — Remove `System.exit(1)` from the auth path.~~** *Done in A10.1 — throws instead.*

**A9 — Credentials and config hygiene.** *Done.* `sync-users.csv` is tracked in git — `.gitignore` only covers
`sync-users.*.csv`, which does not match it. `CognitoHelper` also carries a hardcoded client ID and
user-pool ID as defaults. Untrack the CSV, widen the ignore rule, move IdP identifiers to config.

**A10 — Delete dead weight.** *Done.* `AvniEntities.json` is unused and already inconsistent with the
hardcoded list. `SyncDetailsBody.json` is unused — the sim posts `EmptyBody.json`. The commented
`resetSyncs` block can go too. *(`Recorder.java`, `Engine.java`, `IDEPathHelper.java` and
`recorder.conf` were removed under A1 — they were IDE-launcher scaffolding that no longer compiles
against Gatling 3.15.)*

**A10.1 — Put authentication behind `AUTH_MODE`.** *Done.* Rather than deleting the Cognito path, it
sits behind a system property defaulting to `none`.

Under `none` the simulation sends only the `USER-NAME` header and the auth chain does no work —
`AUTH-TOKEN` is not added to the protocol at all. This is the mode every soak, stress and spike run
uses, and the only one viable past the token lifetime.

Under `cognito` the token path runs. Keeping it costs one conditional and four dependencies, and buys
two things deleting would have forfeited: short runs against Cognito environments such as staging and
prerelease — the only way to exercise that path once B1 closes the perf environment — and B2 as a flag
flip rather than a code restoration.

**It has to be exercised or it rots**, which is the failure mode already seen three times in this
repo: `AvniEntities.json`, the duplicate `avni-server/perf/gatling` harness, and the `legacy` storage
mode dropped from D6.3. An occasional smoke run under `AUTH_MODE=cognito` against staging is what
keeps it honest.

A2 and A8 were folded in while the code was open — the token cache is now a `ConcurrentHashMap`, and
`CognitoHelper` throws rather than calling `System.exit(1)`. **A3 is acknowledged, not fixed:** the
Cognito call still blocks inside a session function and stalls the injector's event loop, which is
why it is confined to the opt-in path. Fixing it properly means pre-minting off the virtual-user
path — disproportionate for a second-class mode, and recorded here rather than hidden.

**A11 — Archive runs with their metadata.** *Done.* Gatling already keeps `simulation.log` in each
report directory; what was missing was any record of what produced it. An `archiveRun` task now
finalizes every `gatlingRun` and writes `run-metadata.json` beside it: simulation commit, target,
injection profile, entity table source, dataset and server build.

Three deliberate choices:

- **Absence is recorded, not omitted.** The server build and dataset identity cannot be discovered —
  the server exposes only `/ping`, which returns `pong` — so they are written as `unrecorded` unless
  `-DSERVER_BUILD` and `-DDATASET_ID` are passed, and the task says so on the console. A field that
  is quietly missing reads as "not applicable" later; one that says `unrecorded` reads as "nobody
  wrote it down".

**`DATASET_ID` should now be a recipe name.** The generator emits a recipe, a manifest and an H5
verdict per dataset, so a run can name which one it used and the three files say exactly what that
was — inputs, row counts with content hashes, and whether it passed the gate. Without that the field
records a string nobody can resolve later.
- **A dirty working tree is flagged.** The run cannot be reproduced from the recorded SHA alone, and
  that is worth knowing before a result is quoted.
- **The entity table source is captured** — `openchs-models@1.33.81` — so a change in what the
  simulation asks for is visible in the archive rather than having to be inferred from dates.

**A12 — Update the README.** *Done, and kept current since.* Almost every task in this plan changes something the README documents,
and it is the only operator-facing documentation the repo has.

*Wrong today, independent of any other task:*

- The example CSV header is `userName,lastModifiedDateTime,password|token` — a single column literally
  named `password|token`, not the four columns the README describes. Fix the example file and the
  prose together.
- `PAGE_SIZE` is documented as defaulting to 100. The client ships 1000 (D8).

*Invalidated by work in this plan:*

- The `password` / `token` columns and the "requires AWS developer credentials on the machine
  executing the simulation" note both disappear under B1.
- `BASE_URL` default `https://perf.avniproject.org` changes when the environment goes private (F4.4).
- `NOW` changes meaning once the window end comes from the server response (D2).

*Missing and worth adding:*

- `STORAGE_MODEL` (D6.3) and the injection profile selector (E3).
- How to regenerate the entity table and what the CI drift check enforces (C1).
- What makes a run pass or fail, now that assertions exist (A6).
- Where results are archived and how to compare runs (A11).
- A link to this plan.

> **Do not batch this.** Each task that changes an interface updates the README in the same change;
> A12 is the backstop sweep for what is already wrong and for anything missed. A single documentation
> pass at the end is how the README got into this state.

---

## B. Authentication across a multi-hour run

Tokens are minted once and cached for the life of the run, so any run past the one-hour token lifetime
collapses into 401s.

### Options

| Option | How it works | Cost | Verdict |
|---|---|---|---|
| **User-ID auth** (`AVNI_IDP_TYPE=none`) | Server authenticates from the `USER-NAME` header; no token involved. The sim sends a header and nothing else. | Loses per-request JWT verification and user lookup from measurements. Requires a network-isolated environment. | **Decided** |
| **Extend token TTL** | A perf-only Cognito app client with ID-token validity raised well beyond an hour. | Still needs AWS credentials on the runner; still hits Cognito rate limits during ramp; has a ceiling; a config change someone must remember exists. | Reserve |
| **Refresh in-simulation** | Background scheduler refreshes via `REFRESH_TOKEN_AUTH`; tokens resolved per request through the protocol `sign` hook so refresh is transparent to running users. | Most work, and the component most likely to fail in a way that looks like a server problem. | Only if a finding implicates auth |

**A10.1 keeps both of the first two available** behind `AUTH_MODE`, defaulting to `none`. The Cognito path has no refresh, so it stays limited to runs shorter than the token lifetime — but it survives for short runs against Cognito environments, and it makes B2 a flag flip rather than a project.

**B1 — Run the perf server with `AVNI_IDP_TYPE=none`.** *Decided.* Confirmed in `AuthenticationFilter:68`: when
the IdP type is `none`, the filter calls `authenticateByUserName` using the `USER-NAME` and
`ORGANISATION-UUID` headers and skips token verification entirely. The simulation drops Cognito
completely — no minting, no expiry, no refresh, no AWS credentials on the runner, no Cognito rate
limits during ramp. A10.1 resolves A2 and A8 and makes A3 moot for the default path.

> **Hard constraint.** With `IdpType.none`, anyone who can reach the server is authenticated as
> whatever username they put in a header. The perf environment must be network-isolated — security
> group or VPN, never publicly reachable, never sharing a database with anything real.
>
> This breaks the existing CI deploy path, which reaches `perf.avniproject.org` over the public
> internet. **F4 is a prerequisite for B1, not a follow-up.**

**B2 — Measure the auth-cost offset.** *Available, not yet run.* The one thing B1 gives up is the
per-request cost of `authenticateByToken`: JWT verification plus a user lookup.

Cheap now that A10.1 kept the Cognito path behind `AUTH_MODE`. Run the same simulation twice against
one Cognito environment — `AUTH_MODE=none` and `AUTH_MODE=cognito` — and the delta is the number. No
code to restore, no separate rig, and it does **not** need the perf environment: staging or
prerelease serves, since both run Cognito.

Worth taking once, early, while a Cognito environment is convenient. Until it is, the recorded
position is that the simulation under-counts per-request work by an unmeasured constant.

**B3 — Fallback: refresh tokens off the hot path.** Only if a finding implicates auth.
`AdminInitiateAuth` already returns a refresh token; refresh via `REFRESH_TOKEN_AUTH` on a background
scheduler at ~45 minutes into a `ConcurrentHashMap`. Critically, stop pinning the token into the
session at scenario start — resolve it per request through the protocol's `sign` hook, so a refresh is
transparent to virtual users already running.

---

## C. Entity list — stop hand-maintaining it

The 60-entry list is hardcoded in `sync()`. The git history is largely a record of repairing its
drift; the root cause is two sources of truth and no drift detection.

**C1 — Generate the entity table from `EntityMetaData.js`.** *Done.* `avni-models/src/EntityMetaData.js` is
the client's canonical, versioned list — entity name, resource path, reference/tx type, and the
query-parameter name per entity. Emit the sim's table from it with a small script, commit the output,
and add a CI check that fails when regenerating produces a diff. This converts a recurring manual fix
into a build-time guarantee.

**C2 — Reconcile the entity list.** *Done.* The simulation has **64 entries; `EntityMetaData` has 74**, and
the drift runs in both directions.

*Missing from the simulation (13):* `AttendanceRecord`, `AttendanceType`, `Calendar`,
`CalendarDateMarker`, `CustomCardConfig`, `DashboardFilter`, `DownloadableContent`, `ResetSync`,
`RuleFailureTelemetry`, `Session`, `SyncTelemetry`, `TaskUnAssignment`, `VideoTelemetric`.

*Present in the simulation but not canonical (3):*

- **`ProgramOutcome`** — absent from *both* the client's `EntityMetaData` and the server's
  `SyncEntityName` enum. Fully dead: `filterChangedEntities` gates on
  `SyncEntityName.existsAsEnum`, so the server can never return it and the simulation's entry is a
  no-op line
- **`ProgramConfig`** — absent from the client's `EntityMetaData` but **still present in the server
  enum**. The server would honour a request for it; the client stopped asking. So the simulation
  asking is unrealistic rather than broken
- **`TaskUnAssigment`** — a typo, missing an `n`, in *both* the entity name and the resource path.
  The server declares `TaskUnAssignment` and `/taskUnAssignments/v2`. **Fixed** — see below

> **The typo was a live bug, not cosmetic.** `sync()` matches with
> `doIfEquals("#{syncDetail.entityName}", "#{entity.entityName}")`, so `TaskUnAssigment` never matched
> the server's `TaskUnAssignment` and **that entity was silently skipped on every run** — no error, no
> warning, just an entity that was never synced. `SyncDetailsBody.json` carries the correct spelling,
> which is why it stayed invisible.
>
> This is the strongest argument for C1: a generated list cannot contain a typo, and a drift check
> would have caught all sixteen discrepancies at once rather than one at a time.

A cross-check of all 64 simulation entity names against the server's 79-constant `SyncEntityName`
enum found **only `ProgramOutcome`** unknown to the server — so apart from the typo, every other
entity the simulation asks for is at least a name the server recognises. The remaining reconciliation
is C1's job.

Also: `News` is commented out in the simulation. It can be re-enabled once the environment has a
configured `bucketName` and consistent stored URLs — see D5.4; it does not require a real bucket.

**C3 — Split `EntityApprovalStatus` by entity type.** *Done.* The five per-type entries came free with
C1's generator, but the generator initially dropped the parameter that matters.

`ConventionalRestClient` sets **both** `privilegeParam` and `apiQueryParamKey`, each to the same
`entityTypeUuid` — they are alternatives in appearance only. Exactly the five EntityApprovalStatus
entities declare both, and `EntityApprovalStatusController` reads `entityType` and **`entityTypeUuid`**
— not `subjectTypeUuid`. Emitting one parameter therefore sent the type discriminator the server
ignores and dropped the one it uses, returning approvals for every type rather than one. The
generator now emits both, in the order the client merges them.

---

## D. Fidelity gaps against the real client

Where the simulation and `SyncService.js` disagree.

**D1 — Post real sync statuses to `/v2/syncDetails`.** *Done.* *(Highest value in the plan.)* The client posts
its full `entitySyncStatus` array — one row per `(entityName, entityTypeUuid)` with a `loadedSince`
timestamp. The simulation posts `EmptyBody.json`.

**What the server does with it** (`SyncController.getChangedEntities`): any syncable item *missing*
from the client's list is added with `loadedSince = REALLY_OLD_DATE` (1900); disabled entities are
dropped; then `filterChangedEntities` runs per row, dispatching to a `DeviceAwareService`,
`NonScopeAwareService` or `ScopeAwareService` to ask whether anything changed since `loadedSince` —
**one database query per row**.

So an empty body does not take a cheaper path: the server synthesises the complete list at 1900, and
the simulation therefore only ever drives the **full-sync** shape of this endpoint. It can never drive
the incremental shape, which is the common production case, and every per-row query runs with the
same 1900 timestamp — so their selectivity and query plans are unrepresentative of production.

**How stale is a real `loadedSince`? Measured (Q2):**

**Measured: p25 2.4 min, p50 16.1 min, p75 12.5 h, p90 39.4 h, p99 8.2 days.**

**Users sync far more often than the plan assumed, and the median is minutes rather than hours.**
Q4 corroborates this independently: its peak hour held 792 syncs across 267 distinct users — 3.0 syncs
per user per hour, or one every 20 minutes, against Q2's 16-minute median. Two unrelated queries
agreeing closes the question.

**The distribution is bimodal and both modes matter.** A median of 16 minutes alongside a p75 of 12.5
hours is not one behaviour with spread; it is repeated syncing within a working session, and a long
gap until the next session. D1's `loadedSince` spread must reproduce both — drawing from a single
distribution centred on either mode gets the incremental payload wrong in opposite directions.

**This is also why 98% of syncs are light (Q5).** Syncing every 16 minutes leaves very little to
transfer, which is consistent with the p50 device holding only ~715 rows in total (Q3). The heavy tail
comes from the rarer long gaps and from resets (Q10), not from ordinary use.

```sql
with gaps as (
  select sync_end_time
         - lag(sync_end_time) over (partition by user_id order by sync_end_time) as gap
  from sync_telemetry
  where sync_source is distinct from 'avni-perf-simulation'
    and sync_source is distinct from 'automatic-upload-only'
    and sync_status = 'complete'
    and sync_start_time > now() - interval '90 days'
    and sync_start_time <= now()
)
select percentile_cont(array[0.25, 0.5, 0.75, 0.9, 0.99])
         within group (order by extract(epoch from gap) / 3600) as gap_hours_p25_50_75_90_99
from gaps
where gap is not null;
```

**How to build the array per user:**

1. *Bootstrap once per user.* POST `/v2/syncDetails` with `[]`. The server's own response returns the
   complete set of entity + entityTypeUuid combinations for that user's organisation — every subject
   type, program and encounter type — with the same field shape as the request
   (`EntitySyncStatusContract` is `{uuid, entityName, loadedSince, entityTypeUuid}`, which the sim's
   `SyncDetail` already parses). It round-trips; no need to derive org structure independently.

   > **Built.** The simulation runs this once per user before its first real `syncDetails` call and
   > caches the result, so the body now carries the entity *and* its type uuid. Until it did,
   > `matchesEntity` compared both and every typed entity — `Individual`, `Encounter`,
   > `ProgramEncounter`, `ProgramEnrolment`, and everything split by subject type or form mapping —
   > fell through to the server's 1900 default and full-synced whatever the mode said. **That is
   > most of the sync volume, so incremental mode was not exercising the incremental path at all.**
   >
   > Two virtual users on one account can race and both bootstrap. That costs one wasted request
   > rather than a wrong body, and a lock inside a session function would stall the injector's event
   > loop — a worse trade. If a body is ever built without a bootstrapped list the run says so on
   > the console rather than quietly falling back.
2. *Cache it* in a `ConcurrentHashMap` keyed by username, and build the request body with
   `StringBody(session -> …)` rather than trying to carry a 60-row array in the CSV.
3. *Rewrite `loadedSince` per scenario.* **Built as `SYNC_MODE`**: `full` puts every row at 1900,
   `incremental` at `now − INCREMENTAL_SINCE_HOURS`, `csv` takes the feeder's value, and
   **`realistic` draws each entity its own window from Q2's measured gaps**.

   The buckets this plan originally guessed at — 60% yesterday, 25% last week — are replaced by the
   measurement, and the measurement is a different shape: a median of 16 minutes beside a 75th
   percentile of 12.5 hours is two behaviours rather than one with spread. Drawing every entity
   from a distribution centred on either mode would get the incremental payload wrong in opposite
   directions.

   Verified against Q2 across 5,000 draws: p25 0.040h against 0.039, p50 0.287 against 0.269, p75
   11.9 against 12.5, p90 39.6 against 39.4. A single user's entities span minutes to days, which is
   the point — uniform timestamps produce uniform selectivity in the per-row queries, and that is a
   query plan production never runs.

Also send the client's query parameters: `includeUserSubjectType=true&deviceId=`. `deviceId` is not
cosmetic — `filterChangedEntities` routes some entities through
`isSyncRequiredForDevice(loadedSince, deviceId)`, so sending none takes a different branch. Add a
stable per-user device ID to the feeder.

### D1.1 — Measure what `syncDetails` costs *and* what it saves

**Measured (Q8), over 112,349 syncs: the client posts 79 tracked entities and 4 come back changed at
p50, 7 at p90 — an average changed fraction of 6.1%.** So roughly **94% of `filterChangedEntities`'
per-row queries exist to establish that nothing changed**.

> That 79 also matches the generated entity list's 79, which this plan previously read as confirming
> the client posts every entity every time. **It is a coincidence.** The entity list counts entity
> *types*; the syncDetails body counts *rows*, which is 55 types contributing one row each plus a
> couple of dozen keyed on subject types and form mappings. The two numbers are built differently
> and happen to meet.

**This does not make `syncDetails` a bad trade — read the other side first.** Without it the client
would issue ~75 entity requests instead of ~4, and each one pays `SetOrganisationJdbcInterceptor`'s
three Postgres round trips on connection borrow and release. That is on the order of 225 round trips
of pure role-switching overhead against one borrow plus 79 queries — before counting 75 HTTP round
trips over a field mobile network. **The endpoint is buying a great deal**, which is exactly the
framing "Measure before fixing" asks for.

**Two things about that row count are worth having before anyone attributes its cost.**

`SyncDetailsService.getAllSyncableItems` builds the list in two parts. **Fifty-five entities are
added flat**, one row each, and that includes every metadata entity — `Concept`, `Form`,
`FormElement`, `ConceptAnswer`, `EncounterType`. **A configuration with 5,000 concepts therefore
posts exactly as many rows as one with 50.** What moves the count is the number of subject types,
programmes and encounter types, since the rest of the list is keyed on form mappings. So 79 is
roughly 55 fixed and 24 variable.

**And the count is per user, not per organisation.** Every branch is gated on
`groupPrivileges.hasPrivilege(...)`, so a user without `ViewSubject` on a subject type never
receives its rows. Two users in one organisation post different-sized bodies, which means this cost
varies by privilege — worth ruling out before attributing a difference between users to anything
else.

**The finding is the shape of the work, not its existence.** Answering "4 of 79 changed" via 79
separate queries is the part worth attacking — a single set-based query joining against a `VALUES`
list of the posted statuses, or a per-organisation high-water mark that lets most syncs skip the
per-entity check entirely, would return the same answer at a fraction of the cost. **Measure the
endpoint's share of total sync time before building either** (F1/F2); a 6.1% changed fraction is
strong evidence of waste but says nothing yet about how much of the wall clock it occupies.


`getChangedEntities` does a nested linear scan (`serverSyncableItems.forEach` ×
`clientSyncStatuses.stream().noneMatch`), and `filterChangedEntities` issues **one database query per
row**. For an organisation with many subject types, programs and encounter types that is potentially
hundreds of queries on the endpoint every sync calls first.

**But that cost is the point of the endpoint.** `syncDetails` exists to tell the client which entities
actually changed, so the client requests only those instead of blindly polling all ~60. Framing it as
a bottleneck to remove is wrong; the real question is the trade:

| | |
|---|---|
| **Cost** | One `filterChangedEntities` query per entity + type row, plus the nested scan. Scales with organisation complexity, not with data volume. |
| **Saves** | One paginated entity request per entity that has *not* changed — each of which would otherwise be an HTTP round trip, an auth filter pass, a connection borrow with its three `SET` statements (F2.1), and a query returning zero rows. |

So the trade swings on **how many entities actually change between syncs**:

- **Incremental sync, few changes** — strongly positive. N cheap existence checks replace N full
  paginated queries plus their round trips.
- **Full or first sync, everything changed** — pure overhead. It runs N queries to conclude
  "everything changed", and the client then fetches everything regardless.

**This is answerable from production today, before any load test** — [measurement query](production-measurement-queries.md) **Q8** gives the
distribution of how many entities actually return rows per sync. If the typical sync sees 3 of 60
entities change, `syncDetails` is earning its cost many times over and effort belongs elsewhere. If
it is 50 of 60, the endpoint is mostly ceremony.

Note the outcome is unlikely to be "remove it" either way. If the cost proves significant, the fixes
are to make it cheaper — batch the per-row checks into a single query, or maintain a per-organisation
last-modified summary the endpoint can consult — not to send the client back to polling every entity.

**Under load this also interacts with D8:** at page size 1000 the per-request overhead `syncDetails`
saves is amortised over ten times fewer requests, which weakens the benefit side of the trade
compared with when this endpoint was designed.

**D2 — Take the window end from the server response.** *Done.* The client reads it from the
`syncDetails` response rather than its own clock — and uses **two different values**:

| Entity type | Window end | Why |
|---|---|---|
| Reference | `now` | `getRefData`'s signature takes three arguments and is called with four, so the `endDateTime` passed to it falls on the floor |
| Transactional | `nowMinus10Seconds` | `getTxData` does take it |

The ten-second offset presumably avoids missing records written while the sync is in flight. Whether
the reference-side discrepancy is intentional is unclear — it looks like an argument-count slip — but
it is what runs, so it is what the simulation reproduces. `NOW` survives as an override for runs that
need a pinned window.

**D3 — Model the push/upload path.** *Done, pending a smoke run and Q17.* Everything behind
`postAllEntities` was untested: `@Transactional(rollbackFor = Exception.class)` handlers whose write
contention, lock waits and index-maintenance cost are a different class of bottleneck from the read
path, and could not appear in any run.

**The client has no bulk endpoint, and that is the finding.** `chainPostEntities` builds one POST
per record and `ChainedRequests.fire()` reduces the queue over a single promise chain, so a device
with twenty queued encounters makes **twenty sequential round trips** — each through the full
authentication filter, the organisation interceptor and its own transaction. Push cost scales with
record *count* in requests, not only in bytes, and none of the per-request overhead the read path
measured at 174 ms is amortised across a batch. A push-heavy sync is therefore closer in shape to
twenty small syncs than to one large one.

Entities go in a fixed order, parents first — `EntityMetaData.model()` reversed, which the generated
table is already in. The simulation walks that table rather than a list of its own, so the order
stays right if the client's changes.

**Push writes, so it is off by default.** Once `PUSH=on`, a run changes the database it measured:
the next run is not the same experiment and the dataset's H5 verdict no longer describes the tables.
The startup banner says as much in both directions, because the failure mode is someone reading a
read-only run as the realistic case. A deny list refuses the protected hosts outright — pushed
subjects and encounters are indistinguishable from field data afterwards.

**References are harvested from the deployment, not configured.** A pushed record has to point at a
subject type, an address, an enrolment and concepts that this user can actually see; invented UUIDs
are rejected in the handler and would measure the validation path instead of the write path. Four
page-0 reads per user, once, collect them — which keeps the push path working against a generated
dataset, a restored dump or a hand-built org, with no shared UUID list to keep in step. Observations
are carried **verbatim** from real rows rather than synthesised, because insert cost here is
dominated by GIN maintenance over the observations jsonb and the key count and value shapes are the
load.

A device that cannot be seeded pushes nothing and fails nothing, so `after()` reports how many
devices were only partially seeded and what they lacked. Without it a run against a dataset with no
enrolments finishes green having exercised almost none of the write path.

**Two things are still open.** The volumes — 20 program encounters, 2 encounters, 1 subject, 1
enrolment per sync — are arithmetic from the customer's "20 encounters per worker per day", not
measurement; **Q17** replaces them from production's own `entity_status->'push'`, and its second
half matters more than its first: if most real syncs push nothing, modelling every user as pushing
twenty overstates the write path by that ratio. And the payload shapes are built from the client's
`toResource` getters and checked field-by-field against the server's request contracts, but **have
not been sent to a running server** — that smoke run is the gate before any push result is quoted.

**D4 — Post sync telemetry at end of sync.** *Done.* A write on the hot path, and the one that
populates the table this plan's whole measurement strategy leans on — so omitting it both under-counted
write load and produced runs that generated no telemetry of their own.

Rows are tagged `syncSource: avni-perf-simulation` so simulated syncs are separable from real ones in
`sync_telemetry`. **Every measurement query should filter them out**, or simulation runs will pollute the very
distributions they are meant to be calibrated against.

`entityStatus` carries real per-entity counts but no phase durations: the simulation neither parses
nor persists, so it has no honest value to report for the fields avni-client#2121 adds.

**D5 — Model the presigned-URL calls, not the media transfers.**

Observation media is **not** bulk-synced — it is fetched on demand when a user views a subject or
encounter. And in every media path, **the bytes go client ↔ S3 directly; avni-server only issues
presigned URLs, one request per file**:

| Path | Server call | When |
|---|---|---|
| Media **upload** | `GET /media/uploadUrl/{fileName}`, then PUT direct to S3 (`MediaQueueService:241-248`) | Inside `mediaSync`, which runs on **every sync**, before `dataServerSync` |
| Media **view** | `GET /media/signedUrl?url=…` (`MediaService:126`), then fetch direct from S3 | On demand, when a user opens a record |
| Downloadable content | `/media/modelBlobUrl`, then `downloadWithoutAuth` | In the sync chain |

Three consequences.

**D5.1 — Media upload is unmodelled sync-path load.** *Done, with D3.* A user with N queued media
files makes N `GET /media/uploadUrl/{fileName}` calls before the data sync even begins, each going
through the full authentication filter and organisation interceptor. This is genuine per-sync server
load and the simulation did not touch it at all.

**It is also strictly serial and strictly first.** `MediaQueueService.uploadMedia` chunks the queue
by `PARALLEL_UPLOAD_COUNT`, which is **1** — the chunking machinery around it suggests concurrency
that does not happen — and `sync()` runs `mediaSync` to completion before `dataServerSync` starts.
So the whole media queue drains, one file at a time, before the first record is posted.

**The rate is a property of the bundle, not of the platform.** The first version of this used
production's 2.14% of `program_encounter` rows carrying a media observation — one file per fifty
encounters. That figure spans 986 organisations, most of which capture no images at all, and it is
the wrong base rate for a screening programme. Two structural facts about the customer's bundle
raise it by roughly three orders of magnitude, and **a flat count of media form elements misses
both**.

**Repeatable question groups.** The oral screening encounter's images sit inside question groups
marked `repeatable`, linked to their parent by `parentFormElementUuid`. The group named *"Take
photos of all lesions and 1 photo without lesion"* says plainly what that means: the element is
filled once per lesion, so **one form element produces as many files as the patient has lesions**.
Two such groups are mandatory on that form, and at eight repeats each they give **16 files per
encounter** — the customer's own figure, which the bundle now reproduces exactly.

**Display-only elements, which must not be counted.** Three of the six media elements carry
`editable: false`: the AI assessment's copy of each image and the gallery of suspicious ones. They
reference files another element already captured and uploaded. Counting them would double every
image in the form.

| | Captured files per filled form |
|---|---|
| Oral Screening Encounter | 2 mandatory images, each in a repeatable group — **16 at 8 repeats** |
| Mental Health Encounter | 1 audio, mandatory, not repeatable |
| Clinician Review Form | display-only — **0** |
| Averaged over all 12 encounter types | **1.42** |

**What a sync then costs, by encounter mix** — 22 records pushed, 500 KB per file, serial and
entirely ahead of the first record:

| Oral screening share of encounters | Files per encounter | Files per sync | Data | At 1 Mbps |
|---|---|---|---|---|
| Uniform, 1 of 12 | 1.42 | 31 | 15 MB | 125 s |
| A quarter | 4.08 | 90 | 44 MB | **6 min** |
| Half | 8.08 | 178 | 87 MB | **12 min** |
| All of them | 16.0 | 352 | 172 MB | **23 min** |

**For this deployment, sync time is a media problem rather than a data problem.** The 22 POSTs are
seconds; the images are minutes. That is worth knowing before anyone tunes a query — and at the
pilot's 500 workers, the upper rows are 86 GB a day of uploads, which is an operational question in
its own right.

`make survey_bundle BUNDLE=... --media-repeats N` reports all of this per form type. `bundle.py`
now counts media elements rather than discarding them, resolves question-group parents, and
excludes display-only copies.

> **Two inputs the bundle cannot supply**, and both are large. **How often a repeatable group is
> filled** — nothing records it, and it is a straight multiplier on everything above. **The
> encounter mix** — the table's own spread, 11x between its first and last rows. Neither blocks
> anything: both are parameters, defaulted to the conservative end and documented with their range,
> so a run that wants the upper rows asks for them.

**D5.2 — Do not transfer the bytes, but do spend the time.** *Revised.* The original reasoning held
that since S3 serves the objects directly, transferring them measures S3 and consumes bandwidth
without exercising avni-server. That is true and still the conclusion — but it was used to justify
charging **nothing** for media, and that is a much larger distortion than the one it avoided.

A sync is not just its server requests. At the bundle's 1.42 files per encounter — the *conservative*
reading, a uniform encounter mix — a device pushing 22 records queues **31 files**, and at 500 KB
each (the client captures 1280x960 at quality 1) that is real time on a field link:

| Upload bandwidth | Transfer | Sync duration | vs 14.1 s of server work |
|---|---|---|---|
| 0.3 Mbps | 388 s | 402 s | **29x** |
| 1 Mbps | 125 s | 139 s | **10x** |
| 3 Mbps | 42 s | 56 s | 4x |
| 10 Mbps | 12 s | 26 s | 2x |

A screening-dominated mix multiplies every figure in that table by up to eleven.

**So the fix is to model the time, not to send the bytes.** Transferring would reproduce the
*injector's* network — a fat in-region pipe that moves 500 KB in tens of milliseconds — which is
neither the server's load nor the device's timing. A pause reproduces the timing, which is the half
that matters, and can be swept across bandwidths the way a real transfer cannot. This is the same
trade D6 already makes for parse-and-persist: model the elapsed cost, do not perform the work.

`MEDIA_MODEL=pause` is the default; `none` restores the old behaviour and says so loudly at startup.

> **What this buys and what it does not.** It fixes sync duration, and it stops the data push
> arriving sooner than any real device could send it — which matters because those POSTs are the
> server load. It does **not** verify that a presigned URL works end to end. That is a wiring check
> against a real bucket, not a load question, and belongs in a smoke test.

**The consequence for every concurrency figure in this plan:** media time inflates *syncs in
progress* without touching *server requests in flight*, because during the transfer the device asks
avni-server for nothing. At case 13's arrival rate and a uniform mix those diverge from 9.7 to 96;
at a quarter screening, to 258. Both numbers are true and they answer different questions — see
[test-scenarios.md](test-scenarios.md).

**Measured, and superseded as a default: 2.14% of `program_encounter` rows carry a media
observation** (59 of 2,759 sampled). Against 6.86 million rows that is roughly 147,000 media-bearing
encounters. It remains the right figure for *production as a whole* and the wrong one for any single
deployment — see D5.1 for why the bundle replaced it.

**D5.3 — On-demand viewing: out of scope.** *Decided.* `/media/signedUrl` traffic is driven by users
browsing records rather than syncing, and this exercise is sync-focused. It is not modelled.

Note that it shares an endpoint family with upload, so whatever D5.1 learns about signing cost — and
about the `@Transactional` overhead below — applies to viewing too, should it ever be picked up.

**D5.4 — A real S3 bucket is probably not required.** Worth stating carefully, because both the
simulation's own comment and earlier drafts of this plan got the reason wrong.

`generatePresignedUrl` is a **purely local computation** — the SDK signs a canonical request from the
credentials, bucket name, key, method and expiry, and makes no call to S3. A presign for a
non-existent bucket succeeds and returns a well-formed URL; it would only fail when something
actually fetched it, which D5.2 says the simulation never does. There is also **no bucket validation
anywhere** — no `doesBucketExist`, no `headBucket`, no `@PostConstruct` check in `StorageService`,
`AWSS3Service` or `S3Service` — so the server will not fail at startup either.

**Why `News` actually fails today is a configuration mismatch, not S3 connectivity.**
`AWSS3Service.generateMediaDownloadUrl` authorises *before* signing:

```java
if (!mediaDirectory.equals(mediaDirectoryFromUrl) || !(bucketName.equals(amazonS3URI.getBucket()))) {
    throw new AccessDeniedException(...);
}
```

It parses the **stored** URL and compares its bucket against the server's configured `bucketName`,
and its media directory against the organisation's. News rows carrying production `heroImage` URLs on
a server configured with a different bucket therefore throw `AccessDeniedException` — entirely
server-side, with S3 never contacted. The simulation's comment that this "connects to prod s3 which
fails" is a misdiagnosis.

What is actually required:

| | |
|---|---|
| A configured `bucketName` | Must be **set**; need not exist |
| The organisation's `mediaDirectory` populated | `getOrgDirectoryName()` throws `IllegalStateException` if null |
| Generated media URLs consistent with both | Under our control, since the dataset is generated (H) — emit `heroImage` and observation media URLs matching the configured bucket and media directory, and `News` works uncommented |

**One thing left to verify:** `/media/modelBlobUrl` calls `getURLForExtensions(key, organisation)`,
and it sits on the sync chain via `downloadContent` / `DownloadableContentService`. It returns a URL
and is very likely presigning like the rest, but `StorageService` does contain genuine server-side S3
calls (`getObject`, `listObjects`, `doesObjectExist`), so confirm this one before concluding the sync
path never touches S3 for real.

Creating an empty bucket is cheap and removes the question entirely — but it should be a deliberate
choice, not an assumed requirement.

> **Confirmed: presigning itself is pure CPU.** `AWSS3Service.generateMediaDownloadUrl` parses the
> URI, regex-matches the media directory, compares strings, and calls
> `s3Client.generatePresignedUrl` — which signs locally with no S3 round trip. `authorizeUser()` and
> `getOrgDirectoryName()` both read `UserContextHolder`, a ThreadLocal the authentication filter has
> already populated. No database query.
>
> **But the wrapper is not free.** `generateUploadUrl` and `generateDownloadUrl` are both annotated
> `@Transactional(readOnly = true)`, so each call borrows a pooled connection and pays the
> interceptor cost in F2.1 — three Postgres round trips — while issuing no SQL of its own. Note the
> batch `POST /media/signedUrls` has no `@Transactional` at all, which suggests the annotation is
> incidental rather than deliberate. Removing it from the two presign endpoints is a plausible cheap
> win; confirm nothing downstream depends on the transaction first.

**Still to confirm:** whether concept media URLs (`concept.media[].url`, downloaded during reference
sync at `PARALLEL_DOWNLOAD_COUNT = 1`) are signed or direct.

**D6 — Interim weighted storage pause.** Replace the uniform constant with a per-entity weight table
scaled by page record count. Concrete task, detailed below.

**D7 — Measured storage cost model.** Replace the weight table's estimates with measured coefficients.
Detailed below.

**D8 — Page size is wrong by 10×.** The client ships `pageSize: 1000`
(`packages/openchs-android/config/initialSettings.json`); the simulation defaults `PAGE_SIZE` to 100.
Detailed below — it changes the shape of the load, not just a constant.

**D9 — Reset sync.** *Done — request modelled, and no scenario is needed.* The `ResetSync` pull now runs where
the client runs it — **before `syncDetails` is even requested**. `dataServerSync` calls
`getResetSyncData` first and `getSyncDetails` only afterwards, which the simulation had inverted.

**Measured, 27 weeks: a normal week is ~194 resets, and 89% of them are org-wide.** Across 13–24
organisations and 40–184 users, that is a median of 1.8 resets per affected user — steady background
activity rather than an event.

**One week was 130× that: 25,141 resets, essentially all org-wide, over 14 organisations but only 156
users — about 161 resets per user in a single week.** A user cannot usefully be reset 161 times in a
week; each reset discards local data and forces a full re-download, and the *next* one arrives long
before the previous re-download finishes. That is a runaway, not a workload.

**This is the highest-load event the system produces, and it is the scenario most worth building.**
It combines both worst cases at once — every affected user forced onto the full-sync path rather than
the incremental one, and all of them starting together. Against Q5's measured band-10 p50 of 1,076 s,
the 184 users of the worst normal week represent roughly **55 device-hours of full sync**, arriving in
a burst. Compare that to a peak hour's ordinary traffic of 792 syncs that are 98% light, and the
asymmetry is the point.

**Not modelled, and the reason is the finding.** The April week is
[avni-client#2115](https://github.com/avniproject/avni-client/issues/2115) — a reset sync that
re-arms itself when the sync following it does not complete. **It is a defect, so load-testing it
would be measuring a bug rather than a workload**, and no amount of server capacity is the right
answer to one. The card is filed; these figures are evidence of its cost, which is the useful thing
to do with them.

**Normal reset volume needs no scenario either.** At ~194 a week across 13–24 organisations and 1.8
per affected user, it is a trickle of users dropping onto the full-sync path — which is exactly what
the test cases' 1% fresh-sync mix already models, and at a higher rate.

Two further quirks reproduced: `getResetSyncData` does not reverse the metadata list, and it passes
the client's own clock as `now` rather than the server's — which it could not use anyway, not having
called `syncDetails` yet.

**Still outstanding: the stampede.** A reset forces every affected user into a full re-download, and
that is a scenario rather than a request — it belongs with E3's spike profile. Whether it is worth
building depends on how often resets actually happen, which [measurement query](production-measurement-queries.md) **Q10** answers. A reset forces affected users into a full re-download, so it is potentially the single largest
load event the server sees — and it is triggered by configuration changes, meaning it can hit many
users of an organisation at once. Two things needed: add `ResetSyncs` to the entity list (C2 already
covers this), and model the post-reset full-sync stampede as a scenario (E3's spike profile is the
natural home). Scope this deliberately rather than leaving it commented out.

---

## D6 / D7. Modelling client-side parse and persist time

This deserves its own treatment because getting it wrong invalidates every capacity number the
simulation produces.

### The shape is already correct

`ConventionalRestClient.js:99–102` carries an explicit comment:

> `persistAll may be async (SQLite bulkCreate path) — await it to ensure the current page is fully`
> `persisted before the next page is fetched.`

The client is **strictly serial**: fetch page N → fully persist page N → fetch page N+1. Entities are
sequential too (`getAll` chains `getAllForEntity` with `.then()`). So the simulation's structure —
request, pause, next request — models the real client correctly, and removing the pause would
absolutely hit the server harder than reality. The pause stays.

### What is actually wrong

`pause(0, MAX_REALM_STORAGE_PAUSE)` is a uniform 0–2s draw, mean 1s, applied **identically** to:

- a page of 100 `Concept` rows — small, flat, cheap to parse and insert
- a page of 100 `ProgramEncounter` rows — each carrying an observation set, orders of magnitude more
  parse and write work

The pause is uncorrelated with the thing it models. Consequence: heavy entities are under-paused (the
server is hit harder than reality) and light entities are over-paused (the server is hit more softly
than reality, and the run is padded with dead time). It is not "too much" or "too little" pause — it
is the wrong *shape*.

### D6 — Interim weighted pause (Phase 1)

Do not wait for measurement. A weight table scaled by record count is strictly better than one uniform
constant, and it is a small, self-contained change. Ship it first, then replace the estimates with
measured coefficients under D7.

**D6.1 — Measure the baseline per-record cost.** The existing constant cannot supply it. The pause
averages 1000 ms per page; at the simulation's current `PAGE_SIZE` of 100 that implies 10 ms/record,
and once D8.1 sets page size to 1000 the same constant implies 1 ms/record. Neither number was ever
derived from anything — the constant was chosen against a page size the client no longer uses, and
scaling it either way just propagates the original guess.

Measure it instead. `sync_telemetry` holds real sync durations alongside per-entity record counts, so
plotting total duration against total records pulled yields an observed ms-per-record directly —
[measurement query](production-measurement-queries.md) **Q1**. No code, no dependencies; start it immediately.

Call the result **`baseMsPerRecord`**. Everything in D6.2 is expressed as a multiple of it, so the
tier work can be written and reviewed before the number arrives.

**Measured: `baseMsPerRecord` = 9.2 ms/record.** Two independent methods converge on it.

Q1's regression over 108,374 syncs returns a slope of **9.19 ms/record**, and Q5's volume bands, which
make no linearity assumption at all, give a median band-implied cost of **10.0 ms/record**:

| Band | Midpoint records | p50 duration | Implied ms/record | n |
|---|---|---|---|---|
| 2 | 7,500 | 82.9 s | 11.1 | 989 |
| 3 | 12,500 | 125.4 s | 10.0 | 453 |
| 4 | 17,500 | 176.6 s | 10.1 | 373 |
| 5 | 22,500 | 212.0 s | 9.4 | 143 |
| 6 | 27,500 | 308.1 s | 11.2 | 67 |
| 7 | 32,500 | 233.0 s | 7.2 | 35 |
| 8 | 37,500 | 284.6 s | 7.6 | 43 |
| 9 | 42,500 | 346.8 s | 8.2 | 20 |

**Take 9.2 ms/record, subject to the netting-out caveat below.**

**Eighty bad rows out of 131,538 were hiding this.** The first run returned r² = 0.00001 and a
63-second intercept, which read as "duration is not linear in record count". After D1's guard dropped
63 future-dated rows, 2 with negative duration and 15 over two hours — **0.06% of the table** — r² rose
to **0.186** and the intercept fell to 26.5 s. The worst offender carried a `sync_start_time` in
**2031**, giving it a duration of roughly five years and enough leverage in a least-squares fit to
flatten the entire slope.

The lesson generalises past this query: **least-squares regression has unbounded sensitivity to
outliers, so an r² near zero is a signal to inspect the extremes before concluding anything about the
relationship.** The band analysis was the right cross-check precisely because percentiles are
insensitive to them — it gave ~10 ms/record from data that made the regression read as noise.

**r² = 0.186 is still low, and that is genuine rather than an artefact.** 98% of syncs sit in band 1,
where duration spans 14.1 s at p50 to 80.0 s at p95 — a five-fold spread driven by network, device and
server load, not by record count. So the slope is a sound estimate of the *marginal* cost of one more
record and a poor predictor of any individual sync's duration. For sizing a per-record pause, marginal
cost is exactly the quantity wanted.

**The intercept still is not a fixed cost.** 26.5 s exceeds band 1's p50 of 14.1 s, which is
impossible for a genuine per-sync overhead; it remains an artefact of fitting a line through a
long-tailed distribution. Use 14.1 s as the honest figure for a light sync.

> **Q1 gives a ceiling, not the value.** Production sync duration is client parse-and-persist time
> **plus network plus server response time**. The simulation's pause must represent client work only —
> the server under test supplies its own response time — so using Q1's figure directly would
> double-count the server. Two ways to net it out: subtract the server's own share, which
> `AuthenticationFilter`'s per-request timing logs already record (F2), or take the clean number from
> D7's device instrumentation and use Q1 only as a sanity ceiling. Either way, **do not use Q1's
> output as `baseMsPerRecord` unmodified.**

**D6.2 — Invent a weighting, then measure and validate it.** In that order, and do not skip the last
step. The initial model is a guess whose only job is to be better than one uniform constant; what
makes it trustworthy is validation against real syncs (F7), not the plausibility of its construction.

**`baseMsPerRecord` is the input that matters.** It comes from D6.1's measurement against real
production syncs, and it is the only number here with any claim to reflecting reality. Everything
else in this model is a shape applied to it, and every one of those shapes is provisional until F7
validates it.

Build the tiers below as that shape. They are a guess, and they are meant to be replaced by D7's
per-entity measurements as soon as those exist.

<details>
<summary><strong>A note on <code>EntityMetaData.syncWeight</code> — do not build on it</strong></summary>

`EntityMetaData` carries a `syncWeight` on each of its 74 entries (values 0–4), used by
`ProgressbarStatus.js` to size progress-bar increments:

```js
this.progress += (syncWeight / ((totalNumberOfPages === 0 ? 1 : totalNumberOfPages) * 100));
```

It looks appealing — per-entity, maintained alongside the entity list, free with the C1 generator —
and it is recorded here mainly so nobody rediscovers it and assumes it is more than it is.

**Its correlation with actual parse-and-persist cost is unestablished and probably weak.** It is a
per-entity *total* spread across pages rather than a per-record cost; it conflates typical row count
with per-row expense; and it exists to make a progress bar advance smoothly, which is a UX goal, not
a measurement. Nobody has ever checked it against a clock.

Treat it as trivia unless and until something measures it. Do not weight the model with it, do not
average it against the tiers, and do not let a disagreement between it and a measured value cast
doubt on the measurement — `baseMsPerRecord` wins by default, every time.

</details>

Starting tiers, as multipliers of `baseMsPerRecord`:

| Tier | × base | Entities |
|---|---|---|
| **Light** | 0.2 | Flat lookup rows: `Gender`, `TaskStatus`, `TaskType`, `ApprovalStatus`, `StandardReportCardType`, `LocationHierarchy`, `Privilege`, `Groups`, `GroupPrivileges`, `MyGroups`, `GroupRole`, `MenuItem`, `AddressLevel`, `LocationMapping` |
| **Medium** | 1.0 | Config and light transactional: `Concept`, `ConceptAnswer`, `Form*`, `OrganisationConfig`, `Translation`, `PlatformTranslation`, `Dashboard*`, `ReportCard`, `Documentation*`, `Rule*`, `Checklist*`, `IdentifierAssignment`, `Comment*`, `Task*`, `UserSubjectAssignment`, `SubjectMigration`, `EntityApprovalStatus`, `GroupSubject`, `SubjectProgramEligibility` |
| **Heavy** | 3.0 | Observation-bearing: `Individual`, `ProgramEnrolment`, `ProgramEncounter`, `Encounter` |

Since `baseMsPerRecord` is the *observed fleet average* across a real entity mix, the multipliers are
weights around that average — they do not need to sum or normalise to anything, but they should
straddle 1.0, which they do.

**The heavy tier checks out against the data.** Band 10 pulls ~47,500 records in 1,076 s, and a sync
that large is dominated by observation-bearing rows — so its implied **22.4 ms/record against the
fleet's 8.85 is a ratio of 2.5**, near the 3.0 the tier assigns. The tiering was judgement, but it is
judgement the measurements support.

> **`ProgramOutcome` was in this list and is not in the model.** The generator assigns tiers by
> name, so it would have been a silent no-op — 14 light entities where the plan claimed 15. Removed.

> **These multipliers are judgement, not measurement.** The tiering reflects payload structure —
> whether a row carries an observation set — which is the dominant cost driver. The ratios matter more
> than precision within a tier, and D7 replaces the whole scheme with per-entity measurements. Three
> tiers is deliberate: a finer split is false precision on numbers this soft.

**The per-page term is not negligible — it is the dominant one, and this plan had it backwards.**

An earlier version of this section omitted per-page overhead on the grounds that at a page size of
1000 it was small against the per-record term. That reasoning only holds for full pages, and almost
no page is full: **98% of production's syncs pull under 5,000 records across 81 requests**, so most
pages carry a handful of rows and the fixed cost is nearly the whole cost. At 50 records the
per-record term is **3% of the sync**.

It can be measured, too. A production sync is **81 requests over 14.1 seconds — 174 ms a page**,
made up of the server's response, the mobile round trip and the client's own per-request work.

**And it is the term that shapes load.** A real device issues one request every 174 ms. On a LAN the
round trip disappears, so a simulation without this term issues requests roughly **four times faster
per user** than any device — which does not make the test conservative, it manufactures contention
that cannot occur and invites chasing it. Pass `MS_PER_PAGE` as 174 minus the server's own median
response, since the simulation genuinely incurs that part.

Writing a page is also one transaction, so the incremental cost of record N sits well below the
first record's. A pure `records × rate` model charges a 10-record page a tenth of a 100-record page
when in practice they cost nearly the same.

**D6.3 — Implement.** *Done.*

- Add a `msPerRecord` field to the `AvniEntity` model (populated by the C1 generator, so new entities
  get a tier assignment rather than silently defaulting).
- Capture the page's record count in a check — `jmesPath("_embedded.<resourceName> | length(@)")`.
- Replace `.pause(0, maxPauseToSimulateRealmStorage)` with the computed pause.
- Introduce `STORAGE_MODEL` as a system property: `weighted` (default) and `zero` (pure server
  saturation runs, client cost removed). Delete the uniform pause outright rather than keeping it as
  a third mode — no existing run results need preserving, and an unexercised config path rots the
  same way `AvniEntities.json` did.

**Built**, as `msPerPage + records × tier × baseMsPerRecord`, with `STORAGE_MODEL=zero` to remove
client cost entirely for saturation runs.

**A warning added during the build was wrong and has been removed**, and the way it was wrong is
worth keeping. It compared a full 1,000-record heavy page — 27.6 s — against the 14.1 s median sync,
and concluded the coefficient must be too high. But a median sync is band 1 and pulls almost nothing;
**a full heavy page only occurs in band 2 and above, where a sync runs 83 s to 1,076 s**, and 27.6 s
inside an 82.9 s sync is unremarkable. Comparing a heavy page against a light sync compares two
things that never co-occur.

Re-deriving the coefficient properly is what settled it. Anchoring the intercept at band 1's p50
gives **8.85 ms/record**, against Q1's 9.19 — a 4% difference, which is noise. The slope was never
the problem; **the free intercept was**, and every unanchored fit returned a value that could not fit
inside a 14.1 s sync.

**`STORAGE_MODEL=zero` is not a neutral fallback**, which is worth stating because it looks like one.
Removing the pause lets a virtual user issue its 81 requests back to back, bounded only by the
server's response — at a 20 ms response that is **9× a real device's request rate, and 17× at 10 ms**.
It is a deliberate over-drive for saturation runs, not a way to avoid choosing a coefficient.

### D7 — Measured cost model (Phase 3)

**Step 1 — Measure, don't guess.** Replace D6.2's three judgement-based multipliers with a measured
per-record cost for each entity:

```
t_page = cost_per_record[entity] × record_count
```

One coefficient per entity, not two — the per-page overhead stays omitted for the reason given in
D6.2: at a page size of 1000 it is negligible, and it cannot be separated from the per-record term by
measurement anyway.

Two sources, in order of how fast you can get them:

- *Fast, narrow:* instrument `persistAll` in a debug build on one representative low-end device. Gives
  usable coefficients in a day.
- *Slow, durable, free:* add per-entity timing to `sync_telemetry`. Production already records
  per-entity record counts but only counts, not durations — adding elapsed-ms per entity to the
  `push`/`pull` arrays yields real coefficients across the entire device fleet and every network
  condition, accumulating from the next release.

Do the first to unblock; do the second because it is the number you will trust.

**Step 2 — Apply as a computed pause, not a constant.** Capture the record count from each page
response, then pause a duration derived from it:

```java
.exec(http(...)
    .check(jmesPath("_embedded." + resourceName + " | length(@)").ofInt().saveAs("recordCount")))
.pause(session -> Duration.ofMillis(
    overheadMs + perRecordMs * session.getInt("recordCount")))
```

Gatling's Java API accepts a `Function<Session, Duration>` for `pause`, so the whole model fits in one
expression per entity.

**Step 3 — Validate via F7.** The calibration gate applies the model against real production syncs.
If simulated durations don't land in the real distribution, the coefficients are wrong; re-fit and
repeat.

### Deliberately not doing

**Fitting a distribution to pause times.** Real parse-and-persist times are right-skewed, and modelling
that skew is tempting. It buys nothing here: individual pause variance averages out across hundreds of
concurrent virtual users, and what the server experiences is the aggregate arrival rate. Use the point
estimate. Add jitter only if runs turn out to look artificially synchronised.

**Separate Realm and SQLite coefficients.** The *server* load is identical regardless of which local
database the client writes to — only the client-side pause differs, and only in the capacity
translation. Building a dual-coefficient model with a selector property, to characterise a migration
that has already been decided, is scope creep. Use whichever backend the fleet majority runs
(`sync_telemetry.app_info.activeBackend` says which) and revisit only if the migration turns out to
move sync duration materially.

### The deeper point: two questions need two profiles

The pause governs how long one user's sync takes, therefore how many users are concurrently mid-sync,
therefore the aggregate request rate at any given user count. That means it matters differently
depending on what is being asked:

| Question | Pause treatment |
|---|---|
| **Capacity** — "can we take N users at 9am?" | Realism is the entire point. Use the measured model. An unrealistic pause makes the answer wrong in either direction. |
| **Choke point** — "where does the server break, and why?" | Control the arrival rate directly rather than letting it emerge from a guessed client model. Drive RPS explicitly with `throttle` (`reachRps(x) in (y), holdFor(z)`) or a closed injection model. |

Given the stated goal is choke-point discovery, the second mode is what most runs will use. But the
measured model is still needed to translate a finding into a business answer — "breaks at 400 RPS" is
only actionable once you can say how many field users that represents.

Support both via the `STORAGE_MODEL` property introduced in D6.3 — D7 replaces `weighted` in place
rather than adding a mode, leaving `weighted`/`measured` and `zero` as the only two.

---

## D8. Page size

The client ships `pageSize: 1000` in `packages/openchs-android/config/initialSettings.json`. The
simulation defaults `PAGE_SIZE` to 100, set when this repo was created and never updated. Every run
recorded so far has therefore tested a pagination shape the client stopped using.

This is not a one-line constant fix, because the change alters what the server is being asked to do:

**Request count collapses, payload size explodes.** A user pulling 40,000 records makes 400 requests
of ~100 rows at the old size, versus 40 requests of ~1000 rows at the real one. Per-request overhead —
auth filter, transaction setup, connection acquisition — drops tenfold in aggregate, while response
serialisation cost and payload size rise by the same factor.

**The prime suspect changes.** At page size 100, request count and per-request overhead dominate, and
deep-offset pagination is the obvious thing to look for. At 1000, response serialisation, heap
allocation and GC pressure during marshalling become the likelier bottleneck — a page of 1000
observation-bearing rows may be several megabytes. Any earlier reasoning about where the server
chokes, made against the 100-row shape, needs revisiting.

**Offset-based pagination gets cheaper, not worse.** *Confirmed:* the v2 endpoints take a Spring Data
`Pageable` and return a `Slice` (`SlicedResources` / `SliceImpl`), which is `LIMIT … OFFSET`
underneath — offset-based, not keyset. Total rows skipped across a full entity pull is therefore
roughly `n² / (2 × pageSize)`, and moving 100 → 1000 cuts that by a factor of ten.

Worth noting what `Slice` already avoids: unlike `Page`, it issues **no `COUNT(*)` query** — it fetches
`size + 1` rows to determine `hasNext`. That is why the simulation checks `slice.hasNext` on v2
endpoints and `page.totalPages` on the older ones. So the expensive half of offset pagination is
already gone on v2; only the row-skipping remains, and the page size change has absorbed most of that.
Deep pagination drops down the suspect list accordingly.

**Timeouts need explicit configuration.** A page of 1000 heavy rows may take long enough to approach
Gatling's default request timeout. Set timeouts deliberately in the simulation rather than inheriting
defaults, and check what the client uses — a timeout firing mid-run looks exactly like a server
failure.

### Tasks

**D8.1 — Source the page size from the client config.** *Done.* Do not hardcode 1000. Read it from
`initialSettings.json` in the same generator that produces the entity table (C1), so it cannot drift
again. This is the third instance of the same failure mode in this repo; fix it structurally.

**D8.2 — Keep page size in mind as a remedy, not a test axis.** If serialisation, heap or GC turns out
to be the bottleneck, smaller pages relieve it; if per-request overhead or offset depth dominates,
larger pages do. That makes page size a candidate *fix* to evaluate once a choke point is named — not
a standing 100 / 1000 / 2000 matrix to run speculatively. Keep `PAGE_SIZE` overridable so the
experiment is cheap when it is warranted.

**D8.3 — Establish what the fleet actually runs.** `avni-models/src/Schema.js:470` falls back to 100
when a stored `pageSize` is `0`, `undefined` or `null`, so installs predating the change may still be
on 100 — the fleet is probably mixed, and nothing currently records which. Add `pageSize` to
`sync_telemetry.app_info` alongside the per-entity durations D7 needs; both ride the same client
release. Until then, treat the production split as unknown and test both sizes.

**D8.4 — Set explicit request and response timeouts** in the simulation, sized for the largest
plausible page.

---

## E. Scenario and workload design

**E1 — Deterministic feeder.** *Done.* `random()` draws with replacement, so the same real user could
be driven by two virtual users at once — contention the field does not have — while others in the file
never ran. Now `circular()`: walks the file in order and wraps, making runs repeatable and load even.

The simulation also prints its configuration at startup and **warns when `USER_COUNT` exceeds the
file**, which is the one case `circular()` still oversubscribes a user. The fix there is more users,
not a larger `USER_COUNT`.

**E2 — Separate full and incremental sync scenarios.** *Done for pull.* `SYNC_MODE` selects the
window: `full` forces 1900-01-01, `incremental` forces a recent window (`INCREMENTAL_SINCE_HOURS`,
default 24), `csv` takes it from the user file. The scenario is named for the mode, so reports say
which was run.

The difference is not marginal. Against a local dev database:

| Mode | Requests | Mean |
|---|---|---|
| `full` | 44 | 57 ms |
| `incremental` | **16** | 30 ms |

**64% fewer requests.** The committed user file has always held 1900-01-01, so every run to date has
exercised only the heaviest case — and the common production case had never been run at all.

> **That 64% predates the bootstrap and understates the difference.** It was measured while the
> status body carried an empty `entityTypeUuid`, so every typed entity fell through to the 1900
> default and full-synced — reference data was doing most of the work the figure reflects. With D1
> built, the typed entities honour the window too, and the real incremental profile will be
> different again.

**Upload-only background sync is not modelled, and does not need to be.** It was disabled in practice
some time ago, which is why `sync_source = 'automatic-upload-only'` is near-absent from recent
telemetry — that absence reflects reality rather than a gap in the data. Modelling it would reproduce
a flow production no longer runs. Should it ever be re-enabled, D3 has since built the push half, so
it would be a scenario that skips the download rather than new modelling.

### Scenarios and test cases

**Moved to [test-scenarios.md](test-scenarios.md)** — the deployment being modelled, the datasets at
each growth point, and the test cases with numbers, for customer review. Different audience and
different lifecycle from this document: that one is what the instrument gets pointed at, this one is
how it gets built.

Three things from it bear on the sections below. **Supervision is assumed at sub-centre level** — if
it sits higher, per-device volume changes by an order of magnitude and so does what this exercise
tests. **Ten workers share a village catchment**, so the same rows are read several times over.
And **fresh sync is 1% of syncs daily**, which is the mix E2 was missing.


**E3 — Named injection profiles.** The first four are the customer's scenarios and come before the
rest; the remainder are the instrument's own.

- *Field worker sync* — one catchment. The common case, and the one the 1% fresh-sync mix applies to
- *Supervisor sync* — the union of many field workers' catchments. Expected to be the heavy case, and
  probably what Q3's 99th percentile has been measuring all along
- *Combined* — both roles concurrently, in their real population ratio. **This is the realistic one**,
  and running either role alone will understate contention: supervisors pull wide while field workers
  pull often, and they compete for the same connection pool
- *Training and onboarding* — **50 to 100** new field workers first-syncing together from one
  location, against an organisation holding **configuration only and no field data**. Every device
  starts empty, so every sync is a full pull of the same reference data at the same moment. That makes
  it a reference-data and `syncDetails` test with catchment volume removed entirely, which is both the
  cheapest scenario to build — a bundle load, no generation — and the cleanest isolation of the
  per-row `filterChangedEntities` cost in D1.1. **Build this one first**
- *Growth comparison* — the same profile replayed against the day 60, day 120 and day 180 datasets.
  The finding is the shape of the curve between them, not any single run
- *Smoke* — one user, CI-gated
- *Load* — expected peak
- *Stress* — ramp to the knee
- *Spike* — a burst above the working-day plateau. **Not a start-of-day herd:** Q4 shows arrivals
  ramping into a broad plateau from 10:00 to 17:00 IST, peaking at 16:00 rather than at the start of
  the day — 09:00 carries barely half the 16:00 volume. (The *shape* holds regardless of the Q4
  bucketing defect, which scaled every hour equally; the absolute rates come from the re-run.) Whatever this profile spikes *from*,
  the baseline it returns to is a sustained plateau, and the plateau is the more valuable case to run
  because it is where production actually lives
- *Soak* — multi-hour; the case that raised the auth question
- *Contended* — sync against a concurrent ETL cycle, export, or bulk import (F5.4). The delta against
  the equivalent uncontended profile is the finding

**E4 — Multi-tenant load.** *First-class, not finding-triggered — see section I.* The feeder and
user provisioning must be able to span organisations with a controllable mix.
**[test-scenarios.md](test-scenarios.md) fixes the shape:** two state-level tenants of ~500 workers
each alongside ~8 NGO tenants sharing ~500. That is a realistic spread and large tenants beside small
ones at once, so noisy-neighbour effects are not a separate run. Start at 2 tenants, then 5, then the
full set.

**Whether those tenants sit beside production's existing 986 organisations is a question the cases
answer rather than assume.** Test cases 5, 6 and 7 run the same load with the customer alone, with
everyone else's data present, and with everyone else's traffic on top. The deltas say whether sharing
costs anything and — because 6 and 7 are separated — whether the cost is structural or contention.
Those have different remedies, so running them as one case would leave the finding unattributable. Neither can surface in a single-org run, and the
shared connection pool plus per-borrow `set role` churn make cross-tenant contention a distinct
failure mode from anything a single tenant produces.

**E5 — Size everything from `sync_telemetry`.** Production already records per-sync duration,
per-entity push/pull counts, local data volumes, device and connection type. Take user counts, data
volumes and push volumes from that table rather than inventing them.

**Measured, per real hour (Q4):**

| | Syncs | Rate | Distinct users |
|---|---|---|---|
| Busiest hour ever recorded (12:00 IST) | **792** | 0.220/sec | **267** |
| p95 hour (16:00 IST) | 614 | 0.171/sec | — |
| Average busy hour (16:00 IST) | 378 | 0.105/sec | 158 |

**Arrival rate is not concurrency.** At the measured p50 of 14.1 s per sync, the busiest hour
production has ever recorded works out to roughly **3 syncs in flight**; even assuming every sync ran
at the p95 duration of 80 s it reaches only **18**. That is strikingly low, and it is the single most
consequential number in this plan: **the server is nowhere near saturated on arrival rate**, so choke
points will be found in per-sync cost and in the heavy tail, not in concurrency.

Size *Load* against 792 syncs/hour and *Stress* as a ramp well past it — the ramp is where the knee
is, and reproducing production's arrival rate alone will not find one.

**Activity is a working-day plateau, not a start-of-day herd.** Hourly averages hold above 200 syncs
from **09:00 to 21:00 IST**, peaking at 16:00, with real evening activity — 19:00 still averages 245.
The *Spike* profile should burst above that plateau rather than model a morning rush that does not
exist.

**Volume mix (Q5): 98% of syncs pull under 5,000 records.** Any profile built predominantly on `full`
mode is modelling the remaining 2%.

## F. Observability, environment and run process

The gating workstream. Without it, every run yields "it got slow" and no cause — and the simulation
work above produces findings nobody can act on.

**F1 — Attach the existing instrumentation to the load-test environment.** Smaller than it first
appears. `avni-server`'s *build* declares no Micrometer, Actuator or OpenTelemetry — but that is
because **New Relic is already the APM, attached at runtime as a javaagent** rather than compiled in.
Every non-local environment carries it in `avni_server_opts`
(`-javaagent:/opt/newrelic/newrelic.jar -Dnewrelic.environment=…` in prod, staging, prerelease,
rwb_prod and rwb_staging), and `avni-infra` has a `configure/roles/newrelic/` role that provisions it.

So F1 is mostly *configuration of a new environment*, not *building instrumentation*. Target set:

- `pg_stat_statements` and the slow query log
- JVM and GC metrics
- **Tomcat JDBC pool gauges** — active, idle and *waiting* borrows; a non-zero wait count is the
  smoking gun for pool exhaustion
- per-endpoint p95/p99

Two things worth knowing before instrumenting, both verified in `avni-server`:

- **The pool is Tomcat JDBC, not HikariCP.** `application.properties:14` sets
  `spring.datasource.type=org.apache.tomcat.jdbc.pool.DataSource`. HikariCP is on the classpath but
  unused, so Hikari's metrics will read as zero and Hikari-shaped dashboards will silently show
  nothing. Instrument the Tomcat pool.
- **Pool size is not configured**, so it sits at the Tomcat JDBC default. That makes a concrete,
  falsifiable prediction: concurrency beyond that default should produce borrow waits before
  anything else saturates. Worth testing early — it is cheap to confirm and, if true, the first
  choke point is a one-line configuration change.

#### Almost none of this needs an avni-server code change

`avni_server_opts` is a universal escape hatch: it is templated into `OPENCHS_SERVER_OPTS` by
`configure/roles/avni_appserver/templates/appserver.conf.j2` and already carries both `-D` Spring
properties and a `-javaagent`. So each item is set from `avni-infra` group_vars:

| Item | How |
|---|---|
| Per-endpoint p95/p99, JVM and GC metrics, pool gauges | Attach the existing `newrelic` role to the load-test environment |
| Pool size | `-Dspring.datasource.tomcat.max-active=…` — no need to edit `application.properties` |
| F2 log level | `-Dlogging.level.org.avni.server.framework.security.AuthenticationFilter=WARN` |
| GC logging, if not relying on the agent | `-Xlog:gc*` |
| `pg_stat_statements`, slow query log | RDS parameter group plus `CREATE EXTENSION` — infrastructure, but the RDS side rather than Ansible |

`AVNI_IDP_TYPE` is likewise already templated, so B1 needs no code change either.

**What does need avni-server code**, and neither is an investigation:

- The **F2.1 remediation** below — collapsing the two `SET` statements and removing the unconditional
  `getMetaData()` evaluation. Measuring the cost is configuration; fixing it is code.
- **F3** — deleting `avni-server/perf/gatling/`.

**The gap:** `configure/group_vars/` has no perf or loadtest environment file at all — the
environments are prod, staging, prerelease, rwb_*, onpremise, snapshot and vagrant. All of the above
lands in a file that does not exist yet, which belongs with the environment work in F4/F5.

**F2.1 — The per-connection organisation interceptor costs three round trips per borrow.**
*Verified in code, not speculation.* `application.properties:17` registers
`SetOrganisationJdbcInterceptor` on the Tomcat JDBC pool. Reading
`framework/tomcat/SetOrganisationJdbcInterceptor.java`:

- **On borrow** (`reset`), two separate statements execute:
  `set role "<dbUser>";` then `set application_name to "<dbUser>";`
- **On release** (`invoke`, when the method is `close`), a third: `RESET ROLE`

That is **three Postgres round trips wrapped around every pooled connection use**, before any
application query runs. It is how multi-tenancy is enforced — the role drives row-level security
(`enable_rls_on_tx_table`) — so it is doing necessary work, but the cost lands on the path of every
single request that touches the database.

There is a second, subtler cost in the same class. `invoke` builds a TRACE log line for every proxied
connection method other than `getMetaData` and `toString`, and its argument is
`connection.getMetaData().getConnection().hashCode()`. Parameterised logging defers *formatting* but
not *argument evaluation*, so `getMetaData()` is called on every `prepareStatement`, `createStatement`,
`commit` and `setAutoCommit` regardless of whether TRACE is enabled.

**Why this is high on the suspect list:** it is per-connection-borrow rather than per-query, it is
unconditional, it interacts directly with the unconfigured pool size in F1, and requests that need no
database at all still pay it whenever they are wrapped in `@Transactional` — `/media/uploadUrl` being
a concrete example (D5).

**Measure it; do not fix it yet.** Plausible fixes exist — collapsing the two `SET` statements into
one round trip, removing the unconditional `getMetaData()` evaluation — but applying them before the
cost is known is the pre-emptive optimisation this plan's method exists to avoid. A suspect found by
reading is a hypothesis, not a finding.

**F2 — Check request logging isn't itself the choke point.** `AuthenticationFilter` logs at INFO twice
per request — on receipt, and on completion with timing — including the full query string. Under load
that is a plausible bottleneck in its own right. Measure it, and decide deliberately what level the
perf environment runs at.

**F3 — Reconcile the second Gatling setup.** `avni-server/perf/gatling/` is a separate, older harness.
Fold it in or delete it; maintaining two guarantees both drift.

### F4 — Deploying the server to the closed environment

**Distributed injection is deferred.** One injector until something says otherwise — Gatling OSS has
no orchestration, so multiple injectors mean merging logs by hand, which is real work for a problem
nobody has yet. **The signal to revisit is the injector appearing in its own results**: saturated CPU
on the load generator, or response times rising with virtual user count while the server's own
metrics stay flat. F7's calibration gate is where that would surface.

**Prerequisite for B1.** B1 requires the perf environment be unreachable from the internet. CircleCI
deploys to it from the internet. That has to be resolved before the environment can be closed.

**What exists today.** `avni-server/.circleci/config.yml` has a `PERF_deploy` job. It attaches the
built zip from the workspace, downloads `avni-infra` from GitHub, decrypts the Ansible vault, and runs
`make deploy-avni-server-perf` with `app_zip_path=~/artifacts/`. **Ansible runs on the CircleCI
container** and pushes the artifact to the instance over SSH; `setup_server_access` supplies an
ephemeral keypair via `aws ec2-instance-connect send-ssh-public-key`.

The key is delivered through the AWS control plane and is already IAM-authenticated. **The only thing
requiring a public path is the SSH connection itself** — a direct TCP hop to the instance, which today
works because `perf.avniproject.org` resolves publicly. That single hop is the whole problem, and the
whole fix.

**F4.1 — Tunnel the SSH hop through the AWS API.** Two options, neither needing any inbound security
group rule or public IP:

- *EC2 Instance Connect Endpoint* — `aws ec2-instance-connect open-tunnel` used as an SSH
  `ProxyCommand`. **Smallest change:** the job already uses EC2 Instance Connect under the same IAM
  model, so this is a proxy command plus an endpoint resource in the VPC.
- *SSM Session Manager* — `ProxyCommand` of
  `aws ssm start-session --document-name AWS-StartSSHSession`. Needs the SSM agent, an instance role,
  and NAT or VPC endpoints. More conventional, slightly more setup.

Both move authorisation from network position to IAM, which is a stronger control than any IP
allowlist.

> **Explicitly rejected: allowlisting CircleCI's IP ranges.** It is a paid add-on, the published list
> changes, and it opens the environment to a large pool of shared CI infrastructure — defeating
> precisely the isolation that made `AVNI_IDP_TYPE=none` acceptable in the first place. Do not trade
> B1's safety property for CI convenience.

**F4.2 — Adapt the Ansible invocation.** Ansible itself barely changes: the tunnel is configured
through `ansible_ssh_common_args` or an SSH config block, and the `avni-infra` make targets are
otherwise untouched. The substantive change is that the inventory must address the host by **instance
ID** rather than DNS name, since both transports target the instance through the AWS API rather than
a resolvable hostname.

**F4.3 — Give the instance an egress path.** In a private subnet with no NAT gateway or VPC
endpoints, any package the playbook fetches at deploy time — apt, Maven, Docker pulls — fails. This
is the most common way a first closed-environment deploy breaks. Audit what the deploy playbook
actually fetches and provision accordingly.

**F4.4 — Confirm DNS.** `perf.avniproject.org` currently resolves publicly. Decide whether it becomes
a private hosted zone record or the deploy addresses the instance by ID only, and make sure the
simulation's `BASE_URL` still resolves from inside the boundary.

### F5 — Dataset and environment parity

**Longest lead time in the plan; start it first.** Choke points are data-volume dependent — an index
that is fine at 10k rows is a sequential scan at 10M — so an under-sized database invalidates every
run regardless of how faithful the simulation is. This was previously filed as an open question; it is
on the critical path and needs an owner.

**F5.1 — Choose and build the dataset.** Anonymised production clone or synthetic generator. See
**section H** — this is the largest single piece of work in the plan, and Avni's metadata-driven
observation model makes it substantially harder than "insert N rows".

**F5.2 — Document environment parity, and its gaps.** Instance sizes, Postgres version and
configuration, connection pool sizing, JVM flags, whether the database is shared or dedicated. Any
deviation from production must be written down — every result carries an asterisk otherwise, and the
asterisk needs to be legible when someone reads the findings months later.

**F5.3 — Suppress outbound side effects.** Anything that reaches a third party must be dead: SMS,
notifications, and the Glific/flow integrations behind `MessageSenderJob`. Enforce at the
infrastructure boundary, not in application config alone, so a configuration mistake cannot cause an
incident.

**F5.4 — Run the co-tenant workloads deliberately.** Sync does not have the server to itself. Every
load below shares the same instance, the same connection pool and the same fixed 3,000 IOPS (G4), so
suppressing them produces a server that is quieter than any real one. **Model the significant ones as
scenarios and treat the delta against sync-alone as a finding**, rather than deciding case by case at
run time.

| Load | Trigger | Shape | Verdict |
|---|---|---|---|
| **ETL** | Quartz, every 90 min | Reads `public` in competition with sync, writes org schemas, drops and recreates materialised views | **Scenario.** Scheduled and recurring, so an ETL cycle landing on the start-of-day herd is an ordinary production event |
| **Longitudinal export** | User-triggered, Spring Batch (`ExportBatchConfiguration`) | Bursty heavy analytical scans. `AVNI_LEGACY_LONGITUDINAL_EXPORT_LIMIT` exists because these got out of hand | **Scenario.** Same contention shape as ETL, potentially larger |
| **Bulk import** | User-triggered (`/concepts/bulk`, `/api/subjectMigration/bulk`, `/extension/upload`) | Bursty heavy writes, paying the same GIN-index maintenance as D3's push path | **Scenario**, once D3 exists to compare against |
| **Webapp** | Concurrent human users, `/web/*` | Separate query paths, same tables | **Background load.** A constant concurrent trickle, not a burst |
| **HR and aggregate reporting** | Admin-triggered, `/report/hr/*`, `/report/aggregate/*` | Analytical queries over the same tables | **Background load** |
| **Messaging** | `MessageSenderJob`, fixed-delay poll | Continuous, low volume | **Leave running**, outbound suppressed per F5.3 |
| **Storage management** | `StorageManagementJob`, cron | Periodic | **Leave running** |
| **Metabase** | BI users | Points at the **read replica** (`avni.read.database.server`), not the primary | **Out of scope** |

**Before modelling any of this, find out which ones actually coincide with peak sync.** Export and
import runs are recorded — `AvniJobRepository`, `ExportJobParametersRepository`, `JobStatus` — so
their timestamps can be correlated against observed load peaks the same way `sync_telemetry` can. A
co-tenant workload that never overlaps the sync herd is not worth a scenario; one that routinely does
is arguably more important than anything in the sync path itself.

### F6 — Run-to-run data lifecycle

**D3 has landed, so this is live.** With `PUSH=on` the database changes with every run and runs stop
being comparable. See **section G** for the full treatment — this is the hardest operational problem
in the plan and the one most likely to silently invalidate results.

Push being off by default buys time rather than a reprieve: an unconfigured run is still read-only,
but no scenario that means to measure the write path can run twice until the restore path works.

### F7 — Calibration gate

**Prove the simulation reproduces reality before trusting any finding.** `sync_telemetry` records
real sync durations alongside per-entity record counts and local data volumes, which makes this a
concrete, passable test rather than an aspiration:

> Run a simulated user against the same per-entity record counts as a real production sync. The
> simulated total sync duration should land inside the observed distribution of real sync durations
> for that data volume and device class.

If it does not, the simulation is not yet an instrument and its findings are not evidence. This gates
believing results, not producing them — run it after D6 and again after D7, and re-run it whenever
the client changes something the simulation models.

**E7 — Co-tenant sync traffic.** *Distinct from F5.4, which is the batch workloads.* Case 7 needs
production's other organisations to be **syncing**, not merely present — that is the whole difference
between it and case 6, and it is what separates a structural cost from a contention one.

It needs a second scenario driving arrivals at production's own measured shape: **792 syncs in the
busiest recorded hour** (Q4), against the co-tenant dataset H7 produces. Those users need feeder
entries and sync-status baselines, which case 6's co-tenants do not.

**Cheaper than it looks, and worth checking before building it properly.** The co-tenant load exists
to occupy the connection pool, CPU and IO — it does not have to be faithful per user. A single
scenario replaying a representative sync at the right arrival rate may be enough, and is a great deal
less work than provisioning 986 organisations' worth of realistic users.

---

## G. Anatomy of a test run

What actually has to happen for one run to produce a trustworthy number. Most of this does not exist
yet and is not covered by the task list above, which is about the simulation rather than the ritual
around it.

### G1 — One-time, per environment

| Step | Notes |
|---|---|
| Provision the environment | F4, F5.2 |
| Load the implementation bundle | The generator reads its metadata ids back out |
| Dump the target's columns and metadata ids | `columns.sql` and `refs.sql` — the generator projects rows onto the target's own schema rather than a committed list |
| Generate and load the dataset | From a committed recipe (H). F5.1 — the long pole |
| Users and catchments arrive with it | The generator emits them alongside the rows, so they cannot miss each other — see G5 |
| Bootstrap per-user sync-status baselines | D1's bootstrap call — one `POST /v2/syncDetails` with `[]` per user |
| **Run H5's gates** | Statistical, then the manual client check. **Both need the users above**, since the structural half is a sync |
| Capture the pristine snapshot | This is what every subsequent run restores to |

**Order matters twice here.** The snapshot comes last, after users and baselines exist, so restoring
never destroys them. And **H5's gates come before the snapshot, not after**: a snapshot of an
unblessed dataset propagates the problem into every run that restores it, and by then the cost of
finding out has multiplied.

### G2 — Per run, before

- **Restore the database to the reference snapshot.** See G4 — this is the answer to the bloat
  problem, not `DELETE`.
- **Decide and apply a cache policy.** A freshly restored database has cold `shared_buffers` and cold
  OS page cache; the first run against it will look dramatically worse than the second for reasons
  that have nothing to do with the server. Either run a fixed warm-up and discard it, or accept cold
  starts — but do the same thing every time and write down which.
- **Reset per-run statistics** — `pg_stat_statements_reset()`, JVM metric counters, log rotation — so
  the collected data covers this run only.
- **Generate the scenario's sync-status arrays** by rewriting `loadedSince` on the cached baselines
  per D1's distribution.
- **Record run metadata** (A11): simulation SHA, server build, dataset identity and row counts,
  injection profile, `STORAGE_MODEL`, `PAGE_SIZE`, cache policy.

### G3 — During

Start observability capture, run the injection profile, and leave it alone. One decision to make
consciously: **autovacuum on or off.** Leaving it on is realistic — production has it on, and an
autovacuum storm mid-run is a genuine production failure mode worth catching. Turning it off is
deterministic. Prefer on for choke-point hunting, but record it as a known source of run-to-run
variance rather than being surprised by it.

### G4 — Protecting against index and table drift

**The problem.** Insert-then-delete cycles do not return a database to its prior state. `DELETE`
leaves dead tuples until `VACUUM`; `VACUUM` marks index pages reusable but **does not shrink the index
or compact sparse pages** — only `REINDEX` does. So repeated run/teardown cycles progressively bloat
indexes, degrade cache hit ratio, and shift query plans as statistics drift. Runs stop being
comparable to each other, and the database stops resembling production. This is exactly the failure
mode to avoid.

**The answer is to never delete.** Let the run dirty the database however it likes, then discard the
whole thing and restore. Teardown is a restore, not a set of `DELETE` statements.

**The environment is RDS PostgreSQL 16.8**, which rules out the usual answers — no filesystem access,
no EBS or ZFS snapshots, no `pg_basebackup`.

#### Two viable candidates

Neither is obviously better. **Decide by timing both once, not by argument.**

| | `CREATE DATABASE … TEMPLATE` | `pg_dump` / `pg_restore --jobs` |
|---|---|---|
| Peak storage | **2× dataset** | **~1× dataset** |
| Reset time | Fast — file-level page copy | Slow — full index rebuild, GIN worst |
| Where the artefact lives | A second database in the instance | S3, outside RDS storage |
| Index state | Whatever the template holds | Always pristine |

The storage difference has one cause: **`TEMPLATE` copies alongside the original, so source and
target coexist.** With a dump you `DROP DATABASE` *first* and restore into the space freed.

Whether that peak is affordable is a provisioning question for the infrastructure plan, not this one.
Flag the requirement — a template reset needs roughly twice the dataset in headroom — and let the
sizing decision sit where it belongs.

#### Sizing the dataset

Measured on the production read replica:

| Bucket | Size | Relations |
|---|---|---|
| `public` (transactional) | 70 GB | 143 |
| Org schemas (ETL) | 62 GB | 10,367 |
| System | 1.5 GB | 68 |

**The transactional dataset to reproduce is ~70 GB.** That is the number section H generates against.

Storage *provisioning* — allocation size, IOPS and throughput settings, autoscaling — is an
infrastructure concern and is not specified here. This plan states one requirement, in section J:
**IO parity with production.** How that is achieved belongs to the infrastructure plan.

Both reset options fit comfortably within a production-matching allocation, so **the choice between
them is decided by timing, not by storage**.

#### Storage IO is a prime suspect before any test runs

A 134 GB working set behind GIN indexes on `observations`, serving sync reads at page size 1000,
capped at **3,000 IOPS and 125 MiB/s**. Once the active set exceeds `shared_buffers`, that ceiling is
plausibly *the* constraint rather than CPU, the connection pool, or any query-level suspect.

Checkable on production today, with no load test: CloudWatch `ReadIOPS` + `WriteIOPS` against 3,000,
`ReadThroughput` + `WriteThroughput` against 125 MiB/s, at peak. Add `DiskQueueDepth` — sustained
non-zero queue depth is the signal that IO is binding.

It constrains remediation too, which is worth knowing before a finding lands: production's IO ceiling
cannot simply be raised in place. The options available, and their cost, are an infrastructure
question — but any of them forfeits parity with today's production, so a finding here changes what
subsequent runs are measuring against.

#### A fifth of the index bulk earns almost nothing

Index usage can only be read on the primary — `idx_scan` counters are per-instance, and the replica
serves Metabase alone. Measured across 66 indexes over 69 days.

**Six of the seven GIN observation indexes have never been scanned**, together about 794 MB. The
seventh, on the same column type over the same window, took over 1.5 million scans — so the counter
works and the opclass is usable, and these six are simply not being read.

**This sharpens H3 rather than contradicting it.** H3 warns that GIN maintenance dominates insert cost
on the push path. For these six that is now the *whole* story: write tax and cache pressure with no
read benefit. It also fits the `jsonb_path_ops` limitation noted under Q9 in the queries document —
the opclass supports `@>`, `@?` and `@@` but **not** `?`, so key-presence filters cannot use these
indexes at all.

**Counting every index scanned fewer than a thousand times, roughly 4.08 GB — 21% of index bulk on
these four tables — earns almost nothing.** The largest index in the database is in that set, scanned
about twelve times a day for 2.5× `shared_buffers` of storage. Unique constraints are excluded from
the total, since they enforce correctness whatever their scan count.

**The cold ones are not arbitrary — they are one sync strategy nobody uses.** Each table carries five
`sync_N` indexes, one per sync strategy: `sync_1` keys on `address_id` (sync by location), `sync_2` on
`individual_id` (by subject), `sync_3` on `sync_concept_1_value` (by one attribute) and `sync_4` on
both `sync_concept_1_value` and `sync_concept_2_value` (by two attributes). The scan counts line up
with that exactly — `individual_sync_2_index` took 3.48 billion scans, while the `sync_4` family is
the bulk of the cold 4.08 GB.

So this is not a set of indexes that turned out useless. It is **the two-attribute sync strategy
being almost unused across the platform**, with an index per table standing ready for it. That is a
product question rather than a schema one, and it changes who the finding belongs to.

**The hot path is narrow and small.** The three busiest indexes are 185 MB, 88 MB and 29 MB, and they
carry billions of scans between them. The bulk sits in indexes that are barely touched.

**Several heavily-used indexes are poorly selective**, the worst reading tens of thousands of rows per
lookup. An index returning that much per scan leaves the planner filtering afterwards — a plausible
contributor to the per-sync cost that Q4 says cannot be explained by concurrency. **F1/F2 should
attribute time here before anyone assumes the bottleneck is elsewhere.**

> **Two caveats before anyone acts on this.** Sixty-nine days misses quarterly and annual reporting
> paths, so an index used only by those would look idle. And **dropping indexes is out of scope for
> this plan** — the finding belongs to whoever owns schema changes. What matters here is that the
> simulation's dataset must reproduce these indexes *as they are*, cold ones included, or its cache
> behaviour will not match production.

> **Per-index names, sizes and scan counts are recorded in `avni-product-ops`**
> (`context/production-database-state-2026-09.md`), along with the full result set behind every figure
> in this plan. This repository is public and carries the summarised findings only.

#### ETL shares that ceiling, on a 90-minute cycle

`avni-etl` maintains a **flat analytical schema per organisation**, converting every JSONB key to a
column, plus passthrough tables (all rows including voided) and materialised views **dropped and
recreated at the end of every run**. A Quartz job runs it **every 90 minutes**.

**Storage.** ETL is 62 GB against public's 70 GB — but that aggregate ratio is misleading, because
**ETL is not enabled for every organisation**. The meaningful figure is the multiplier for orgs that
have it, and their transactional data is some subset of the 70 GB. Still to be measured; the ratio
could comfortably exceed 1× per enabled org.

> `organisation.schema_name` is populated regardless and is **not** an enablement flag — ETL is
> invoked per organisation externally. The empirical signal is which org schemas actually contain
> relations, and their per-schema sizes.

**IO contention, which matters more.** ETL reads the public schema — competing directly with sync
reads — writes the org schema, and rebuilds materialised views, all against the same fixed 3,000 IOPS.
An ETL cycle coinciding with the start-of-day sync herd is a *recurring, scheduled* production event,
not a hypothetical. **Sync load with and without a concurrent ETL cycle should be a scenario**, and
the delta between them is itself a finding.

**10,367 relations across the org schemas**, against 143 in `public`. That is a large catalog for
autovacuum and the planner to carry, and it scales with tenant count — relevant when section I's
tenant count is chosen for the generated dataset.

#### A third option, specific to this project

**Regenerate rather than restore.** The dataset is generated (section H), so the generator's bulk
`COPY` is essentially `pg_restore`'s data phase without a stored artefact — same index-rebuild cost,
nothing to manage, no storage doubling. Likely lands close to `pg_restore` on time. Include it when
timing the other two.

#### Ruled out, and why

| Method | Why not |
|---|---|
| **`pg_transport`** (transportable databases) | The fastest-sounding option, and genuinely a physical streaming transport — but **access privileges and ownership are not carried over; all objects arrive owned by the destination user** ([AWS docs](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.TransportableDB.html)). Avni's multi-tenancy *is* per-org database roles, RLS policies and `openchs` ownership, so transport would flatten the mechanism the system runs on. It also moves only *between* instances, requiring a second RDS instance to hold the pristine copy. Recorded here because it is the obvious suggestion. |
| **Aurora fast cloning** | Copy-on-write, seconds, no storage doubling — **the right tool for exactly this problem.** Not available: this is RDS PostgreSQL, not Aurora. Only relevant if Aurora is on the table for production anyway; switching engines to make a load test convenient is backwards. |
| **`pg_basebackup`, EBS/ZFS snapshots, Database Lab Engine** | All need filesystem access or self-managed Postgres. Using them means the perf database is no longer RDS — trading away production parity, which is a worse loss than a slow reset. |
| **AWS DMS, Blue/Green deployments** | Continuous sync and deployment tooling. Not reset mechanisms. |
| **RDS snapshot restore** | Right for baseline creation and portability, wrong per-run — see below. |
| **`DELETE` + `VACUUM` / `REINDEX`** | Progressively worse each cycle; `REINDEX` takes as long as a restore and yields a less realistic index than production has. |

> **Two RDS-specific problems with snapshot restore as a per-run mechanism.**
>
> **It cannot restore in place.** `RestoreDBInstanceFromDBSnapshot` always creates a *new* instance
> with a new endpoint. A per-run reset would mean restore → rename-swap or repoint → delete the old
> instance, every run.
>
> **Lazy loading makes the first run meaningless.** A restored RDS volume is hydrated from S3 on first
> touch of each block. Until blocks fault in, I/O latency is dramatically worse than steady state —
> so a freshly restored instance will look catastrophically slow for reasons that have nothing to do
> with the server. You must pre-warm by reading every block (`pg_prewarm`, or full scans of every
> table and index) before measuring, and that pre-warm can take as long as the restore did. This is
> more severe than the buffer-cache warming noted in G2, because it is at the storage layer.

**PostgreSQL 16 detail, if `TEMPLATE` wins.** Since PG15 the default `CREATE DATABASE` strategy is
`WAL_LOG`, which writes the entire copy through WAL and is slow for a large template. Specify
`STRATEGY = FILE_COPY` explicitly:

```sql
DROP DATABASE IF EXISTS avni_perf;
CREATE DATABASE avni_perf TEMPLATE avni_perf_template STRATEGY = FILE_COPY;
```

**Parameter group parity is part of this.** `shared_buffers`, `work_mem`, `max_connections`,
`effective_cache_size` and the autovacuum settings all come from the RDS parameter group, and a
restored instance inherits the snapshot's. Match production's, or record the deviation under F5.2.

**Needed as soon as a scenario turns push on.** Download sync is read-only and a default run still
modifies nothing, so the decision can wait for the first `PUSH=on` run rather than for Phase 2 in
general — but it now gates that run rather than sitting behind it.

#### Which snapshot

There is no pre-existing snapshot to restore from — H6 rules out production data, so the dataset is
generated. **The baseline snapshot is one this project creates, once, and then guards.**

The environment ends up holding two distinct artefacts with different jobs:

| Artefact | Where it lives | Used for |
|---|---|---|
| **`avni_perf_template`** — the pristine generated dataset | A database inside the RDS instance | The per-run reset. `CREATE DATABASE avni_perf TEMPLATE avni_perf_template STRATEGY = FILE_COPY` before each run. |
| **The baseline snapshot** — of the whole instance, which contains that template | An RDS manual snapshot | Rebuilding the instance from scratch, standing up a second environment, or recovering a corrupted template. Never the per-run reset. |

**How the baseline is built, in order:**

1. Provision an empty instance with the production-matched parameter group.
2. Create the organisation from the checked-in config (H1).
3. Run the generator and bulk-load into `avni_perf_template` (H2, H4).
4. Build indexes, `ANALYZE`.
5. Provision perf users and catchments (G5) — these must be *inside* the snapshot, or every rebuild
   re-provisions them.
6. Validate (H5). Do not snapshot unvalidated data.
7. **Take the manual snapshot.** The instance now contains a verified, pristine template.

Per-user sync-status baselines (G1) sit in the harness rather than the database, so they are outside
the snapshot — but they depend on the users from step 5, which are inside it.

**Make it a manual snapshot, not an automated backup.** RDS automated backups expire with the
retention window; a manual snapshot persists until explicitly deleted. The generated dataset costs
days to produce, so it must not be able to age out. Tag it against deletion.

**Version the snapshot with what produced it** — generator commit, org config revision, and the row
counts from H5. When the generator changes, the dataset changes, and results either side of that are
not comparable. The snapshot identifier belongs in every run's metadata (A11), which is what makes
that discontinuity visible later rather than mysterious.

**Keep the working database out of it.** Snapshot the instance holding only `avni_perf_template`;
the working `avni_perf` is derived per run and has no business being preserved.

Note the distinction the table encodes: a snapshot preserves production's *steady-state* bloat, a
logical restore removes it. Both are defensible; what is not defensible is a bloat level that varies
between runs. **Determinism matters more than absolute realism here**, because the primary comparison
is run against run.

**This is now mandatory rather than deferrable.** It could be put off while download sync was
read-only: the only write was `POST /syncTelemetry` (D4), one small row per user. **D3 ended that.**
A run with `PUSH=on` inserts subjects, enrolments and encounters, so the database it measured is not
the database the next run measures, and the dataset's H5 verdict stops describing the tables.

The default protects the gap in the meantime — push is off unless asked for, so an unconfigured run
is still read-only and still needs no restore. But every scenario that means to measure the write
path needs the restore path working first.

### G5 — User provisioning

One-time per environment, but it needs a script — it is not a manual task at the volumes involved.

**B1 collapses most of this.** With `AVNI_IDP_TYPE=none` there are no Cognito users to create: the
server authenticates from the `USER-NAME` header, so provisioning reduces to creating rows in the
server's own user tables. No AWS calls, no rate limits, no password management, no
`sync-users.csv` credential column.

What the script has to do:

- Create N users in the target organisation, idempotently, so re-running it is safe.
- **Assign catchments.** This is the lever that controls sync volume per user — a user with a small
  catchment syncs almost nothing regardless of how large the database is. If the goal is to model
  users carrying 40,000 observations, catchment assignment is how that is achieved.
- Emit `sync-users.csv` with a stable per-user `deviceId` (D1 needs it — `filterChangedEntities`
  branches on it).
- Bootstrap each user's sync-status baseline and cache it.

> **The dataset and the user set must be designed together.** F5.1 decides what data exists; G5
> decides who can see it. Designing them separately produces users whose catchments do not intersect
> the data, and a simulation that measures nothing. Treat them as one task with one owner.

---

## H. Test data generation

The largest single piece of work in the plan, and the one with no existing tooling —
`avni-server/scripts/seed` holds two org-specific SQL dumps, not a generator.

The difficulty is that Avni is metadata-driven. An observation is
`ObservationCollection extends HashMap<String, Object>` persisted as **JSONB**, keyed by concept UUID,
with values whose valid shape depends on that concept's datatype and, for `Coded`, on its specific
answer set. You cannot generate a valid observation without first reading the organisation's form
configuration.

### H1 — Split metadata from transactional data

This split is what makes the problem tractable, because the PII is entirely on one side of it.

| | Source | Why |
|---|---|---|
| **Metadata** — forms, form element groups, form elements, concepts, concept answers, subject types, programs, encounter types, address level hierarchy | **Checked-in implementation config** | Real configuration from a real implementation, already in version control. No governance question, reproducible, diffable. |
| **Transactional** — individuals, enrolments, encounters, and their observations | **Generate synthetically** | This is where the PII lives. Generating sidesteps anonymisation entirely. |

**Use an existing implementation config repo rather than cloning production metadata.** Avni
implementations keep their configuration in version control — typically `concepts.json`, a `forms/`
directory, `formMappings.json`, `encounterTypes.json`, `catchments.json`, address-level data, and a
`create_organisation.sql` to bootstrap it. `avni-health-modules` supplies the shared reference concept
and rule library on top.

This is strictly better than cloning production metadata: no governance question, versioned, and a run
can state exactly which config revision it used.

**Which configuration is a parameter of the run, not a fixed choice.** The generator takes the config
source as input; it must not hard-code one implementation. Different runs will want different
configurations, and the one used should be recorded in the run metadata (A11) alongside its revision,
because org shape materially changes what is being measured.

**So is tenant count.** The generator must be able to produce **N organisations with a realistic size
distribution**, not one — and that is required even when load is driven against a single org, because
RLS selects one tenant's rows out of a table holding every tenant's. See section I2; it is the easiest
thing in this plan to get quietly wrong.

**Covering organisation size.** Org complexity is itself a load variable — it drives the syncDetails
row count and therefore the per-row queries in `filterChangedEntities` (D1.1). A configuration
representing a small or typical implementation will not exercise that; a large one will. Cover the
range deliberately, either by selecting configurations of different sizes or by scaling one — 
duplicating concept trees and form mappings to reach a realistic large-org shape — rather than
assuming the small case generalises.

### H2 — The generator

1. **Read the org's form configuration.** `form_mapping` → `form` → `form_element_group` →
   `form_element` → `concept`. For each (subject type, program, encounter type) combination this
   yields the exact set of concept UUIDs a valid observation may contain, each concept's datatype, and
   for `Coded` concepts their permitted `concept_answer` UUIDs.
2. **Emit observations keyed by concept UUID**, with values valid for the datatype —
   `Numeric` within the concept's absolute low/high where defined; `Coded` drawn from that concept's
   own answers, scalar or array per `multiSelectTypes`; `Date`/`DateTime` within a plausible window
   relative to the parent entity's date; `Subject`/`Location`/`Encounter` referencing a real existing
   UUID of the right kind. Skip media datatypes unless D5 puts media in scope — they imply S3 objects.
3. **Apply a fill rate.** Real forms are not completely filled. Populating every element inflates
   observation size and distinct-key count beyond production, which matters more than it sounds — see
   H3.
4. **Respect skip logic** where cheap. Form elements have visibility rules, so a uniformly random fill
   produces combinations that cannot occur. Lower priority than fill rate for load purposes, but it
   affects key distribution.

### H3 — The distributions that actually determine load

Getting row *counts* right is the easy half. These are what change server behaviour, in rough order of
impact:

- **Rows per entity type within a user's catchment.** Drives sync volume directly. Ties to G5 —
  catchment assignment and data generation must agree.

  **Measured across 2,828 users (Q3)** — `totalCounts` is each device's own row count:

  | Entity | p50 | p90 | p99 |
  |---|---|---|---|
  | Subjects | 464 | 5,685 | 42,519 |
  | Enrolments | 100 | 1,653 | 15,254 |
  | Program encounters | 89 | 11,762 | 153,126 |
  | Encounters | 62 | 3,167 | 53,670 |
  | **Total rows on device** | **~715** | **~22,267** | **~264,569** |

  **A 370× spread between the median device and the 99th percentile.** The median device holds about
  700 rows — almost nothing — while the heaviest holds a quarter of a million. Catchment generation must
  reproduce the tail rather than the median: a generator that gives every user a typical catchment
  produces no heavy syncs at all, and the heavy tail is where the choke points are. It also explains
  Q5's bands directly, since 98% of syncs pull under 5,000 records.
- **Distinct concept-UUID cardinality across observations.** **Measured (Q6): 5,623 distinct concepts**
  appear as observation keys in a 1% sample of `program_encounter`.

  **That figure spans every organisation** — the query carries no organisation filter — and getting
  the level wrong in either direction produces the wrong index. A real implementation bundle reaches
  a few hundred concepts through its live form mappings, so **total cardinality comes from tenant
  count, not from inflating any one organisation**. Generating a single org with 5,623 concepts would
  misrepresent production as badly as generating one with a dozen. See the GIN note below.
- **Fill rate — observations per row.** Drives payload size, serialisation cost and GIN index size.
  **Measured (Q6):**

  | Table | p50 keys | p95 keys | Mean bytes |
  |---|---|---|---|
  | `program_encounter` | 12 | 34 | 879 |
  | `individual` | 7 | 29 | 742 |
  | `encounter` | 4 | 22 | 526 |
  | `program_enrolment` | 2 | 20 | 360 |

  The generator should reproduce both the median and the p95 — a generator that emits a constant key
  count per row produces a GIN index of the wrong shape even when the mean matches.
- **Coded answer value cardinality.** Same mechanism.
- **Temporal spread of `last_modified_date_time`.** Easy to overlook and it invalidates D1's whole
  purpose: if every generated row shares a timestamp, incremental sync returns either everything or
  nothing, and no incremental scenario means anything. The spread must look like real editing
  activity over time.

  **Measured (Q14), and it differs sharply by table:**

  | Table | Age p50 | p90 | p99 | Edited after creation | Median days to first edit |
  |---|---|---|---|---|---|
  | `encounter` | 821 d | 1,663 | 2,664 | 40.1% | 383 |
  | `individual` | 788 d | 1,791 | 2,991 | 36.7% | 595 |
  | `program_encounter` | 698 d | 1,897 | 2,869 | **74.8%** | **32** |
  | `program_enrolment` | 444 d | 2,076 | 2,724 | 61.0% | 274 |

  **Production data is old** — a median row was last touched nearly two years ago, and the 99th
  percentile reaches eight years. A generator emitting recent rows makes every incremental window
  return far more than production would.

  **Program encounters have to be written twice.** Three quarters are edited and the median edit
  lands 32 days after creation, against 383 to 595 days elsewhere. That is the scheduled-visit
  pattern: the row is created when a visit is booked and filled in when it happens. A generator
  writing each row once produces neither the edit volume nor the timestamp spread, and that is the
  difference between an incremental sync returning a realistic trickle and returning nothing.
- **Address level hierarchy shape.** Drives the scope-resolution queries behind catchment filtering.
  **Measured (Q13) across the 812 organisations holding any location:**

  | Depth | Orgs | Median locations | Max | Avg branching |
  |---|---|---|---|---|
  | 1 | 231 | 1 | 357 | — |
  | 2 | 98 | 4 | 167 | 4.8 |
  | 3 | 215 | 3 | 6,259 | 5.3 |
  | 4 | 136 | 20 | **500,039** | 9.4 |
  | 5 | 101 | 120 | 20,419 | 3.3 |
  | 6–8 | 30 | 155–2,593 | 2,251 | 1.8–4.0 |

  **Generate four levels with a branching factor near 9.** Depth 4 is where the working hierarchies
  sit, and it holds the largest by a wide margin — one organisation's 500,039 locations are 42% of
  every location on the platform. Depths 2 and 3 are more common by org count but hold almost nothing,
  a median of 3 or 4 locations each.

  **28% of organisations have no hierarchy at all** — 231 sit at depth 1 with a median of one
  location, and a further 174 hold none. That matches the tenant skew below: the generator should
  leave a large share of its organisations essentially unconfigured rather than giving each one a
  hierarchy.

  > **The deep-chain anomaly is one organisation, not a platform-wide defect.** Depths 9 through 26
  > each held exactly 763 locations — 13,734 in total, all belonging to a single org, where it is 68%
  > of that org's locations. It looks like 763 chains extended one level at a time. **It does not need
  > reproducing in the generated dataset**, but `lineage` is an `ltree` walked by catchment scope
  > resolution and RLS ancestor lookups, so a 26-level path costs materially more to walk than a
  > 4-level one. Worth someone's attention outside this plan.

- **Tenant count and size skew**, and **organisation hierarchy depth** — the first two set total table
  size and planner statistics, the third sets how far reference-table RLS walks ancestors. See
  section I. **Measured (Q12): 986 organisations, and the skew is severe.** The largest holds **21% of
  all subjects** on its own; the top 10 hold 63%; the top 50 hold over 90%. **473 organisations — 48% —
  hold no subjects at all.**

  Two consequences for the generator. Reproducing "986 tenants" by making 986 similar ones would
  misrepresent production entirely: the right shape is a handful of very large tenants, a moderate
  tail, and roughly half the tenants empty. And **user count does not predict data volume** — the
  largest organisation by users (1,494) ranks 71st by subjects. E4's noisy-neighbour scenario needs
  both axes varied independently, because production varies them independently.
- **Total size: target ~70 GB of transactional data.** That is production's `public` schema; the
  per-organisation ETL schemas are a further 62 GB (G4). Size against the transactional figure, not
  against the instance's allocated storage — those differ by several times.
- **Indexes outweigh the rows they index.** The four sync-path tables hold **13.6 GB of data against
  19.4 GB of indexes** — a 1.43× ratio overall, and 3.7× on `program_enrolment`. Together they are 33 GB
  of the 70 GB schema, and **21× the instance's 933 MB `shared_buffers`**. A generator that reproduces
  row counts but not index bulk will show a cache hit ratio production cannot achieve, which makes it
  the single easiest way to produce optimistic numbers. Reproduce index definitions exactly (G4).
- **The ETL-enabled fraction is a generator parameter.** ETL is not enabled for every organisation,
  so its storage and IO contribution depends on how many generated orgs have it. Enable it on none
  and the ETL-contention scenario disappears; enable it on all and both storage and IO contention
  exceed production's.

> **The GIN indexes make observation cardinality a first-class concern.**
> `V1_03__AddGinIndexForObservations.sql` creates `GIN (observations jsonb_path_ops)` on `individual`,
> `program_enrolment` and `program_encounter`. Three consequences:
>
> - GIN maintenance dominates insert cost on the push path (D3) and scales with the number of distinct
>   keys per document — so push benchmarks are only as realistic as the observation cardinality.
>   **Q7c makes this sharper than expected: six of the seven observation GIN indexes have never been
>   scanned in 69 days of production, so for them the maintenance cost is the only cost.** The
>   simulation must still build them — cold indexes occupy cache and slow writes exactly as production's
>   do — but the push-path finding is now concrete rather than hypothetical.
> - GIN's `fastupdate` pending list causes periodic merge spikes rather than uniform write latency. A
>   genuine production failure mode, and one the simulation can only reproduce with realistic data.
> - If synthetic observations draw on fewer concepts or lower-cardinality values than production, the
>   index is smaller, hotter in cache, and faster — and every number you produce is optimistic.

### H4 — Loading it

Bulk-load with `COPY` directly into the tables, not through the API — the API is orders of magnitude
slower and millions of rows are needed. Build indexes after the load, then `ANALYZE`.

The tradeoff is that `COPY` bypasses server-side validation, so a generator bug produces data the
application cannot read. Mitigate by round-tripping a sample through the real API and comparing.

**Checked, rather than assumed: very little is recomputed behind a write.**
`virtual_catchment_address_mapping_table` is a plain view over a SQL function, so there is nothing to
populate or refresh — a location belongs to a catchment when any point in its `lineage` is declared
against it. There are no materialised views, and no triggers on the four transactional tables.

**The schema moves, and only one failure mode is silent.** A renamed or dropped column, a new
`NOT NULL` column without a default, an incompatible type change — each stops a `COPY` outright. **A
new nullable column simply arrives empty**, and that has a precedent worth keeping in mind:
`sync_concept_1_value` was added by V1_208 and is indexed by `sync_3` and `sync_4`, so a generator
predating it would have loaded cleanly while producing data that never touched those paths. The
generator therefore requires every column in the target to be accounted for — written, or declared
unwritten with a reason — and refuses to emit a load script otherwise, stamping the Flyway migration
it was checked against into the script.

**Two things do have to be right on the way in.** `address_level.lineage` carries a check constraint
requiring the path to end `.parent_id.id`, so a wrong immediate parent is rejected — but its own
comment says it does not validate the whole tree, so a wrong *ancestor* loads cleanly and hands
catchment expansion the wrong scope silently. And the denormalised columns the application would
otherwise set — `address_id`, `program_encounter.individual_id`, and the two `sync_concept_*_value`
columns — have to be written by the generator, because the sync indexes cover them and a null loads
without complaint while quietly keeping the data off the index paths production uses.

Post-load indexes are pristine, with none of production's accumulated bloat — acceptable here, because
G4 snapshots this state and every run restores to it, so it is at least deterministic. Note the
deviation in F5.2.

### H5 — Proving the data is good enough

Two checks, both cheap:

**Structural.** *Half built.* `tools/data-generator/structural_check.sh` runs the simulation against
a loaded dataset in full-sync mode, one virtual user per role, and **asserts zero failures** — a
stricter bar than a load run, because this asks whether the data is readable at all rather than
whether an error rate is acceptable. A6's assertions carry it.

**The client half stays manual and cannot be automated from here.** The simulation only proves the
server responded. The client is what proves the data is *valid* rather than merely well-shaped: a
generated observation violating a form's skip logic surfaces there and nowhere else, because nothing
server-side evaluates the rule. Device automation belongs to the Android plan.

So a dataset passing the automated half is **loadable, not blessed**, and the verdict file records
the two separately rather than letting one stand for the other.

**It is a task, not a caveat.** Someone runs it once per dataset — four steps in the generator's
README, needing a device or emulator and half an hour — and writes the result into the verdict file.
It sits in G1 after the users exist — the structural half is a sync, so it cannot run before them —
and before the pristine snapshot, because a snapshot of an unblessed dataset propagates the problem
into every run that restores it.

**Statistical.** *Built* — `tools/data-generator/validate.sql` produces the statistics and
`validate.py` judges them against the measured profile, exiting non-zero so it can gate a run rather
than be read and ignored.

**The checks are ordered by how hard they are to fake, and that ordering is the finding.** Row counts
the generator sets directly, so matching them proves only that the loader worked. Observation key
medians it targets, so matching them is weak evidence — **a generator emitting a constant key count
passes the median and fails the p95**, which is exactly the failure H3 warns about.

**Index bytes per row is the check that cannot be targeted.** It falls out of how many distinct keys
each row actually carries. Production's figures from Q7c, normalised per row: `individual` 99 B,
`program_encounter` 69 B, `encounter` 59 B, `program_enrolment` 54 B of GIN per row. An order of
magnitude lighter means the cardinality is wrong, the index sits in cache, and every push number is
optimistic with nothing in the run to show why. **Heavier than production fails too** — that makes
the server look worse than it is, which is a different way of not measuring production.

One trap avoided: **per-organisation concept cardinality is compared against the bundle's own
reachable set, not against Q6's 5,623.** That figure spans all 986 organisations, and judging one
generated tenant against it would fail a correct dataset.

### H6 — Decided: no production clone

**An anonymised production clone is not available.** Recorded here so it is not re-proposed: it would
have been more faithful than generation, but it is ruled out, and generation (H1–H5) is the path.

Two consequences follow.

**H6.1 — Production *statistics* are still required, even though production *data* is not.**
**Confirmed available.** Runnable SQL for each of the queries below is in [production-measurement-queries.md](production-measurement-queries.md). These are all
aggregate queries returning counts, durations and sizes — no personal data leaves the database:

| Needed for | Query against production |
|---|---|
| D6.1 | Sync duration vs. records pulled → `baseMsPerRecord` |
| D1 | Distribution of `loadedSince` gaps → realistic incremental scenarios |
| E5 | Org sizes, per-entity push/pull counts, peak-hour concurrency |
| F7 | Real sync duration distribution, to calibrate against |
| H3 | Fill rate, distinct concept cardinality, JSONB size distribution |
| H5 | `pg_total_relation_size` per index, row counts per entity |

Most come from `sync_telemetry`, which is telemetry rather than health data. Confirm this access
explicitly and early — it is a much smaller ask than a data clone, and it is the difference between a
calibrated simulation and a guessed one.

**H6.2 — Without a clone, H5's validation carries more weight.** A generated dataset is the only
dataset, so nothing else will catch a generator that produces unrealistic cardinality. Treat H5 as a
gate rather than a nice-to-have: run both checks before the dataset is blessed, and re-run them
whenever the generator changes.

### H7 — Generate production's tenant skew

**Cases 6 and 7 do not exist without this, so the hosting decision has no number behind it until it
is built.** It is a second generation run against a different specification rather than a variation
of the customer's: **986 organisations, 48% of them holding nothing, the largest holding 21% of all
subjects** (Q12), with the location hierarchies and catchments to match.

Three things make it cheaper than it sounds. Half the organisations are empty, so they cost a row in
`organisation` and nothing else. The bulk sits in a handful of large ones, so the generator's
existing per-tenant path covers most of it. And the co-tenants **do not sync in case 6**, so their
users exist only to make catchments resolvable — no feeder entry, no sync-status baseline.

**Size it against production rather than against the customer.** Q7's row counts are the target:
2.75 M subjects and 6.86 M program encounters across all organisations.

**Built** — `tools/data-generator/co_tenants.py`, with a recipe committed. 513 generated tenants
holding 2,548,061 subjects and 3.1 M encounters at day 180, plus 473 organisations that exist as a
row and nothing else. Sizes are interpolated through Q12's measured ranks rather than fitted, since
no single power law holds across the range — the exponent is 0.84 between ranks 1 and 10 and 1.57
between 1 and 156. Every share reproduces within two points.

Loaded together, cases 6 and 7 carry about **1.8× case 5's rows**, so expect the co-tenant half to
dominate load time and disk.

---

## I. Multi-tenancy as a test dimension

Avni is multi-tenant, and both deployment models exist in the estate — a shared installation hosting
many organisations, and dedicated installations. **They perform differently, and a test built against
one says little about the other.** Which model is being tested has to be a deliberate choice.

### I1 — How tenancy is implemented

Three mechanisms, all on the hot path:

- **Row-level security.** Every org-scoped table carries a policy
  `USING (organisation_id = ANY (public.rls_visible_org_ids()))`. The function is `STABLE`, so it is
  evaluated once per query rather than per row, but it does query `organisation` and
  `organisation_group_organisation` each time.
- **Reference tables use a wider predicate** — `rls_visible_org_ids_with_ancestors()`, which reads
  `public.org_ids` to include ancestor organisations. So **reference-data visibility walks an org
  hierarchy**, and hierarchy depth is itself a variable.
- **`current_user` is the organisation's `db_user`**, set by `SetOrganisationJdbcInterceptor`'s
  `set role` on every connection borrow (F2.1). RLS and the interceptor are one mechanism, not two.

> `V1_398__IndexableRLSOrgPolicies.sql` exists because the earlier policy referenced
> `organisation.db_user` directly and was not index-friendly. **Multi-tenant RLS cost has already been
> a real problem in this codebase once.** That is reason enough to treat it as a first-class dimension
> rather than a footnote.

### I2 — Why this changes the dataset, even for single-tenant load

The most important consequence, and the easiest to miss:

**`organisation_id = ANY (…)` selects your rows out of a table containing every tenant's rows.** Index
depth, buffer cache hit ratio, planner statistics and the cost of the index scan are all driven by
**total table size**, not by one tenant's slice.

So a dataset containing one organisation with 1M observations behaves quite differently from one
containing fifty organisations totalling 50M, even when the load is driven against a single org in
both cases. **A single-tenant dataset systematically understates production cost on a shared
installation.**

Two further effects in the same family:

- **Planner statistics are computed across all tenants.** With skewed tenant sizes — the realistic
  case — selectivity estimates for `organisation_id` reflect the aggregate distribution. Plans chosen
  for the average tenant may be wrong for the largest one, which is precisely the tenant most likely
  to have a performance problem.
- **Buffer cache holds the union of active tenants' working sets**, not one tenant's.

**Consequence for H:** the generator must be able to produce **N organisations with a realistic size
distribution**, not one. Treat tenant count and size skew as generator parameters alongside the config
source (H1). This is required even if the first runs drive load against a single org.

### I3 — Why this changes the load model

Driving multiple tenants concurrently exercises things a single-tenant run cannot:

- **The connection pool is shared across all tenants**, so pool exhaustion is a cross-tenant
  phenomenon.
- **`set role` churns on every borrow.** Under multi-tenant load, consecutive borrows of the same
  connection switch roles constantly. Whether that defeats prepared-statement or plan caching is an
  open question worth measuring — if it does, the cost is invisible in any single-tenant test.
- **Noisy neighbour** — one large organisation's sync degrading everyone else's, which E4 covers.

**Consequence for E and G5:** the feeder and user provisioning must be able to span organisations, with
a controllable mix. E4 is promoted from finding-triggered to a first-class scenario.

### I4 — Deployment model is a run parameter

| Model | What it tests |
|---|---|
| **Shared** — many organisations in one installation | RLS selectivity against a large aggregate table, cross-tenant pool contention, role churn, noisy neighbour, planner statistics skew |
| **Dedicated** — one organisation per installation | The per-tenant path with none of the above. Cheaper to set up, and a legitimate target if that is the model being sold |

Neither is "the" configuration. Record which model a run used in its metadata (A11) alongside tenant
count and size distribution — results are not comparable across models, and a number quoted without
that context is misleading.

### I5 — What to measure

- [ ] Cost of the RLS predicate — compare an org-scoped query with RLS active against the same query
      as a superadmin role where the policy does not apply
- [ ] How that cost scales with **tenant count** and with **total table size**, which are separable
- [ ] Reference-table RLS versus transactional-table RLS, given the ancestor walk
- [ ] Whether `set role` churn under multi-tenant load affects plan or prepared-statement caching
- [ ] Whether planner statistics skew produces different plans for the largest tenant

Tracked with the other measurement work in the avni-server card, not fixed pre-emptively.

---

## J. What the harness requires of the environment

Every infrastructure obligation this plan creates, gathered in one place so provisioning work can read
it off directly instead of reconstructing it from the sections above. Each item traces to the task
that produced it.

**This section states requirements, not sizing.** Instance classes, storage sizes, pool values and
heap settings are deliberately absent — they belong to F5.2 (parity, recorded per environment) and to
the Success criteria table, and this plan does not have those numbers yet. An item's absence here
means the harness does not require it, not that it is unnecessary.

### I1 — Network and access

| Requirement | From |
|---|---|
| Not publicly reachable: no public IP and no inbound security group rule on the application host | B1 |
| A deploy path that works with no inbound rule — EC2 Instance Connect Endpoint as an SSH `ProxyCommand` (preferred, since CI already uses EC2 Instance Connect under the same IAM model), or SSM Session Manager | F4.1 |
| Hosts addressable by **instance ID**, because both transports target instances through the AWS API rather than a resolvable name | F4.2 |
| An outbound path for deploy-time package fetches — NAT gateway or VPC endpoints. Without it the first Ansible run fails on apt, Maven and Docker pulls | F4.3 |
| DNS resolved deliberately: a private hosted zone record or instance-ID addressing. Whichever is chosen, `BASE_URL` must resolve from wherever the injector runs | F4.4 |
| A documented position for the load injector and a route from it to `BASE_URL`. Whether one injector suffices is an open question in this plan; providing somewhere to put it is an environment obligation | Open questions |

### I2 — Application configuration

| Requirement | From |
|---|---|
| `AVNI_IDP_TYPE=none` | B1 |
| Connection pool size set **explicitly** rather than left at the Tomcat JDBC default — the default is itself a predicted choke point, so it must be a knob, not an accident | F1 |
| Log level for `AuthenticationFilter`'s twice-per-request INFO logging chosen deliberately | F2 |

### I3 — Database

| Requirement | From |
|---|---|
| PostgreSQL 16.8 | G4 |
| Dedicated — must not share a database with anything real | B1 |
| Parameter group matching production's, autovacuum settings included | G4 |
| **IO parity with production** — storage class, IOPS and throughput. The plan requires the parity; the infrastructure plan owns how it is achieved and what the numbers are | G4 |
| `pg_stat_statements` and slow query logging enabled | F1 |
| **Storage IO characteristics stable for the life of the environment** — they must not change between runs, whether by autoscaling, resizing or any other means, or runs stop being comparable | G4 |
| Headroom for the chosen reset method — `TEMPLATE` needs roughly 2× the dataset, `pg_restore` ~1×. The dataset is ~70 GB (G4) | G4 |
| Snapshot and restore available for **baseline creation and dataset portability** — explicitly not as the per-run reset, for the lazy-loading reason in G4 | G4 |

### I4 — Data and side effects

| Requirement | From |
|---|---|
| Outbound side effects impossible — notifications, SMS, external integrations. Enforce at the infrastructure boundary rather than in application config alone, so a configuration mistake cannot cause an incident | F5.3 |
| The co-tenant workloads present and runnable — ETL host, export and import jobs, webapp. They share the instance and the IOPS budget, so an environment without them is quieter than any real one | F5.4 |
| A configured `bucketName` and a populated organisation `mediaDirectory`. **An actual S3 bucket is probably not needed** — presigning is local and nothing validates the bucket's existence; see D5.4. Create one only as a deliberate choice | D5.4, C2 |
| An outbound path for run artefacts: `simulation.log`, generated reports and run metadata | A11 |

### I5 — Observability

All of F1, restated as an environment obligation: `pg_stat_statements`, slow query log, JVM and GC
metrics, Tomcat JDBC pool gauges including waiting borrows, and per-endpoint p95/p99. The environment
must be able to explain *why* it slowed down, not only report that it did — without this the entire
plan produces unactionable findings.

Mostly satisfied by attaching the existing `newrelic` Ansible role and setting a few `-D` properties
in `avni_server_opts`; see F1. The blocker is that **no perf or loadtest group_vars file exists**, so
there is nowhere for that configuration to live yet.

---

## Sequencing

Ordering reflects dependencies, not estimates.

| Phase | Tasks | Why here |
|---|---|---|
| **0 · Foundation** | **Q1–Q15** → **Success criteria**, **H**, **F5**, **G1**, **G5** · A1, A9, A10 · **F4** → B1 · F1 | **~~Run the [measurement queries](production-measurement-queries.md) first.~~** *Done, and tracked per query.* They were a day's work with no dependencies, and they populated the Success criteria table, `baseMsPerRecord`, the `loadedSince` distribution, catchment sizing and the generator's target statistics. **H, F5 and G5 are the longest lead time in the plan and must be designed together; start them immediately after.** **F1 gates everything** — without server instrumentation the rest produces unactionable findings, though it is mostly attaching the existing New Relic agent to a new environment rather than building anything. **Auth ordering: F4 opens the deploy path, then B1 closes the environment.** B2 is deferred (see B), so nothing now has to happen before the cutover. B1 collapses most of G5; A2, A3 and A8 are resolved by A10.1. |
| **1 · Fidelity** | **D8.1** → C1, C2, C3 · D1, D2, **D6**, D9 · A4, A5, A6, A7 | Make the read path match the client and the harness trustworthy. D8.1 first — cheapest correction in the plan, and every prior run is invalid until it lands. D1 is the highest-value change: it likely alters which server code path is exercised at all. D6.1 and D8.3's SQL have no dependencies and can start immediately. Run **F7** at the end of this phase. |
| **2 · Coverage** | D3, D4 · **G4** · E1, E2 | Add the write path. New bottleneck class, and the one most likely to hold a surprise. **D3 and D5.1 are done**; G4's restore mechanism is what remains, and it is now the gate rather than a deferral — a `PUSH=on` run cannot be repeated without it. Q17 replaces D3's guessed push volumes. |
| **3 · Workload** | **D7** · E3, E5, **E7** · **H7** | Shape and size the load from production telemetry, then push until something breaks. D5 no longer sits here - upload landed with D3 and viewing is out of scope. D7 needs the per-entity durations added to `sync_telemetry`, so it trails a client release — as does D8.3, which rides the same release. Re-run **F7** after D7. |
| **4 · Operate** | A11 · F2, F3 · **A12** | Saturate, name the resource, fix, re-run. Expect four to six iterations — each fix reveals the next bottleneck. A12 is a backstop sweep only — README changes ride with the task that causes them, and the two items already wrong today can be fixed in Phase 0. |

**Test cases with numbers are in [test-scenarios.md](test-scenarios.md)**, ready for customer review.
Still open in them: that every supervisor sits at sub-centre level, which changes per-device volume
by an order of magnitude. Sync frequency is confirmed at once a working day, the acceptable error
rate at 0.05%, and the clustered window is covered by running cases 11 to 13 rather than by settling
it in advance.

**Deliberately unscheduled.** **D8.2** (page size tuning) and **E4** (noisy neighbour) are
finding-triggered — pull them forward when a result points at serialisation or at tenancy, not on a
calendar.

---

## Open questions

**[open-questions.md](open-questions.md) is the list**, and it is the only copy. What is still
outstanding turns on **how many supervisors sit above sub-centre level and at which tiers**, which
sets per-device volume and so decides whether the exercise is about the fleet or about a handful of
very heavy devices.

Keeping a second copy here is what let the two drift apart, so this section now holds only what the
plan itself decided. What the tests will *answer* is under **Measure before fixing** above.

### Closed

- **~~Perf environment isolation.~~** *No limitation.* The isolated deploy path is designed — an EC2
  Instance Connect Endpoint tunnels SSH through the AWS API to an instance with no public IP and no
  inbound rule, using the IAM model CI already relies on (F4.1). Nothing blocks `AVNI_IDP_TYPE=none`;
  it is build work in the infrastructure plan, not an unknown.
- **~~Who does this?~~** *The dedicated Avni team for Tanuh.*
- **~~How many media files does a typical sync upload?~~** *Answerable in SQL* — [measurement query](production-measurement-queries.md) **Q9**.
  `sync_telemetry` does not record media counts, but media observations do: they are keyed by concepts
  whose `data_type` is a media type, so their creation rate per user is derivable directly.
- **~~How often do resets happen?~~** *Answerable in SQL* — [measurement query](production-measurement-queries.md) **Q10** against the
  `reset_sync` table, which records every reset with user, subject type, organisation and timestamp.
- **~~State-wide facility search?~~** *Outside the current scope, decided with the customer.*
  Facility staff are expected to search across a whole state's beneficiaries. That is a `/web/*`
  query path whose cost scales with total tenant size rather than with catchment size, so it needs
  its own sizing. **Additive rather than excluded** — the harness, dataset and environment all serve
  it, so bringing it in later is a new set of scenarios rather than a new exercise
  ([scope](open-questions.md)). Until then: **a passing sync run is not clearance for search at that
  scale.**
- **~~Sync only, or webapp and API consumers too?~~** *Answered: they are separate query paths.* The
  webapp uses `/web/*` endpoints (≈150 call sites in `avni-webapp/src`) and touches only two
  sync-style endpoints, both reference data (`rule`, `ruleDependency`). So mobile sync and the webapp
  hit the same tables through **different queries** — fixing a slow sync query does not fix the
  webapp's equivalent, though a missing index would benefit both. Keeping scope to sync is correct,
  and webapp performance is a separate exercise.
- **~~Is pagination offset- or keyset-based?~~** *Answered: offset-based*, via Spring Data `Pageable`.
  See D8 — v2 returns a `Slice`, so the `COUNT(*)` half is already avoided; only row-skipping remains.

---

## Related

- **Raw result sets live in `avni-product-ops`** (`context/production-database-state-2026-09.md`),
  which is private. **This repository is public and carries summarised findings only** — ratios,
  percentiles and the figures the plan reasons about. Per-organisation sizes, per-index scan counts
  and the full hourly and weekly series are recorded there.
- **[test-scenarios.md](test-scenarios.md)** — the deployment being modelled and the test cases
  with numbers, for customer review. Split out because it has a different audience: that is what the
  instrument gets pointed at, this is how it gets built.
- **[open-questions.md](open-questions.md)** — the inputs this plan is waiting on. What it will
  answer is under *Measure before fixing*.
- **[production-measurement-queries.md](production-measurement-queries.md)** — the SQL behind every
  figure in this plan marked as measured, the caveats on running it, and the defects corrected across
  three runs against production. Findings live here, in the sections that use them: Success criteria,
  D1, D1.1, D3, D5, D5.1, D6.1, E3, E5, G4 and H3.
- Client-side performance (device profiling, Perfetto, Hermes profiler, Maestro/Flashlight) is a
  separate track — it answers "how long does sync take on a low-end phone", not "where does the server
  choke".
- `sync_telemetry` is already a production RUM for the sync path and is under-exploited. Per-entity
  *durations* (currently only counts are recorded) would feed both D6 and client-side work.
