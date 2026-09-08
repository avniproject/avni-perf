# Extending the Sync Simulation

Task breakdown for turning `avni-perf` from a working sync probe into an instrument capable of
finding choke points in the Avni server.

**Scope:** server-side, sync only. Client-side performance (device profiling, Maestro/Flashlight,
production RUM) is tracked separately.

**Status:** planning draft, September 2026.

---

## Where it stands

`AvniSyncSimulation` mints a Cognito token per user, posts `/v2/syncDetails`, then walks a hardcoded
list of ~60 entities, paginating each one that appears in the response. It groups requests per entity,
splits reporting by `entityTypeUuid`, and pauses per page to stand in for client-side storage time.

That is a real, working download-sync probe and a good foundation.

| | |
|---|---|
| Gatling plugin | 3.9.2 → 3.15.1.2 available |
| Gradle wrapper | 7.6 (plugin minimum) |
| Java toolchain | not declared — runs inherit ambient JDK |
| Entities in sim | 60, hardcoded in `sync()` |
| Push path coverage | none |
| Server APM | none |
| Assertions | commented out |

The work below is of two kinds: making the simulation **faithful** to what the client actually does,
and making it **trustworthy** as a measuring instrument. Neither is optional given the goal — an
unfaithful simulation finds the wrong bottleneck, and an untrustworthy one reports the injector's
limits as the server's.

---

## Success criteria

**This section is unfinished and blocks A6.** Nothing below can be asserted on until these numbers
exist, and they are not derivable from the codebase — they are a product decision informed by
production telemetry.

**What this work is for.** Finding choke points in the current server. Not capacity certification, not
regression gating — those are different exercises with different designs, and adopting either goal
later would change several decisions in this plan.

**Numbers that must be filled in before A6 can be implemented:**

| Target | Source | Value |
|---|---|---|
| p95 full sync duration, by data volume band | `sync_telemetry`, current production distribution | *TBD* |
| p95 incremental sync duration | `sync_telemetry` | *TBD* |
| Acceptable error rate under load | Product decision | *TBD* |
| Concurrent-user target to design against | Largest org size + expected growth | *TBD* |
| Peak-hour concurrency to reproduce | `sync_telemetry` timestamps, start-of-day distribution | *TBD* |

The honest default for a choke-point exercise is to derive thresholds from *today's* production
distribution and assert "no worse than current" — that is enough to detect a regression and enough to
recognise a knee, without requiring anyone to invent an SLO first.

**Definition of done.** The exercise ends when the top bottlenecks have been named, attributed to a
specific resource, and either fixed or explicitly accepted with a reason. Not when a run passes.

---

## A. Upgrade and harness hygiene

Six minor versions behind, with several patterns that will distort results before the server is ever
the limiting factor.

**A1 — Gatling 3.9.2 → 3.15.1.2.** Also bump the Gradle wrapper from 7.6 to current 8.x, and pin a
Java toolchain; `build.gradle` declares none today. Work through Gatling's upgrade guides one minor at
a time rather than jumping. Watch: the JDK baseline, the `simulation.log` format (it governs whether
logs from separate injectors can be merged), report generation, and the check/EL API used by
`jmesPath` and `transformWithSession`.

> The specific breaking changes per version were not verifiable at time of writing — the upgrade guide
> pages did not render through automated fetch. Treat the list above as the areas to check, not as a
> complete migration list.

**A2 — Fix the token cache data race.** `userTokens` is a static `HashMap` written concurrently from
Gatling's Netty threads. Unsynchronised `HashMap` under concurrent writes can corrupt its internal
structure. *Moot if B1 is adopted.*

**A3 — Stop blocking the injector event loop.** `CognitoHelper.getTokenForUser` is a synchronous
network call made inside `exec(session -> …)`. Blocking inside a session function stalls the
event-loop thread and every virtual user scheduled on it — worst exactly during ramp, when many users
authenticate at once. *Moot if B1 is adopted.*

**A4 — Materialise each response body once.** The two `checkIf` predicates each call
`response.body().string()`, so every page of every entity is turned into a String twice purely to test
for the substrings `totalPages` and `hasNext`. On large payloads this burns injector CPU and inflates
the latency being measured. Replace with a single parsed check.

**A5 — Flatten the nested entity loop.** `foreach(entities)` wrapping `foreach(syncDetails)` with a
`doIfEquals` is at minimum 60 × 60 ≈ 3,600 in-session comparisons per virtual user per sync — and that
is a floor, not an estimate. The syncDetails list carries one entry per entity *type instance*, so
every encounter type, program and subject type adds a row (visible in `SyncDetailsBody.json`, which
already has several `Encounter` entries). For a large organisation the real figure is several times
higher. Resolve the ordered work list once in a session function, then iterate it.

**A6 — Re-enable assertions.** The `forAll().failedRequests()` assertion is commented out, so no run
can pass or fail today. Add failed-request and per-group p95 assertions.

> **Blocked on Success criteria.** "Add p95 assertions" is not implementable until someone says p95
> of what, against what threshold. Fill in the table at the top of this document first; the
> "no worse than current production" default is a legitimate answer and unblocks this immediately.

**A7 — Name requests meaningfully.** `http(entityTypeUuid)` names every reference-entity request with
the empty string, since those entities have no type UUID. Name by entity plus UUID.

**A8 — Remove `System.exit(1)` from the auth path.** One user's Cognito failure currently terminates
the entire run, discarding all results collected so far. Fail the virtual user instead. *Moot if B1 is
adopted.*

**A9 — Credentials and config hygiene.** `sync-users.csv` is tracked in git — `.gitignore` only covers
`sync-users.*.csv`, which does not match it. `CognitoHelper` also carries a hardcoded client ID and
user-pool ID as defaults. Untrack the CSV, widen the ignore rule, move IdP identifiers to config.

**A10 — Delete dead weight.** `AvniEntities.json` is unused and already inconsistent with the
hardcoded list. `SyncDetailsBody.json` is unused — the sim posts `EmptyBody.json`. `Recorder.java` and
the commented `resetSyncs` block can go too.

**A11 — Archive runs with their metadata.** Keep each run's `simulation.log` alongside the sim's git
SHA, the server build, `BASE_URL`, injection profile and dataset identity. Without this, runs cannot
be compared and no trend line exists.

**A12 — Update the README.** Almost every task in this plan changes something the README documents,
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
| **User-ID auth** (`AVNI_IDP_TYPE=none`) | Server authenticates from the `USER-NAME` header; no token involved. The sim sends a header and nothing else. | Loses per-request JWT verification and user lookup from measurements. Requires a network-isolated environment. | **Recommended** |
| **Extend token TTL** | A perf-only Cognito app client with ID-token validity raised well beyond an hour. | Still needs AWS credentials on the runner; still hits Cognito rate limits during ramp; has a ceiling; a config change someone must remember exists. | Reserve |
| **Refresh in-simulation** | Background scheduler refreshes via `REFRESH_TOKEN_AUTH`; tokens resolved per request through the protocol `sign` hook so refresh is transparent to running users. | Most work, and the component most likely to fail in a way that looks like a server problem. | Only if a finding implicates auth |

**B1 — Run the perf server with `AVNI_IDP_TYPE=none`.** Confirmed in `AuthenticationFilter:68`: when
the IdP type is `none`, the filter calls `authenticateByUserName` using the `USER-NAME` and
`ORGANISATION-UUID` headers and skips token verification entirely. The simulation drops Cognito
completely — no minting, no expiry, no refresh, no AWS credentials on the runner, no Cognito rate
limits during ramp. It also deletes A2, A3 and A8 outright.

> **Hard constraint.** With `IdpType.none`, anyone who can reach the server is authenticated as
> whatever username they put in a header. The perf environment must be network-isolated — security
> group or VPN, never publicly reachable, never sharing a database with anything real.
>
> This breaks the existing CI deploy path, which reaches `perf.avniproject.org` over the public
> internet. **F4 is a prerequisite for B1, not a follow-up.**

**B2 — Measure and record the auth-cost offset.** The one thing B1 gives up is the per-request cost of
`authenticateByToken` — JWT verification plus a user lookup. Run a short profile both ways once, write
down the delta, and treat it as a known constant offset rather than pretending it is zero.

> **Must run before the environment closes.** B2 needs a working Cognito path to measure against, so
> it has to happen while the environment is still reachable — before F4/B1 cut over, not after.
> Otherwise it requires reopening the environment to collect a number nobody is blocked on. If that
> window is missed, drop B2 rather than reopening.

**B3 — Fallback: refresh tokens off the hot path.** Only if a finding implicates auth.
`AdminInitiateAuth` already returns a refresh token; refresh via `REFRESH_TOKEN_AUTH` on a background
scheduler at ~45 minutes into a `ConcurrentHashMap`. Critically, stop pinning the token into the
session at scenario start — resolve it per request through the protocol's `sign` hook, so a refresh is
transparent to virtual users already running.

---

## C. Entity list — stop hand-maintaining it

The 60-entry list is hardcoded in `sync()`. The git history is largely a record of repairing its
drift; the root cause is two sources of truth and no drift detection.

**C1 — Generate the entity table from `EntityMetaData.js`.** `avni-models/src/EntityMetaData.js` is
the client's canonical, versioned list — entity name, resource path, reference/tx type, and the
query-parameter name per entity. Emit the sim's table from it with a small script, commit the output,
and add a CI check that fails when regenerating produces a diff. This converts a recurring manual fix
into a build-time guarantee.

**C2 — Add the entities the sim is missing.** Present in `EntityMetaData`, absent from the simulation:

- `DownloadableContent`
- `CustomCardConfig`
- `Session`
- `AttendanceRecord`
- `RuleFailureTelemetry`
- `VideoTelemetric`
- `ResetSyncs`
- `News` — currently commented out because it reaches prod S3. Fix by pointing the perf environment at
  its own bucket rather than skipping the entity.

**C3 — Split `EntityApprovalStatus` by entity type.** The client issues five separate paginated pulls
— Subject, Encounter, ProgramEncounter, ProgramEnrolment, ChecklistItem — each with its own
`entityTypeUuid`. The sim makes one unparameterised call, so it under-counts both request volume and
server work for this entity.

---

## D. Fidelity gaps against the real client

Where the simulation and `SyncService.js` disagree.

**D1 — Post real sync statuses to `/v2/syncDetails`.** *(Highest value in the plan.)* The client posts
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

**How to build the array per user:**

1. *Bootstrap once per user.* POST `/v2/syncDetails` with `[]`. The server's own response returns the
   complete set of entity + entityTypeUuid combinations for that user's organisation — every subject
   type, program and encounter type — with the same field shape as the request
   (`EntitySyncStatusContract` is `{uuid, entityName, loadedSince, entityTypeUuid}`, which the sim's
   `SyncDetail` already parses). It round-trips; no need to derive org structure independently.
2. *Cache it* in a `ConcurrentHashMap` keyed by username, and build the request body with
   `StringBody(session -> …)` rather than trying to carry a 60-row array in the CSV.
3. *Rewrite `loadedSince` per scenario* — all rows at 1900 for full sync, all at `now − 1 day` for
   incremental, or a realistic spread for the faithful case. Real users' entities drift apart:
   reference data was last synced when configuration changed, transactional data yesterday. Since
   `loadedSince` is what feeds the per-row queries, uniform timestamps produce uniform and
   unrepresentative selectivity. Source the spread from `sync_telemetry` sync history, or approximate
   with buckets (~60% yesterday, 25% last week, 10% last month, 5% fresh device).

Also send the client's query parameters: `includeUserSubjectType=true&deviceId=`. `deviceId` is not
cosmetic — `filterChangedEntities` routes some entities through
`isSyncRequiredForDevice(loadedSince, deviceId)`, so sending none takes a different branch. Add a
stable per-user device ID to the feeder.

> **Suspect found while reading this code.** `getChangedEntities` does a nested linear scan
> (`serverSyncableItems.forEach` × `clientSyncStatuses.stream().noneMatch`), and `filterChangedEntities`
> issues one query per row. For an organisation with many subject types, programs and encounter types
> that is potentially hundreds of queries on the most-called endpoint in the protocol. Worth an
> `EXPLAIN` pass under F1 independent of the simulation work.

**D2 — Take `now` from the server response.** The client uses `now` / `nowMinus10Seconds` returned by
`syncDetails` as the window end. The sim substitutes its own `NOW` property, which changes the window
every entity is queried against.

**D3 — Model the push/upload path.** Everything behind `postAllEntities` — `POST /individuals`,
`POST /programEncounters` and the rest — is untested. These handlers are
`@Transactional(rollbackFor = Exception.class)`; write contention, lock waits and index-maintenance
cost are a different class of bottleneck from the read path and cannot appear in any run as it stands.
Derive realistic per-entity push volumes from production `sync_telemetry.entity_status->'push'`.

**D4 — Post sync telemetry at end of sync.** Every real client ends every sync with
`POST /syncTelemetry`. It is a write on the hot path, currently unmodelled.

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

**D5.1 — Media upload is unmodelled sync-path load.** A user with N queued media files makes N
`GET /media/uploadUrl/{fileName}` calls before the data sync even begins, each going through the full
authentication filter and organisation interceptor. This is genuine per-sync server load and the
simulation does not touch it at all. It is the part of media that most clearly belongs in scope.

**D5.2 — Do not transfer the bytes.** Since S3 serves the objects directly, having the injector PUT
and GET real files measures S3 and consumes bandwidth without exercising avni-server. Model the
presigned-URL requests; skip the transfers. This makes media cheap to include rather than a reason to
exclude it.

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

**D9 — Reset sync is unmodelled.** `SyncService` calls `getResetSyncData` and
`confirmUserAndResetSync` *before* the main pull, and the simulation's `resetSyncs` call is commented
out. A reset forces affected users into a full re-download, so it is potentially the single largest
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
appendix query **Q1**. No code, no dependencies; start it immediately.

Call the result **`baseMsPerRecord`**. Everything in D6.2 is expressed as a multiple of it, so the
tier work can be written and reviewed before the number arrives.

> **Q1 gives a ceiling, not the value.** Production sync duration is client parse-and-persist time
> **plus network plus server response time**. The simulation's pause must represent client work only —
> the server under test supplies its own response time — so using Q1's figure directly would
> double-count the server. Two ways to net it out: subtract the server's own share, which
> `AuthenticationFilter`'s per-request timing logs already record (F2), or take the clean number from
> D7's device instrumentation and use Q1 only as a sanity ceiling. Either way, **do not use Q1's
> output as `baseMsPerRecord` unmodified.**

**D6.2 — Classify entities into weight tiers.** Three tiers, expressed as multipliers of
`baseMsPerRecord` rather than absolute milliseconds:

| Tier | × base | Entities |
|---|---|---|
| **Light** | 0.2 | Flat lookup rows: `Gender`, `ProgramOutcome`, `TaskStatus`, `TaskType`, `ApprovalStatus`, `StandardReportCardType`, `LocationHierarchy`, `Privilege`, `Groups`, `GroupPrivileges`, `MyGroups`, `GroupRole`, `MenuItem`, `AddressLevel`, `LocationMapping` |
| **Medium** | 1.0 | Config and light transactional: `Concept`, `ConceptAnswer`, `Form*`, `OrganisationConfig`, `Translation`, `PlatformTranslation`, `Dashboard*`, `ReportCard`, `Documentation*`, `Rule*`, `Checklist*`, `IdentifierAssignment`, `Comment*`, `Task*`, `UserSubjectAssignment`, `SubjectMigration`, `EntityApprovalStatus`, `GroupSubject`, `SubjectProgramEligibility` |
| **Heavy** | 3.0 | Observation-bearing: `Individual`, `ProgramEnrolment`, `ProgramEncounter`, `Encounter` |

Since `baseMsPerRecord` is the *observed fleet average* across a real entity mix, the multipliers are
weights around that average — they do not need to sum or normalise to anything, but they should
straddle 1.0, which they do.

> **These multipliers are judgement, not measurement.** The tiering reflects payload structure —
> whether a row carries an observation set — which is the dominant cost driver. The ratios matter more
> than precision within a tier, and D7 replaces the whole scheme with per-entity measurements. Three
> tiers is deliberate: a finer split is false precision on numbers this soft.

Per-page overhead (parse setup, transaction open/commit) is omitted from the model entirely. At a page
size of 1000 it is negligible against the per-record term, and carrying a second constant that cannot
be measured separately adds nothing.

**D6.3 — Implement.**

- Add a `msPerRecord` field to the `AvniEntity` model (populated by the C1 generator, so new entities
  get a tier assignment rather than silently defaulting).
- Capture the page's record count in a check — `jmesPath("_embedded.<resourceName> | length(@)")`.
- Replace `.pause(0, maxPauseToSimulateRealmStorage)` with the computed pause.
- Introduce `STORAGE_MODEL` as a system property: `weighted` (default) and `zero` (pure server
  saturation runs, client cost removed). Delete the uniform pause outright rather than keeping it as
  a third mode — no existing run results need preserving, and an unexercised config path rots the
  same way `AvniEntities.json` did.

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

**D8.1 — Source the page size from the client config.** Do not hardcode 1000. Read it from
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

**E1 — Deterministic feeder.** `csv(...).random()` lets two virtual users drive the same real user
concurrently — contention that does not occur in production — while other users never run at all. Use
`circular()` or `queue()` for repeatable, non-overlapping runs.

**E2 — Separate full and incremental sync scenarios.** The committed CSV sets `lastModifiedDateTime`
to 1900-01-01, so every user performs a full first sync every run. Incremental sync is the common
production case and has a completely different profile. Add upload-only background sync as a third
(`sync_source = ONLY_UPLOAD_BACKGROUND_JOB`).

**E3 — Named injection profiles.**

- *Smoke* — one user, CI-gated
- *Load* — expected peak
- *Stress* — ramp to the knee
- *Spike* — the start-of-day thundering herd; realistic worst case for a field app
- *Soak* — multi-hour; the case that raised the auth question

**E4 — Multi-org / noisy neighbour scenario.** *Finding-triggered, not baseline.* Drive one large
organisation alongside several small ones and watch whether the small orgs' latency degrades. A
tenancy bottleneck cannot surface in a single-org run — but build this when something points at
tenancy (shared connection pool saturation, row-level-security overhead, lock contention across
orgs), not before.

**E5 — Size everything from `sync_telemetry`.** Production already records per-sync duration,
per-entity push/pull counts, local data volumes, device and connection type. Take user counts, data
volumes and push volumes from that table rather than inventing them.

---

## F. Observability, environment and run process

The gating workstream. Without it, every run yields "it got slow" and no cause — and the simulation
work above produces findings nobody can act on.

**F1 — Instrument the server.** `avni-server`'s build declares no Micrometer, Actuator,
OpenTelemetry, New Relic or Datadog — there is nothing beneath the Gatling report. Minimum viable set:

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
a concrete example (D5). Quantify it early: it is cheap to measure and, if significant, the fixes
range from a one-line log change to batching the two `SET` statements into one round trip.

**F2 — Check request logging isn't itself the choke point.** `AuthenticationFilter` logs at INFO twice
per request — on receipt, and on completion with timing — including the full query string. Under load
that is a plausible bottleneck in its own right. Measure it, and decide deliberately what level the
perf environment runs at.

**F3 — Reconcile the second Gatling setup.** `avni-server/perf/gatling/` is a separate, older harness.
Fold it in or delete it; maintaining two guarantees both drift.

### F4 — Deploying the server to the closed environment

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

**F5.3 — Suppress outbound side effects.** Notifications, SMS, external integrations, ETL and
reporting jobs. Also decide whether background jobs *should* run during a test: they compete for the
same database and are arguably part of realistic load, so this is a choice to make explicitly rather
than discover.

### F6 — Run-to-run data lifecycle

Once D3 lands and the simulation pushes data, the database changes with every run and runs stop being
comparable. See **section G** for the full treatment — this is the hardest operational problem in the
plan and the one most likely to silently invalidate results.

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

---

## G. Anatomy of a test run

What actually has to happen for one run to produce a trustworthy number. Most of this does not exist
yet and is not covered by the task list above, which is about the simulation rather than the ritual
around it.

### G1 — One-time, per environment

| Step | Notes |
|---|---|
| Provision the environment | F4, F5.2 |
| Load the dataset | F5.1 — the long pole |
| Provision perf users and catchments | G5 below |
| Bootstrap per-user sync-status baselines | D1's bootstrap call — one `POST /v2/syncDetails` with `[]` per user |
| Capture the pristine snapshot | This is what every subsequent run restores to |

The last step matters: the reference snapshot must be taken **after** users and baselines exist, so
restoring never destroys them.

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

**The environment is RDS PostgreSQL 16.8**, which rules out the usual answer. Options in order:

| Method | Verdict |
|---|---|
| **`CREATE DATABASE … TEMPLATE`** | **Best for per-run reset.** File-level copy inside the existing instance: no new instance, no endpoint change, and — critically — the storage blocks are already hydrated, so none of the penalty below. Needs ~2× storage and no active connections to the template during the copy. |
| **RDS snapshot restore** | **Use for the baseline, not per run.** See the two problems below. Right tool for rebuilding the environment from scratch and for moving the dataset between environments. |
| **`pg_restore` from dump** | Logically identical but physically pristine — indexes rebuilt with zero bloat. Deterministic, slow at scale. Reasonable fallback. |
| **`DELETE` + `VACUUM` / `REINDEX`** | **Avoid.** Progressively worse each cycle; `REINDEX` takes as long as a restore and yields a less realistic index than production has. |

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

**PostgreSQL 16 detail for the template copy.** Since PG15 the default `CREATE DATABASE` strategy is
`WAL_LOG`, which writes the entire copy through WAL and is slow for a large template. Specify
`STRATEGY = FILE_COPY` explicitly:

```sql
DROP DATABASE IF EXISTS avni_perf;
CREATE DATABASE avni_perf TEMPLATE avni_perf_template STRATEGY = FILE_COPY;
```

**Parameter group parity is part of this.** `shared_buffers`, `work_mem`, `max_connections`,
`effective_cache_size` and the autovacuum settings all come from the RDS parameter group, and a
restored instance inherits the snapshot's. Match production's parameter group and storage class
(gp3 throughput and IOPS included) or record the deviation under F5.2 — this is an easy one to get
wrong silently.

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

**Simplification worth knowing:** download sync is read-only. Until D3 lands, runs do not modify
application data at all and need no restore — only `POST /syncTelemetry` (D4) writes, and that is one
small row per user. Restore-per-run only becomes mandatory when the push path arrives, which means
this whole apparatus can be deferred to Phase 2 rather than built up front.

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

**Use an existing implementation config repo rather than cloning production metadata.**
`jss-sickle-cell-screening` is a complete org definition already on disk — `concepts.json` (256
concepts), `forms/` (4 forms), `formMappings.json` (11 mappings), `encounterTypes.json`,
`catchments.json`, real `address-level/` data down to village, and `create_organisation.sql` to
bootstrap it. `avni-health-modules` supplies the shared reference concept and rule library on top.

This is strictly better than cloning production metadata: it carries no governance question at all,
it is versioned alongside the plan, and a run can state exactly which config revision it used.

**Covering organisation size.** The JSS config is realistic but modest — it represents the typical-to-
small end. Large organisations have many more programs, forms and concepts, and org complexity is
itself a load variable (it drives the syncDetails row count, and therefore the per-row queries in
`filterChangedEntities`). If no larger config is available to check in, synthesise one by scaling this
one — duplicate concept trees and form mappings to reach a realistic large-org shape — rather than
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
- **Distinct concept-UUID cardinality across observations.** See below; this is the one most likely to
  be got wrong.
- **Fill rate — observations per row.** Drives payload size, serialisation cost and GIN index size.
- **Coded answer value cardinality.** Same mechanism.
- **Temporal spread of `last_modified_date_time`.** Easy to overlook and it invalidates D1's whole
  purpose: if every generated row shares a timestamp, incremental sync returns either everything or
  nothing, and no incremental scenario means anything. The spread must look like real editing
  activity over time.
- **Address level hierarchy shape.** Drives the scope-resolution queries behind catchment filtering.

> **The GIN indexes make observation cardinality a first-class concern.**
> `V1_03__AddGinIndexForObservations.sql` creates `GIN (observations jsonb_path_ops)` on `individual`,
> `program_enrolment` and `program_encounter`. Three consequences:
>
> - GIN maintenance dominates insert cost on the push path (D3) and scales with the number of distinct
>   keys per document — so push benchmarks are only as realistic as the observation cardinality.
> - GIN's `fastupdate` pending list causes periodic merge spikes rather than uniform write latency. A
>   genuine production failure mode, and one the simulation can only reproduce with realistic data.
> - If synthetic observations draw on fewer concepts or lower-cardinality values than production, the
>   index is smaller, hotter in cache, and faster — and every number you produce is optimistic.

### H4 — Loading it

Bulk-load with `COPY` directly into the tables, not through the API — the API is orders of magnitude
slower and millions of rows are needed. Build indexes after the load, then `ANALYZE`.

The tradeoff is that `COPY` bypasses server-side validation, so a generator bug produces data the
application cannot read. Mitigate by round-tripping a sample through the real API and comparing.

Post-load indexes are pristine, with none of production's accumulated bloat — acceptable here, because
G4 snapshots this state and every run restores to it, so it is at least deterministic. Note the
deviation in F5.2.

### H5 — Proving the data is good enough

Two checks, both cheap:

**Structural.** Point the real client (or the simulation) at it and confirm a full sync completes and
subjects render without rule failures. Catches datatype and reference errors immediately.

**Statistical.** Compare aggregates against production: rows per entity, mean observations per row,
distinct concept count, JSONB size distribution, and — the single most informative check —
**`pg_total_relation_size` per index**. If the generated GIN index is an order of magnitude smaller
than production's for comparable row counts, the observation cardinality is wrong and every push
number will be optimistic.

### H6 — Decided: no production clone

**An anonymised production clone is not available.** Recorded here so it is not re-proposed: it would
have been more faithful than generation, but it is ruled out, and generation (H1–H5) is the path.

Two consequences follow.

**H6.1 — Production *statistics* are still required, even though production *data* is not.**
**Confirmed available.** Runnable SQL for each of the queries below is in the appendix. These are all
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

---

## I. What the harness requires of the environment

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
| Storage class, IOPS and throughput matching production | G4 |
| `pg_stat_statements` and slow query logging enabled | F1 |
| Storage headroom for a **second copy of the dataset** — the per-run reset is `CREATE DATABASE … TEMPLATE` against a pristine template database held on the same instance | G4 |
| Snapshot and restore available for **baseline creation and dataset portability** — explicitly not as the per-run reset, for the lazy-loading reason in G4 | G4 |

### I4 — Data and side effects

| Requirement | From |
|---|---|
| Outbound side effects impossible — notifications, SMS, external integrations. Enforce at the infrastructure boundary rather than in application config alone, so a configuration mistake cannot cause an incident | F5.3 |
| A decision, recorded, on whether ETL and reporting background jobs run during tests — they compete for the same database and are arguably part of realistic load | F5.3 |
| A configured `bucketName` and a populated organisation `mediaDirectory`. **An actual S3 bucket is probably not needed** — presigning is local and nothing validates the bucket's existence; see D5.4. Create one only as a deliberate choice | D5.4, C2 |
| An outbound path for run artefacts: `simulation.log`, generated reports and run metadata | A11 |

### I5 — Observability

All of F1, restated as an environment obligation: `pg_stat_statements`, slow query log, JVM and GC
metrics, Tomcat JDBC pool gauges including waiting borrows, and per-endpoint p95/p99. The environment
must be able to explain *why* it slowed down, not only report that it did — without this the entire
plan produces unactionable findings.

---

## Sequencing

Ordering reflects dependencies, not estimates.

| Phase | Tasks | Why here |
|---|---|---|
| **0 · Foundation** | **Q1–Q7** → **Success criteria**, **H**, **F5**, **G1**, **G5** · A1, A9, A10 · B2 → **F4** → B1 · F1 | **Run the appendix queries first** — they are a day's work with no dependencies, and they populate the Success criteria table, `baseMsPerRecord`, the `loadedSince` distribution, catchment sizing and the generator's target statistics. **H, F5 and G5 are the longest lead time in the plan and must be designed together; start them immediately after.** **F1 gates everything** — without server instrumentation the rest produces unactionable findings. **Order matters within auth: B2 must be measured while Cognito still works, then F4 opens the deploy path, then B1 closes the environment.** B1 deletes A2, A3, A8 and collapses most of G5. |
| **1 · Fidelity** | **D8.1** → C1, C2, C3 · D1, D2, **D6**, D9 · A4, A5, A6, A7 | Make the read path match the client and the harness trustworthy. D8.1 first — cheapest correction in the plan, and every prior run is invalid until it lands. D1 is the highest-value change: it likely alters which server code path is exercised at all. D6.1 and D8.3's SQL have no dependencies and can start immediately. Run **F7** at the end of this phase. |
| **2 · Coverage** | D3, D4 · **G4** · E1, E2 | Add the write path. New bottleneck class, and the one most likely to hold a surprise. **G4's restore mechanism lands with D3** — until the simulation writes, runs are read-only and need no teardown at all, so this apparatus can be deferred to here rather than built up front. |
| **3 · Workload** | **D7** · E3, E5 · D5 (if scoped) | Shape and size the load from production telemetry, then push until something breaks. D7 needs the per-entity durations added to `sync_telemetry`, so it trails a client release — as does D8.3, which rides the same release. Re-run **F7** after D7. |
| **4 · Operate** | A11 · F2, F3 · **A12** | Saturate, name the resource, fix, re-run. Expect four to six iterations — each fix reveals the next bottleneck. A12 is a backstop sweep only — README changes ride with the task that causes them, and the two items already wrong today can be fixed in Phase 0. |

**Deliberately unscheduled.** **D8.2** (page size tuning) and **E4** (noisy neighbour) are
finding-triggered — pull them forward when a result points at serialisation or at tenancy, not on a
calendar.

---

## Open questions

- **Success criteria.** The table at the top of this document. Blocks A6, and shapes what counts as a
  finding. The "no worse than current production" default is a legitimate answer.
- **Perf environment isolation.** Can it be locked down enough to run `AVNI_IDP_TYPE=none`? Gates B1
  and therefore three other tasks.
- **~~Production statistics access.~~** *Granted.* Queries Q1–Q7 in the appendix are ready to run;
  their outputs feed the Success criteria table, D6.1, D1, E5, F7 and H3/H5. **Running them is now the
  first task in Phase 0** — most other open questions resolve from their output.
- **A larger org config.** (H1.) `jss-sickle-cell-screening` is the *only* complete implementation
  config available locally — ~250 concepts, 4 forms — and it represents the typical-to-small case. Is
  there a bigger one that can be checked in? If not, the large-org shape has to be synthesised by
  scaling it, and that becomes a task rather than a question.
- **How many media files does a typical sync upload?** (D5.1.) Each one is a
  `GET /media/uploadUrl/{fileName}` call on the sync path, so the distribution sets how much server
  load media contributes. `sync_telemetry` does not record media counts, so this needs another source
  — S3 object creation rate per org over a period is the most likely proxy. **This is the only media
  question that blocks anything**; D5.2 already settles that the transfers themselves are not
  simulated, and the S3 bucket is required regardless of the answer.
- **~~Is on-demand media viewing in scope?~~** *Decided: no.* Browsing workload, not a sync one. See
  D5.3.
- **Reset sync scope.** (D9.) Modelling the post-reset stampede is potentially the highest-load
  scenario in the system. Worth including, but confirm how often resets actually happen in production
  before investing in it. Needs H6.1 access to answer.
- **Distributed injectors.** Gatling OSS has no orchestration; multiple injectors mean merging
  `simulation.log` files by hand (`gatling.sh -ro`). Cannot be answered until the concurrent-user
  target in Success criteria exists — one large injector goes a long way.
- **Who does this, and over what period?** Sequencing here reflects dependencies only. Someone will
  need to attach effort and ownership before it becomes a schedule.

### Closed

- **~~Sync only, or webapp and API consumers too?~~** *Answered: they are separate query paths.* The
  webapp uses `/web/*` endpoints (≈150 call sites in `avni-webapp/src`) and touches only two
  sync-style endpoints, both reference data (`rule`, `ruleDependency`). So mobile sync and the webapp
  hit the same tables through **different queries** — fixing a slow sync query does not fix the
  webapp's equivalent, though a missing index would benefit both. Keeping scope to sync is correct,
  and webapp performance is a separate exercise.
- **~~Is pagination offset- or keyset-based?~~** *Answered: offset-based*, via Spring Data `Pageable`.
  See D8 — v2 returns a `Slice`, so the `COUNT(*)` half is already avoided; only row-skipping remains.

---

## Appendix — production statistics queries

Starting points for the H6.1 queries, all read-only aggregates. Validate and tune the time windows
before trusting output.

> **Run these against a read replica if one exists.** The `jsonb_object_keys` scans in Q6 touch large
> tables; `TABLESAMPLE` keeps them cheap, but avoid peak hours regardless.

**Q1 — `baseMsPerRecord` ceiling (D6.1).** Remember this includes network and server time; see the
caveat in D6.1.

```sql
with s as (
  select
    extract(epoch from (sync_end_time - sync_start_time)) * 1000 as duration_ms,
    (select coalesce(sum((e->>'done')::int), 0)
       from jsonb_array_elements(entity_status->'pull') e) as pulled
  from sync_telemetry
  where sync_status = 'complete'
    and sync_end_time > now() - interval '30 days'
    and sync_source is distinct from 'ONLY_UPLOAD_BACKGROUND_JOB'
)
select count(*) as syncs,
       percentile_cont(0.5)  within group (order by duration_ms / pulled) as p50_ms_per_record,
       percentile_cont(0.95) within group (order by duration_ms / pulled) as p95_ms_per_record
from s
where pulled > 100;
```

**Q2 — `loadedSince` gap distribution (D1).** Drives the realistic-spread scenario.

```sql
with gaps as (
  select sync_end_time
         - lag(sync_end_time) over (partition by user_id order by sync_end_time) as gap
  from sync_telemetry
  where sync_status = 'complete'
    and sync_end_time > now() - interval '90 days'
)
select percentile_cont(array[0.25, 0.5, 0.75, 0.9, 0.99])
         within group (order by extract(epoch from gap) / 3600) as gap_hours_p25_50_75_90_99
from gaps
where gap is not null;
```

**Q3 — Per-user data volume (E5, G5, H3).** `totalCounts` is the local row count on each device, which
is effectively "rows in this user's catchment" — the number that drives both catchment design and
generated data volume.

```sql
select percentile_cont(array[0.5, 0.9, 0.99]) within group (
         order by (entity_status->'totalCounts'->>'programEncounters')::numeric)
         as program_encounters_p50_p90_p99,
       percentile_cont(array[0.5, 0.9, 0.99]) within group (
         order by (entity_status->'totalCounts'->>'subjects')::numeric)
         as subjects_p50_p90_p99
from sync_telemetry
where sync_status = 'complete'
  and entity_status ? 'totalCounts'
  and sync_end_time > now() - interval '30 days';
```

**Q4 — Peak-hour concurrency (E5, Success criteria).** The start-of-day herd, by local hour.

```sql
select extract(hour from sync_start_time at time zone 'Asia/Kolkata') as hour_ist,
       count(*) as syncs,
       count(distinct user_id) as users
from sync_telemetry
where sync_start_time > now() - interval '30 days'
group by 1
order by 1;
```

**Q5 — Sync duration by volume band (F7, Success criteria).** The distribution the calibration gate
compares against.

```sql
with s as (
  select extract(epoch from (sync_end_time - sync_start_time)) * 1000 as duration_ms,
         (select coalesce(sum((e->>'done')::int), 0)
            from jsonb_array_elements(entity_status->'pull') e) as pulled
  from sync_telemetry
  where sync_status = 'complete'
    and sync_end_time > now() - interval '30 days'
)
select width_bucket(pulled, 0, 50000, 10) as volume_band,
       count(*) as syncs,
       percentile_cont(0.5)  within group (order by duration_ms) as p50_ms,
       percentile_cont(0.95) within group (order by duration_ms) as p95_ms
from s
group by 1
order by 1;
```

**Q6 — Observation shape (H3, H5).** The numbers that determine whether generated data behaves like
production. Repeat per entity table.

```sql
select percentile_cont(0.5)  within group (order by k) as p50_obs_keys,
       percentile_cont(0.95) within group (order by k) as p95_obs_keys,
       avg(sz)::int                                    as avg_obs_bytes
from (
  select (select count(*) from jsonb_object_keys(observations)) as k,
         pg_column_size(observations)                           as sz
  from program_encounter tablesample system (1)
  where observations is not null
) t;

-- distinct concept cardinality across observations
select count(distinct key) as distinct_concepts
from (
  select jsonb_object_keys(observations) as key
  from program_encounter tablesample system (1)
) t;
```

**Q7 — Row counts and index sizes (H5).** The single most informative comparison against generated
data — a GIN index an order of magnitude smaller than production's means the cardinality is wrong.

```sql
select relname, n_live_tup
from pg_stat_user_tables
where relname in ('individual', 'program_enrolment', 'program_encounter', 'encounter')
order by n_live_tup desc;

select relname, indexrelname,
       pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
       idx_scan
from pg_stat_user_indexes
where relname in ('individual', 'program_enrolment', 'program_encounter')
order by pg_relation_size(indexrelid) desc;
```

**Q8 — Fleet page size split (D8.3).** *Not yet answerable* — `pageSize` is not recorded in
`app_info`. Rides the same client release as D7's per-entity durations. Until then the production
split between page size 100 and 1000 is unknown and both must be tested.

---

## Related

- Client-side performance (device profiling, Perfetto, Hermes profiler, Maestro/Flashlight) is a
  separate track — it answers "how long does sync take on a low-end phone", not "where does the server
  choke".
- `sync_telemetry` is already a production RUM for the sync path and is under-exploited. Per-entity
  *durations* (currently only counts are recorded) would feed both D6 and client-side work.
