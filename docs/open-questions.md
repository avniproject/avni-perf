# Open questions

Everything [the sync simulation plan](sync-simulation-plan.md) and
[the test scenarios](test-scenarios.md) are waiting on.

**This document holds the inputs only** — the questions someone has to answer before the tests can
be designed, built or run. No amount of running will settle them. **Three remain.**

Work is not a question, so it is not here. Anything outstanding that someone could simply go and do
is a task in [the plan](sync-simulation-plan.md), and the status table at the top of that document
says what has and has not been started.

The questions the tests *answer* are a different kind and live in
[the plan](sync-simulation-plan.md#what-the-tests-will-answer), because they are what the exercise is
for rather than something it is waiting on. Conflating the two is how work like this goes wrong: an
output answered in advance is precisely what the exercise was built to replace.

Answering one means editing the section named against it. This document is an index, not a second
source of truth.

---

## The questions

Ordered by how much turns on the answer.

### 1. Which tier supervises?

**Assumed: an ANM at a sub-centre, covering 8 field workers.**
Blocks test cases 3–8 and the generator's catchment sizing.

**This is the one that changes what the exercise measures.** At sub-centre level a supervisor holds
37,200 records at day 180 — 0.14× the heaviest device production has already seen — so no case
exceeds production's existing tail and this becomes a test of concurrency and tenancy. At block level
a supervisor holds 920,000, which is **3.5× that device**, and it becomes a test of volume as well.

| Tier | Field workers each | Records at day 180 | Full sync | vs production's heaviest |
|---|---|---|---|---|
| Sub-centre | 8 | 37,200 | 5.7 min | 0.14× |
| PHC | 45 | 207,000 | 32 min | 0.78× |
| Block | 200 | 920,000 | 141 min | 3.5× |

### 2. How often does a worker sync?

**Assumed: 4 times a working day.** Blocks every arrival rate in the test cases.

**Three figures are in play and they span two orders of magnitude.**

| Source | Frequency | Platform-wide, per hour |
|---|---|---|
| **The requirement** | **once a week** | ~20 syncs, 0.08 in flight |
| This document's assumption | 4 a working day | ~564 syncs, 2.2 in flight |
| Production today (Q2) | median gap of **16 minutes** | — |

For scale, production's busiest hour ever recorded was 792 syncs.

**The requirement and the measurement are probably not in conflict.** Once a week reads as a floor —
the longest a device may go without syncing — rather than a description of what field workers do.
Production's own p75 gap is 12.5 hours and its p99 is 8.2 days, so roughly 1% of real gaps exceed a
week, which is about what a weekly minimum would produce.

**If weekly is what the deployment expects, this exercise changes shape.** Arrival rate falls to
around 20 syncs an hour across every tenant — a fortieth of production's peak — and **fewer than one
sync is in flight at any moment**, so concurrency stops being worth testing at all. What remains is per-sync cost and tenancy, which cases 5, 6 and 7 already
target.

**The payload barely moves, which is the part worth knowing.** A longer gap means more accumulated
changes per sync, but not many: a field worker's village produces 60 encounters a day, so a weekly
sync carries around 420 records against 15 for a four-a-day one, and a supervisor 1,120 against 40.
Both sit far inside the light band where 98% of production's syncs already live. **So frequency
drives the arrival rate and almost nothing else** — which is why this needs an answer rather than a
midpoint.

### 3. What error rate is acceptable under load?

Blocks the last unfilled row of the Success criteria table.

**The only success criterion no query can supply** — everything else in that table is now measured.
A6 is built and takes it as `MAX_FAILED_PERCENT`, so this is a number to choose rather than code to
write.

---

## Measurements

**Fourteen of fifteen appendix queries have run.** Results are recorded against each one in
[production-measurement-queries.md](production-measurement-queries.md) and interpreted in the plan
section that uses them.

| What | State |
|---|---|
| **Q11 — fleet page size split** | **Not answerable.** `pageSize` is not recorded in `sync_telemetry`, so it needs a client change first (D8.3) |
| **Locations per catchment in production** | **No query written.** The generator declares one location per catchment and real bundles carry three. Changes the mapping table's size and the expansion view's work, not what anyone syncs |

---

## Assumptions carried, that nobody is being asked about

They would change conclusions if false, so they are listed rather than buried.

| Assumption | Where | Why it is held |
|---|---|---|
| All of this customer's organisations behave alike, so one usage pattern covers them | [test-scenarios.md](test-scenarios.md) | The customer's own, recorded as theirs |
| A generated dataset can stand in for production data | H6 | An anonymised clone is not available. Settled rather than open — but it makes H5's validation the only thing that will catch an unrealistic generator |
| Sync is the whole exercise | Closed questions | State-wide search is explicitly out of scope. **A passing sync run is not clearance for search**, because search cost grows with tenant size where sync cost grows with catchment size |
| The three growth datasets differ only in encounter count | [test-scenarios.md](test-scenarios.md) | Beneficiary population does not grow with programme activity |
| A catchment is declared against one location | H · `tools/data-generator` | A generator default, not a platform constraint — the mapping table is many-to-many and real bundles carry three locations per catchment |

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

**This decision left one thing unexercised, so a case was added for it.** Configuration size drives
the `syncDetails` row count and therefore D1.1's per-row queries — Q8 measured 79 entities tracked
against 4 changed, so 94% of that work proves nothing changed, and the cost grows with the
configuration rather than with the data. Nothing else varies it, so **case 11** runs case 1 against a
small bundle and a large one. It needs no generated data at all.

### Distributed injectors

**Deferred. One injector until something says otherwise.**

Gatling OSS has no orchestration, so multiple injectors mean merging logs by hand — real work for a
problem nobody has yet. **The signal to revisit is the injector showing up in its own results**:
saturated CPU on the load generator, or response times that rise with virtual user count while the
server's own metrics stay flat. F7's calibration gate is where that would surface. Scope it then, not
now.

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
list.

- **Production statistics access** — granted; fifteen queries written, fourteen run.
- **On-demand media viewing** — out of scope. A browsing workload, not a sync one.
- **Anonymised production clone** — not available. Generation is the path.
- **State-wide facility search** — out of scope, with the caveat above.
- **Webapp and API consumers** — separate query paths; keeping to sync is correct.
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
