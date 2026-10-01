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

**How many times this is paid.** Every case except 1 runs with the push path on, so every run
leaves the dataset mutated and the next needs a pristine start. There is no sharing a reset
between runs.

| | runs | on |
|---|---|---|
| cases 1–7 | 7 | one empty, three on two-state day-180, three on ten-tenant ± co-tenants |
| case 8, growth | 3 | day 60, 120, 365 — day 180 reuses case 4's result |
| cases 9–13 | 5 | ten-tenant ± co-tenants |
| **Phase 4** | **15** | |
| Phase 5, four to six iterations | 4–6 | |
| **total** | **~20**, of which ~19 would need a reset first | case 1 has no field data and does not push |

At the projected ~21 min for a ten-tenant reset, **19 resets is about 7 hours** of reset time
across Phases 4 and 5; by the teardown path it is 11–12. So a mechanism that saves ten minutes a
reset saves better than three hours of the exercise, which is what Day 9 is actually deciding.

> **Superseded by the block ordering, 1 Oct 2026: it is about ten resets, not nineteen.** Phase 4
> needs five — one per block plus case 8's three dataset swaps — and Phase 5's four to six stay
> one per run, because re-measuring after a fix is the point of them. The arithmetic above is kept
> because it is what Day 9's decision was made against, and a mechanism that saves ten minutes a
> reset is worth less when there are half as many resets. `truncate` still wins: at 388 s measured
> against the teardown's 1,013 s, five resets is 32 min against 84.

**The co-tenant datasets are the gap in that arithmetic.** Cases 6, 7, 12 and 13 need 513 further
organisations present — the ones of Q12's 986 that hold data. The other 473 would be bare
`organisation` rows; `co_tenants.empty_rows()` builds them, nothing calls it, and 1 Oct 2026
decided to leave it that way. `co-tenants-day-180` is 513 tenants and 3.13M
encounters, so it is comparable in size to the pilot dataset itself, and nobody has measured what
loading it costs. **Size it before Day 10 commits to the shape.** The ordering below is built so it
is loaded once and never unloaded.

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

**The reload was faithful**, which is the part worth checking rather than assuming: both state
tenants came back at **501,000 subjects and 1,799,926 encounters** each, and day 180 specifies
500 workers x 20 encounters x 180 days = 1,800,000. **Organisation 3 came back empty**, which is
correct and is the mechanism's known cost — `TRUNCATE` cannot distinguish tenants and only the two
state datasets were reloaded. Its small dataset needs its own reload if it is wanted.

> **The `audit` row count is not yet reconciled, and this result should not be read as confirming
> the cleanup is correct.** The run reported `audit` holding one row. That cannot be a row count:
> the trigger writes one audit row per inserted row, and the reload had just written about 2.3M
> rows into each of two organisations, so `audit` should hold roughly 4.6M. Two readings, and they
> are not close together. Either the figure means the count query returned one row — in which case
> the mechanism worked and the table is at its intended steady state — or `audit` really does hold
> one row, in which case the delete removed the metadata's audit rows as well as the orphans, and
> **it would have done so silently**, because referential integrity is suppressed for that
> statement. 42 tables would be left with `audit_id` values pointing at nothing, reads would not
> notice, and the environment would look healthy.
>
> Settling it needs `select count(*) from audit` and a dangling-reference check against `concept`,
> `form` and `form_element`. Deferred 1 Oct 2026 with the environment down. **Until then the 49 s
> is a measurement of something whose correctness is unestablished**, and the timing above should
> be trusted ahead of the conclusion.

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

## Phase 4 — Execution (Days 12–20)

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

The first calendar ran case 7 on Day 15 and then **11, 12, 13** on Day 16. Case 11 is in the
*separate* hosting group, so it needs the co-tenants **gone**, and 12 and 13 need them back. That is
an unload of 513 organisations — a `DELETE` teardown of a dataset holding 3.13M encounters — and a
reload, hidden inside one day of the calendar, to serve a single one-hour run.

**Moving case 11 next to case 5, before the co-tenants are ever loaded, makes their presence a
one-way door.** Load once, never unload. That is the single largest saving here and it costs
nothing.

### The blocks

| Block | Reset | Runs, in order | Why this grouping |
|---|---|---|---|
| **A — separate, day 180** | one, at the front | **1, 2, 3, 4, 5, 11, 10, 9** | Case 1 pushes nothing, so it is free at either end. 3 before 4 so per-device cost is known before the mix. 11 here rather than after 7, so co-tenants are never unloaded. 10 overnight. **9 last, because it breaks things** and Block B's reset cleans up after it |
| **B — co-tenants** | one, plus the co-tenant load | **6, 7, 12, 13** | The reset before 6 restores the customer's tenants to exactly case 5's starting state, which is what makes the 5 -> 6 delta mean anything. 6 -> 7 then carries ~7,700 rows of drift, 0.11% |
| **C — growth** | three dataset swaps | **8** at day 60, 120, 365 | Day 180 reuses case 4's result. These are different datasets, so the loads are not avoidable |

**Five resets for fifteen runs, against fifteen.** With Phase 5's four to six re-measurements, which
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

### The one measurement that would validate it

Run **case 11 twice, back to back, with no reset**. One hour each. If per-sync record counts and p50
duration agree within noise, the block strategy holds for every adjacency in it, because 11 is the
heaviest pusher of the set at ~46,200 rows. **Two hours to de-risk the three, and it is the only
part of this that is an assumption rather than arithmetic.**

> **Considered and rejected: making case 8's growth datasets nest**, so day 60 could be appended to
> rather than reloaded. It does not work as the generator stands. `band_width(tenant, days)` scales
> with `days`, so day 60 and day 120 allocate different id bands and neither is a prefix of the
> other. It could be made to work by sizing every band for day 365 — about 22M ids, comfortably
> inside int4 — but it also needs rows emitted in day order so the smaller sets are genuine
> prefixes. That is a generator change with real risk to save roughly an hour.

| Day | Block | Cases | Why here |
|---|---|---|---|
| **12** | A | **1** (training cohort, 30 min), then **2** (field workers, 4 h) | Case 1 is config-only and the cheapest real load. Case 2 is the common case and the baseline everything else is read against |
| **13** | A | **3** (supervisors, 2 h driven) and **4** (combined, 4 h) | Case 4 is *the* realistic case. Case 3 first so its per-device cost is known before the mix |
| **14** | A | **5** (ten tenants, 2 h) and **11** (clustered, 1 h) | Both are separate-hosting, so they run before the co-tenants exist. 11 is case 5's day compressed into an hour; the sync window is unconfirmed and these are the two ends of the bracket |
| **14–15** | A | **10** (soak, 12 h, overnight) | Needs the instance to itself. Case 4's load sustained, so the block's residue is immaterial to it |
| **15** | A | **9** (stress ramp, until it breaks) | Last in the block: the knee is only interpretable once the unstressed shape is known, and whatever it leaves behind is cleared by Block B's reset |
| **16** | B | Reset, load the co-tenants, then **6** (2 h) and **7** (2 h). Analyse 5/6/7 together | 5 -> 6 is the cost of their presence, 6 -> 7 the cost of their activity. The reset is what makes 6 comparable with 5 |
| **17** | B | **12** and **13** (clustered, 1 h each) | The same two tenancy shapes with the day compressed. No reset: 12 and 13 are read against 11 and against each other |
| **18–19** | C | **8** (growth, 2 h x 3 — day 60, 120, 365) | Three dataset loads, one per point. Day 180 reuses case 4 |
| **20** | — | Slack | Day 9 measured the reset at a two-tenant scale; at ten tenants it is projected. If the projection is wrong this is where it is absorbed |

> **Two supervisor spans, not one.** Cases 3 to 8 are specified across an 8-to-20 worker span, which
> changes both the supervisor count and each catchment's width. **Run the ends, not the middle** —
> the low end is the most concurrent, the high end holds the heaviest device. That doubles those
> cases if both ends are wanted; decide at Day 13 whether the budget is there.
>
> **It also doubles the datasets, not just the runs.** The span changes how many supervisors exist
> and how wide each catchment is, and both are structural rows — users and catchments, not
> transactional. Switching spans is a re-provisioning rather than a reload, so the two ends are
> two blocks, not two runs inside one.

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
