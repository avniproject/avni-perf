# Execution plan

Day-wise ordering for getting from *the harness is built* to *the scenarios have been run and the
findings are believable*.

**The plan** ([sync-simulation-plan.md](sync-simulation-plan.md)) says how the instrument was built.
**The scenarios** ([test-scenarios.md](test-scenarios.md)) say what to point it at. This says in what
order, and what has to be true before each step is worth starting.

**Status:** drafted 28 September 2026, before any of it has run. Every duration past Day 3 rests on
two numbers nobody has measured — how long a dataset takes to load, and how long a restore takes —
so treat the shape as firm and the dates as provisional.

---

## Two things gate everything, and neither is in this repository

**1 — The environment.** `avni-infra#112`. Nothing below Day 1 can start without it. It is smaller
than it was: F4 is a security group allowlist plus the SSH tunnel CI mostly has, and
`configure/group_vars/loadtest_vars.yml` already carries the New Relic agent, production's heap, an
explicit pool size and `avni_idp_type: none`.

**2 — The bundle carrying the programme design.** Cases 2 to 13 size `program_enrolment` and
`program_encounter` rows. **The bundle the customer exports today has no live programs** — every
form mapping is a general `Encounter` on one `Patient` subject type — so the generator cannot
produce the designed shape. The simulation switches with one property; the dataset cannot.

> **Decide this before Day 4, because it changes what Days 7 to 9 build.** Either the designed
> bundle arrives, or the datasets are generated against the current one with
> `PUSH_ENCOUNTER_MODEL=general` and **every result carries that deviation**. Waiting silently is
> the one option with no upside — it converts a known deviation into a schedule slip.

---

## Phase 0 — Environment (Days 1–3)

Nothing here is measurement. The goal is a server that answers, that is reachable only from the
injector, and that is instrumented.

| Day | Task | Done when |
|---|---|---|
| **1** | F4: security group allowlist for the injector; EC2 Instance Connect Endpoint for the SSH hop; CI deploy through the tunnel (F4.1, F4.2) | `PERF_deploy` succeeds end to end, and the app port answers from the injector and refuses from anywhere else |
| **2** | Deploy the server. Confirm `loadtest_vars.yml` applied: heap, pool size, log level, `avni_idp_type: none`. Suppress outbound side effects (F5.3) — SMS, notifications, Glific | `/ping` answers; a request with only `USER-NAME` authenticates; nothing can reach a third party |
| **3** | F1: verify New Relic reports and the pool gauges arrive. Enable `pg_stat_statements` and the slow query log. Record instance classes, Postgres version, parameter group into F5.2's parity record | A dashboard shows JVM, GC and pool metrics for a request you just made |

> **Day 3 is not optional and is the most commonly skipped.** Without instrumentation every run
> yields "it got slow" and no cause, which is the failure this whole exercise exists to avoid.

---

## Phase 1 — Prove the groundwork, small (Days 4–6)

**Do not generate the real dataset yet.** Every step below is faster to debug on a tiny tenant, and
each one has a failure mode that would otherwise surface eight hours into a load.

| Day | Task | Done when |
|---|---|---|
| **4** | Generate a **deliberately small** deployment — one tenant, a few villages. Load it with `COPY` (H4). Run H5's statistical gate and the structural check | The gate exits zero, and a real client syncs one field worker and one supervisor account without error |
| **5** | G5: user provisioning against the loaded dataset. Baseline sync statuses. Then **the first real smoke run** — `PROFILE=smoke` against the environment, `PUSH=off` | A one-user sync completes green, and `run-metadata.json` records commit, dataset, server build and injector |
| **6** | **The push smoke** — `PUSH=on` at the same small scale. This is the run D3 has been waiting for. Then media (`MEDIA=on`) | Records arrive, `syncTelemetry` posts, and the report shows no failures |

> **Day 6 is where the harness gets its first contact with a real server.** Expect defects here
> rather than in Phase 4 — that is the point of the ordering. The three serverless gates
> (`make unit_test`, `make smoke_closed_port`, `make test_data_generator`) have never been able to
> catch anything that needs a server to be wrong.

---

## Phase 2 — The real dataset and the reset mechanism (Days 7–10)

| Day | Task | Done when |
|---|---|---|
| **7** | Generate the **day-180** dataset from its committed recipe. Load it. **Time both** | Row counts match the recipe's manifest exactly |
| **8** | H5's gates against it, then the client structural check. Fix what they catch | Gate exits zero; a real client syncs against the full dataset |
| **9** | **G4: build the restore mechanism.** Snapshot the verified instance as a template, then time a restore. Tag the snapshot against deletion; version it with the generator commit and H5's row counts | A restore returns a pristine database, and **you know how many minutes it takes** |
| **10** | Generate and load the **co-tenant** dataset (513 organisations) and take its snapshot. Generate day 60, 120 and 365 if case 8 is in scope | Four snapshots exist, each versioned |

> **Day 9's number sets the cadence for everything after it.** A run is *restore + run + collect*,
> so if a restore is 40 minutes, a 2-hour case is a half-day and a 4-hour case is a day. Do not plan
> Phase 4 until this is measured.

> **Do not skip the snapshot in favour of deleting rows between runs.** `DELETE` leaves dead tuples,
> `VACUUM` does not shrink indexes, and runs progressively stop resembling each other. Determinism
> matters more than absolute realism here, because the primary comparison is run against run.

---

## Phase 3 — Calibration (Day 11). **The gate.**

**F7. Nothing before this produces evidence, and nothing after it is trustworthy until it passes.**

Run a simulated user against the same per-entity record counts as a real production sync, and check
the simulated duration lands inside the observed distribution for that volume and device class —
production's `14.1s + 8.85ms × records`.

**Expect this to fail first time, and budget a day for it.** The coefficients it fits are deliberate
upper bounds rather than measurements: `BASE_MS_PER_RECORD` at 0.60 is derived from a 2-second page
ceiling, and `MS_PER_PAGE` at 174 still double-counts the server's own response time, which the
simulation genuinely incurs. **Day 11 is when both get real values** — net the server's median
response out of `MS_PER_PAGE`, refit `BASE_MS_PER_RECORD`, re-run.

> If it cannot be made to pass, stop. A simulation that does not reproduce a known sync is not an
> instrument, and every number after it is decoration.

---

## Phase 4 — Execution (Days 12–20)

Order is chosen so each case is interpretable when it runs, not so the calendar looks full. **Record
every run's metadata; two runs that differ in more than one property answer nothing.**

| Day | Cases | Why here |
|---|---|---|
| **12** | **1** (training cohort, 30 min), then **2** (field workers, 4 h) | Case 1 is config-only and the cheapest real load. Case 2 is the common case and the baseline everything else is read against |
| **13** | **3** (supervisors, 2 h driven) and **4** (combined, 4 h) | Case 4 is *the* realistic case. Case 3 first so its per-device cost is known before the mix |
| **14** | **5** (ten tenants, 2 h) and **6** (co-tenant data present, 2 h) | The delta between them is what tenancy costs structurally |
| **15** | **7** (co-tenant load, 2 h). Analyse 5/6/7 together | 6→7 separates structural cost from contention. Both must be read before moving on |
| **16** | **11, 12, 13** (clustered, 1 h each) | The same three tenancy shapes with the day compressed into an hour. The sync window is unconfirmed; these are the other end of the bracket |
| **17** | **8** (growth, 2 h × 4 — day 60, 120, 180, 365) | Needs its own day and three extra restores. Day 180 can reuse case 4's result rather than re-running |
| **18** | **9** (stress ramp, until it breaks) | Deliberately after the others: the knee is only interpretable once the unstressed shape is known |
| **19–20** | **10** (soak, 12 h) | Overnight. Leaks and autovacuum interaction need hours, and it needs the instance to itself |

> **Two supervisor spans, not one.** Cases 3 to 8 are specified across an 8-to-20 worker span, which
> changes both the supervisor count and each catchment's width. **Run the ends, not the middle** —
> the low end is the most concurrent, the high end holds the heaviest device. That doubles those
> cases if both ends are wanted; decide at Day 13 whether the budget is there.

---

## Phase 5 — Findings (Days 21+)

**Expect four to six iterations, not one pass.** Each fix reveals the next bottleneck, and the
sequence is: saturate, name the resource, fix, re-run. Findings that implicate the server become
cards in `avni-server#1060`; the two already suspected are the storage IO ceiling and the
per-connection `set role` churn (F2.1).

---

## What would make this slip, honestly

- **The environment.** Everything is behind `avni-infra#112`. It is the whole critical path.
- **The bundle.** No designed programme means no designed dataset. Decide by Day 4.
- **Restore time.** Unmeasured until Day 9. If it is an hour, Phase 4 stretches by days.
- **F7 not passing.** Budgeted one day; could be three. It is also the step most likely to send
  work back into the harness.
- **First contact.** Days 5 and 6 are the first time any of this touches a real server. The three
  serverless gates cannot catch anything that requires a server to be wrong, and this epic has
  already found four defects whose whole character was passing silently.

**Rough total: four weeks to first findings**, of which the first three days are not in this team's
hands.
