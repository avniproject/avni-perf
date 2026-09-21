# Open questions

Everything [the sync simulation plan](sync-simulation-plan.md) and
[the test scenarios](test-scenarios.md) are waiting on.

**This document holds the inputs only** — the questions someone has to answer before the tests can
be designed, built or run. No amount of running will settle them.

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

### 2. How often does a worker sync per working day?

**Assumed: 4.** Blocks every arrival rate in the test cases.

Nothing measured or supplied gives a figure. **Every arrival rate scales linearly with it**: at 2 a
day the platform peaks near 350 syncs an hour, at 8 near 1,400, against production's record of 792.

### 3. What error rate is acceptable under load?

Blocks the last unfilled row of the Success criteria table.

**The only success criterion no query can supply** — everything else in that table is now measured.
A6 is built and takes it as `MAX_FAILED_PERCENT`, so this is a number to choose rather than code to
write.

### 4. Is "500 workers" field workers only, or all users?

**Assumed: field workers, with 62 supervisors added per state tenant on top.**
Blocks the deployment table and user provisioning.

If it is the total, the deployment is 11% smaller.

### 5. Is 500 workers the pilot, the first year, or the design target?

**Assumed: a pilot.** Blocks the scope of every conclusion rather than the build.

A real state runs 165,000 ASHAs, so 500 is 0.3% of one. **Nothing in a 500-worker result
extrapolates upward** — tenant data volume grows with worker count, and sync cost follows it through
index size and cache residency.

### 6. Which organisation configuration(s) to run against?

Blocks H1 and F5.1, though not building anything.

The generator takes the bundle as a parameter and supports **one per tenant**, so the mechanism
exists. What is open is the choice. Worth covering a range of sizes deliberately: configuration size
drives the `syncDetails` row count and therefore D1.1's per-row queries, where Q8 measured 79
entities tracked against 4 changed.

### 7. Distributed injectors — needed, or not?

Blocks F3.

Gatling OSS has no orchestration, so multiple injectors mean merging logs by hand. One injector may
well carry the whole deployment's load. Measure before building for it.

### 8. Over what period?

Blocks sequencing. Ownership is settled; the order in the Sequencing table reflects dependencies
rather than a calendar.

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

## Waiting on something, not on an answer

Not questions. Work that cannot proceed until something else exists, listed so it is not mistaken for
an open decision.

| What | Waiting on |
|---|---|
| **H5 steps 3–4**, the manual client check | A loaded dataset and a device. The automated half is built, and a dataset passing only that half is **loadable, not blessed** |
| **The generator's column and metadata dumps** | A target database with a bundle loaded. `columns.sql` and `refs.sql` are written |
| **Production's tenant skew** | A decision to build it. Cases 6 and 7 need it, so the hosting comparison cannot run until it exists |
| **Q7c's index usage, re-read later** | Nothing — it has run. Worth repeating after any index change, since `idx_scan` counts only since the server last restarted |

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
