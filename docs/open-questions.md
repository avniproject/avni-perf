# Open questions

Everything [the sync simulation plan](sync-simulation-plan.md) and
[the test scenarios](test-scenarios.md) are waiting on.

**This document holds the inputs only** — the questions someone has to answer before the tests can
be designed, built or run. No amount of running will settle them.

Nothing else lives here. **Work** someone could simply go and do is a task in
[the plan](sync-simulation-plan.md), whose status table says what has and has not been started.
**Measurements** are tracked per query in
[production-measurement-queries.md](production-measurement-queries.md), which records what each one
returned or why it has not run.

The questions the tests *answer* are a different kind and live in
[the plan](sync-simulation-plan.md#what-the-tests-will-answer), because they are what the exercise is
for rather than something it is waiting on. Conflating the two is how work like this goes wrong: an
output answered in advance is precisely what the exercise was built to replace.

Answering one means editing the section named against it. This document is an index, not a second
source of truth.

---

## The questions

### How many supervisors sit above sub-centre level, and at which tiers?

**Assumed: all of them at sub-centre, covering 8 field workers each.** Being asked of the customer.
Blocks test cases 3–8 and the generator's catchment sizing.

**It is not one choice but a mix.** Supervision can sit at any level above the sub-centre, and a
real establishment probably has some at each. What the cases need is how many at each tier, because
per-device volume changes by an order of magnitude between them:

| Tier | Field workers each | Records at day 180 | Full sync | vs production's heaviest device |
|---|---|---|---|---|
| Sub-centre | 8 | 37,200 | 5.7 min | 0.14× |
| PHC | 45 | 207,000 | 32 min | 0.78× |
| Block | 200 | 920,000 | 141 min | **3.5×** |
| District | ~2,200 | — | — | far beyond |

**Volume per device is the risk this sets.** With sync frequency confirmed at once a day,
concurrency is settled — the deployment produces under one sync in flight — so how much any single
device carries is what is left, and this is the number that decides it. If everyone supervises at
sub-centre, no case exceeds what production already carries and the exercise confirms the server
holds. If a handful supervise at block level, those few devices are individually heavier
than anything production has measured, and the exercise is about them.

**A handful is enough to matter.** These are not averages over a population: one block-level
supervisor carries 920,000 records whatever the rest do, so the answer needed is a count per tier,
not a typical case.

---

## Scope, and what expanding it would mean

**The current scope is sync.** Not because sync is the only thing that matters, but because it is
one coherent path that can be measured properly, and the paths below were set aside to keep it
that way.
Each is additive: the harness, the dataset and the environment all serve them too, so bringing one
in is a new set of scenarios rather than a new exercise.

| Out of scope | Why it was set aside | What bringing it in would need |
|---|---|---|
| **State-wide facility search** | Cost grows with total tenant size where sync's grows with catchment size, so it scales differently and would need its own sizing | Scenarios against `/web/*` search endpoints, and a dataset sized to the searchable set rather than to catchments |
| **Webapp and API consumers** | Separate query paths — the webapp uses `/web/*` and touches only two sync-style endpoints, both reference data | Scenarios per endpoint. The same dataset serves them |
| **On-demand media viewing** | A browsing workload driven by what users open, not by sync | A real bucket with objects in it, and a model of viewing behaviour that nothing currently measures |

**One consequence travels with the boundary rather than with any one item.** A clean sync result says
nothing about the three above, and search is the one where that matters most: its cost scales with
the thing sync is insulated from. **A passing sync run is not clearance for search at state scale**,
and the temptation to read it that way is exactly why the boundary is written down.

---

## Assumptions carried, that nobody is being asked about

They would change conclusions if false, so they are listed rather than buried.

| Assumption | Where | Why it is held |
|---|---|---|
| All of this customer's organisations behave alike, so one usage pattern covers them | [test-scenarios.md](test-scenarios.md) | The customer's own, recorded as theirs |
| A generated dataset can stand in for production data | H6 | An anonymised clone is not available. Settled rather than open — but it makes H5's validation the only thing that will catch an unrealistic generator |
| The three growth datasets differ only in encounter count | [test-scenarios.md](test-scenarios.md) | Beneficiary population does not grow with programme activity |
| A catchment is declared against one location | H · `tools/data-generator` | A generator default, not a platform constraint — the mapping table is many-to-many and real bundles carry three. **Q16 will settle it** |

---

## Decided, and why

Answers rather than absences. Kept because each one shapes something downstream, and a decision with
no visible reasoning gets relitigated.

### Which organisation configurations to run against

**Two shapes, matching the two hosting models the cases compare.**

- **Separate hosting** — the customer's tenants, all on a **similar configuration and similar load**.
  There is no reason to vary them: on their own infrastructure, nobody else's shape affects them.
- **Shared hosting** — the same tenants, plus **production's existing organisation skew** as it
  actually is: 986 organisations, 48% holding nothing, the largest holding 21% of all subjects
  (Q12).

That is not two settings of one dial; it is **two tenant-shape specifications the generator has to
produce**. The first it already builds. The second is the outstanding generation run that cases 6
and 7 wait on.

**A case was briefly added for what this left unexercised, then dropped.** Configuration breadth
does move the `syncDetails` row count, but by less than it looked and without needing its own run:
55 of Q8's 79 entities are added flat whatever the configuration holds, the per-row checks are
independent so the relationship is linear, and **case 1 already measures the per-row cost** — a
broader configuration is then arithmetic. Tripling the row count adds around 6% of one sync. If case
1 shows `syncDetails` is a large share of a config-only sync, a breadth variation earns its place.

### Distributed injectors

**Deferred. One injector until something says otherwise.**

Gatling OSS has no orchestration, so multiple injectors mean merging logs by hand — real work for a
problem nobody has yet. **The signal to revisit is the injector showing up in its own results**:
saturated CPU on the load generator, or response times that rise with virtual user count while the
server's own metrics stay flat. F7's calibration gate is where that would surface. Scope it then, not
now.

### Sync frequency: once a working day

Confirmed. Not the four a day this work assumed, and not the once a week the requirement states —
that reads as a floor, and production's own 16-minute median gap as within-session behaviour.

**Every arrival rate divides by four, and the result is striking.**

| Case | Syncs/hour | In flight | Was, at 4/day |
|---|---|---|---|
| 2 · field workers, one tenant | 42 | 0.16 | 0.7 |
| 4 · combined, one tenant | 47 | 0.18 | 0.7 |
| 5 · all ten tenants | 141 | **0.55** | 2.2 |
| 6, 7 · ten tenants plus production active | 933 | 3.65 | 5.3 |

**The customer's entire deployment produces under one sync in flight at any moment**, against
production's own busiest hour ever recorded at 3.1. Every single-tenant case runs at a fifth of that.

So this is unambiguously not a concurrency exercise. It measures per-sync cost, data volume and
tenancy — and **the only case where the server sees meaningful simultaneous load is one where
production's own traffic supplies most of it**. Worth saying plainly to whoever reads a green
result: cases 2, 3 and 4 passing says almost nothing about contention, because there is none to
contend with.

A day's accumulation is what each sync carries: 60 records for a field worker's village, 160 for a
supervisor's sub-centre. Both sit far inside band 1, where 98% of production's syncs already live.

### Acceptable error rate: 0.05%

Confirmed, and it fills the last measurable row of the Success criteria table. A6 takes it as
`MAX_FAILED_PERCENT`, so it is the harness default rather than a number to remember.

What it permits, at 81 requests a sync:

| Case | Requests/hour | Failures allowed |
|---|---|---|
| 4 · combined | 3,794 | **1.9/hour** |
| 5 · all ten tenants | 11,421 | **5.7/hour** |
| 6, 7 · with production active | 75,573 | 37.8/hour |

**At these volumes a single flapping entity breaches it**, which is the point: 0.05% against an
81-request sync means roughly one sync in twenty-five may lose one request. A run that fails this
has a fault, not noise.

### 500 workers is the pilot

Confirmed. It scopes every conclusion this exercise produces, and the scoping is sharper than it
sounds: **a state runs 165,000 ASHAs, so the pilot is 110× smaller in workers and in beneficiaries
alike.**

| | Workers | Beneficiaries |
|---|---|---|
| Pilot, whole deployment | 1,504 | 1,506,000 |
| One state | 165,000 | 165,000,000 |

**Nothing in a pilot result extrapolates to a state on its own.** Sync cost follows data volume
through index size and cache residency, and those do not scale linearly — an index that fits in
cache and one that does not behave differently in kind, not in degree.

**The stress ramp does not close that gap, and it is worth being clear about why.** Case 10 ramps
*arrival rate* against a pilot-sized dataset. What will not extrapolate is *data volume*. Ramping
users harder against 1.5 million beneficiaries says nothing about 165 million.

**The growth comparison is the only evidence available**, and it should be read as exactly that. Case
8 runs the same load against day 60, 120, 180 and 365 — **day 365 was added for this reason**, because
three points over 180 days is a short baseline for a curve carrying the whole extrapolation question.
If cost is flat across all four, that is weak evidence it stays flat further out. If it bends, the
bend is the finding and the pilot has already told you something about the state.

**Testing a state directly is not currently practical.** A state-sized day-180 dataset is around 759
million rows — five hours to generate at the measured rate, and roughly 220 GB on disk against the
pilot's 2 GB. If a statement about state scale is ever needed, that is the size of the ask, and it is
a separate exercise.

### Over what period the work runs

**Not an open question, and previously listed as one in error.** Ownership is settled and the
Sequencing table orders by dependency, so nothing in the design, the build or the execution is
waiting on a date.

Worth separating from something it reads like: the **day 60, 120 and 180** datasets are *data ages*
the tests run against, not a project calendar. All three exist at once, and they are compared in a
single sitting rather than across six months.

---

## Closed

Recorded briefly so none of it gets relitigated. Full reasoning is in the plan's own closed-questions
list. What is out of scope is in **Scope** above rather than here, because scope is a boundary that
can move rather than a question that was settled.

- **Production statistics access** — granted. [Which queries have run](production-measurement-queries.md#what-has-run) is tracked there.
- **Anonymised production clone** — not available. Generation is the path.
- **Token expiry across a long sync** — a harness limitation only. The real client refreshes per
  request, so a multi-hour sync is fine for it.
- **Perf environment isolation** — designed, not an unknown.
- **Rolling data** — year two accrues at year one's rate, with nothing ageing out.
- **Reset storm** — **not modelled.** The week Q10 found at 130× the normal rate is
  `avni-client#2115`, a reset that re-arms itself when the following sync does not complete. Testing
  it would measure a defect rather than a workload. Normal reset volume is a trickle onto the
  full-sync path, which the 1% fresh-sync mix already covers at a higher rate.
- **Is "500 workers" field workers only?** — **yes, field workers only.** Supervisors are added on
  top, so a state tenant is 500 plus 62. The deployment table stands as written.
