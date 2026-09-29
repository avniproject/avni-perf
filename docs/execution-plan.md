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

## At a glance

| Phase | Days | |
|---|---|---|
| **Day 0** | *while the bare environment is up* | Verify what is cheaper to check with no application listening — the WAF rule, outbound suppression, and whether a manual snapshot survives `destroy`. |
| **0 · Environment** | **1–3** | A server that answers, reachable only from the injector, and instrumented. |
| **1 · Prove the groundwork, small** | **4–6** | Generate, load, provision and smoke on a deliberately tiny tenant. First contact with a real server. |
| **2 · Real dataset and reset** | **7–10** | The day-180 dataset loaded and gated, the restore mechanism built and **timed**. |
| **3 · Calibration** | **11** | **F7, the gate.** Nothing before it is evidence; nothing after it is trustworthy until it passes. |
| **4 · Execution** | **12–20** | Cases 1 to 13, ordered so each is interpretable when it runs. |
| **5 · Findings** | **21+** | Saturate, name the resource, fix, re-run. Four to six iterations, not one pass. |

**Roughly four weeks to first findings**, of which Days 1 to 3 are not in this team's hands.

**Three of those rows carry most of the risk.** Day 9 produces the restore time, and a run is
*restore + run + collect*, so that number sets Phase 4's cadence rather than being a detail of it.
Day 11 is the one that can send work back into the harness, because both storage coefficients are
deliberate upper bounds rather than measurements. And Days 5 to 6 are the first time any of this
touches a real server — the three gates that run without one cannot catch anything that needs a
server to be wrong, and this epic has already found four defects whose whole character was passing
silently.

---

## One thing gates everything, and it is not in this repository

**1 — The environment.** `avni-infra#112`. Nothing below Day 1 can start without it. It is smaller
than it was: F4 is a security group allowlist plus the SSH tunnel CI mostly has, and
`configure/group_vars/loadtest_vars.yml` already carries the New Relic agent, production's heap, an
explicit pool size and `avni_idp_type: none`.

**2 — ~~The bundle carrying the programme design.~~ Settled: out of scope.** *29 Sep 2026.* The
design is still being built, and the exercise no longer waits for it. These runs use the shape the
current bundle exports — a general `Encounter` on one `Patient` subject type — and the simulation
now defaults to `PUSH_ENCOUNTER_MODEL=general` to match. Separate runs later if the design lands
and anyone wants them.

> **This removes a gate, not a risk.** Days 7 to 9 can build immediately; the generator already
> guards enrolment generation on the bundle's programmes, so it produces the general shape without
> changes. What the exercise gives up is written down in F5.2's parity record: `program_encounter`
> — production's largest table at 11.4 GB with a GIN index — is never written, nor is
> `program_enrolment`, so the enrolment join on the pull side never happens. Volume is preserved;
> the tables it lands on are not production's.

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

### Day 0 — What to verify while the infrastructure is up and the application is not

*Added after a bare OpenTofu environment was stood up to test the scripts.* An empty environment is
not a waste of a window — **several of section J's contract rows are easier to check with nothing
listening**, because an application answering can mask the thing being tested.

**Three are cheaper now than they will ever be again:**

| Check | Why now |
|---|---|
| **The WAF's rate rule** — fire >550 requests in five minutes from an un-allowlisted source and confirm blocking, then from the injector and confirm the scope-down exempts it | WAF acts before the target, so **no application is needed**. With one deployed, a 403 from the WAF and a 5xx from a struggling server look similar in a Gatling report — which is exactly how this defect would reach a run |
| **Outbound suppression at the boundary** (F5.3) — from the instance, try to reach the SMS, notification and Glific endpoints and confirm each fails | With the app absent there is no application-level config that could mask a boundary rule that is not actually there. Testing this later proves only that *something* blocked it |
| **Whether a manual snapshot survives `tofu destroy`** | This is the one to check **before** the destroy test, not after. G4 depends on a manual snapshot persisting; the generated dataset costs days to produce. Finding out that destroy takes the snapshot with it is survivable today and catastrophic on Day 10 |

**Everything else that is infrastructure-only, and worth recording rather than re-deriving later:**

- **Reachability** — the app port must be *refused* from the injector (security group allows, nothing
  listening) and *time out* from anywhere else (security group blocks). **Those two failures look
  identical in a browser and mean opposite things**, so check the distinction explicitly.
- **The SSH path** — `aws ec2-instance-connect open-tunnel` as a `ProxyCommand`, addressing the host
  by **instance ID**. Confirm CI's IAM role can do it, not just yours.
- **Egress** — apt, Maven and a Docker pull from the instance. A first closed-environment deploy
  most often breaks here, and it breaks eight minutes into a deploy rather than immediately.
- **DNS** — `loadtest.avniproject.org` resolves from wherever the injector runs.
- **Injector round-trip time.** Measure it and write it down. A sync is ~109 requests, so 25 ms of
  RTT is 2.7 s on a 14.1 s median — a constant offset, not noise. It belongs in the parity record
  and it is why runs from different injector positions are not comparable.
- **The database, against J's list** — version 16.8, dedicated, parameter group including autovacuum,
  `pg_stat_statements` and slow query logging enabled, storage class, IOPS and throughput.
- **Storage IO stability** — confirm RDS storage autoscaling is **off** and the volume is not on
  burst credits. IO characteristics that drift mid-exercise make runs incomparable in a way that is
  very hard to spot afterwards.
- **Snapshot and restore on the empty instance.** It will not tell you the restore time for a real
  dataset, but it proves the mechanism and gives a floor. Day 9's number is what sets Phase 4's
  cadence.

> **Fill in F5.2's parity record from these rather than from intentions.** Instance classes, Postgres
> version, parameter group, storage class and IOPS are all knowable today. Recorded now they are
> facts; recorded later they are recollections.

**What cannot be checked without the application**, so do not go looking: New Relic reporting and the
pool gauges (F1), `avni_idp_type`, pool size and log level, and anything about sync. The one adjacent
piece that *is* checkable is **egress to New Relic's collector** — worth confirming, since a silent
agent on Day 3 is otherwise indistinguishable from a misconfigured one.

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
- ~~**The bundle.**~~ Settled — the programme design is out of scope and the exercise no longer waits for it.
- **Restore time.** Unmeasured until Day 9. If it is an hour, Phase 4 stretches by days.
- **F7 not passing.** Budgeted one day; could be three. It is also the step most likely to send
  work back into the harness.
- **First contact.** Days 5 and 6 are the first time any of this touches a real server. The three
  serverless gates cannot catch anything that requires a server to be wrong, and this epic has
  already found four defects whose whole character was passing silently.

**Rough total: four weeks to first findings**, of which the first three days are not in this team's
hands. Taking the programme design out of scope removed a gate on Days 7 to 9 rather than shortening
them.
