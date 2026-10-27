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
| **4 · Execution** | *ordered, not dated* | Cases 1 to 14, in a sequence where each is interpretable when it runs — see **The sequence**. |
| **5 · Findings** | *after* | Saturate, name the resource, fix, re-run. Four to six iterations, not one pass. |

**Status as of 19 Oct 2026.** Phases 0–3 complete, and **Phase 4 is done: every case in the sequence has run.** **Block A is done** — the soak (**10**) on
10 Oct, and the stress ramp (**9**) on 12 Oct as 12a/12b/12c, which settled the ceiling at
12.85 Mrec/h without push and 11.32 with; case 11 has run at 1,682/h, at 550/h four times, and
at a 15-minute window. **Block B's dataset is provisioned, loaded and verified** — 513 co-tenant
organisations, 6.25 M transactional rows, every organisation matching its manifest, with the
timings under [the archetype measurements](#before-the-ten-tenant-cases-can-be-generated).
**Cases 6 and 7 are done (14 Oct), and together they answer Block B's question: co-tenant
presence costs 0.3% per record, their activity at production's busiest hour costs 18%** — CPU on
both tiers with nothing saturated, so it is work per record rather than contention. Both followed a
pilot reset that removed 120,929 rows of push residue. **Case 12 (15 Oct) adds the
concurrency half: compressing the same work 12x costs 170% more server time per record and takes
app CPU to 81%. Case 13 then broke — the first run in the exercise to do so — and in breaking
resolved the ceiling question: asking 47% more removed 38% of the throughput, and **12.85 Mrec/h
turns out to be a saturated server rather than a maximum, with 21.0 available below the knee.**
Block B is complete.** **Block C is complete (15–16 Oct) and there is no knee.**
Per-record server cost falls and flattens — 0.386 → 0.347 → 0.326 ms across days 60, 120 and 365 —
while records per sync tracks dataset depth exactly, x6.08 for x6.08 at day 365. What grows is the
**device's** wait: a median sync goes 21.4 s → 122.5 s and p95 to 369.5 s, linear in depth. The
server is not the constraint anywhere on this curve, which makes the remaining question a product
one rather than a performance one. The reset before it emptied the co-tenants' 6.25 M transactional rows so the curve
is not damped by a constant background. The
day 60/120/365 archives are in S3.
**Block A′ is complete (19 Oct) and the sequence has no unrun rows left.** The span sweep
settles the outermost loop: widening a supervisor's catchment 2.38× gives **2.33–2.44× the records
per sync** across three independent runs, at **about +5% per record** — and field workers, whom the
span does not touch, hold at 1.00× in the same runs and bound that figure's noise at 1–2 points.
**It is case 8's answer reached from a different input**: volume is linear on this server however
it arrives. A supervisor's median sync goes 3.0 → 7.1 minutes, which is a product question about
supervisor tooling rather than a server one. Nothing in it justifies widening the sweep.
[`findings-span20.md`](findings-span20.md).
**The vertical scale sweep is done (21 Oct) and the campaign's most repeated claim survives a
direct test**: app CPU is the constraint, and more of it is the relief. Case 13 at 4 vCPU went from
467 failures to **zero** and from a p95 of 56.7 s to **434 ms**, with CPU at 54% rather than 99% —
the same bed, the same load, only the instance type changed. The constraint has moved most of the
way to the database (RDS 33% → 41%), so capacity planning past 4 vCPU should expect to size that
next. [`findings-vertical-scale.md`](findings-vertical-scale.md).
Run-by-run state is in **[The sequence](#the-sequence)**; results are in
[`run-log.md`](run-log.md) and the `findings-*.md` files. `pilot-day-180` was **reloaded on
14 Oct** — organisations 10–19 torn down and restored with the co-tenants left in place, removing
120,929 rows of residue — and case 6 pushed nothing, so it is clean. Case 7 pushes nothing either;
reload again before anything that turns on a small delta after a pushing run.

**Roughly four weeks to first findings**, of which Days 1 to 3 are not in this team's hands. **Phases 4 and 5 carry no dates on purpose**: runs slip, one gets re-run, another overtakes two others, and a calendar that has to be re-read as "whenever this actually goes" is worse than no calendar. What binds them is order, not dates.

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

> **Getting a user is the chicken-and-egg, and it is solved.** The users the scenarios run as come
> from the dataset generator, which needs a bundle and two files dumped from the target database —
> so requiring one would mean the readiness check could only run *after* the expensive thing it
> exists to de-risk. `make bootstrap_user ORG=… USERNAME=…` emits idempotent SQL for one syncable
> user with no dataset behind it: one location and its type, a catchment, a group carrying
> privileges, and the membership row. It reuses the generator's own row builders, so a bootstrap
> user is shaped exactly like a generated one. `--user` is optional on the check, which runs
> everything that does not need one and says what it skipped.

**Run `make check_environment URL=… USER=…` first.** It asks all of the questions below that can
be asked over HTTP, in one pass, and exits non-zero if the environment is not ready. It exists
because three environment windows produced three failures — a null `version` on a `user_group`
row, missing AWS credentials, and a user with no catchment — each found one at a time by a person
running a simulation and reading a stack trace, when every one was a single request away from
being visible.

It names those three specifically when it sees them, and it checks the thing a `200` does not
prove: **that the user resolves privileges**. Without a group carrying `has_all_privileges` the
sync succeeds and silently omits every entity holding field data (G5), so "syncDetails returned
200" is not the same as "this environment can be measured".

**Three are cheaper now than they will ever be again:**

| Check | Why now |
|---|---|
| **The WAF's rate rule** — `make check_environment … WAF=1`, from the machine that will drive the load | WAF acts before the target, so **no application is needed**. It fires past the 550-per-five-minutes threshold and fails if any request comes back 403, because an un-exempted injector is throttled and **Gatling reports the WAF's 403s as the server failing** — a corrupted run that looks like a finding. Opt-in and last, since if the injector is not exempt everything after it would be blocked for the rest of the window |
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

**Measured 30 Sep 2026, on the day-180 state tenants.** 501,000 subjects and 1,799,926 encounters
per tenant, under Phase 4 conditions: full index parity with production, and the audit trigger's
per-row notices suppressed.

| | per tenant | rate | both tenants |
|---|---|---|---|
| **load into an empty organisation** | **402 s** (6.7 min) | 5,728 rows/s | **13.4 min** |
| teardown, then reload | 1,013 s (16.9 min) | — | 34 min |
| &nbsp;&nbsp;— the `DELETE` half | 611 s (10.2 min) | 3,769 rows/s | 20 min |

**Deleting costs 1.52x inserting**, because every one of the 15 indexes on `encounter` has to be
updated per row. So **`teardown` is not the per-run reset** — it is 2.5x a plain load and leaves
dead tuples on top. It stays what it was built for: the iteration-phase reset, where it empties one
organisation without touching its neighbours and a restore would be far too slow a loop.

> **The two corrections cancelled.** This load is 402 s against 404 s measured before index parity
> and before the notices were suppressed. Five more indexes per insert and ~4.6 million fewer
> notice lines turn out to be near-equal and opposite, which neither figure predicted. The
> coincidence is worth stating rather than hiding, because it means the earlier number was right
> by accident and the reasoning behind it was not.

**How many times this is paid.** Every case except 1 and 14 runs with the push path on, so every
such run leaves the dataset mutated and the next needs a pristine start. There is no sharing a reset
between runs.

| | runs | on |
|---|---|---|
| cases 1–7 | 7 | one empty, three on **one state tenant of** the ten-tenant pilot, three on all ten ± co-tenants |
| case 8, growth | 3 | day 60, 120, 365 — day 180 reuses case 4's result |
| cases 9–13 | 5 | ten-tenant ± co-tenants |
| case 14, full sync | 1 | one state tenant; pulls only, so it mutates nothing |
| **Phase 4** | **16** | |
| Phase 5, four to six iterations | 4–6 | |
| **total** | **~21**, of which ~19 would need a reset first | cases 1 and 14 have no push, so neither does |

> **Cases 2, 3 and 4 are not on a separate two-tenant dataset (corrected 6 Oct 2026).** This table
> said "two-state day-180", which predates the block ordering below. Block A takes **one** reset
> and contains cases 5 and 11, which need ten tenants — so Block A loads `pilot-day-180`, and
> cases 2, 3 and 4 run against **one state tenant inside it**. `states-day-180` and the pilot share
> organisation ids 10 and 11 but no usernames at all, so the distinction is not academic: it is why
> the feeders are named for their dataset.

At the projected ~21 min for a ten-tenant reset, **19 resets is about 7 hours** of reset time
across Phases 4 and 5; by the teardown path it is 11–12. So a mechanism that saves ten minutes a
reset saves better than three hours of the exercise, which is what Day 9 is actually deciding.

> **Superseded by the block ordering, 1 Oct 2026: it is about ten resets, not nineteen.** Phase 4
> needs five — one per block plus case 8's three dataset swaps — and Phase 5's four to six stay
> one per run, because re-measuring after a fix is the point of them. The arithmetic above is kept
> because it is what Day 9's decision was made against, and a mechanism that saves ten minutes a
> reset is worth less when there are half as many resets. `truncate` still wins: at 388 s measured
> against the teardown's 1,013 s, five resets is 32 min against 84.

### Before the ten-tenant cases can be generated

**The pilot recipes named live organisations, and that is fixed but not finished.**
`pilot-day-60/120/180/365` carried `organisation_id` 1 to 10, which are not free on the load
environment: 1 is the platform organisation, 3 is the customer's, 9 is a fixture and 10 is the
first state tenant. Generating against them would have written a pilot dataset into four live
organisations.

The existing guard is weaker than it looks: `_refs` refuses an organisation with no entry in
`refs.json`, which is what stopped this so far — but only while *some* of the ten are missing.
Provision the other six and generation proceeds into OpenCHS.

Organisation ids are `SERIAL`, assigned when a tenant is provisioned, so a committed recipe cannot
hold real ones. All four now carry `organisation_id: null` and `Recipe.to_deployment` refuses
them rather than defaulting — a default here is a guess at which organisation to overwrite. A
half-filled recipe is refused too, since it would generate for the tenants that have ids and skip
the question for the rest.

**Provisioned 6 Oct 2026.** `state-1` and `state-2` already existed at 10 and 11; `ngo-1` to
`ngo-8` were created and the server assigned **12 to 19**, read back from `GET /organisation`
rather than inferred from the sequence. Each carries the full bundle, verified against the
bundle's own JSON by `provision-org.sh` step 5: 39 form mappings, 2 subject types, 16 encounter
types, 406 concepts, in all eight. The four pilot recipes now hold those ids and build.

**`refs.json` re-dumped, and two further defects surfaced on the way to generating.**

**The bundle's `organisationConfig` did not reach the eight new organisations.** `refs.json` showed
`customRegistrationLocations` for 3, 10 and 11 but not 12–19, while the bundle ships it. The file
was in the zip, first in import order, matched `OrganisationConfigRequest` exactly, and
`saveOrganisationConfig` scopes by `organisationId` — and each organisation already had a config
row created during its own provisioning, which the bundle's settings never replaced. Applied
through `POST /organisationConfig` for all eight and confirmed by a re-dump: 11 rows, every pilot
tenant covered.

**What let it through is a gap in the check, not bad luck.** `provision-org.sh` step 5 verifies form
mappings, subject types, encounter types and concepts against the bundle's own JSON. It does not
verify organisation config, so the import reported COMPLETED, four checks passed, and the one thing
that did not land was the one thing unverified. It likely affects every organisation provisioned
this way.

**And `supervisor_level` was the `TenantSpec` default**, `Sub-Centre`, which this bundle's hierarchy
does not contain: truncated at the deepest permitted registration type the chain is
State > District > Taluka > Village, so `cat.plan` raised. `states-day-180` has carried `Taluka`
since it was built and the pilots inherited the default. Set on every pilot recipe.

**The ten-tenant pilot now builds**: 1,682 users across organisations 10–19, and
`scenario-feeders.py` writes `case5-users.csv` for the first time.

> **The scenarios' 188 supervisors assumed the low end of the span, which is now established
> rather than inferred.** Fixing the span at 8 gives **190** — 63 per state tenant and 8 per NGO,
> against the scenarios' 1,504 workers and 188 supervisors. That is the table's own arithmetic
> reproduced, so the figure was never wrong; it was a different point on the range.
>
> **The span that was actually unstated was the recipe's.** `pilot-day-180` left
> `workers_per_supervisor` null, which takes `hy.ESTABLISHMENT` — and that supervises at
> Sub-Centre, a tier this bundle does not have, so supervision fell back to Taluka and the span
> landed at **12.5**, 120 supervisors. Neither an end of the range nor the measurement. Q13's
> measured 8.4 is now written into the recipe rather than inherited.
>
> **Two spans are built, 8.4 and 20** — `pilot-day-180` (1,682 users, 176 supervisors) and
> `pilot-day-180-span20` (1,580 / 74), 6,896,792 and 6,896,276 rows, 0.007% apart: the same
> beneficiaries and encounters, differently supervised. **Span 8 was generated and dropped** — 63
> supervisors per state tenant against 8.4's 60 is a 5% difference and not worth a run, because the
> measurement sits almost on the low end already. **Switching spans is a reload, not a flag**,
> which is why both exist rather than one parameterised at run time; see Phase 4's ordering.
>
> **Both spans are in S3** — `s3://avni-loadtest-936573213727/datasets/`, as
> `pilot-day-180.tar.gz` and `pilot-day-180-span20.tar.gz`, about 562 MB each from 2.88 GiB on
> disk, uploaded 6 Oct 2026. **Every generated dataset lives under that prefix**, including the
> growth points below.
> `states-day-180` is there too, as one tarball per tenant, and for that one S3 is the only copy
> left: the generator writes to `/tmp`, and `/tmp/states-day-180` had already been emptied by the
> machine's cleaner by 6 Oct. **Generated datasets are not durable where they are written**, which
> is the reason to upload one the day it is built rather than the day it is needed.
>
> **Block C's growth points went up the same day**, generated 6 Oct 2026 against the same bundle
> and the same organisation ids, all four pinned at span 8.4 so the curve varies encounter volume
> alone:
>
> | dataset | rows | on disk |
> |---|---|---|
> | `pilot-day-60` | 3,306,220 | 1.22 GiB |
> | `pilot-day-120` | 5,101,506 | 2.05 GiB |
> | `pilot-day-180` | 6,896,792 | 2.88 GiB |
> | `pilot-day-365` | 12,432,076 | 5.46 GiB |
>
> **The increments are the check that they form one series**: 1.795M rows per 60 days between 60,
> 120 and 180, and day 365's 185 further days predict 12.43M, which is what it came out at.
> Beneficiary population does not grow with the growth point, so everything above the first point
> is encounters. Each set's byte counts match its manifest and all 110 `\copy` paths resolve.
>
> **Case 8 reuses `case4-users-pilot.csv` at every point**, which holds because `plan_ids` gives
> the first tenant the same id base whatever `days` is. Only 561 of 1,682 usernames survive a
> growth-point change and they are exactly that feeder; see the test in `test_recipe.py`.
>
> **The one thing to check on the first extraction.** Each tenant's `load.sql` carries *absolute*
> `\copy` paths — `/tmp/<set>/<tenant>/<table>.tsv` — so the archive has to land back at exactly
> that path for any of it to resolve. 110 statements per set, all of them wrong together if the
> root differs, and the failure happens at load time on the server with the transfer already paid
> for. The sizes are a free check that both sets arrived whole: they differ by 10,240 bytes, one
> tar block, which is the 516-row difference between the spans and nothing else.

**The co-tenant datasets are the gap in that arithmetic.** Cases 6, 7, 12 and 13 need 513 further
organisations present — the ones of Q12's 986 that hold data. The other 473 would be bare
`organisation` rows; `co_tenants.empty_rows()` builds them, nothing calls it, and 1 Oct 2026
decided to leave it that way. `co-tenants-day-180` is 513 tenants and 3.13M
encounters, so it is comparable in size to the pilot dataset itself.

**Provisioned and generated 13 Oct 2026.** The 513 exist at organisation ids 24–566 with their
archetype bundles imported, and the dataset is built: 6,253,693 rows, 3.12 GiB — within 10% of the
whole pilot. **Loading it is still unmeasured**, which was the open question here and remains the
open question: the reset budget rests on a ~21-minute projection extrapolated from two tenants, and
this is the load that tests it. The ordering below is built so it is loaded once and never
unloaded.

> **The co-tenants are provisioned after Block A, not before it (decided 6 Oct 2026).** Generating
> their data needs their organisations to exist first: `refs.sql` reads `subject_type.id` and
> friends *per organisation*, and those rows come into being when the bundle is imported into that
> organisation. So provisioning is a prerequisite of generation, not a step beside it.
>
> **That collides with what case 5 measures.** Case 5 is separate infrastructure — "the customer's
> own load with nobody else's data in the tables" — and on genuinely separate infrastructure the
> other organisations do not exist at all, not even empty. Each carries roughly 510 config rows,
> so 513 of them is about 262,000 rows before a single subject, plus their weight in planner
> statistics and RLS, which this document already says matters for the 473 empty ones. Provisioned
> early, cases 5 and 11 would run against them and the 5 -> 6 delta would isolate the co-tenants'
> *data* rather than their presence.
>
> Snapshots could have held both states apart. The simpler answer was taken: **nothing touches the
> database until Block A is done.**
>
> **And the recipe's organisation ids are placeholders, which is the pilot's bug waiting.**
> `co-tenants-day-180.json` carries 1001 to 1513, from `co_tenants.plan(first_organisation_id=
> 1000)`. The server assigns ids; it does not accept them. This instance currently holds 13
> organisations — 1, 3, 9 and 10 to 19 — so the next one created is 20, and nothing in the range
> the recipe names will exist. **Read the ids back from `GET /organisation` after provisioning and
> record them**, exactly as the eight NGO tenants were, rather than inferring them from the
> sequence. The pilot shipped with 1 to 10, which named four live organisations, and
> `unassigned_organisations()` cannot catch this case because these ids look assigned.
>
> **Measured 9 Oct 2026, and it does not fit in Block B.** One `large-pull-heavy` organisation
> takes **232 seconds** — `cotenant-timing-probe`, id 20, of which ~220 s is the server's batch
> import. **Imports do not run concurrently**, so 513 of them is **26 to 33 hours serial**, against
> a block that also has to hold a reset, a load and two runs.
>
> This previously bracketed the step at 85 minutes to 8.5 hours and said to time one first. Timing
> one is what found this: the step is an order of magnitude past the top of that bracket, and
> Block B cannot open with it as specified.
>
> **All three archetypes measured 12 Oct 2026, back to back on a warm idle server**, which is what
> the paragraph above asked for. Every import verified complete — concepts, form mappings, subject
> types and config all matching the bundle, so none of these is the timing of a failed import.
>
> | archetype | time | concepts | form mappings | probe org |
> |---|---|---|---|---|
> | `large-pull-heavy` | **183 s** | 1,523 | 118 | `cotenant-probe-large` |
> | `push-dominated` | **72 s** | 1,172 | 67 | `cotenant-probe-push` |
> | `media-heavy` | **110 s** | 341 | 19 | `cotenant-probe-media` |
>
> **The hybrid set of 11 + 97 + 2 is 9,217 s — about 2 hours 35 minutes.** It fits inside a working
> day, and the step that could not open Block B as specified now can.
>
> **Two cautions for anyone reusing these numbers.** The same `large-pull-heavy` bundle measured
> **232 s on 9 Oct and 183 s on 12 Oct** — a 21% spread between days, so treat any single figure as
> ±20%. And **the timings do not scale with bundle size**: `media-heavy` has a third the concepts of
> `push-dominated` and takes 53% longer, at rates of 3.1, 8.3 and 16.3 concepts/second. The poll
> counts explain why — `provision-org.sh` prints one `STARTED` per poll and logged 13, 35 and 21 of
> them, which at ~5.2 s each reproduces 72, 183 and 110 almost exactly. **These measurements are
> quantised to the poller, not the importer**, so the per-archetype ratios are soft even though the
> total is sound. The routes out, and what each trades, are in `docs/dataset-provenance.md`.

> ### Block B as executed, 12–13 Oct 2026
>
> **Provisioning, 513 organisations.** Run from the app host against `localhost:8021` — the app
> host cannot reach its own ALB, whose security group admits only the injector CIDR — detached
> under `setsid nohup`, with the environment stopped overnight between the two days.
>
> | | tenants | wall | per tenant |
> |---|---|---|---|
> | 12 Oct, from co-003 | 380 | ~8.5 h | 72 → 80 s, rising |
> | 13 Oct, after restart | 131 | **155 min** | 69 → 73 s, flat |
> | | **513** | **~11 h** | 0 failed |
>
> The rise and its reset are the uptime drift recorded in
> [`runbook-provisioning-stop-resume.md`](runbook-provisioning-stop-resume.md): ~13% over ~380
> imports and ~12 h, fully recovered by a restart, and **not** a function of how many
> organisations already exist. Budget 11 h, not the 2 h 35 m the hybrid set above projected —
> that figure was for 110 tenants, not 513.
>
> **The data load, 6.25 M transactional rows, 2.9 GB of TSV.**
>
> | step | | |
> |---|---|---|
> | upload | 2.8 GB → **512 MB** gzipped, streamed to S3 | **46 s** |
> | host fetch + extract | via the VPC gateway endpoint, not the EICE tunnel | ~1 min |
> | load, 85 tenants | first attempt, **with** the per-tenant `ANALYZE` | **102 min** |
> | load, 428 tenants | `ANALYZE` stripped, one at the end | **199 s** |
> | teardown, 11 orgs | 3,526,311 rows, **with** the FK scaffolding indexes | **8 min** |
> | reload, 11 orgs | 3,520,627 rows | **21 min** |
>
> **A clean run is about 40 minutes.** The 102 minutes above was 64% `ANALYZE`; stripping it
> leaves ~2,730 rows/s, and 6.25 M rows at that rate is ~38 min. Everything beyond that was
> rework — a stale generation for the 11 `large-pull-heavy` tenants, and a teardown that scanned
> 4.4 GB per user until two foreign keys were indexed. Both are written up in the runbook.
>
> ### The 20 Oct 2026 reload, and what it cost to learn
>
> **The co-tenant bed was reloaded on 20 October in 38 min 39 s** — within the ~40 minutes above —
> after a day spent making it take hours. Every number below is measured, and the write-ups live
> beside the code they constrain: `copy_writer.py` and `tools/restore-co-tenants.sh`.
>
> **1. A multi-table load must not be wrapped in one transaction.** Each tenant's `load.sql` used
> to be a single `BEGIN … COMMIT`. `program_encounter` is loaded after the two largest tables, so
> it always inserted into a transaction already holding ~700k new rows, and that costs about
> **100x per row** and worsens as the transaction grows:
>
> | 50,000 `program_encounter` rows | |
> |---|---|
> | prefix in one transaction | 185,165 ms — **270 rows/s** |
> | prefix committed table-by-table | 10,875 ms — **4,600 rows/s** |
> | no prefix at all | 1,712 ms — **29,200 rows/s** |
>
> One tenant's 413,320 rows had not finished after 33 minutes; without the wrapper the same copy
> took **31 seconds**. The generator no longer emits it and the tests assert its absence. The cost
> is atomicity — a failed load leaves a tenant partly loaded — which is the right trade, because
> the loader verifies counts against the manifest and a partial tenant is torn down and redone.
>
> **2. Do not drop indexes to speed a load. It makes it 350x slower.** Measured in isolation on an
> empty table the secondary indexes cost 3.6x, which is a trap: during a real load, dropping them
> took `program_encounter` from **4,570 rows/s to 13**. Something fires per row and does a lookup,
> and without its index that becomes a sequential scan over a table growing under it. The same
> mistake makes a **teardown quadratic** — deleting a parent checks every child table, and without
> the child-side index that is a scan per row. A cleanup that ran in **3.4 seconds** with indexes
> present had not finished in **26 minutes** without them. This is the `filled_by_id` lesson of
> 13 Oct in a more expensive form.
>
> **3. `audit` is unbounded and nothing resets it.** 89,330,284 rows and 11 GB by 20 Oct. Every
> insert into an audited table fires `audit_table_trigger`, worth about **5x** on bulk load, and
> `teardown_org.py` deliberately never touches it — which is how it got that big. It can only be
> reset when nothing references it, i.e. between campaigns. **Write-path cost therefore drifts
> upward across a campaign**, which no finding currently accounts for, because every one of them
> measures read-dominated sync.
>
> **4. Snapshot the bed after anything expensive.** Until 20 Oct the newest snapshot predated the
> 11-hour co-tenant provisioning and `BackupRetentionPeriod` was **0**, so there was no cheap way
> back to a known-good database — which is why one bad load cost a day.
> `avni-loadtest-bed-pilot180-cotenants-20261020-1734` is the pilot at span 8.4 with all 513
> co-tenants loaded and verified. Restore it instead of rebuilding.
>
> **5. Two operational traps that wasted hours.**
> `pkill` on a psql client does **not** stop the server backend — the transaction keeps running and
> `count(*) = 0` from another session is MVCC hiding it, not a rollback; use `pg_terminate_backend`
> and check `pg_stat_activity`. And `ALTER TABLE … DISABLE TRIGGER USER` does **not** disable
> foreign-key triggers, which are internal; only `session_replication_role = replica` does.
>
> **6. Never identify generated rows by id range.** `id >= 301000000` also matches bundle rows,
> whose server-assigned ids sit near 2,100,005,408 — so a count of "generated structural rows"
> came back as 513 organisations when the true answer was zero, and sent the restore down a wrong
> path. `teardown_org.py` cuts structural tables **by provenance** precisely for this reason.
>
> **Three numbers to carry into any reset estimate for this dataset**, none of which the Block A
> figures predict:
>
> - **`ANALYZE` must run once, not per tenant.** A bare `ANALYZE` covers every table in the
>   database; 513 of them cost more than every `COPY` combined.
> - **Load cost is superlinear in what is already there.** `individual` copied at 6,024 rows/s
>   into a near-empty table and ~130 rows/s once it held 2.5 M, a 45x spread. A full reload does
>   not scale from this one by row count alone.
> - **Tearing down an organisation that has users needs an index that production lacks.**
>   `encounter.filled_by_id` and `program_encounter.filled_by_id` are unindexed FKs to `users`;
>   without them one organisation took 35 minutes, with them all eleven took 8.
>
> ### The pilot reset with the co-tenants in place, measured 14 Oct 2026
>
> The plan above said a truncate reload of the pilot "should land near 20 minutes rather than 100,
> but that is an extrapolation ... so it wants measuring the next time a reload is needed." This is
> that measurement, and **the truncate path was not available**: `reset-transactional.sql` is
> global, so it would have emptied the 513 co-tenant organisations along with the pilot. A
> per-organisation teardown of 10–19 is the only cut that leaves Block B's dataset standing.
>
> | phase | | |
> |---|---|---|
> | fetch `pilot-day-180.tar.gz` from S3 to the host | | 41 s |
> | create the two FK scaffolding indexes | | 35 s |
> | **teardown**, organisations 10–19 | 7,017,721 rows | **601 s** (10m) |
> | drop the scaffolding indexes, before the load | | 4 s |
> | **load**, ten tenants, one `ANALYZE` at the end | 6,896,792 rows | **3,272 s** (55m) |
> | `VACUUM` | | 989 s (16m) |
> | `REINDEX` of the ten tables this cycle rewrote | | 427 s (7m) |
> | **total** | | **5,377 s — 1 h 30** |
>
> Against the 1 h 40 the old per-tenant `db-load-remote.sh` path cost on 12 Oct, and against a
> 20-minute truncate that cannot be used here at all.
>
> **Teardown is the number that moved.** 7 M rows in ten minutes, where one co-tenant organisation
> took 35 minutes the day before. That is the FK index, and it is the whole reason this reset fits
> in a morning.
>
> **The superlinearity caution above needs qualifying.** It predicted a slower load because
> `individual` already held the co-tenants' 2.5 M rows. Per-tenant times say otherwise — eight
> identical 286,415-row tenants ran 338, 187, 121, 114, 75, 72, 111 and 109 seconds, *improving*
> 4.7x before settling near 2,600 rows/s. RDS had restarted that morning, so the first tenant was
> paying to fault index pages into a cold `shared_buffers`, and cache state dominated table size
> over this range. **The first tenant after an RDS restart is not a usable sample**, and an
> estimate anchored on it was out by a factor of three.
>
> **What the reset actually removed.** Teardown took 7,017,721 rows and the load returned
> 6,896,792 — a difference of **120,929**, which is the push residue from case 11 run 1, pairs A–E
> and 12c, plus 273 `sync_telemetry` rows. That gap is the point: case 6's 5 → 6 delta now reads as
> co-tenant presence rather than co-tenant presence plus five runs of accumulated writes.
>
> **Verified afterwards**, the way 8 October's reload was: 1,506,900 individuals and 5,396,156
> encounters across the pilot and organisation 3, `n_dead_tup` at zero on all four transactional
> tables, the co-tenants untouched at 2,548,061 individuals and 1,282,772 encounters, and no rows
> anywhere outside pilot, organisation 3 and the co-tenants. The `REINDEX` was included because
> this was the second delete-and-reinsert cycle and the first left B-trees ~5% larger.

**Measured, and `truncate` wins by a factor of three.**

| mechanism | clear | reload | total | |
|---|---|---|---|---|
| **truncate**, 1 Oct | **50 s** | 338 s | **388 s** (6m28s) | the clear now includes the audit cleanup |
| truncate, 30 Sep | 1 s | 334 s | 335 s (5m35s) | raw `TRUNCATE`, audit rows left to accumulate |
| teardown | 611 s | 402 s | 1,013 s (16m53s) | per-organisation; leaves 2.3M dead tuples for vacuum |
| regenerate | — | 402 s | 402 s | needs an empty target |
| template | unmeasured | — | — | needs the application's connections to `openchs` dropped |
| dump | unmeasured | — | — | needs `postgresql-client-16` on the host |

`truncate` still wins by a factor of two and a half, and the audit cleanup costs **49 s** of the
difference.

**One second to clear 2.3M rows across four tables and everything `CASCADE` reached.** The 611 s
`DELETE` did the same work by walking every row and updating all 15 indexes on `encounter` and 16
on `individual`. That is the whole gap between the two, and it is the O(1)-against-O(rows)
difference the candidate was added to test.

**The reload got faster too, which was not predicted** — 334 s against 402 s. It loads into files
that were just recreated, so there are no dead tuples to skip and no bloated indexes to descend,
where the teardown's reload was inserting into files still holding 2.3M dead rows. So the
teardown pays twice: once to delete, and again on the insert that follows.

**Deleting is layout-dependent. Loading is not.** The same 2,302,635 rows, measured four times:

| operation | layout | seconds | |
|---|---|---|---|
| `DELETE` | rows physically contiguous, from a truncate rebuild | 413 | |
| `DELETE` | rows fragmented by an earlier cycle | **621** | **+50%** |
| `\copy` | into freshly truncated files | 405 | |
| `\copy` | into files holding live index entries | 410 | +1.2% |

**A reload costs what it costs.** A delete costs whatever the table's history left behind, and it
gets worse the more the table has been cycled — which is precisely what an iteration loop does to
it. Across ~19 resets that spread alone is an hour nobody can plan around, on top of the teardown
being three times slower at its best.

> **Measured again 12 Oct 2026 on the full pilot dataset, and the slow path was taken.** A reload
> of all ten tenants ran **teardown 54 min + load 45 min = about 1h40** — `make teardown_org`
> emitting per-organisation `DELETE`, then `db-load-remote.sh` once per tenant.
>
> **That was the wrong tool for the job.** Per-organisation `DELETE` is right when *one*
> organisation needs emptying; this was all ten, which is the case `TRUNCATE` exists for. The
> figures above put truncate at 6m28s against the teardown's 16m53s on 2.3M rows, and the gap is
> almost entirely the clear — one second against 611.
>
> **The fast path is available and was not used.** `tools/reset-transactional.sql` is the
> truncate-based reset, and every tenant directory already carries a `reload.sql` (6 `\copy`
> statements, transactional rows only) beside the `load.sql` that was used (13, config included).
> Scaled from the 2.3M-row measurements it should put a full pilot reload near **20 minutes**
> rather than 100 — but that is an extrapolation and the pilot dataset has never been reset this
> way, so it wants measuring the next time a reload is needed rather than being quoted.
>
> **One difference that is not just speed.** `reset-transactional.sql` is **global**: it empties
> every transactional table, which includes organisation 3 `tanuh-load` and its 900 individuals.
> The per-organisation teardown does not. Where that data matters, the slow path is the correct
> one and the hour is the price of keeping it.
>
> For Block B this is the difference between a 20-minute reset and a 100-minute one, which across
> the resets that block needs is hours.

So `truncate` wins on more than wall clock: **its clear is one second whatever the layout**, which
is what makes a cadence predictable rather than merely short.

> The reload's own small spread has the same cause, one step removed: 334 s into freshly truncated
> files, 405–410 s into files still holding live index entries, and 402 s into files still holding
> 2.3M dead rows after a `DELETE`. Part of `truncate`'s advantage is that it hands the loader empty
> files, not the clear itself — and the `DELETE` path pays twice, once to delete and again on the
> insert that follows.

**The uuid-based teardown was validated end to end here**, which is the first time it has run
against real data. Both tenants came back with 227 addresses (212 generated + 15 the bundle
created), 210 catchments (207 + 3), 542 users (541 + 1) and 13 groups (1 + 12): it removed exactly
the generated rows and left every bundle row in place. That is what the provenance cut replaced the
id-range cut to achieve, and it is now measured rather than reasoned about.

**Restoring after it needs a transactional-only script.** `load.sql` copies 11 tables and 7 of them
are structural; a transactional `TRUNCATE` leaves those rows in place, so reloading the whole
script collides on all seven. The benchmark greps the four it needs, which is fine for a benchmark
and a trap for anyone restoring by hand — "just reload" is the wrong instinct and fails seven
statements in.

**Its cost is scope, and the first run demonstrated it.** `TRUNCATE` cannot distinguish tenants, so
it emptied organisations 3 and 11 as well and only state-1 was reloaded. A reset built on it has to
reload every dataset the database holds, which is the right shape for a per-run restore and the
wrong one for the iteration loop — where `teardown_org.py` still earns its place by emptying one
organisation without touching its neighbours.

**What it saves across the exercise.** `TRUNCATE`'s clear is O(1) so it stays at a second whatever
the dataset; the teardown's `DELETE` scales with rows. At ten-tenant scale that is a 51-minute
reset against a 20-minute one, and **across ~19 resets it is about 9.7 hours** — most of two
working days, and more than the difference between any other pair on this list.

**Decided, 30 Sep 2026: `truncate` + `reload.sql`.** Clear the transactional tables across the
database, then reload every dataset it holds. 335 s for a two-tenant day-180 tenant, ~20 min
projected at ten-tenant scale, no storage headroom, no artefact, and no vacuum debt.

`dump` is not worth measuring — it rebuilds every index with GIN worst of all, so it cannot
approach 5m35s. `template` might: a file-level page copy needs no reload at all, so perhaps 60 s
against 335. **It is an optimisation, not a blocker**, and it stays unmeasured for now — it needs
the application's connections to `openchs` dropped, and whether the 2x storage headroom exists is
a provisioning question for avni-infra#112. Phase 4 can be planned on 20 minutes a reset; if
`template` is arranged later it shortens the cadence without changing anything else.

**What the mechanism consists of**, so it is not reassembled from this prose later. It lives in
`tools/reset-transactional.sql`, one file, because the benchmark has to measure what a run
performs and two copies of a truncate list drift:

1. Capture the `audit` ids held by every table the truncate is about to empty — the four, plus
   the `CASCADE` closure, read from `pg_constraint` rather than listed.
2. `TRUNCATE individual, encounter, program_enrolment, program_encounter CASCADE` — one second,
   and `CASCADE` clears the run artefacts that reference them: sync telemetry, approval statuses,
   comments, checklists.
3. Delete those captured `audit` rows, then `VACUUM` the table.
4. `reload.sql` per dataset the database holds — emitted beside `load.sql`, transactional tables
   only, because the structural rows survive the truncate and reloading them collides.
5. Sequences are not restarted. They sit above the dataset and each reload's own `setval` keeps
   them there; winding them back would hand out ids the application has already used.

### Why `audit` is cleared by DELETE and never by TRUNCATE

**Added 1 Oct 2026.** A BEFORE INSERT trigger on 63 tables writes one `audit` row per inserted
row, so a 2.3M-row load creates 2.3M audit rows, the truncate orphans every one of them, and the
next cycle adds 2.3M more. Left alone that is the only part of the reset that grows without bound
— roughly 200 MB a cycle, reclaimed by nothing.

**It still cannot go in the `TRUNCATE` list, and the gap between those two facts is the whole
point.** 42 foreign keys reference `audit(id)`, and they are not the transactional tables: they
are `concept`, `form`, `form_element`, `form_mapping`, `subject_type`, `address_level`,
`organisation_config` and the rest of the metadata. `TRUNCATE audit CASCADE` empties all of them.
`reload.sql` carries transactional rows only, so recovery would mean provisioning the organisation
again from its bundle — and the dangerous command is two words longer than the safe one.

**The delete suppresses referential integrity, and the reason is arithmetic rather than
convenience.** Every one of those 42 constraints is `NO ACTION` with no index on the referencing
`audit_id` column, so deleting a referenced row costs one sequential scan per constraint per row.
At 2.3M rows that is not slow, it is infeasible. `SET LOCAL session_replication_role = replica`
suppresses the checks, and it is safe for a specific reason rather than a general one: the rows
deleted are exactly those whose owning tables the `TRUNCATE` on the previous line has just
emptied, so by construction nothing references them. That argument holds only while the capture
set is the truncate's own cascade closure, which is why the closure is computed from the
catalogue. `SET LOCAL` confines it to the transaction, so the reload that follows still fires the
trigger.

**A guard, because `CASCADE`'s reach is the thing that can change under this silently.** The
script refuses if the closure ever includes a table the reload cannot restore — `users`,
`concept`, `address_level`, `audit` itself. Today none of them reference the four. A foreign key
added next release would turn a reset into a re-provisioning, and the first sign would be a
scenario failing to authenticate.

**It leaves the table at a steady size rather than a small one.** The delete leaves dead tuples
and the `VACUUM` marks them reusable, so the next cycle's inserts refill them instead of extending
the file. `VACUUM FULL` would reclaim the space properly and take an `ACCESS EXCLUSIVE` lock to
hand back space the next reload immediately asks for again.

### Measured, 1 Oct 2026: the audit cleanup costs 49 seconds

The reasoning said seconds rather than the `DELETE` benchmark's 611 s, because the capture is a
sequential scan of four tables and the delete touches one narrow table with one index. **50 s
against the raw truncate's 1 s**, so the reasoning held and the number is now a number.

| | per reset | Phase 4, 5 resets | had it stayed 19 resets |
|---|---|---|---|
| raw `TRUNCATE` + reload | 335 s | — | — |
| with the audit cleanup | 388 s (+16%) | **+4 min across the phase** | +16 min |

So it is affordable, and the block ordering above makes it more so — the two changes were decided
independently and compound in the same direction.

**The full two-tenant cycle is 764 s, 12m44s**: 50 s reset, 338 s for the first dataset, 376 s for
the second. That is the figure Phase 4's cadence should be planned on at this scale, not the 388 s
the benchmark reports, because the benchmark reloads one dataset directory and the reset empties
the whole database.

**The reload was faithful**, which is the part worth checking rather than assuming:

| org | | individuals | encounters | addresses | catchments | users | groups |
|---|---|---|---|---|---|---|---|
| 10 | state-1 | 501,000 | 1,799,926 | 227 | 210 | 542 | 13 |
| 11 | state-2 | 501,000 | 1,799,926 | 227 | 210 | 542 | 13 |
| 3 | the customer's | 0 | 0 | 21 | 7 | 11 | 13 |
| 1, 9 | platform, fixtures | 0 | 0 | 16 | 4 | 2 | 14 |

Day 180 specifies 500 workers x 20 encounters x 180 days = 1,800,000, so both state tenants came
back whole.

**The other organisations show the mechanism working exactly as designed, and that is the useful
part of this table.** They lost their transactional rows and kept every structural one: the
customer's organisation still holds its 21 addresses, 7 catchments, 11 users and 13 groups. That is
`TRUNCATE` on the four transactional tables and nothing else, which is why `reload.sql` carries
transactional rows only — reloading the full `load.sql` would now collide on all seven structural
tables. Recovering the customer's organisation is a `reload.sql` away, not a re-provisioning.

> **On the `audit` figure the run reported as "one row".** It cannot be a post-reload row count,
> and the confirmed counts above are what settle it rather than an assumption: `audit.id` is the
> target of a NOT NULL `audit_id` on every one of these tables, and only the trigger sets it, so a
> reload of 4.6M rows either wrote 4.6M audit rows or failed on the constraint. It did not fail —
> the counts are exact. So `audit` holds at least 4.6M rows and the figure is the count query
> reporting one row of output. The cleanup is at the steady state it was built for.
>
> **What the counts also rule out** is the way this could have gone badly. The delete suppresses
> referential integrity, so an over-wide capture would have removed referenced rows in silence.
> Three things say it did not: the `survives` guard did not fire, so the CASCADE closure contained
> no protected table; every organisation kept its structural rows, so the cascade did not reach
> `address_level`, `catchment`, `users` or `groups`; and those tables' audit rows were therefore
> never captured.
>
> **One check is still outstanding** and is worth doing once rather than reasoning about again: a
> dangling-reference count against `concept`, `form` and `form_element`, which are metadata the
> truncate never touches and whose audit rows the reload does not recreate. Deferred 1 Oct 2026
> with the environment down. The reasoning above makes a problem unlikely rather than impossible,
> and the difference matters because the failure would be invisible to reads.

`teardown_org.py` is not this. It stays the iteration-phase reset, where emptying one organisation
without touching its neighbours is worth 611 s.

> **Do not skip the snapshot in favour of deleting rows between runs.** `DELETE` leaves dead tuples,
> `VACUUM` does not shrink indexes, and runs progressively stop resembling each other. Determinism
> matters more than absolute realism here, because the primary comparison is run against run.

> **That applies to measured runs, not to the days before them.** While the generator is still
> changing, a reset happens many times a day and a restore is far too slow a loop — so
> `make teardown_org ORG=n ID_BASE=b` emits SQL that empties an organisation in place. Dead tuples
> are irrelevant when nothing is being compared yet. Switch to G4's restore at F7, and do not
> switch back. **Which mechanism that is remains open** — `CREATE DATABASE … TEMPLATE`, a
> `pg_restore`, or regenerating — and RDS snapshot restore is not among the per-run candidates:
> it cannot restore in place, and lazy loading leaves a restored instance with far worse I/O until
> every block has faulted in. See #11, § G4.

**No run is read-only**, which is the part that catches people out. Every sync ends with
`POST /syncTelemetry`, so a pull-only scenario still leaves a row per user per sync; a push
scenario writes subjects and encounters with server-assigned ids; and every insert fires the
`audit` trigger. Two things no reset here reaches: media uploaded by a push run lives in S3 and
survives any database-side restore, and `audit` grows regardless.

---

## Phase 3 — Calibration (Day 11). **The gate.**

**F7. Nothing before this produces evidence, and nothing after it is trustworthy until it passes.**

Run a simulated user against the same per-entity record counts as a real production sync, and check
the **marginal cost of one more record** matches production's — a measured **5.2 ms/record**.
Marginal cost rather than total duration against a band: a band comparison passed a 15,732-record
sync by grading it against band 1, which covers under 5,000.

**Done, 1 Oct 2026: 5.20 ms/record, 1.00x, zero KO.** It took three attempts and two false passes,
and both false passes are worth knowing about because neither showed up in the run.

- **The band bug** above — the gate itself was wrong, not the simulation.
- **A key mismatch.** `StorageProfiles` was keyed lowercase while the simulation looks up entity
  names, so every lookup missed and fell through to the uniform `3 × 2.78 = 8.34` the profiles
  existed to replace. It scored 8.80 against the then-anchor of 8.85 and passed. Caught by dividing
  124 s by 15,732 records by hand. The startup banner now prints each pulled entity's resolved rate
  and whether it is measured or a tier.

**The anchor itself moved, from a fitted 8.85 to a measured 5.2.** 8.85 was a regression through
total sync duration and fit neither of Q5's bands — 58.4 s predicted against 14.1 observed, 434.5
against 1,076. The replacement was measured from production's `AuthenticationFilter` logs: 11 days,
1.88M requests, the gap between a client's consecutive page requests with server time and a 307 ms
network base netted out, counting only confirmed full pages. See `tools/inter_request_gap.py`.
Client cost varies by **organisation**, not day, which is why there are two storage profiles.

> If it cannot be made to pass, stop. A simulation that does not reproduce a known sync is not an
> instrument, and every number after it is decoration.

---

## Phase 4 — Execution

Order is chosen so each case is interpretable when it runs, not so the calendar looks full. **Record
every run's metadata; two runs that differ in more than one property answer nothing.**

### Run in blocks, and reset between blocks rather than between runs

**Revised 1 Oct 2026.** The first ordering reset before every run — ~19 resets at ~21 minutes, about
seven hours. Most of them were not buying anything.

**A reset exists to remove push residue, and push residue is small.** Every case except 1 pushes, at
about **27 rows a sync** on the customer profile (`Individual` 0.60 x 3.3, `ProgramEnrolment`
0.33 x 4.0, `ProgramEncounter` 1.0 x 24.0). Against day 180's 6,891,600 rows:

| case | syncs collected | rows pushed | share of the dataset |
|---|---|---|---|
| 2 | 167 | ~4,600 | 0.07% |
| 4 | 187 | ~5,100 | 0.07% |
| 5 | 282 | ~7,700 | 0.11% |
| 10, soak | 562 | ~15,300 | 0.22% |
| 11, 12, 13 | 1,692 each | ~46,200 each | 0.67% |

Cases 2, 3, 4, 5, 11 and 10 back to back come to **about 80,000 rows — 1.2%**, which is below the
run-to-run variance this document already attributes to autovacuum and to the reload's own spread.

**So the reset is not mainly protecting against volume. It is protecting three specific things**,
and only these:

1. **The delta comparisons.** 5 -> 6 and 6 -> 7 are read as differences, so the customer's data has
   to be identical across them. This is the binding constraint, not the 1.2%.
2. **Case 8**, where dataset size *is* the independent variable, so residue contaminates the thing
   being measured.
3. **Case 9**, which runs until something breaks and leaves unknown state behind.

Everything else can be blocked.

### The ordering this replaces forced a co-tenant unload

The first ordering ran case 7 and then **11, 12, 13** after it. Case 11 is in the
*separate* hosting group, so it needs the co-tenants **gone**, and 12 and 13 need them back. That is
an unload of 513 organisations — a `DELETE` teardown of a dataset holding 3.13M encounters — and a
reload, hidden inside one day of the calendar, to serve a single one-hour run.

**Moving case 11 next to case 5, before the co-tenants are ever loaded, makes their presence a
one-way door.** Load once, never unload. That is the single largest saving here and it costs
nothing.

### The blocks

| Block | Reset | Runs, in order | Why this grouping |
|---|---|---|---|
| **A — separate, day 180** | one, at the front | **1, 14, 2, 3, 4, 5, 11, 10, 9** | Case 1 pushes nothing, so it is free at either end. 3 before 4 so per-device cost is known before the mix. 11 here rather than after 7, so co-tenants are never unloaded. 10 overnight. **9 last, because it breaks things** and Block B's reset cleans up after it |
| **B — co-tenants** | one, plus the co-tenant load | **6, 7, 12, 13** | The reset before 6 restores the customer's tenants to exactly case 5's starting state, which is what makes the 5 -> 6 delta mean anything. 6 -> 7 then carries ~7,700 rows of drift, 0.11% |
| **C — growth** | three dataset swaps | **8** at day 60, 120, 365 | Day 180 reuses case 4's result. These are different datasets, so the loads are not avoidable |

**Five resets for sixteen runs, against sixteen.** *(Resolved 9 Oct 2026 — this stands, with three
exceptions; see [Resolved 9 Oct 2026](#resolved-9-oct-2026-keep-the-blocks-with-three-exceptions)
below. A reset was measured at 1h40, and drift at ~0.5% per run.)* With Phase 5's four to six re-measurements, which
stay one-per-run because re-measuring after a fix is the whole point, that is about **ten against
nineteen — roughly 3.2 hours** — plus the co-tenant unload and reload that no longer happens.

### What running in blocks costs

**`CACHE_POLICY` stops being true, and it is recorded per run.** G2 records `warm-from-reload`.
Inside a block every run after the first is `warm-from-previous-run`, which is a different thing:
warmed by a read-mostly workload against the pages a sync touches, rather than by a bulk write
through every page in the table. `archiveRun` needs the second value or it will record something
false — which is worse than recording nothing.

**Position within a block becomes a confounder.** Later runs sit on a more-bloated table, with
autovacuum having fired at some point nobody chose. Compare adjacent positions, not distant ones,
and treat a block boundary as the only place a clean comparison is guaranteed.

**Record each run's actual starting row counts.** With a reset before every run they were knowable
from the dataset; in a block they are not. Measuring the drift is the honest way to run this —
inferring it from the table above is not.

### Resolved 9 Oct 2026: keep the blocks, with three exceptions

**The validating measurement failed, and the strategy stands anyway.** Five runs could not resolve
drift — see [`findings-case11-pair.md`](findings-case11-pair.md) — but they failed because the
instrument cannot see a 0.5% signal against a 3.3x larger artifact, **not because drift turned out
to be large.** Those warrant different responses, and only the second would justify abandoning this.

**The residue volume is known exactly, even though the pair failed.** Two independent measurements
a day apart: **25.72 rows/sync** (8 Oct, 1,682 syncs) and **25.48** (9 Oct, 550 syncs).

**The effect is bounded at about 0.5% per run.** Taken from the all-positive subsets of the paired
data — the only part that behaves as residue must, since residue cannot subtract: **+0.51%** (A/B)
and **+0.29%** (C/D). The arithmetic agrees: 25.5 rows/sync against ~15,000 records/sync, amplified
by catchment sharing, lands in the same place.

**0.5% is an order of magnitude below what these cases exist to detect** — the differences that
matter are 2x to 10x, and 224x between a saturated and an unsaturated run. It changes no conclusion
any case reaches.

**And a reset costs 1h40, now measured rather than estimated**: teardown 53 min, load 45 min, on
9 Oct. Eleven extra resets is about **18 hours**, two and a half working days, to protect against
something smaller than the noise in most of the figures above.

**The exceptions, where 0.5% per run stops being negligible:**

1. **Where a small delta is the measurement.** Block B's reset before case 6 already exists for
   this reason. The rule: **any finding that turns on a difference under ~5% gets its own reset.**
2. **Before and after case 9.** It breaks things by design, and must not precede case 10.
   Block B's reset already cleans up after it.
3. **When cumulative drift passes ~2%** — four runs. Block A's remaining exposure is small (case 10
   is ~564 syncs, then 9), and Block C reloads anyway, but a long future block should reset at its
   midpoint rather than ride nine runs of accumulation.

**What replaces the validating run:** measure residue after every pushing run. It is one query and
a minute, two runs already agree to 1%, and it turns "we assume drift is small" into a recorded
figure. **Do not retry the paired validation until `sync-durations.csv` carries per-entity record
counts per user** — without that, a third attempt uses the same instrument and produces the same
unreadable result.

### The one measurement that would validate it

Run **case 11 twice, back to back, with no reset**. One hour each. If per-sync record counts and p50
duration agree within noise, the block strategy holds for every adjacency in it, because 11 is the
heaviest pusher of the set at ~46,200 rows. **Two hours to de-risk the three, and it is the only
part of this that is an assumption rather than arithmetic.**

> **Run at reduced load, and that bounds what it licenses (8 Oct 2026).** Case 11 at the full 1,682
> saturated the server, which is not a baseline anything can be read against — a second run agreeing
> with a saturated first would say more about the ceiling than about the residue. So the pair runs
> at reduced load from a dataset reloaded to its pre-run-1 state, which is the right call: both
> halves start from the same place, which is the whole point.
>
> **What it then answers is the adjacency at that load.** If the residue acts through planner
> statistics or table bloat, its effect scales with how much the first run wrote — so a reduced-load
> pair agreeing does not license the adjacency between two *saturated* runs, which is the case the
> block ordering actually exposes the suite to. State the load with the result; do not let
> "the block strategy holds" be read without it.
>
> **The comparison is per user, not per run.** `compare-pair.py` joins the two runs on `userName`,
> which the proportionally ordered feeder makes possible: both runs draw the same prefix, so the
> same cohort syncs in each. Run-level means would average away a shift that moved some users and
> not others, which is the shape a residue effect would take.

> **Thresholds pinned 8 Oct 2026, before the runs, so the bar is not drawn to fit the result.**
> Run 1 of the pair saturated and is not run A — 12.6 syncs/min against 28 demanded, p95 42 s,
> timeouts at the 60 s client ceiling — but it did measure the residue this test turns on.
>
> **Noise floor, 0.065%, measured.** The void case 4 run and case 2 covered the same effective
> workload on separate reloads, days apart: **10,838 vs 10,831 records per sync**, mean duration
> 60.8 s against 60.8 s. It is the only true replication pair in the run log.
>
> **Effect ceiling, 0.238%, arithmetic.** Case 11 pushes **25.72 rows per sync** — 43,257 rows over
> 1,682 syncs, measured 8 Oct against the 1,506,900 / 5,396,156 baseline, two ways that agreed to
> the row. Had the estimate of ~46,200 above been wrong this test would have been mis-sized; it was
> within 6.4%. If run B re-pulled *every* row run A wrote, that is +25.72 on a ~10,831 baseline.
>
> **So the effect is only ~3.7x the noise, and the threshold has to sit between them.** A round
> +-1% band would pass even with the full effect present, and would "validate" the block strategy
> by being too blunt to detect its failure.
>
> **Records per sync decides it.** One-sided — residue can only add.
>
> | (B-A)/A | verdict |
> |---|---|
> | <= +0.10% | **pass** — drift under half the ceiling, the block strategy holds |
> | +0.10% to +0.30% | ambiguous — consistent with residue being pulled |
> | > +0.30% | **fail** — above the arithmetic ceiling, so the cause is not residue |
>
> **p50 duration cannot settle this.** At n~600 with case 5's spread — p50 60.6 s, mean 72.9,
> p95 182.2 — the median carries a standard error near 5%, so the difference carries ~7% and a
> 2-SE band is **+-15%**, wider than any residue effect could be. It is a gross-regression check,
> not evidence. A p50 that looks close must not stand in for the record-count test.
>
> **Protocol.** Reload `pilot-day-180` before run A — `SYNC_MODE=realistic` reads by
> `lastSyncTime`, and 8 Oct's residue sits compressed into a 1h45 window, a shape the modelled
> distribution does not contain. **No reset between A and B**; that is the experiment. Warm up
> first, or run A is cold and run B warm and the cache artifact swamps the signal. Rate ~500-600
> syncs/hour, not 1,682. `CACHE_POLICY` then records `warm-from-reload` for A and
> `warm-from-previous-run` for B, which is the distinction drawn above.
>
> **Compare on the common prefix.** If the runs complete different sync counts, truncate both to
> `min(nA, nB)` from `sync-durations.csv` first. The feeder is well interleaved — the first 600 of
> `case5-users-pilot.csv`'s 1,682 rows are 89.7% field worker against 89.5% overall, org-10 33.3%
> against 33.4% — so a prefix is representative and case 4's trap does not apply here.

> **Corrected 9 Oct 2026, before the runs, on two things found while setting them up.**
>
> **The gap is deterministic, so the comparison should be paired.** `realisticLoadedSince` derives
> the window from `(userName + "|" + entityName).hashCode()` — `AvniSyncSimulation.java:1665`,
> "derived from the user and entity name rather than drawn at random, so a run reproduces". Run A
> and run B therefore hand the *same* user the *same* window. `sync-durations.csv` is
> `userName,records,durationMs,pausedMs,serverMs,profile`, so the two runs join on `userName` and
> **under the null each user's record count is identical, not merely close**. Any non-zero paired
> difference is signal. That is a far sharper instrument than comparing means, and the mean bands
> below are the fallback for users that do not pair.
>
> One residual: `loadedSince` is *now minus* the hashed gap, so run B's window slides forward by
> the hour between the runs. Irrelevant for gaps of days or months, material for the few drawn in
> hours — those users lose an hour at the old end and gain the hour that contains run A's pushes.
>
> **The 0.238% ceiling was too low, because it assumed each pushed row is pulled once.** It is not:
> `pilot-day-180` puts **3 field workers per village** and **8.4 workers per supervisor**, so a row
> pushed into a village is re-pulled by that village's other field workers and by the supervisor
> above it. At 550 of 1,682 feeder rows — ~492 field workers and ~58 supervisors — the average
> re-pull multiplier is about **1.35**, giving 25.72 x 1.35 = ~34.7 records on a ~10,831 baseline,
> an effect ceiling of **~0.32%**.
>
> **Revised bands: pass at <= +0.10%, ambiguous +0.10% to +0.40%, investigate above +0.40%.** The
> old "fail above +0.30%" would have put a genuine full-residue result at 0.32% on the wrong side
> of the line and called the cause something other than residue.

> **Outcome, 9 Oct 2026: five runs, no answer, and the bands above are moot.** Written up in
> [`findings-case11-pair.md`](findings-case11-pair.md). The pairs returned +2.69%, +8.65% and
> +1.63% — all far above any ceiling — but none of it is drift. Residue can only add, and 57 users
> pulled *fewer* records; the effect is flat across organisations that pushed eight times different
> volumes; and it appears in a `PUSH=off` control that wrote nothing but `sync_telemetry`, where 38
> of 416 users reading byte-identical frozen data still differed by >1,000 records.
>
> **The harness is not reproducible, by design.** `drawFullSync` uses `ThreadLocalRandom` and says
> so: *"a run is not bit-reproducible … expect the count to vary run to run."* Recorded full syncs
> were 7, 4, 8, 2 and 3 across the five runs. That accounts for 5 of 52 steppers. **The other 47
> are unexplained**: the `syncStatusBody` empty-`entityTypeUuid` fallback was refuted (its warning
> appears zero times and bootstrap calls equal sync counts in every run), and the traced user is
> `fullSync=false` in all five runs while swinging 10,962 to 14,186.
>
> **A paired comparison assumes a reproducibility this harness does not offer.** The artifact is
> ~284 records/sync against a residue signal of ~85. Before attempting this again: set
> `-DFULL_SYNC_PERCENT=0`, and prove or kill the bootstrap fallback. Re-running the pair at another
> rate will not help.
>
> **The server was cleared.** Sequential and concurrent replays of both the paged pull and
> `syncDetails` returned identical answers every time, including 40 users across two concurrent
> passes with zero disagreements.

> **Considered and rejected: making case 8's growth datasets nest**, so day 60 could be appended to
> rather than reloaded. It does not work as the generator stands. `band_width(tenant, days)` scales
> with `days`, so day 60 and day 120 allocate different id bands and neither is a prefix of the
> other. It could be made to work by sizing every band for day 365 — about 22M ids, comfortably
> inside int4 — but it also needs rows emitted in day order so the smaller sets are genuine
> prefixes. That is a generator change with real risk to save roughly an hour.

> **Revised 7 Oct 2026, after cases 1, 2, 3, 14 and 4.** Five runs in, two things are settled that
> this schedule was written without.
>
> **Only case 1 has ever loaded the server, and it did it by concentration alone.** Same 100 users
> and same 4,300 requests every time; only the arrival window moved:
>
> | window | rps | req in flight | p95 |
> |---|---|---|---|
> | 900 s | 4.8 | 0.2 | 200 ms |
> | 180 s | 22.8 | 1.0 | 196 ms |
> | 90 s | 43 | 3.2 | 376 ms |
> | 60 s | 52 | 22 | 2,242 ms |
> | 15 s | 57 | 71 | 6,768 ms |
>
> Throughput flattens near **50 rps** while p95 rises 34x. Every steady case sits two orders of
> magnitude below that — case 2 at 0.2 rps, case 3 at 0.32, case 14 at 0.54, all under 340 ms p95
> with the app server at ~2.1% CPU. **And the unrun cases do not get close**: at measured
> requests-per-sync, case 5 projects to ~0.7 rps, case 11 to ~8.9, and case 13 — the heaviest in
> the plan — to ~13, about a quarter of a ceiling that 100 users crossed in a 60-second burst.
>
> **Four changes follow.**
>
> **1. Case 9 moves up, and the ceiling it looks for is not the one case 1 found.** Case 1 pulls
> config only; the *data-path* ceiling is unmeasured, and case 9 is the only case that can find it.
> It was scheduled last so the unstressed shape would be known first — cases 2, 3, 4 and 14 have
> now established it, so that condition is met and the reason to keep it last is gone.
>
> **2. A cluster tighter than an hour.** *(Run 9 Oct 2026 — see
> [`findings-case11-burst.md`](findings-case11-burst.md). It does not reach 35 rps: the data path
> saturates on app-server CPU at 18.5 rps, with the app at 99.1% and RDS at 24–32%. Saturated
> throughput is **~775 syncs/hour**, reproducible across injection shapes — 13.3 syncs/min at
> 1,600/h over 15 min against 12.6 at 1,682/h over 60 min. The projection below assumed the
> demanded arrival rate is achieved; above 775/hour it is not.)* Cases 11–13 compress a day into an hour and still only
> reach 9–13 rps. The real analogue of case 1's burst — a shift ending, signal returning, a
> training cohort — concentrates the cohort into minutes. **Case 11 at a 15-minute window** lands
> near 35 rps, which is where the interesting behaviour starts, and costs 15 minutes.
>
> **3. Case 5 need not run four hours to say nothing.** Two hours is already more than enough to
> establish a rate that three runs have independently put at idle. Case 10 keeps its twelve hours:
> its subject is bloat and autovacuum drift over time, not load.
>
> **4. Stop quoting total sync duration as a server result until D7 lands.** 93–94% of every
> headline figure — case 14's 80 s, case 3's 223 s — is `pausedMs`, modelled from records pulled
> and never measured on a device. Report `serverMs` and record counts as findings and label the
> totals as modelled. **The run that fixes this is D7, step 6 below.**

### The sequence

**Ordered, not dated.** This was a day-by-day schedule and it had stopped describing what happens:
runs slipped, case 4 was re-run, case 11 overtook cases 9 and 10, and every date in it had to be
re-read as "whenever this actually goes". What matters is what must precede what. The order below
is binding; the calendar is not.

| # | Block | Run | State |
|---|---|---|---|
| 1 | A | **1** — training cohort, 30 min, swept across arrival windows 900 s to 15 s | done, 10 runs. [`findings-case1.md`](findings-case1.md) |
| 2 | A | **14** — full sync, 90 min | done. [`findings-case14.md`](findings-case14.md) |
| 3 | A | **2** — field workers, 4 h | done. [`findings-case2.md`](findings-case2.md) |
| 4 | A | **3** — supervisors, 2 h driven | done. [`findings-case3.md`](findings-case3.md) |
| 5 | A | **4** — combined, 4 h | done; the first attempt sampled one role and is not a measurement. [`findings-case4.md`](findings-case4.md) |
| 6 | — | **D7** — client storage, device, Realm and SQLite | done. [`findings-d7.md`](findings-d7.md) |
| 7 | A | **5** — ten tenants, 2 h | done. **No findings document**: case 5 is the baseline cases 6, 12 and 13 are read against, and it is written up in theirs. The run itself is [`2026-10-08T12-04-15Z-case5-d484f18`](run-log-detail.md#2026-10-08t12-04-15z-case5-d484f18) |
| 8 | A | **11** — clustered, 1 h | done at the full 1,682; saturated. **No findings document** — the run is [`2026-10-08T14-05-56Z-case11-run1-d484f18`](run-log-detail.md#2026-10-08t14-05-56z-case11-run1-d484f18) |
| 9 | A | **11 twice, back to back, no reset** — the block-strategy validation | **inconclusive, 9 Oct.** Five runs at 550/h — A/B, C/D and a `PUSH=off` control — could not resolve drift, because the harness is not reproducible. The block strategy was settled another way: see *Resolved 9 Oct 2026* above. [`findings-case11-pair.md`](findings-case11-pair.md) |
| 10 | A | **10** — soak, 12 h, overnight | **done 2026-10-10.** 561 syncs, 50,098 requests, **0 failed**, p95 290 ms. **No measurable degradation over twelve hours** once normalised per record — the trend is noise, not drift. No reload: the finding is hour 1 against hour 12 of one run. Confirmed at the endpoint and in the JVM, 14 Oct. [`findings-case10.md`](findings-case10.md) |
| 11 | A | **11 at a 15-minute window**, 15 min | **done 9 Oct, ahead of 10.** Scaled to 400 users rather than the full 1,682, so the backlog is 400 syncs. Reaches 18.5 rps, not the ~35 predicted — **saturates on app CPU**. [`findings-case11-burst.md`](findings-case11-burst.md) |
| 12a | A | **9** — stress ramp on the data path, ten tenants, realistic mix | **done 2026-10-12.** 200→3,000/h over 45 min, `PUSH=off`. **App CPU, and now it is evidence**: pinned 99% for thirty minutes while RDS sat at 16–25% with `ReadLatency` flat. Knee ~1,160–1,290 syncs/h, and **not** GC. [`findings-case9-12a.md`](findings-case9-12a.md) |
| 12b | A | **9 with `SYNC_MODE=full`** — same ramp, every sync a full pull | **done 2026-10-12, twice.** **The database cannot be made to bind** even when every sync pulls everything. **The ceiling is records per hour** — ~12.8 M without push — holding across two sync modes and 18–435 devices in flight. [`findings-case9-12b.md`](findings-case9-12b.md) |
| 12c | A | **9 with push on** — same ramp, write path included | **done 2026-10-12.** 12a's ramp with push on. **The write path does not bind either**, and it failed *less* than 12a — push cuts the same work into smaller requests. Ceiling confirmed at a sixth run: **12.85 Mrec/h without push, 11.32 with**. [`findings-case9-12c.md`](findings-case9-12c.md) |
| 13 | B | **Provision 513 organisations**, import each one's archetype bundle, re-dump `refs.sql`, generate and load the co-tenant data | **done 2026-10-13.** 513 organisations at ids 24–566, **6,253,693 rows loaded and verified** against every manifest, 0 failed. **The `co-NNN` → id map must be read from [`co-tenant-provisioning.tsv`](co-tenant-provisioning.tsv) and never derived** — the ids are not contiguous. Provisioning ~11 h; a clean load is ~40 min, and the day cost more only through rework. Timings under [the archetype measurements](#before-the-ten-tenant-cases-can-be-generated) |
| 14 | B | **6** — co-tenants present, 2 h | **done 2026-10-14.** Case 5's run unchanged, with 513 co-tenants present and syncing nothing. 280 syncs, **0 failed**. **Presence costs 0.3% per record**, with sync duration unchanged. [`findings-case6.md`](findings-case6.md) |
| 15 | B | **7** — co-tenants syncing, 2 h | **done 2026-10-14.** Case 6 plus `CO_TENANTS=on` at 792/h, production's busiest recorded hour. 61,683 requests, **0 failed**. **Activity costs 18% per record where presence cost 0.3%** — CPU on both tiers with nothing saturated, so headroom will not remove it. [`findings-case7.md`](findings-case7.md) |
| 16 | B | **12** and **13** — clustered, 1 h each | **12 done 2026-10-15; 13 is row 16b.** Case 6 compressed: **6.59 devices in flight against 0.55**, co-tenants present and idle. 31,409 requests, **0 failed**. **The same work twelve times denser costs 170% more server time per record** — contention, not extra work — and takes app CPU to 81%. [`findings-case12.md`](findings-case12.md) | 
| 16b | B | **13** — clustered, co-tenants syncing, 1 h | **done 2026-10-15.** Case 12 plus `CO_TENANTS=on`, **9.7 in flight**, three times production's peak. **The first run to break** — 1.22% failed, almost all clients giving up at 60 s. **Asking 47% more removed 38% of the throughput**, which resolves case 12's ceiling question: **12.85 Mrec/h is a saturated server, not a maximum**. [`findings-case13.md`](findings-case13.md) |
| 17 | C | **8** — growth, 2 h each at day 60, 120 and 365 | **done 2026-10-16 — no knee at six times the history.** 94 syncs at each point, **0 failed** throughout. **Records per sync tracks dataset depth one-for-one** and **per-record server cost falls then flattens**, 0.386 → 0.347 → 0.326 ms. **What grows is the device's wait**: a median sync goes 21.4 s → 122.5 s, linear in depth. The server is not the constraint anywhere on this curve. [`findings-case8.md`](findings-case8.md) |
| 18 | A′ | Reload `pilot-day-180-span20`, split with `--variant span20`, re-run **3**, **4**, **5** | **done 2026-10-19 — the span scales the work and barely touches the cost of it.** All three runs on one load with no reset between them, **zero failures in 13,609 requests**. **Records per sync track the catchment three times independently** — 2.33×, 2.33×, 2.44× against a 2.38× ratio — while **field workers, whom the span does not touch, hold at 1.00×** and serve as the control. Supervisors cost **about +5% more per record**, and the control says that figure carries 1–2 points of run-to-run noise. A median supervisor sync goes **3.0 → 7.1 minutes**, 94% of it the modelled client pause. **Cases 4 and 5 look like nothing happened until split by role**, and their p95 *falls* 182 s → 80 s purely because supervisors drop from a tenth of the cohort to a twentieth — composition, not speed. No knee, and nothing that justifies widening the sweep. [`findings-span20.md`](findings-span20.md) |
| 19 | — | **Vertical scale sweep** — case 13 at 2 vCPU and 4 vCPU | **done 2026-10-21 — more vCPU is the relief, and it is now measured rather than inferred.** The run that broke at `m6g.large` is uneventful at `m6g.xlarge`: **467 failures → 0**, p95 **56,714 ms → 434 ms**, under-800 ms **5.15% → 99.6%**, app CPU **99% → 54%**. Only the instance type changed; heap stayed pinned at 5120m and the pool at 100. **The constraint moved toward the database** — RDS 33% → 41%, the gap between tiers narrowing from ~65 points to ~13 — which makes 8 vCPU the interesting next point and the 4 vCPU injector a thing to watch. **Timeslices, 22 Oct:** the saturation was **555 s of garbage collection against 18** (old-generation collections only on 2 vCPU; heap 2,778 MB mean, 5,096 peak) — a quarter to a half of the 4.19 → 3.13 gap — and **98% of the control's request time was the authentication filter's own time** (exclusive; 14% at 4 vCPU), with 48,865 monitor-blocked thread events against 571. The cliff has a place: the filter, where every request takes a pooled connection before any controller runs. [`findings-vertical-scale.md`](findings-vertical-scale.md) |
| 20 | — | **Clustered — co-tenant load, media push** — 1,500 workers at 8 files per encounter, co-tenants at 792/h, on 4 vCPU; the scenario [`scenario-clustered-media-push.md`](scenario-clustered-media-push.md) sized in advance | **done 2026-10-21 — it holds, and the server is 2% of it.** **415,082 requests, 0 failed**, p95 503 ms, 98.05% under 800 ms. Media files per customer sync **p50 160, exactly the 20 × 8 predicted**, mean 197, max 1,184. **A median customer sync is 12.5 minutes, of which 10.7 is the device uploading** — 88.9% of sync time is upload wait, 8.8% the modelled storage pause, **2.3% the server, queueing included** (18 s median). The run's wall time was 2 h 20 m for a 1 h injection: 20 users drew 100+ encounters, so 800+ files, and each spent 53–80 min uploading serially before pushing a record — the last injected at 13:28 finished at 14:49. **CPU 11,542 s for the hour (predicted ~10,300), app 68% mean / 94% peak (predicted 61–68%), RDS 70% mean / 98.5% peak** — the application landed inside the estimate and **the database went to its ceiling**, driven by 295,000 `uploadUrl` calls the model priced as nearly free. **The instrument caveat**: `serverMs` in `sync-durations.csv` includes the upload wait, because only the storage pause is subtracted; corrected from the server's own log. [`findings-clustered-media-push.md`](findings-clustered-media-push.md) |
| 21 | — | **`DummyInterceptor` removed — case 13 at 2 vCPU** | **done 2026-10-21 — off the cliff, without a reset by choice**: row 20's residue biases against the test jar, so the saving reads as a lower bound. Same box, same hour, one registration removed: **467 failures → 0**, p50 **38,782 → 295 ms**, under-800 ms **5% → 83%**, all 2,474 syncs recorded against the control's 2,007. The queue decided it at +15 min — the control's in-flight count climbed 64 → 338 and never recovered; the test arm's held at 34–49 all hour. **App CPU 8,403 → 6,358 s (−24%)**, 4.19 → 2.57 s per sync — more than the predicted ~3.7 because the control's figure carries saturation waste, which row 22 removes. **The old build's knee is bounded for the first time at 900–1,030 req/min on 2 vCPU.** The test arm runs at 84% mean / 99% peak, so the margin bought is what case 13 needed, not a large one. **Timeslices, 22 Oct:** on the same box the filter's own time fell from 98% to 10% of request time, blocked events 48,865 → 2,811, GC 555 → 53 s — busy, not drowning. [`findings-interceptor.md`](findings-interceptor.md) |
| 22 | — | **`DummyInterceptor` removed — case 12 at 2 vCPU** | **done 2026-10-21 — the clean delta is 19%, not 12.6%.** Both arms healthy, 1,682 syncs each, 0 failed each, identical work (records p50 10,778 vs 10,872): **app CPU 6,152 → 4,999 s (−18.7%)**, 3.66 → 2.97 s per sync against a predicted ~3.2; app CPU 81% → 65% mean; `serverMs` p50 8.7 → 5.2 s; p95 1,707 → 746 ms, under-800 ms 70.6% → 96.1%. The 12.6% was the interceptor's share of *request wall time* under a profiler; its CPU cost, with the `@Transactional` boundary and the connection it takes, is larger. Control is row 16's 15 Oct run, not re-run — six days and a reload older than the case 13 control, and the result is not close enough for that to matter. Ran without a warm-up straight after row 21, `CACHE_POLICY=warm-from-preceding-run`. **Timeslices, 22 Oct — where the 18.7% went:** `Spring/HandlerInterceptor` is **11.7% of the control's request time** (the profiler's 12.6%, reproduced); the `gender` query is only **8% of that segment**, the `@Transactional` boundary around it the rest; every other statement then ran ~25% faster at equal call counts, which is why the CPU saving is half the segment's wall time. [`findings-interceptor.md`](findings-interceptor.md) |
| 23 | — | **Clustered — co-tenant load, media push, re-drawn** — row 20 with supervisors pushing nothing and the customer's own spread (`CUSTOMER_PUSH_DRAW=v2`) | **done 2026-10-21 — RDS comes off its ceiling: 98.5% → 81.4% peak.** Run after 21 and 22 without a reset, as planned. Every prediction landed: **217,400 media files** (~215,000), 1,344 users pushing (the 156 supervisors none), **p50 160 / max 360 files per sync**, wall **1 h 20 m** (~1 h 25 m), **10,714 CPU s** (~10,400), app ~62% over the hour (~61%). RDS mean 62% → 52% and peak 98.5% → 81.4% for 26% fewer `uploadUrl` calls — the media calls were the spike, the pulls are the floor. No customer sync over 30 min (row 20: 63); server+queue p50 18 → 13 s. **Gatling says BUILD FAILED on 2 KO of 327,309**: org 24's `groups` endpoint, which had 500'd on every call that day including two inside row 19 — a standing data defect, not load; **fixed 23 Oct** (18 rows whose creator, org 24's deleted bootstrap user, was repointed to `admin`). [`findings-clustered-media-push.md`](findings-clustered-media-push.md) |
| 24 | — | **Case 15 at ten encounters a day** — row 23 with the customer draw halved (`CUSTOMER_PUSH_DRAW=v3`, mean 10), on row 23's hardware | **done 2026-10-23 — the push model landed; the database did not follow the media down.** 107,080 media files (~107,500 predicted), p50 80 / max 184 per sync, 203,439 requests, **0 failed**, wall 1 h 11 m (~1 h 15 m), field-worker sync p50 6.6 min (~6.5), **9,285 CPU s** (~8,600), app 61% mean over the hour (~60%). **RDS 62% mean / 79% peak against ~40% predicted**: halving `uploadUrl` moved it ~72% → ~67% steady — the pulls are the floor, as row 23's timeslices said. Rows 25–26's database figures are therefore low; database load scales with the pull, and the pull with users. [`findings-clustered-media-push.md`](findings-clustered-media-push.md) |
| 25 | — | **Case 15 scaled out, test 1** — 5,000 users, ten encounters a day, 8 files each; app **8 vCPU**, database **8 vCPU** | **done 2026-10-23 — 3.3× the users cost 2× the CPU, and the app had a quarter in hand.** 573,458 requests at 159 rps, **1 failed** (org 24's `groupPrivilege`, the same deleted-user defect), p50 / p95 **12 / 234 ms**, 99.99% under 800, wall 1 h 11 m. **18,536 CPU s** against ~25,500 predicted; **app 61.6% mean / 75.5% peak of 8 vCPU** (~89% predicted), **RDS 31.6% / 37.8%** (~22%), read IOPS 575 peak of 3,000, pool 35 of 100, injector 6.7%. Records per sync 8,402 (−40% on row 24, the ten-a-day history), ~3.4 CPU s per customer sync against ~5.3. A field worker waits 6.1 min, 4.8 s of it the server. The planned 12,000 IOPS did not apply — gp3 provisioning needs ≥ 400 GiB, the volume is 250 — and was never needed for the run. [`findings-clustered-media-push.md`](findings-clustered-media-push.md) |
| 26 | — | **Case 15 scaled out, test 2** — 10,000 users, ten encounters a day, 8 files each; app **16 vCPU**, database **16 vCPU** | **done 2026-10-23 — twice the users on twice the cores reproduced row 25: 1,107,301 requests at 307 rps, 0 failures, p95 231 ms; 35,564 CPU s (1.92× row 25 for 2× the syncs, ~3.4 per customer sync); app 58.9% mean of 16, RDS 27.4%, pool 44 peak, heap 1,220 MB, injector 11.5%; field-worker sync 364 / 525 / 783 s with the server's share 1.3%.** Dataset `pilot-day-180-10k` loaded with `SWAP_PARALLEL=1`, one psql session per tenant: 27,958,930 rows in 42 min (~11,100 rows/s) on the **baseline volume** — the planned 12,000 IOPS / 500 MB/s could not be applied (gp3 provisions IOPS and throughput only from 400 GiB; the volume is 250; `RESIZE.md` records it) and was not needed: the parallel load sat on the 125 MB/s *throughput* baseline, not IOPS, and the run peaked at 212 read IOPS. REINDEX took 9.5 min on `db.m6g.4xlarge`. Org 24's deleted bootstrap user was repointed in all 27 of its tables before the run — the first row with zero failures. The injector stayed at `m6g.xlarge` for the run and went to `m6g.large` with the end-of-day stop; `m6g.large` is the tofu default from 23 Oct. Predictions scored in [`findings-clustered-media-push.md`](findings-clustered-media-push.md#row-26-10000-users-on-16-app-and-16-database-vcpu): the upper bounds held (CPU s at 72% of predicted), the database's "~20%, low" did not (27%). [Rows 24–26](#rows-24-26)
| 27 | V | **Re-baseline on the production build** — anchors A and B, each **twice**, on `v18.1.0` (`789092feb`), what production runs | **done 2026-10-27 — 18.1 reproduces 17.3 on both anchors; the rig is 5–8% dearer than when the 17.3 controls were measured, and today's runs replace them.** Anchor A twice: 3.96 and 3.83 CPU s per sync, p95 2,433 and 1,905 ms, app 90% and 88% of 2 vCPU (row 28 put the 17.3 jar at 3.92 / 2,219 the same day). Anchor B twice: 4.28 and 4.25 CPU s per sync, p95 449 and 449 ms, app 65% of 4 and RDS 60% of 2, against row 24's 4.05 / 446. 0 failures in all four. Statement counts match the 17.3 captures to a fraction of a percent on both anchors, so the signature table stands. **Row 29's controls: A 3.9 ± 0.07 CPU s/sync at ~89% of 2 vCPU, p95 1,900–2,450 ms; B 4.27 ± 0.02 at ~65% of 4, p95 ~447 ms.** [Results](#rows-27-28-results)
| 28 | V | **Drift check, only if row 27 does not reproduce 17.3** — anchor A once on the old jar `2c0215679` | **done 2026-10-27 — the rig moved, not the code.** Anchor A on `2c0215679`, same day, bed and classes as row 27's pair: **3.92 CPU s per sync, p95 2,219 ms**, app 89.7% — between the two 18.1 runs (3.96 / 3.83, p95 2,433 / 1,905) and within 1% of r1 on identical statement counts. The 15 Oct control (3.66, p95 1,709, app 84%) is therefore not comparable with anything measured now; what changed on the rig in twelve days is not identified — candidates are the fresh reindexed bed, the `audit` table's growth, and the instance landing on another host after the stop/start. [Results](#rows-27-28-results)
| 29 | V | **One fix per jar** — #1097, #1098, #1103, the #882 cache fix and #1057, each built on the production tag alone and run on A and B | **pending — each as its fix lands.** Each measured against row 27, not stacked on the previous fix, so every saving is attributable. [Validation phase](#validation-phase) |
| 30 | V | **All fixes together** — the combined jar on A and B, then C (case 13, 2 vCPU) and D (5,000 users, 8 + 8) | **pending — after 29.** Fixes interact, so this is the number to quote for the release; C shows whether the knee moved, D whether the gain holds at scale. [Validation phase](#validation-phase) |

#### Rows 21 and 22: removing `DummyInterceptor`

**What is being tested.** `DummyInterceptor` runs a `@Transactional` query against `gender` after
every web request. It is **12.6% of request time** on a healthy server, it never has anything to
flush on a UTC JVM, and it could not flush a dirty entity if it had one, because Hibernate's
auto-flush only fires when the query touches the dirty entity's table. The evidence is in
[`dummy-interceptor.md`](dummy-interceptor.md); the card is avniproject/avni-server#1097. These
two runs price its removal.

**The jars, and why the control needs no new run**

| | file | build |
|---|---|---|
| control | `avni-server-17.3.0-SNAPSHOT.jar` — the jar every run so far has used | `origin/17.3` @ `2c0215679` |
| test | `avni-server-17.3-2c0215679-NO-INTERCEPTOR.jar` | the same commit, with the registration removed from `SyncConfiguration` and `ApiConfiguration` |

**The deployed jar was identified, not assumed.** No run records a server commit — all of them say
`17.3.0-SNAPSHOT` — so `origin/17.3` was rebuilt and compared class by class against the jar in use:
every class identical. A first attempt built from a local checkout 17 commits behind, which would
have folded ETL-export and form-validation changes into the comparison. **The two jars differ in
nothing but the interceptor's registration**, confirmed in the bytecode.

So row 19's `m6g.large` case 13 and row 16's case 12 are valid controls as they stand. Re-running
the control on the same day is still worth doing if the environment has been touched since.

**Row 21 runs without a reset, deliberately.** Row 20, clustered with co-tenant load and media push, ran with push on after these controls and left its rows behind — ten months newer than the generated data, so inside every `realistic` sync window. That can only *add* work: more records to pull per sync. The test jar therefore carries a heavier load than its clean control did, so **any saving it shows is a lower bound**, and the residue cannot flatter the result.

Two consequences for the read-out. **A pass is strong and a failure is ambiguous** — if case 13 comes off the cliff despite the extra work the answer is clear; if it does not, the residue is a live explanation. And **report two figures**: CPU s per sync, the conservative raw comparison, and CPU s per record pulled, which removes most of the residue's effect because case 13 pushes nothing and the residue arrives as extra records. `sync-durations.csv` carries `records` for both runs. Row 22 inherits the same reasoning if it also runs unreset; read it the same way.

**Run each exactly as its control ran** — same instance size, same dataset (`pilot-day-180`), same
feeder and rate, same co-tenant load and seed, New Relic attached, **no profiler**. Only the jar
changes. Pass `-DSERVER_BUILD=2c0215679-no-interceptor`, or the run log cannot tell the two builds
apart. Afterwards run `make cpu_per_sync ACCOUNT=8563864 RUN=case13` before `make run_log`, or the
CPU columns show a dash.

**Predictions, written down before the runs:**

| | control | test, if the full 12.6% comes off |
|---|---|---|
| case 13: CPU s per sync | 4.19 | **~3.7** |
| case 13: total CPU s | 8,403 | **~7,350** |
| case 13: outcome | BUILD FAILED, 467 failures | **the question** |
| case 12: CPU s per sync | 3.66 | **~3.2** |

Expect less than the full 12.6%. It is a share of request time measured under sync-only load, not a
flat per-request constant, and case 13's requests are large — 28 per sync against case 11's 88 — so
a fixed per-request cost is a smaller fraction of each. **Measure in CPU seconds, not wall clock**:
under load wall clock mixes the saving with queueing relief and overstates it.

**Why these two and not a push-heavy case.** The interceptor is a fixed cost per request, so a
media-heavy run with many cheap requests would show a larger effect. But a `PUSH=on` run writes
tens of thousands of rows newer than anything else in `pilot-day-180`, which lands them inside every
`realistic` sync window and forces a reload — exactly what happened after case 11 run 1. Cases 12
and 13 are `PUSH=off` and leave the dataset untouched. **If case 13 comes back ambiguous, spend the
reload on a case 11 pair then.**

**Removed, not path-scoped.** Scoping it to the sync paths takes it off `/ping` and almost nothing
else under a sync workload, which would read as a null result for the wrong reason.

**Housekeeping.** The temp fix lives in a git worktree at `/tmp/avni-17.3-tip`, uncommitted and
marked `DO NOT MERGE`. Remove it with `git worktree remove /tmp/avni-17.3-tip` once both runs are in.

<a id="row-23"></a>
#### Row 23: clustered — co-tenant load, media push, re-drawn

**Row 20 overstated its own workload in two ways, both found after it ran.** Supervisors pushed at
`pushScale` 1.0, so 156 of the 1,500 syncs carried a field worker's twenty encounters a day that a
supervisor covering a Taluka does not record. And the encounter draw was 8 / 20 / 45 / 150 — a
spread with no customer basis, whose tail put 1,200 files on one sync and stretched a one-hour
injection to 2 h 20 m. The customer's own figure is that a heavy day is unlikely to pass thirty.

**This run removes both and changes nothing else.**

| | row 20 | **row 23** |
|---|---|---|
| feeder | `case5-users-pilot.csv` | **`case5-users-pilot-nosuppush.csv`** — the same 1,682 rows in the same order, supervisors at `pushScale` 0.0 |
| encounter draw | 8 / 20 / 45 / 150, mean 24.6 measured | **`v2`: 10 / 20 / 30 / 45, mean 20** |
| everything else | 1,500 over 1 h, 8 files/encounter, co-tenants at 792/h with push on, `m6g.xlarge`, `pilot-day-180`, `MEDIA_MODEL=pause`, New Relic on, no profiler | **identical** |

```
-DSYNC_USERS=case5-users-pilot-nosuppush.csv -DCUSTOMER_PUSH_DRAW=v2 \
-DPUSH_MEDIA_PER_ENCOUNTER=8 -DSERVER_BUILD=<the jar's commit>     # plus row 20's settings unchanged
```

`v2` is the default, but pass it explicitly: the banner and `push.customerDraw` in
`run-metadata.json` then confirm which ran. **A supervisor's `pushScale` of 0 zeroes every push
entity, so its media count is zero too** — it still pays the per-user push seed, four page reads,
once.

**Predictions, written before the run:**

| | row 20, measured | row 23, predicted |
|---|---|---|
| media files, all customer syncs | ~295,500 | **~215,000** (1,344 field workers × 160) |
| media files per field-worker sync | p50 160, mean 197 | **p50 160, mean 160, max 360** |
| upload wait, worst sync | 80 min | **24 min** |
| wall time | 2 h 20 m | **~1 h 25 m** — injection plus the longest upload |
| customer CPU s per sync | ~6.8 | **~6.0** |
| total CPU s for the hour | 11,542 | **~10,400** |
| app CPU, 4 vCPU, mean | 68% | **~61%** |
| **RDS, mean / peak** | **70% / 98.5%** | **the question** — ~60% / ~85% if it falls in step with `uploadUrl` |

The RDS figure is the least certain and the most useful. Row 20 showed the database driven to its
ceiling by `uploadUrl`, a request the scenario priced as nearly free; if it scales with the call
count this run lands well clear of it, and if it does not, something other than the media calls is
holding the database up.

**This is not an A/B.** It changes two things at once — both reductions in push work, so they move
in the same direction — because the aim is the realistic version of the scenario, not to separate
the two. Separating them would take two more runs: `v2` with supervisors at 1.0, or `v1` with them
at 0. **Per-request costs still compare directly with row 20**: CPU and database time per
`uploadUrl`, per encounter `POST`, per record pulled. Totals do not.

**Read `serverMs` corrected, as row 20 had to be.** The harness still adds the media pause to it, so
the raw column overstates server time by the whole upload wait.

> **Order: run this last, without a reset, and reset after it.** Row 20 left on the order of 37,000
> customer encounters plus co-tenant writes in `pilot-day-180`, ten months newer than the generated
> data, so inside every `realistic` window. **For this run that is about +1% of pull work**: a field
> worker's village holds three workers' pushes, ~74 extra records against ~13,800 pulled (+0.5%), and
> a supervisor's Taluka ~207 against ~30,000 (+0.7%). **The media count, upload wait and wall time do
> not depend on the dataset at all**, and the small extra pull load biases CPU and RDS *against* the
> drop this run is looking for — so a fall from row 20's 98.5% RDS peak is real, the same lower-bound
> argument as rows 21 and 22. **Cross-check it**: records pulled per field-worker sync against row 20
> should rise by roughly that +0.5%; much more would undercut the estimate, here and for 21 and 22.
> **Reset after it** — it pushes again and roughly doubles the residue.

<a id="rows-24-26"></a>
#### Rows 24–26: case 15 at ten encounters a day, scaled out

**Requested 23 Oct 2026**: the next tests take the customer to **ten encounters a day at 8 images
each**, then scale users and both tiers together — **5,000 users on 8 app and 8 database vCPU**, and
**10,000 on 16 and 16**. Row 24 is added in front of them: the same halving on row 23's hardware,
so the two scale-out runs are sized on a measured per-sync cost rather than one carried across a
changed draw.

| | row 23, measured | **24** | **25 — test 1** | **26 — test 2** |
|---|---|---|---|---|
| customer users, over 1 h | 1,500 | 1,500 | **5,000** | **10,000** |
| encounters per field-worker sync | `v2`: 10 / 20 / 30 / 45, mean 20 | **`v3`: 5 / 10 / 15 / 23, mean 10** | `v3` | `v3` |
| media files per field-worker sync | p50 160, max 360 | **p50 80, max 184** | same as 24 | same as 24 |
| supervisors | push nothing | push nothing | push nothing | push nothing |
| dataset | `pilot-day-180` | `pilot-day-180` | **`pilot-day-180-5k`**, new | **`pilot-day-180-10k`**, new |
| app | `m6g.xlarge`, 4 vCPU | `m6g.xlarge` | **`m6g.2xlarge`, 8 vCPU** | **`m6g.4xlarge`, 16 vCPU** |
| database | `db.m6g.large`, 2 vCPU | `db.m6g.large` | **`db.m6g.2xlarge`, 8 vCPU** | **`db.m6g.4xlarge`, 16 vCPU** |
| injector | `m6g.xlarge` | `m6g.xlarge` | `m6g.xlarge`, 6.7% mean | `m6g.xlarge`, **11.5% mean, 21.9% peak** — not resized, decided 23 Oct: see below. Downsized to `m6g.large` after the run; the default since |
| co-tenants | 792/h, push on | unchanged | unchanged | unchanged |

**Unchanged throughout:** 8 files per encounter, `MEDIA_MODEL=pause`, co-tenants at production's
busiest hour, New Relic on, no profiler, the 900 s warm-up burst, heap pinned at 5,120 MB, and the
jar rows 20 and 23 ran — `2c0215679`, `DummyInterceptor` still in — unless the fix for
avniproject/avni-server#1097 ships first. Record which in `SERVER_BUILD` either way; the predictions
below say why it matters.

**Co-tenants stay at 792/h.** They are the other organisations on the shared server, and the
customer growing does not make them busier.

##### What has to exist first

1. **The `v3` draw — done 23 Oct 2026.** `PushProfiles.customerEncounters` gains `v3` → `new PushVolume("encounters",
   1.0, 5, 10, 15, 23, 10.0)`: `v2` halved, with a 23 ceiling, so a heavy day sits at a little over
   twice the median as it does in `v2`. A unit test pins the sampled mean to 10, as `v2`'s pins 20.
   **Not `pushScale` 0.5 in the feeder**, which would get the same encounters but would also halve
   every other entity a worker pushes, and would not be recorded as `push.customerDraw`.
2. **Two datasets — generated and archived 23 Oct 2026** (`s3://…/datasets/pilot-day-180-5k.tar.gz`, 1.0 GiB, 13,991,190 rows in 7.4 min; `pilot-day-180-10k.tar.gz`, 2.1 GiB, 27,958,930 rows in 15 min; bundle `tanuh`, the customer's; feeders `case5-users-pilot-5k-nosuppush.csv` and `-10k-`, 5,590 and 11,164 users with supervisors at 0.0). **Not yet loaded** — that needs the database resized and `db_allocated_storage` grown first. The recipes:
   [`pilot-day-180-5k.json`](../tools/data-generator/datasets/pilot-day-180-5k.json) and
   [`pilot-day-180-10k.json`](../tools/data-generator/datasets/pilot-day-180-10k.json). The customer's recipe today has 1,496 field workers and 186 supervisors; 5,000
   and 10,000 users are not in it. `pilot-day-180-5k` and `pilot-day-180-10k` are `pilot-day-180.json`
   with every tenant's `field_workers` scaled by 10/3 and 20/3 — states 500 → 1,667 and 3,333, NGOs
   62 → 207 and 413 — and **`encounters_per_worker_per_day` at 10**, so the history matches the
   projection the pushes now model. Village density, span 8.4 and `beneficiaries_per_village` stay,
   so **a single sync's catchment is the same size as today's**: what grows is the number of
   catchments, and with them the tables. **4,990 and 9,970 field workers** — about 5,600 and 11,200
   users with supervisors, of which the runs inject 5,000 and 10,000 — **5.0 M and 10.0 M
   individuals** against 1.5 M, and 9.0 M and 17.9 M encounters against 5.4 M. Ids top out at 219 M
   and 237 M, clear of the co-tenants' band at 301 M.
   Generate their feeders with `--supervisor-push-scale 0.0`, as row 23's.
3. **The resizes**, through `app_instance_class`, `db_instance_class` and
   `injector_instance_class` (`avni-infra/provision/RESIZE.md`). **Budget for the AZ refusing the
   database class** — it has, repeatedly, for smaller ones — and size `db_allocated_storage` for a
   dataset 3–7 times today's before the load, since it cannot be shrunk afterwards.
   `max_connections` is production's RAM-scaled expression and grows on its own.

##### Predictions, written before the runs

**Arithmetic over rows 13, 19 and 23, not a measurement — row 24 exists to replace its weakest
line.** Row 23's 85-minute window carried 1,500 customer syncs and ~1,125 co-tenant syncs; the
co-tenant share is taken out first, at case 7's 1.68 CPU s and 51.4 requests a sync.

| per customer sync | row 23, 20 a day | **at 10 a day** |
|---|---|---|
| requests | ~180, of which ~145 `uploadUrl` | **~100**, of which ~73 `uploadUrl` |
| database statements | ~2,950 — 12.1 per `uploadUrl`, ~34 per other request | **~1,800** |
| database time | ~5.8 s | **~3.9 s** |
| app CPU s, current jar | ~5.9 — of which the pull is ~3.8 (case 13 at 4 vCPU, net of co-tenants) | **~4.8** — the pull, plus half of row 23's push and `uploadUrl` |
| app CPU s, without the interceptor | — | **~3.9**, row 22's −19% |

The push-and-media remainder halves cleanly whatever its internal split, because both halves of it
— encounters and the files they carry — halve together. **The pull at 3.8 s does not move in row
24**, which pulls from `pilot-day-180`'s twenty-a-day history. **It does move in 25 and 26.** Their
datasets carry a ten-a-day history (`encounters_per_worker_per_day: 10`, so 1,800 encounters per
worker against 3,600), and under `SYNC_MODE=realistic` a sync pulls what its catchment produced
since the device last synced — so each sync's window holds half the encounters, and the pull,
which is two-thirds of a sync's CPU and mostly encounters, falls with it. Bounded: 3.8 s if none of
the pull were encounters, ~1.9 s if all of it were; the truth is between, nearer the low end. **The
tables below keep the 3.8 s and are therefore upper bounds for 25 and 26.** Decided 23 Oct 2026:
keep the history at ten a day, matching the pushes it models, and correct the predictions rather
than the data.

| | **24** | **25 — test 1** | **26 — test 2** |
|---|---|---|---|
| requests per hour | ~190,000, ~55 rps | **~540,000, ~150 rps** | **~1.04 M, ~290 rps** |
| app CPU s for the hour, co-tenants' ~1,330 included | ~8,600 | **~25,500** | **~49,700** |
| **app CPU, current jar** | **~60%** of 4 vCPU | **~89%** of 8 | **~86%** of 16 |
| app CPU, without the interceptor | ~49% | ~71% | ~70% |
| database, mean — row 23's 52% scaled by database time | ~40% of 2 vCPU — **measured 62%: the pulls are the floor** | **~22%** of 8 — **low**; scales with the pull, so with users: nearer 50% | **~20%** of 16 — likewise |
| devices in flight — ~6.5 min a sync | ~160 | ~540 | ~1,100 |
| wall time | ~1 h 15 m — injection plus 184 files at 4 s | same | same |

Every app and database figure for 25 and 26 in this table is an **upper bound**: it carries row
24's pull against a history half as dense. Row 25's measurement replaces it.

**The prediction that matters: on the current jar, both scale-out runs sit at the app's knee and
the database idles.** Users grow 3.3× and 6.7× while app vCPU grows 2× and 4× from row 23's 4 — and
halving the encounters makes a sync only a fifth cheaper in row 24, because the pull, which does
not halve there, is two-thirds of it. In 25 and 26 the pull's encounter share halves as well, so
the saving is larger and the knee further off than the table says — but at 3.3× and 6.7× the users
on 2× and 4× the vCPU, the app is still the tier under load. The database
grows 4× and 8× against a load of 1.7× and 3×, so most of it would sit unused. If this holds, **the
cheaper configuration is the interceptor fix and fewer database vCPU**, not 16 and 16 — and row 25
on the fixed jar would be the run that shows it.

**Where the arithmetic is weakest.** Per-sync CPU is assumed flat from 4 to 16 vCPU; nothing here
has measured past 4, and contention, GC and the 200 Tomcat threads and 100 pooled connections that
avni-server runs on by default may not scale with cores. History at ten a day halves the encounters
each sync pulls, which makes every app figure above an upper bound — and it means **24 is not a
clean bridge to 25**: they differ in history density as well as scale, so 25's per-sync cost is not
24's at 3.3× users, and the step between them is a change of workload per user, not only of scale. And database CPU is scaled on
database time alone, from one 2 vCPU point, for a database whose tables are 3–7 times larger. Row 24 settles the per-sync figure at ten a day;
25 settles whether it holds at 8 vCPU before 26 doubles it.

**Watch during 25 and 26**, from the timeslices: heap peak against the 5,120 MB pin and G1 time
(the first symptom of the 2 vCPU cliff was a full heap), `http-nio` thread counts against 200,
and the injector's own CPU. **The injector is not resized for 26** (decided 23 Oct 2026): CloudWatch
puts it at a **4–5% mean** across every heavy run so far — case 13 B at ~16 rps, the media hour at
~90 rps and ~375 devices in flight, row 23 at ~80 rps — with the ~20–26% peaks in each run's first
five minutes, which is Gradle and the JVM starting, not load. Row 26's ~290 rps and ~1,100
devices is about 3× the media hour, so a mean in the low teens on `m6g.xlarge`; Gatling's 1,024
MB heap on a 16 GB host holds kilobytes per paused user. The watcher records it; if it climbs
past ~50% the result is suspect and the resize is the answer then.

**Order.** 24 ran on `pilot-day-180` on 23 Oct without the reset row 23 called for — on rows
20–23's residue, the same lower-bound reading as 23. 25 and 26 each on a fresh load of their own
dataset, so neither carries residue.

<a id="validation-phase"></a>
#### Rows 27–30: the validation phase — measuring each fix against a new baseline

**Added 26 Oct 2026.** Production has moved off the 17.3 build every run so far was measured on
(`2c0215679`), with no significant performance fix in between. The fixes this campaign raised
will land on that newer base, so **the 17.3 numbers cannot be their control**. This phase rebuilds
the baseline on the production build and measures each fix as a jar that differs from it by one
change.

##### The anchors

Two cover every fix's code path. Two more are kept for the combined jar only.

| anchor | scenario | hardware | dataset | as run before |
|---|---|---|---|---|
| **A** | case 12: 1,682 users over 1 h, `PUSH=off`, co-tenants present and idle | `m6g.large` app (2 vCPU), `db.m6g.large` | `pilot-day-180` | row 22's control — the interceptor's clean delta |
| **B** | case 15 at ten a day: 1,500 users over 1 h, `CUSTOMER_PUSH_DRAW=v3`, `case5-users-pilot-nosuppush.csv`, 8 files per encounter, co-tenants at 792/h with push on | `m6g.xlarge` app (4 vCPU), `db.m6g.large` (2 vCPU) | `pilot-day-180` | row 24 |
| C | case 13: case 12 plus co-tenants syncing at 792/h | `m6g.large`, `db.m6g.large` | `pilot-day-180` | rows 19 and 21 — the cliff |
| D | case 15 scaled: 5,000 users | `m6g.2xlarge`, `db.m6g.2xlarge` | `pilot-day-180-5k` | row 25 |

**A is the cleanest CPU delta**: healthy, pull-heavy, no push, so a fix's saving is not mixed with
saturation waste. **B is the write and media path**, and its 2 vCPU database makes statement-count
changes visible in RDS CPU.

##### Two kinds of evidence per fix

**A signature that proves the fix is live, from the timeslices.** Statement counts are exact, not
sampled, so they confirm a fix took effect even when its CPU effect sits inside the noise.
**A magnitude that sizes it**, read against row 27's spread: CPU seconds per sync
(`tools/cpu-per-sync.py`), database time, RDS CPU, p95.

| fix | signature: on the 17.3 baseline → expected | magnitude: expected | anchors |
|---|---|---|---|
| avniproject/avni-server#1097 — remove `DummyInterceptor` | `gender` selects per request **2.0 → ~0.1**; `sync_telemetry` UPDATE/INSERT **3.00 → 1.00** | app CPU **−19%** on A (row 22) | A, B |
| #1098 — pin UTC in `JodaDateTimeConverter` | UPDATE/INSERT on `sync_telemetry` (A and B) and `encounter`, `program_*` (B) **drops by exactly 1** | database time; one `audit` row less per write | A, B |
| #1103 — parent UUIDs via `@Formula` | `individual` selects per customer sync **down ~75%** (B: 148 on row 24) | app CPU **~−5%** — inside the noise, so the signature carries it | A, B |
| the fix #882 recommends | `users` per request (A 2.2, B 1.48) and `catchment` (A 1.7, B 1.22) **toward 0** | database time — `users` alone was 22% on row 24 and 30% at 10k | A, B |
| #1057 — `exists` for `syncDetails` | `count(individual)` gone from `syncDetails` in `SqlTrace` | `syncDetails` database time | A |
| #1100 + avniproject/avni-client#2218 — batched upload URLs | `uploadUrl` requests per sync **÷ batch size** | RDS CPU, request count | B — **needs the harness to model it first** |
| avniproject/avni-client#2096 — `Slice` endpoints | `COUNT` statements per page **→ 0** | pull database time | A — **needs the harness to model it first** |

The last two change what the client sends, so they wait on a harness switch (`UPLOAD_URL_BATCH`,
and a `/v2` pull mode) and are measured when both the server and client changes exist.

##### Discipline the comparisons depend on

- **Reset before every run**: `tools/reset-transactional.sql`, then the dataset's `reload.sql`.
  Rows 21–24 ran on residue by choice and could only claim lower bounds; this phase wants
  differences, so every run starts from the same rows.
- **The same instance types, warm-up (900 s burst), draw, co-tenant rate and seed** for every run
  on an anchor. Run all of one anchor's jars before resizing for the next.
- **One fix per jar, built from the production tag**, bytecode-checked as the interceptor jar was,
  and recorded in `SERVER_BUILD`. Row 29 measures each against row 27, never stacked; row 30 is the
  only stacked run.
- **Timeslices captured for every run, controls included** — row 16's control nearly aged out
  before it was captured.
- **A fix's magnitude is quoted only if it exceeds row 27's spread.** Below that, the signature
  is the result and the magnitude is reported as "within noise".

##### What it costs

| | runs |
|---|---|
| row 27 — A ×2, B ×2 | 4 |
| row 28 — A on the old jar, only if row 27 does not reproduce 17.3 | 0–1 |
| row 29 — five server fixes × A and B (#1057 on A only) | 9 |
| row 30 — combined on A, B, C, D | 4 |
| **total** | **17–18 one-hour runs**, plus the two client-dependent fixes when the harness models them |

**The production build is `v18.1.0`** (`789092feb`, also `origin/18.1`), deployed by 26 Oct 2026. It
is the 17.3 baseline plus 72 commits — `2c0215679` is an ancestor — and **none of them touch the
sync and push hot paths**:

| changed | relevance |
|---|---|
| `DummyInterceptor`, `JodaDateTimeConverter`, `SetOrganisationJdbcInterceptor`, `AuthService`, `DbRoleRepository`, `AddressLevelCache`, the sync controllers | **untouched** |
| build files, `application.properties`, `ehcache.xml`, migrations | **untouched** |
| `EncounterRepository`, `ProgramEncounterRepository`, `EncounterService` | a visit-date sort for the Completed Visits search (#1015) — not on the sync path |
| `MediaController.generateUploadUrl` | adds file-name checks for the reserved storage namespaces (#1049) — string matching, no database call, so `uploadUrl`'s ~12 statements stand |
| the rest | CSV upload modes, export formatting, hidden concepts, fast-sync dump endpoints — none exercised by the harness |

**So row 27 should reproduce rows 22 and 24 within noise**, and that is the first thing to check.
If it does, the 17.3 findings carry over to 18.1 unchanged and row 28 is skipped; if not, row 28
separates rig drift from code. Every fix jar in row 29 is built on `789092feb`.

**The baseline jar is CircleCI's production build**, `avni-server-18.1.0-SNAPSHOT.jar`, sha256
`87bf747b08a9d2a90f5fa3e9a91cd137a295643976fb6491ae433d550e5ba678`. It carries no commit metadata,
so it was tied to `789092feb` by rebuilding that commit locally (JDK 21, `bootJar`) and comparing
entry by entry, 26 Oct 2026: all 2,184 boot-jar entries and all 1,871 `-plain` entries identical in
content, the only CRC difference being build timestamps inside the nested `avni-server-data` jar.
**A local build of `789092feb` therefore reproduces production's jar**, so a row 29 fix jar built
locally differs from the baseline by its fix and nothing else.

<a id="rows-27-28-results"></a>
##### Rows 27–28, 27 Oct 2026: anchor A

| anchor A, case 12 | 17.3 control, 15 Oct | **18.1 r1** | **18.1 r2** | **17.3 today, row 28** |
|---|---|---|---|---|
| requests / failures | 31,409 / 0 | 31,469 / 0 | 31,259 / 0 | 31,259 / 0 |
| CPU s / per sync | 6,152 / 3.66 | 6,654 / **3.96** | 6,449 / **3.83** | 6,592 / **3.92** |
| app CPU, injection hour | 84.2% | 90.4% | 87.9% | 89.7% |
| RDS CPU / read IOPS | 24.5% / 135 | 26.8% / 117 | 26.0% / 58 | 26.0% / 121 |
| p95 / under 800 ms | 1,709 ms / — | 2,433 / 49% | 1,905 / 60% | 2,219 / 55.5% |
| `individual` selects (timeslices) | 207,252 | 207,264 | 188,012 | 207,217 |

**18.1 reproduces 17.3.** Row 28 — the old jar on the same day, bed and classes — lands between
the two 18.1 runs on every axis, and within 1% of r1 on identical statement counts. r2's lower
figure is the full-sync draw (9% fewer pulls in its window), not the jar. **The rig is 6–8%
dearer than on 15 Oct** and the old control is retired: **row 29's control on A is today's three
runs, 3.9 ± 0.07 CPU s per sync, p95 1,900–2,450 ms at 88–90% of 2 vCPU** — and the spread
reads as ±2% on CPU and ±12% on p95, which is what a fix's magnitude must exceed.

##### Anchor B, the same evening

| anchor B, case 15 at ten a day | row 24, 17.3, 23 Oct | **18.1 r1** | **18.1 r2** |
|---|---|---|---|
| requests / failures | 203,439 / 0 | 204,123 / 0 | 203,771 / 0 |
| CPU s / per sync (2,292 syncs, co-tenants in) | 9,284 / 4.05 | 9,821 / **4.28** | 9,735 / **4.25** |
| app CPU, injection hour | 61.9% of 4 | 65.2% | 64.7% |
| RDS CPU, injection hour | 63.3% of 2 | 61.6% | 58.4% |
| p95 / under 800 ms | 446 ms | 449 / 99.5% | 449 / 99.5% |
| `users` / `gender` selects (timeslices) | 300,994 / 416,562 | 300,869 / 417,999 | — |

**Same verdict on the write path.** B's two runs are within 1% of each other on CPU and 3 ms on
p95; both are 5–6% above row 24 with identical statement counts and identical latency — B's app
is not near a knee, so the rig shift shows only in CPU. r2 ran after a reload of `pilot-day-180`
(parallel teardown of the 7 M-row pilot bed on `db.m6g.large`: 8.6 min; load 16.5; REINDEX
**42.5 min**, IO-bound on the volume — nineteen minutes at exactly 3,000 read IOPS with 4 KB
reads, queue 40–50 and latency 15 ms, then at the 125 MB/s throughput cap — where the 4xlarge
had done it from cache in four). The reindex covers the co-tenants' tables the swap never
touches; narrowing it, or doing the reload on the big class, is the next saving on a reset.

**The signature baseline carries over unchanged.** Every statement's call count in the 18.1
captures matches the 17.3 control to a fraction of a percent: `gender` 66,448 (the
interceptor's), `users` 68,506, `address_level_type` 98,547, the three `sync_telemetry` writes.
The signatures in the fix table above were read off 17.3 and stand for 18.1.

**What this cost to learn, and what it changed in the tooling.** The 10k bed had to come out
before the anchors: one session tearing it down on `db.m6g.large` was IO-bound at ~1.5k rows/s
and had four NGO tenants down after 53 minutes with the two state tenants still to come. Aborted
and redone with `SWAP_PARALLEL=1` on `db.m6g.4xlarge`, where `swap-dataset.sh` now tears down
one session per organisation as it loads: **28.08 M rows in 24 minutes**, the eight NGOs in three;
the whole swap — teardown, vacuum, load, reindex, verification — in 48 minutes. The resizes
there and back cost 7 and 21 minutes. A reset on the pilot bed alone (7 M rows) is cheaper and
stays on the small class.

#### Standing task: back up New Relic weekly

**`Transaction` events are retained for 8 days and the boundary slides by the minute.** Everything
read per request — `databaseDuration`, `databaseCallCount`, `name`, `duration` — lives only there.
When an hour falls off nothing brings it back: the environment that produced it is destroyed
between campaigns, so the run cannot be repeated. `Metric` timeslices last far longer and are the
only reason cases 1 and 2 remain readable at all, but they carry no per-request detail.

**Run it at least once a week, and after every run if the run mattered.** This is not housekeeping;
it is the difference between a finding that can be re-examined and one that can only be quoted.

    export NEW_RELIC_API_KEY=NRAK-...          # a USER key
    python3 tools/newrelic-export.py --account 8563864 --out nr-backup --s3

It is incremental and resumable — an hour already in the manifest is skipped — so a weekly run
writes only the new hours, and it is safe to run while a scenario is in flight because it queries
New Relic rather than the environment.

**The key is the part that catches people out.** NerdGraph takes a user key (`NRAK-`) and returns
401 for anything else. The `NRIQ-` query key used for ad-hoc NRQL will not work, and neither will
`/avni/loadtest/newrelic-license-key` in SSM — that is the *ingest* key the agent uses to send
data, which is a different credential in the opposite direction.

Output lands in `s3://avni-loadtest-<account>/newrelic/`, one gzipped JSONL file per event type
per UTC hour, sliceable by run because every event carries `timestamp` and the run windows are in
[`run-log.md`](run-log.md). `tools/newrelic-query.py` reads the backup offline.

#### The co-tenant set, as provisioned

**All 513 through the API, and no config cloning.** The hybrid was chosen against a projection of
26–33 hours that came from extrapolating one `large-pull-heavy` import across every tenant. With
all three archetypes timed in one session — 183 s, 72 s and 110 s — the same arithmetic gave 10.6
hours, and a clone saving eight hours of unattended machine time was no longer worth new code
running on 403 organisations whose config nothing ever reads.

**Three things the provisioning run settled that the plan had assumed:**

* **The ids are not contiguous and must be read back by name.** The server assigned 24–566 with
  406–435 missing — an id-allocation block the overnight restart discarded. A positional mapping
  from the recipe's 1001–1513 placeholders would have been correct for the first 382 tenants and
  wrong for the remaining 131, starting at `co-383`. That is data loading cleanly into the wrong
  tenant. Matched from `docs/co-tenant-provisioning.tsv`; all 513 resolve, all distinct.
* **Supervision is per archetype, not per deployment.** `supervisor_level` was `Taluka` on all 513,
  which is the *customer's* hierarchy; the co-tenants are built from three production bundles and
  only one has a Taluka. `large-pull-heavy` supervises at AWC Village/Town, `push-dominated` at
  Subcentre, `media-heavy` at Block — and `media-heavy` truncates to three levels, so its leaf is
  Ward rather than Village. Generation raised on `co-001` before writing a row.
* **Observation width varies by bundle, and two archetypes are thin.** `push-dominated` — 500 of
  the 513 — reproduces the profile: 7/25 individuals against a 7/29 target. `large-pull-heavy`
  fills its widest registration form at five keys, which is the form's ceiling rather than a
  choice. `media-heavy` produces no registration, enrolment or programme-encounter observations at
  all: those forms carry zero elements and its enrolment mapping is voided. **`co-001` is
  `large-pull-heavy` and is rank 1 at 16% of the co-tenant draw**, so the heaviest co-tenant has
  the lighter payload. Read case 7 with that in mind: the production aggregate is carried by the
  500, not by the largest.

**The load is unmeasured and is the next thing to time.** 3.12 GiB and 6.25M rows, comparable to
the pilot dataset itself, against a reset budget that still rests on a ~21-minute projection
extrapolated from two tenants.

#### Case 9 is three ramps, because one knee has already been found and it is not this one

**Case 1 located a knee and named its resource: the app server's 2 vCPU.** 45–50 rps usable,
99.19–99.22% CPU cold and 83% warm, with everything else ruled out at one-minute resolution — RDS
at 14–33%, the injector at 3–22% of four cores, load average 0.00.

**But `ReadIOPS` was 0.0 and `ReadLatency` 0.0 throughout.** Case 1's organisation holds no field
data, so that ramp saturated on JSON serialisation of config and `syncDetails` with nothing read
from disk at all. Every other case pulls 10,800 to 43,300 records out of 6.9M rows. There is no
reason to expect the same resource to bind, and a single data-path ramp confirming "it is CPU
again" would be a finding, not a foregone conclusion.

So the iterations vary one dimension each, chosen so that a different answer implicates a
different resource:

| | ramp | what a lower knee here would implicate |
|---|---|---|
| **12a** | ten tenants, realistic mix | the baseline. Is the data path CPU-bound like case 1, or does it bind earlier? |
| **12b** | the same, `SYNC_MODE=full` | bytes per request, not requests. Moves the pressure to RDS, the buffer cache and `ReadIOPS` — the three case 1 could not exercise |
| **12c** | the same, push on | the write path: WAL, lock contention, autovacuum. Still entirely unmeasured |

**Two things to control for, both from case 1's own findings.** **Warm the server first** — cold
gave a third of the throughput and the only failures this environment has produced, so a cold ramp
finds a knee that is not real. And **expect the connection pool to look like the cause when it is
the symptom**: connections pegged at exactly 100 in the cold run, which follows from slow requests
rather than producing them.

**Read these as Phase 5's loop starting early, not as three runs.** The method there is saturate,
name the resource, relieve it, re-run — and with a 2 vCPU app tier already saturating on the
cheapest request the suite can make, "raise the app tier" is a plausible first relief, after which
the interesting knees are whatever sits behind it. Running 12a–c before any relief is what makes
the first "name the resource" step cost three ramps rather than a redesign.

**A fourth would isolate F2.1**, which is still a code-read hypothesis with no measurement against
it: the same ramp single-tenant against ten-tenant at matched rps, to price the organisation
interceptor's three round trips per connection borrow. Worth it only if 12a–c leave multi-tenancy
as the live suspect.

**What the order is actually constrained by**, since the rest is preference:

* **1 and 14 push nothing**, so they are free at either end of a block and cost no reset.
* **D7 before anything is quoted.** 93–94% of every duration is modelled; until it was measured,
  every published figure was provisional. It needs one device, not a quiet server, so it costs
  nothing to place early.
* **3 before 4**, so per-device cost is known before the mix.
* **5 and 11 before the co-tenants exist.** Case 5 is separate hosting — "nobody else's data in
  the tables" — and 11 is its day compressed. Provisioning 513 organisations before them would put
  ~262,000 config rows in the database and make 5 → 6 a comparison of their *data* rather than of
  their presence.
* **The validation pair before anything leans on the block ordering**, because every later
  adjacency assumes it.
* **9 last in A, and its three ramps in the order given.** The knee is only interpretable once the
  unstressed shape is known, and whatever the ramps leave behind is cleared by B's reset — which
  is also why 12c can turn push on without costing a reset of its own. 12a before 12b and 12c
  because it is the one with a comparator: every other case ran the realistic mix, so a knee there
  can be read against them.
* **12 and 13 after 6 and 7**, read against 11 and each other, with no reset between.
* **8 is three dataset loads**, one per growth point, so it cannot share a block. Day 180 reuses
  case 4.
* **A′ last.** It answers a sensitivity rather than a target, and it is the work that gets dropped
  first if B's reset projection turns out wrong — a wrong reset makes every Block B number
  incomparable, while a missing span-20 point leaves the span an interpolation between a measured
  8.4 and a specified 20, which is what it was before.

### D7 — the client storage measurement

**93–94% of every sync figure this exercise reports is a model.** `pausedMs` is computed from
records pulled; `baseMsPerRecord` is 0.61 and the simulation says plainly what it is — *"derived
from the ceiling rather than measured … a deliberate upper bound"*, chosen to put the heaviest
possible page just under `MAX_STORAGE_PAUSE_MS`. Case 14's 80 s and case 3's 223 s rest on it.

**The real client already measures the right quantity, and the loadtest environment can be its
target.** `sync-simulation-plan.md` has D7 *"waiting on fleet rollout and data accumulation"*; it
need not be. One device against this environment answers it in an afternoon, because avni-client
18.0 records per entity, per page:

| field | source | what it is |
|---|---|---|
| `networkMs` | `requests.js` | fetch through response text — network and server |
| `parseMs` | `requests.js` | `JSON.parse` alone, deliberately: *"text() then JSON.parse rather than json(), so parseMs is the parse and nothing else"* |
| `persistMs` | `SyncService.persistAll` | transform and write, *"taken after the batch path's await, so persistMs covers the write on either backend"* |
| `numberOfPulledEntities` | same dispatch | records in that page |

So the comparison is **`(parseMs + persistMs) / numberOfPulledEntities`** against `StorageProfiles`
for the five observation-bearing entities and 0.61 for the rest — per entity, where the model has
one aggregate. `networkMs` is excluded deliberately: the simulation pays network and server for
real, and folding them into a pause is the double-count the `baseMsPerRecord` comment attributes to
Q1. These accumulate into `SyncTelemetry`, which syncs to the server, so the readout is a query
against `sync_telemetry` rather than anything pulled off the device.

**Why 18.0 and not 17.3.** 17.3 is Realm-only; 18.0 opens both engines and chooses per user —
`computeDesiredBackend()` returns SQLite only for members of the `SQLite Migration` group. One
build and two users therefore measure both engines against the same server, the same dataset and
the same client code, where two branches would confound the storage engine with every other
difference between releases. 18.0 is also one models patch from 17.3 (1.33.84 against 1.33.83), and
**`EntityMetaData.js` is byte-identical across 1.33.81 to 1.33.86** — so the entity set matches the
harness's own table of 79 entities with 75 pulled, and per-record figures compare directly to cases
2, 3 and 14.

**Three things must be in place before the environment comes up, or this slips a day:**

1. **The operator's address in the security group.** The application port is allowlisted to the
   injector alone, and deliberately — under `AVNI_IDP_TYPE=none` anyone who can reach it is
   authenticated as whatever username they send. Add the one address, not an open rule.
2. **A `SQLite Migration` group containing the second test user**, which is what flips the backend.
3. **Two users chosen from the pilot** — a field worker and a supervisor, roughly 10,800 and 30,000
   records, the two the model currently claims 80 s and 223 s for.

No client code changes are needed: `AuthService` returns `stubbedAuthService` under
`IDP_PROVIDERS.NONE`, which accepts any password and sends the username as `USER-NAME`, and the
server URL is a settings field.

**What it decides.** If the measured per-record cost is near the model, four findings documents
stand as written. If it is not, their headline durations are wrong by whatever the gap is, and the
server-side numbers — `serverMs`, records, p95 — are the only part that survives. Either way it is
one morning, and every case after it is read differently.

> **The supervisor span is the outermost loop, and it is settled at two points.** Blocks A, B and
> C above all run on `pilot-day-180` — span **8.4**, Q13's measured establishment. Block A′ repeats
> the span-sensitive cases on `pilot-day-180-span20`. Both datasets are generated and staged; what
> the sweep still costs is runs and one reload.
>
> **Why it is a block and not a flag.** The span sets how many supervisors exist and how wide each
> catchment is — users, catchments and their address mappings, all structural rows loaded with the
> dataset. A run cannot switch between them, so the span cannot vary inside a block; it has to
> bracket them.
>
> **Only cases 3, 4 and 5 repeat.** They are the ones whose cohort the span defines. Cases 6, 7 and
> 12–13 vary tenancy and 8 varies growth, and running either against a second span makes a
> difference unattributable to one cause — a two-factor sweep costs four blocks to answer a
> question nobody asked. If one span-20 result shows the span matters more than this expects, that
> is the finding that justifies widening it, in Phase 5.
>
> **It costs a day, and the schedule has exactly one spare.** Block A′ is what that spare buys.
> That is a real trade: if the reset projection is wrong at ten tenants, absorbing that and the
> span sweep want the same day. **Drop the span sweep, not the reset** — a wrong reset makes every Block B
> number incomparable, while a missing span-20 point leaves the span an interpolation between a
> measured 8.4 and a specified 20, which is what it was before.

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
