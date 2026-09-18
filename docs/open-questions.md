# Open questions and assumptions

Everything the [sync simulation plan](sync-simulation-plan.md) is waiting on, in one place, grouped
by who can answer it. Each entry says what it blocks and what happens if the assumption is wrong,
because that is what decides whether it is worth anyone's time.

Answering a question means editing the plan section named against it. This document is an index, not
a second source of truth.

---

## For the customer

The four that move actual numbers. **Q1 is the one that changes what the exercise is.**

| # | Question | Currently assumed | Blocks | If the assumption is wrong |
|---|---|---|---|---|
| **1** | **Which tier supervises?** Is the supervisor an ANM at a sub-centre, covering ~8 field workers — or higher? | Sub-centre, 8 field workers | E6 cases 3, 4, 5, 7 · H | **Order of magnitude.** At sub-centre a supervisor holds 37,200 records at day 180; at PHC 207,000; at block 920,000 — 3.5× production's heaviest measured device. Sub-centre makes this a test of concurrency; block makes it a test of volume too |
| **2** | **How often does a worker sync per working day?** | 4 | E6 arrival rates | Every arrival rate scales linearly. At 2/day the platform peaks near 350 syncs an hour, at 8/day near 1,400 — production's record is 792 |
| **3** | **Is "500 workers" field workers only, or all users?** | Field workers, with 62 supervisors added per state tenant | E6 deployment table · G5 | The deployment is 11% smaller if it is the total |
| **4** | **Is 500 workers the pilot, the first year, or the design target?** | Pilot | Scope of every conclusion | A real state runs 165,000 ASHAs, so 500 is 0.3% of one. Nothing in a 500-worker result extrapolates upward — tenant data volume grows with worker count, and sync cost follows it through index size and cache residency |

**One sanity check rather than a question.** Three ASHAs at 20 encounters a day give a village 60
daily against 3,000 beneficiaries, so every beneficiary is seen about every 50 days. If the real
follow-up interval is monthly or quarterly, either the encounter rate or the beneficiaries-per-village
figure needs adjusting, and E6's dataset sizes move with it.

**And one already answered, recorded so it is not reopened.** Rolling data: year two accrues at year
one's rate, with nothing ageing out.

---

## For the product owner

| # | Question | Blocks | Note |
|---|---|---|---|
| **5** | **What error rate is acceptable under load?** | A6, and the last row of the Success criteria table | The only success criterion no query can supply. Everything else in that table is now measured |
| **6** | **Which organisation configuration(s) to run against?** | H1 · F5.1 | The generator takes the bundle as a parameter, so this does not block building it — only running it. Worth covering a range of organisation sizes deliberately, since configuration size drives the `syncDetails` row count and therefore D1.1's per-row cost |

---

## For the team

| # | Question | Blocks | Note |
|---|---|---|---|
| **7** | **Distributed injectors — needed, or not?** | F3 | Gatling OSS has no orchestration, so multiple injectors mean merging logs by hand. One injector may well carry E6's load; measure before building for it |
| **8** | **Over what period?** | Sequencing | Ownership is settled. The order in the Sequencing table reflects dependencies, not a calendar |

---

## Measurements still outstanding

| # | What | Where | Note |
|---|---|---|---|
| **9** | **Q7c on the primary** | [queries](production-measurement-queries.md) | The index-usage half. `idx_scan` is per-instance, and the replica serves only the reporting tool, so this is the one query that must not run there |
| **10** | **Q11 — fleet page size split** | [queries](production-measurement-queries.md) | **Not answerable yet.** `pageSize` is not recorded in `sync_telemetry`, so it needs a client change first (D8.3) |

Everything else in Q1–Q15 has run. Q14 and Q15 were added after the first pass and both returned.

---

## Assumptions carried in the plan

Not questions anyone is being asked, but things that would change conclusions if they turned out
false. Listed so they are visible rather than buried.

| Assumption | Where | Why it is held |
|---|---|---|
| All of this customer's organisations behave alike, so one usage pattern covers them | E0 | The customer's own assumption, recorded as theirs |
| These tenants may share infrastructure with existing production tenants | E0 · E6 case 6 | Makes production's org skew background load rather than a separate scenario |
| A generated dataset can stand in for production data | H6 | An anonymised clone is not available. This is settled, not open — but it means H5's validation is the only thing that will catch an unrealistic generator |
| Sync is the whole exercise | Closed questions | State-wide facility search is explicitly out of scope. **A passing sync run is not clearance for search**, because search cost grows with tenant size where sync cost grows with catchment size |
| The three growth datasets differ only in encounter count | E6 | Beneficiary population does not grow with programme activity |
| A catchment is declared against one location | H · `tools/data-generator` | A generator default, not a platform constraint — `catchment_address_mapping` is a many-to-many and real bundles carry three locations per catchment. Changes the mapping table's size and what the expansion view computes, not what anyone syncs |

---

## What is no longer open

Recorded briefly so none of it gets relitigated. Full reasoning is in the plan's own closed-questions
list.

- **Production statistics access** — granted; fifteen queries written and all but two have run.
- **On-demand media viewing** — out of scope. A browsing workload, not a sync one.
- **Anonymised production clone** — not available. Generation is the path.
- **State-wide facility search** — out of scope, with the caveat above.
- **Webapp and API consumers** — separate query paths; keeping to sync is correct.
- **Token expiry across a long sync** — a harness limitation only. The real client refreshes per
  request, so a multi-hour sync is fine for it.
- **Perf environment isolation** — designed, not an unknown.
