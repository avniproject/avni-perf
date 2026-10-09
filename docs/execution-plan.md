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

**Status as of 9 Oct 2026.** Phases 0–3 complete. In Phase 4, Block A is done except the soak
(**10**) and the stress ramp (**9**); case 11 has run at 1,682/h, at 550/h four times, and at a
15-minute window. Block B is **blocked** — the co-tenant dataset has never been generated. Block C
is ready whenever: the day 60/120/365 archives are in S3. Run-by-run state is in
**[The sequence](#the-sequence)**; results are in [`run-log.md`](run-log.md) and the
`findings-*.md` files. The dataset currently carries push residue from 9 Oct's six pushing runs
and should be reloaded before anything that turns on a small delta.

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
encounters, so it is comparable in size to the pilot dataset itself, and nobody has measured what
loading it costs. **Size it before Day 10 commits to the shape.** The ordering below is built so it
is loaded once and never unloaded.

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
> **The cost of that is a step nobody has timed.** Block B now opens with 513 bundle imports
> as well as its reset, load and two runs, and a single `provision-org.sh` against this bundle has
> never been measured — 513 x 10 s is 85 minutes and 513 x 60 s is 8.5 hours, which are different
> days. **Time one as the first act of Block B**, before committing the rest of the day to it.
> Three bundles are involved, not one, so the large-pull-heavy import is the one to time.

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
| 1 | A | **1** — training cohort, 30 min, swept across arrival windows 900 s to 15 s | done, 10 runs |
| 2 | A | **14** — full sync, 90 min | done |
| 3 | A | **2** — field workers, 4 h | done |
| 4 | A | **3** — supervisors, 2 h driven | done |
| 5 | A | **4** — combined, 4 h | done; first attempt sampled one role and is not a measurement |
| 6 | — | **D7** — client storage, device, Realm and SQLite | done |
| 7 | A | **5** — ten tenants, 2 h | done |
| 8 | A | **11** — clustered, 1 h | done at the full 1,682; saturated |
| 9 | A | **11 twice, back to back, no reset** — the block-strategy validation | **done 9 Oct — inconclusive.** Five runs (A/B, C/D, plus a `PUSH=off` control E) at 550/h. The harness is not reproducible, so a pair cannot resolve drift — [`findings-case11-pair.md`](findings-case11-pair.md). Resolved without it: see *Resolved 9 Oct 2026* |
| 10 | A | **10** — soak, 12 h, overnight | **next.** Needs `env-teardown.sh hold` so `stop-idle` does not kill it mid-run |
| 11 | A | **11 at a 15-minute window**, 15 min | **done 9 Oct, ahead of 10.** Scaled to 400 users (1,600/h) rather than the full 1,682, so the backlog is 400 syncs not 1,682. Reaches 18.5 rps, not the ~35 predicted — saturates on app CPU — [`findings-case11-burst.md`](findings-case11-burst.md) |
| 12 | A | **9** — stress ramp, until it breaks | |
| 13 | B | **Provision 513 organisations**, import each one's archetype bundle, re-dump `refs.sql`, generate and load the co-tenant data | **blocked.** `co-tenants-day-180.json` has never been generated: `bundle_path` is still the placeholder and `--bundle-root` needs one extracted bundle per archetype (none present locally). This gates all of Block B |
| 14 | B | **6** — co-tenants present, 2 h | |
| 15 | B | **7** — co-tenants syncing, 2 h | |
| 16 | B | **12** and **13** — clustered, 1 h each | |
| 17 | C | **8** — growth, 2 h each at day 60, 120 and 365 | |
| 18 | A′ | Reload `pilot-day-180-span20`, split with `--variant span20`, re-run **3**, **4**, **5** | |

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
* **9 last in A.** The knee is only interpretable once the unstressed shape is known, and whatever
  it leaves behind is cleared by B's reset.
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
