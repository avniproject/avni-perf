# Android Performance Simulation and Profiling Plan

Task breakdown for finding choke points in the Avni Android client.

**Scope:** client-side — sync persistence, UI responsiveness, rule execution, local database. Server
performance is tracked separately in [`sync-simulation-plan.md`](sync-simulation-plan.md).

**Not the goal:** benchmarking devices, or certifying a minimum handset spec. Both are legitimate
exercises with different designs.

**Status:** planning draft, September 2026.

---

## Where it stands

| Component | Technology | Notes |
|---|---|---|
| Local storage | Realm (legacy) → SQLite via `SqliteProxy` | **Migration in flight.** Not Room — a native binding with Drizzle schema export |
| Rule engine | `eval()` in the app's JS runtime (Hermes) | `RuleService.js:47`, `RuleEvaluationService.js:76,169,246,288`. **Not Rhino** — rules run on the same JS thread as everything else |
| UI framework | React Native 0.77.3 | |
| Sync engine | `SyncService`, `react-native-background-worker`, `react-native-background-timer` | Not androidx WorkManager directly |
| JSON handling | `JSON.parse` in the JS runtime | **No Jackson or Gson.** GC pressure here is Hermes GC, not JVM GC |
| Production telemetry | `sync_telemetry` (sync only) | **No client performance telemetry exists** — see A1 |
| Dev benchmarking | `PerformanceBenchmarkService` | Console-logging, reachable from `DevSettingsView`, hardcoded targets |
| Error reporting | Bugsnag (`@bugsnag/react-native`) | Present, and unexploited as a data source |

The goal is to move from "the app is slow" to "the app is slow **because of X**" — and the path there
runs through measurement, not through the remediation list in section H.

### Measure before fixing

Reading the code produces plausible suspects, and section C lists several. **They are hypotheses, not
findings.** Each gets a cost attached before anyone changes it, including the ones where the fix looks
obvious. A cheap-looking fix applied to something costing 2% of frame time burns review and release
cycles while the real bottleneck stays hidden — and on a client, every release cycle is weeks of
field rollout rather than a deploy.

---

## Success criteria

**Unfinished, and it blocks everything downstream.** No target below can be asserted on until it has a
number, and the numbers are not derivable from the codebase — they come from production telemetry that
**does not yet exist** (A1).

| Target | Source | Value |
|---|---|---|
| p95 time to interactive, per key screen | Client telemetry (A1) | *TBD* |
| p95 rule execution time | Client telemetry (A1) | *TBD* |
| p95 incremental sync duration | `sync_telemetry` — available today | *TBD* |
| Frame drop rate under load | Flashlight / Perfetto | *TBD* |
| Peak memory / ANR rate on low-end devices | Bugsnag, Android Profiler | *TBD* |

As with the server plan, the honest default is to derive each from **today's production distribution**
and assert "no worse than current". That is enough to catch a regression and to recognise a knee,
without requiring anyone to invent a UX target first.

**Definition of done.** The exercise ends when the top client-side bottlenecks have been named,
attributed to a specific cause, and either fixed or explicitly accepted with a reason. Not when a
profiling run completes.

---

## A. Production measurement — do this first

The server plan's highest-leverage move was querying production before building anything. The same
applies here, with one difference: **the client telemetry needed does not exist yet**, so step one is
adding it.

**A1 — Add client performance telemetry.** `performance_telemetry` is referenced in draft thinking but
does not exist; `PerformanceBenchmarkService` is dev-only. Capture and upload:

| Field | Why |
|---|---|
| `tti_ms` per key screen | The headline user-facing number |
| `rule_exec_ms` | Rule cost, per rule and per form |
| `db_read_ms` / `db_write_ms` | Hydration and persistence latency |
| `parse_ms` | JSON parse cost during sync |
| `frame_drop_rate` | UI smoothness in the field |
| `active_storage_engine` | Realm vs SQLite — see D3 |
| `memory_pressure_events` | Low-memory warnings and OOM risk |

> **Do this in the same release as the sync plan's client telemetry additions**
> (avniproject/avni-client#2121 — per-entity sync durations and `pageSize`). They are the same piece
> of work reaching the same table from the same code paths, and a client change costs a field rollout.

**A2 — Size the device matrix from the fleet, not from a guess.** `sync_telemetry.device_info` already
records `brand`, `manufacturer`, `deviceType`, `totalMemory`, `freeDiskStorage`, `connectionType` and
`effectiveConnectionType` for every sync. **The real device distribution is queryable today** — see
the appendix. Pick the matrix from the actual bottom quartile of deployed RAM, not from whichever
handsets are in the office.

**A3 — Size the local dataset from the fleet too.** `sync_telemetry.entity_status->'totalCounts'`
gives the per-device row counts users actually carry (subjects, enrolments, encounters,
programEncounters). That distribution defines what "a heavy device" means. This is query **Q3** in the
server plan's appendix — already written.

**A4 — Mine Bugsnag.** ANR and crash rates, segmented by device model and Android version, are
findings already sitting in production. Cross-reference with A2's device distribution: if crashes
concentrate in the low-RAM tier, that is a memory finding before any profiling run.

---

## B. Instrumentation and measurement harness

**B1 — Flashlight for black-box measurement.** FPS, CPU and memory during navigation, form filling and
sync.
- *Alternatives:* Firebase Test Lab performance monitoring (cloud, many devices, less granular);
  Emerge Tools (continuous, paid tiers); Android Profiler (deepest, hardest to automate).

**B2 — Perfetto tracing.** Integrate `androidx.tracing` to mark critical blocks, and visualise
contention between the UI thread, the JS thread and background workers.
- *What to trace:* rule evaluation entry points in `RuleEvaluationService`, `EntityHydrator.hydrate`,
  `SqliteProxy` bulk writes, dashboard render, `JSON.parse` during sync persistence.
- *Alternatives:* React Native DevTools for the JS side (Flipper is gone as of RN ≥0.73); Hermes
  sampling profiler for JS flame graphs — **essential here**, since Flashlight sees JS work only as
  aggregate CPU.

**B3 — Maestro for reproducibility.** Scripts for navigation, form stress, sync scenarios and
concurrent load.
- *Alternatives:* Detox — gray-box for React Native, synchronises with the runtime so it waits
  properly instead of sleeping; more setup than Maestro but materially less flaky. Appium if a
  commercial device cloud is ever needed.

**B4 — Reassure** for React Native render-performance regression tests in CI. No device required.
Complements the above rather than replacing anything.

---

## C. Hypotheses

Each needs a cost attached before any remediation. None is a finding yet.

### C1 — Rule execution blocking the JS thread

Rules are `eval()`'d in the app's JS runtime, so **rule execution and UI rendering share one thread**.
There is no separate engine and no bridge boundary — which means rule cost and UI jank are not two
problems but one.

- **Hypothesis:** complex skip-logic and decision rules block the JS thread long enough to drop frames
  during field entry and form-group transitions.
- **Test:** Hermes sampling profiler during form entry on a low-end device, with rule counts varied.
- **Why it matters:** a frozen keyboard during data entry is the most visible failure mode the app has.

### C2 — Database read and hydration cost

Large lists and dashboard tiles hydrate many objects.

- **Hypothesis:** missing indexes or shallow-hydration misses in `SqliteProxy` produce p99 spikes on
  screen load.
- **Test:** profile profile-open latency and list scroll for subjects at the high end of A3's
  distribution.
- **Note:** `PerformanceBenchmarkService` already benchmarks search, dashboard queries, filtered and
  sorted queries, and hydration. Extend it rather than starting fresh.

### C3 — Sync persistence contending with the foreground

- **Hypothesis:** bulk writes during sync block foreground reads or rule execution.
- **Test:** run Maestro navigation while a heavy sync is in progress; compare against idle.
- **Server-side link:** the sync plan's D6/D7 models exactly this cost from the server's side. The
  per-entity durations A1 adds **are** the input that model needs.

### C4 — JSON parse and memory pressure

- **Hypothesis:** parsing large sync payloads causes Hermes GC pauses and memory pressure on low-RAM
  devices.
- **Test:** Hermes heap snapshots and GC events during full sync.
- **Sharpened by the server plan:** the client requests **`pageSize: 1000`**
  (`config/initialSettings.json`). A page of 1000 observation-bearing rows is a multi-megabyte string
  to parse in one go — so page size is a **client-side** tuning lever too, not only a server one
  (sync plan D8).

---

## D. Test dimensions

Variables that change the answer, and must be recorded on every run.

**D1 — Device class.** From A2's fleet distribution. At minimum: bottom-quartile RAM, median, and
current.

**D2 — Local data volume.** From A3's distribution. At minimum: median device and high-end device.

**D3 — Storage backend — Realm vs SQLite.** The migration is in flight, so **every measurement must
record which backend produced it**, and comparing the two is a primary output rather than a caveat.
`active_storage_engine` in A1 covers the production side; runs must tag it too.

**D4 — Network conditions.** 2G/3G, high latency, intermittent connectivity. Field reality, and it
changes sync duration far more than device class does.

**D5 — Thermal and power state.** Start runs from a consistent device temperature; performance
degrades materially under throttling. Test at low battery with power saver active, where the OS caps
performance independently of anything the app does.

**D6 — Storage pressure.** Device responsiveness degrades as the disk fills. `freeDiskStorage` is in
`device_info`, so the fleet's actual distribution is known.

---

## E. Scenarios

**E1 — Cold start after install.** First launch plus full sync on a low-end device. Plausibly the
worst experience the app offers, and the one a new field worker meets first.

**E2 — Steady-state navigation.** Home → dashboard → subject list → subject profile. Measured idle.

**E3 — Form entry under rule load.** Field input to UI update latency with complex skip logic active.

**E4 — Navigation during background sync.** E2 and E3 repeated while a heavy sync runs. The delta
against uncontended is the finding.

**E5 — Incremental sync.** The common production case, as distinct from the full sync in E1.

**E6 — Post-reset re-download.** A reset forces affected users into a full re-sync (sync plan D9);
on-device cost is unmeasured.

Screens in scope, verified against the source:

| Area | Views |
|---|---|
| Home and dashboards | `HomeScreenView`, `MyDashboardView`, `CustomDashboardView` |
| Subject profile | `SubjectDashboardView` and its tabs (`SubjectDashboardProfileTab`, `SubjectDashboardGeneralTab`, `SubjectDashboardProgramsTab`), `IndividualProfile` |
| Form entry | `SubjectRegisterView` / `SubjectRegisterFormView`, `RegisterView`, `TaskFormView` |

Note `IndividualDetailsCard` is a card component, not a screen — the profile screen is
`SubjectDashboardView`. There is no `EncounterFormView`.

---

## F. Run process

**F1 — Reset between runs.** Runs are not comparable unless the device returns to a known state.
App-data-clear plus full re-sync is slow and couples every run to server performance; pushing a
pre-seeded database file via `adb` is fast and deterministic. **Decide before building the
automation** — this is the client analogue of the server plan's G4, and for the same reason.

**F2 — Environment control.** Consistent thermal starting state, no competing background processes,
airplane-mode-plus-shaped-network rather than ambient wifi, screen brightness and animation scale
pinned.

**F3 — Automated pipeline.** Reset → seed → execute Maestro scenario → capture Perfetto trace and
Flashlight metrics → archive with run metadata.

**F4 — Run metadata.** Every run records: app version and commit, device model, Android version,
**storage backend (D3)**, local data volume, network profile, battery and thermal state at start.
Without this, two runs are not comparable and a trend line is impossible.

**F5 — Calibration gate.** Before trusting any finding, prove the seeded device reproduces reality:
a simulated device carrying a real user's data volume should show a sync duration inside the observed
production distribution for that volume and device class (`sync_telemetry`, server plan Q5). If it
does not, the rig is not yet an instrument.

---

## G. Sequencing

Dependencies, not estimates.

| Phase | Work | Why here |
|---|---|---|
| **0 · Measure production** | A1 (telemetry), A2 (device matrix), A3 (data volumes), A4 (Bugsnag) | A2, A3 and A4 need no code and can start today. **A1 gates the success criteria and most of C**, and should ship in the same client release as avni-client#2121 |
| **1 · Fill in success criteria** | The table above | Nothing can pass or fail until these exist |
| **2 · Build the harness** | B1–B4, F1, F2, F4 | F1 before the automation, not after |
| **3 · Characterise** | C1–C4 against D1–D3, scenarios E1–E5 | Attach costs to hypotheses. Run **F5** at the end of this phase |
| **4 · Iterate** | Fix the largest named cost, re-measure, repeat | Expect several rounds; each fix reveals the next constraint |

**Deliberately unscheduled:** section H. Nothing there gets built until phase 3 says which cost it
addresses.

---

## H. Remediation candidates — not tasks

Recorded so they are not rediscovered, and explicitly **not** work items. Each becomes a task only
when a measurement names the cost it would remove.

1. Move rule evaluation or parsing off the JS thread.
2. Improve `SqliteProxy` indexing and batch loading.
3. Batch or throttle state updates to reduce render churn.
4. Separate read and write paths to reduce sync/foreground contention.
5. Reduce page size for observation-bearing entities, trading request count for parse cost (C4).

---

## Open questions

- **Success criteria.** The table above. Blocks everything.
- **Which devices define the matrix?** Answerable from `sync_telemetry` today (A2) — needs running.
- **Is Detox worth the setup over Maestro?** Gray-box synchronisation buys reliability that matters
  most in exactly the contended scenarios (E4) where black-box waits are flakiest.
- **Does the Realm → SQLite comparison have a deadline?** If the migration completes before the rig
  exists, the comparison becomes impossible to make.
- **Ownership and timeline.** The sequencing above is dependency-ordered only.

---

## Appendix — fleet queries

Read-only aggregates against `sync_telemetry`, runnable today. Use a read replica.

**AQ1 — Device distribution (A2).** Defines the test matrix.

```sql
SELECT device_info->>'brand'                             AS brand,
       device_name,
       android_version,
       round((device_info->>'totalMemory')::numeric / 1073741824, 1) AS ram_gb,
       count(DISTINCT user_id)                           AS users,
       count(*)                                          AS syncs
FROM sync_telemetry
WHERE sync_end_time > now() - interval '30 days'
  AND device_info ? 'totalMemory'
GROUP BY 1, 2, 3, 4
ORDER BY users DESC
LIMIT 30;
```

Read the **bottom quartile of `ram_gb` weighted by users** as the low-end target — not the single
worst device, which may be one handset.

**AQ2 — Network conditions (D4).** What the fleet actually syncs over.

```sql
SELECT device_info->>'connectionType'          AS connection,
       device_info->>'effectiveConnectionType' AS effective,
       count(*)                                AS syncs,
       round(avg(extract(epoch FROM (sync_end_time - sync_start_time))), 1) AS avg_seconds
FROM sync_telemetry
WHERE sync_end_time > now() - interval '30 days'
  AND sync_status = 'complete'
GROUP BY 1, 2
ORDER BY syncs DESC;
```

**AQ3 — Storage pressure (D6).** Whether low disk space is a real field condition or a hypothetical.

```sql
SELECT width_bucket((device_info->>'freeDiskStorage')::numeric / 1073741824, 0, 32, 8) AS free_gb_band,
       count(DISTINCT user_id) AS users
FROM sync_telemetry
WHERE sync_end_time > now() - interval '30 days'
  AND device_info ? 'freeDiskStorage'
GROUP BY 1 ORDER BY 1;
```

**AQ4 — Backend split (D3).** How much of the fleet has migrated.

```sql
SELECT app_info->>'activeBackend' AS backend,
       app_version,
       count(DISTINCT user_id)    AS users,
       percentile_cont(0.95) WITHIN GROUP (
         ORDER BY extract(epoch FROM (sync_end_time - sync_start_time))) AS p95_sync_seconds
FROM sync_telemetry
WHERE sync_end_time > now() - interval '30 days'
  AND sync_status = 'complete'
  AND app_info ? 'activeBackend'
GROUP BY 1, 2 ORDER BY users DESC;
```

This one doubles as a finding in its own right: if p95 sync duration differs materially between
backends at comparable data volumes, that is the migration's answer without any rig at all.

**Local data volume** is server plan query **Q3** — not repeated here.

---

## Related

- [`sync-simulation-plan.md`](sync-simulation-plan.md) — the server side. The two plans share
  measurements: page size (D8 there, C4 here), the client storage cost model (D6/D7 there, A1 and C3
  here), and the telemetry release.
- avniproject/avni-client#2121 — per-entity sync durations and `pageSize` in telemetry. **A1 should
  ship with it.**
