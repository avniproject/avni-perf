# Test scenarios

**For customer review, and for the generator to build against.** Eleven test cases with actual
numbers, and the deployment they are derived from.

Split out of [the sync simulation plan](sync-simulation-plan.md) because it has a different audience
and a different lifecycle: the plan is how the instrument gets built, this is what it will be pointed
at. Every figure here is either something the customer supplied or something derived from it, and the
derivations say so.

**Two assumptions still move the numbers, and one of them changes what the exercise measures.** They
are flagged where they appear and listed in [open-questions.md](open-questions.md): which tier
supervises, and how often a worker syncs — where the requirement says weekly and production measures
a 16-minute median.

---

## The cases

| # | Case | Users | Dataset | Mode | What it answers |
|---|---|---|---|---|---|
| **1** | Training cohort | 100 field workers, all first login within 15 min | Config only, **no field data** | Full | Reference-data sync and `syncDetails` cost, isolated from catchment volume |
| **2** | Field worker steady state | 500 | Day 180, one state tenant | Incremental, 1% full | The common case |
| **3** | Supervisor steady state | 62 | Day 180, one state tenant | Incremental, 1% full | Whether 3× the volume per device changes anything |
| **4** | **Combined** | 500 + 62 | Day 180, one state tenant | Incremental, 1% full | **The realistic case.** Wide and frequent syncs competing for one pool |
| **5** | **Separate infrastructure** | 1,504 + 188 | Day 180, these 10 tenants only | Incremental, 1% full | The customer's own load, with nobody else's data in the tables. **The baseline the next two are measured against** |
| **6** | **Shared — co-tenant data** | 1,504 + 188 | Day 180 **plus production's 986 organisations**, which sync nothing | Incremental, 1% full | What the *presence* of other tenants costs: RLS selectivity, planner statistics, table and index size |
| **7** | **Shared — co-tenant load** | Case 6, plus production's own arrival rate | Same as case 6 | Incremental, 1% full | What their *activity* costs on top: connection pool, CPU, IO. **Cases 5, 6 and 7 together are the hosting decision** |
| **8** | Growth comparison | Case 4 | Day 60, then 120, then 180 | Incremental, 1% full | The shape of the curve. A knee between points is the finding |
| **9** | Reset storm | 562, one tenant, org-wide reset | Day 180 | **All full** | The heaviest real event (Q10 measured it at 130× a normal week) |
| **10** | Stress ramp | Ramp past case 5 until failure | Day 180 | Incremental | Where the knee is, and which resource names it |
| **11** | Soak | Case 4 | Day 180 | Incremental | Leaks, pool exhaustion, autovacuum interaction over hours |

**Build order: 1, 4, 8, then the rest.** Case 1 needs no generated data at all, so it can run before
the generator exists. Case 4 is the one to answer first. Case 8 needs all three datasets, so it sets
the generator's deadline.

### Conditional on one open question

Cases 3 to 8 assume **supervision at sub-centre level** — 8 field workers per supervisor. If it
sits higher, per-device volume changes by roughly an order of magnitude and the cases above change
with it:

| Supervisor tier | Field workers each | Records at day 180 | Full sync | vs Q3's heaviest device |
|---|---|---|---|---|
| **Sub-centre** | 8 | 37,200 | 5.7 min | 0.14× |
| PHC | 45 | 207,000 | 32 min | 0.78× |
| Block | 200 | 920,000 | 141 min | 3.5× |

**At sub-centre level no case here exceeds what production already carries, so this exercise tests
concurrency and tenancy. At block level it tests volume as well.** That is a different exercise, and
it is one answer away.

---

## Hosting is one of the cases, not a given

These tenants could sit on the existing shared platform, beside the 986 organisations Q12 measured —
48% of them empty, the largest holding 21% of all subjects — or on infrastructure of their own. **That
is a decision with a cost attached either way, and it should be made on a number rather than on
instinct.**

Sharing is not free, and multi-tenancy is where the cost hides. Row-level security selects one
tenant's rows out of tables holding every tenant's, planner statistics are computed across all of
them, the connection interceptor runs `set role` on every borrow, and reference-table RLS walks
organisation ancestors. None of that scales with *this* customer's data; all of it scales with the
platform's.

Separate infrastructure removes those costs and adds its own: a second environment to deploy,
monitor, patch and pay for, and a tenant that cannot later be merged back without a migration.

**Cases 5, 6 and 7 are the same load under three conditions, and the deltas between them are the
answer.** Case 5 is the customer alone. Case 6 adds everyone else's *data* but none of their traffic,
which isolates what mere presence costs — RLS selectivity, planner statistics, table and index size.
Case 7 adds their *traffic* too, at production's measured arrival rate of 792 syncs in its busiest
recorded hour (Q4), which is what actually competes for the connection pool, CPU and IO.

**Separating 6 from 7 matters because the two have different remedies.** If the cost is in case 6,
it is structural and follows the data wherever it sits — better indexes, better statistics, a cheaper
RLS predicate. If it only appears in case 7, it is contention, and more capacity or a separate
instance fixes it. Running them as one case would leave you unable to tell which you were looking at.

Running only case 5 would leave the decision exactly where it started.

---

---

## The deployment being modelled

**Two things vary across the cases, and only one of them is the customer's.** The deployment below is
theirs — ten tenants, 1,692 users, 1.5 million beneficiaries. **Where it runs is ours**, and cases 5,
6 and 7 measure both answers rather than picking one:

| Hosting | What is in the database | Cases |
|---|---|---|
| **Separate** | These 10 tenants only | 1–4, 5, 8–11 |
| **Shared, co-tenants idle** | Plus production's 986 organisations | 6 |
| **Shared, co-tenants active** | Plus their traffic | 7 |

Every case except 5, 6 and 7 assumes separate hosting, because a single-tenant question does not need
the other 986 organisations present to answer it. If the hosting comparison says sharing is free, the
distinction stops mattering and the cases can all run on the shared platform.

### The tenants

| | ASHAs | ANMs | Villages | Beneficiaries | Encounters/day |
|---|---|---|---|---|---|
| State tenant (pilot) × 2 | 500 | 62 | 167 | 501,000 | 10,000 |
| NGO tenant × 8 | 63 | 8 | 21 | 63,000 | 1,260 |
| **Platform total** | **1,504** | **188** | **502** | **1,506,000** | **30,080** |

Derived at 3 ASHAs per village, 3,000 beneficiaries per village, 8 ASHAs per sub-centre and 20
encounters per ASHA per day — see **Where the numbers come from** below.

**Confirmed with the customer: "500 workers" means 500 field
workers, with supervisors added on top rather than counted within it.**

### Dataset size at each growth point

| | Encounters | Total rows | vs production today |
|---|---|---|---|
| Day 60 | 1,804,800 | 3,310,800 | 26% of its encounters |
| Day 120 | 3,609,600 | 5,115,600 | 53% |
| **Day 180** | **5,414,400** | **6,920,400** | **79%** |
| Day 365 | 10,979,200 | 12,485,200 | 160% |

Beneficiaries stay at 1,506,000 throughout — 55% of production's current subject count — because
population does not grow with programme activity. **Three datasets are needed**, at day 60, 120 and
180, each a G4 snapshot.

### What each device holds

| | Subjects | Day 60 | Day 120 | Day 180 | Year 1 |
|---|---|---|---|---|---|
| Field worker — 1 village | 3,000 | 3,600 | 7,200 | 10,800 | 21,900 |
| Supervisor — 1 sub-centre | 8,400 | 9,600 | 19,200 | 28,800 | 58,400 |

Full-sync client time at 9.19 ms/record: a field worker **2.1 min** at day 180 and **3.8** at year one;
a supervisor **5.7** and **10.2**.

### Sync frequency — the widest open number

Arrival rate needs a per-worker sync frequency, and three figures are in play across two orders of
magnitude: **the requirement says once a week**, this document assumes **4 a working day**, and
production measures a **median gap of 16 minutes** (Q2).

They are probably not in conflict — a weekly requirement reads as a floor rather than a description,
and roughly 1% of production's real gaps already exceed a week. But the answer changes the arrival
rate by a factor of forty, so it is
[open question 2](open-questions.md). **Assumed here: 4 syncs per worker per working day**, spread
across the 09:00–21:00 plateau Q4 measured in production.

**Only the arrival rate moves with it.** A longer gap means more accumulated changes per sync, but
not many — a weekly sync carries ~420 records for a field worker against 15 for a four-a-day one, and
both sit far inside the light band where 98% of production's syncs already live.

| At 4 syncs/worker/day | Syncs/day | Average hour | Peak hour |
|---|---|---|---|
| One state tenant (562 users) | 2,248 | 187 | ~232 |
| Whole platform (1,692 users) | 6,768 | 564 | ~700 |

For reference, production's busiest hour ever recorded was **792 syncs** (Q4). So the whole
deployment at four syncs a day lands just under production's existing peak. **If the real figure is
two or eight a day, halve or double every arrival rate in the table.**

---

## Where the numbers come from

Everything above derives from this section: what the customer supplied, the real establishment figures
they gave, and the arithmetic between the two. Read it when a number above looks wrong.

**Two deployment shapes, not one.**

| | Geography | Tenants | Workers | Data |
|---|---|---|---|---|
| **State level** | Whole state | 2 | ~500 each | Rolling |
| **NGO** | Smaller, local | ~8 | ~500 across all of them | *TBC* |

So roughly **1,000 workers across 8–10 tenants**, starting at 2 tenants and possibly running the
first tests at 5. For scale: production's busiest hour ever recorded saw **267 distinct users across
every organisation** (Q4). A thousand provisioned workers is about four times production's entire
peak, which makes this a genuine step up rather than a reproduction.

**Customer figures, and what they size.**

| | |
|---|---|
| Programme duration | 1 year |
| Field workers per village | ~10 |
| Beneficiary encounters | ~20 per field worker per day |
| Encounter types per NCD programme | 10 |
| Fresh syncs | 1% of users, from phone loss, replacement or reassignment |
| Onboarding cohort | 50–100 first-time logins in one location |

**The figures close into a model.** Ten workers share a village catchment, a village holds ~3,000
beneficiaries, a supervisor covers ~10 villages, and data accrues at the same rate in year two as in
year one. From 500 workers per state tenant that gives **50 villages and 150,000 beneficiaries**.

**A real state's establishment, supplied by the customer.** ASHA as field worker, ANM as supervisor.

| Level | Units | ASHAs per unit | ANMs per unit | CHOs per unit |
|---|---|---|---|---|
| State | 1 | 165,000 | 24,000 | 20,000 |
| District | 75 | 2,200 | 320 | 265 |
| Block | 850 | 200 | 30 | 25 |
| PHC | 3,600 | 45 | 7 | 6 |
| Sub-Centre | 21,000 | 8 | 1 | 1 |
| Village | 59,000 | 3 | 0 | 0 |

**It is internally consistent** — units times per-unit reproduces the state totals within 7% at every
level — and it corrects the model above in four places.

| | Earlier figure | This table | |
|---|---|---|---|
| Field workers per state | 500 | **165,000** | 330× |
| Field workers per village | 10 | **3** | 3.3× |
| Supervisor span | 10 villages | **2.8** (a sub-centre) | 3.6× |
| Supervisor : field worker | 1:100 | **1:7** | 14× |

**The 1:100 ratio was wrong, as suspected.** A real state runs 165,000 ASHAs against 24,000 ANMs, and
one ANM per sub-centre covers 8 ASHAs. That is 1:7, inside the 1:10–1:25 convention rather than an
order of magnitude outside it.

**The table also settles the visit-interval check, in favour of itself.** Three ASHAs at 20 encounters
a day give a village 60 daily against 3,000 beneficiaries — **every beneficiary seen about every 50
days**. Ten ASHAs gave every 15 days, which is what looked wrong. And 3,000 per village is
independently confirmed: 165,000 ASHAs at the 1-per-1,000-population norm implies a 16.5 crore state,
which over 59,000 villages is 2,797 per village.

**So the supervisor is no longer the extreme case, and which tier supervises decides everything.**

| Supervisor sits at | ASHAs | Encounters/day | Day 180 | Year 1 | vs Q3's heaviest device |
|---|---|---|---|---|---|
| **Sub-Centre (ANM)** | 8 | 160 | 28,800 | **58,400** | **0.38×** |
| PHC | 45 | 900 | 162,000 | 328,500 | 2.15× |
| Block | 200 | 4,000 | 720,000 | 1,460,000 | 9.53× |

An ANM at a sub-centre lands at **0.38× the heaviest device production has already measured** — well
inside observed range, and nothing like the 4.8× claimed above from the 10-village span. **Taking ANM
as the supervisor removes the extreme-volume case from this deployment entirely.** A block-level
supervisor would restore it and then some, so *which role is being modelled* is now the single
highest-leverage question in this section.

**And 500 workers is 0.3% of a state.** That figure has to be a pilot rather than a rollout. Sizing
the exercise at 500 workers while the eventual deployment is 165,000 means this measures the pilot,
which is a legitimate thing to measure — but nothing in a 500-worker result extrapolates to a state,
because the tenant's total data volume grows with worker count and sync cost depends on it through
index size and cache residency. **Worth confirming: is 500 the pilot, the first year, or the design
target?**

Per-device volumes, on the establishment table's figures (see the last section). Encounter counts, not subject counts — a
shared catchment means every worker in a village pulls every encounter recorded there, including the
ones they did not create, so a field worker's sync volume tracks the village's total activity rather
than their own.

| Per device | Subjects | Day 60 | Day 180 | Year 1 | Year 2 |
|---|---|---|---|---|---|
| Field worker — 1 village, 3 ASHAs | 3,000 | 3,600 | 10,800 | 21,900 | 43,800 |
| Supervisor — sub-centre, 8 ASHAs | ~8,400 | 9,600 | 28,800 | 58,400 | 116,800 |

**Both sit inside what production already carries.** Q3's median device holds ~715 rows and its
heaviest ~264,569; a supervisor at year two reaches 116,800, which is under half the existing p99. The
per-device volumes are a real increase on the median but they are not new territory, and that is a
different exercise from the one the 10-village figure implied.

**The dataset target follows from the model.** Two state tenants plus eight NGO tenants come to
roughly **450,000 beneficiaries**, and H sizes against that. Volume grows out of the daily encounter
rate and the worker count, so a longer-term projection is arithmetic on this model rather than a
separate target to build for.

**On the establishment figures, no scenario here exceeds production's existing tail.** Q3's heaviest
measured device holds 153,126 program encounters; a sub-centre supervisor reaches 58,400 at year one
and 116,800 at year two. That reverses what the 10-village span implied, and it changes what this
exercise is for: **not finding the volume at which the server breaks, but confirming it holds at
volumes it already sees, under a concurrency and tenancy mix it has not seen.**

The extreme-volume case returns only if supervision sits above the sub-centre. A PHC-level supervisor
reaches 2.15× the p99 device and a block-level one 9.5×, so that question decides whether volume or
concurrency is the thing being tested.

> **Fresh-sync duration, at the measured 9.19 ms/record (D6.1).** A field worker is **4 minutes at
> year one and 7 at year two**; a sub-centre supervisor **10 and 19**. Those are tolerable. A
> PHC-level supervisor would be **57 minutes** at year one and a block-level one **over four hours** —
> another reason the supervising tier decides what this exercise is measuring.
>
> **Token expiry is not the concern.** The real client calls `getAuthToken()` per request, and
> `CognitoAuthService` resolves it through `cognitoUser.getSession()`, which refreshes against the
> refresh token whenever the id token has expired. A sync of any length is fine. The one-hour lifetime
> is a **harness** limitation, because the simulation mints a token once and caches it for the run —
> which is what section B is about, and what B1 resolves with `AVNI_IDP_TYPE=none`.
>
> What the duration does mean is that *Supervisor* and *Soak* are the same run. A multi-hour sync is
> the normal case for this user rather than an endurance test, so the soak profile should be a
> supervisor fresh sync instead of a synthetic long run.

> **State-wide search is out of scope. Decided.** Sync reads a catchment; a facility search reads the
> whole tenant — different endpoints (`/web/*`), different indexes, different scaling behaviour.
>
> **One consequence travels with that decision: a clean result here says nothing about search.** It is
> the one load whose cost grows with total tenant size rather than with catchment size, which makes it
> precisely the case sync results cannot stand in for. Separate exercise, not scheduled.

**A sanity check worth putting back to the customer.** Ten workers at 20 encounters a day give a
village 200 encounters daily against 3,000 beneficiaries, which implies **every beneficiary is seen
about every 15 days**. If the real follow-up interval is monthly or quarterly, then either the
per-worker encounter rate or the beneficiaries-per-village figure needs adjusting, and the tables
earlier move with it.

**A shared catchment makes ten users read the same rows.** Confirmed by the customer: the ten workers
in a village share its catchment rather than partitioning it. So village data is pulled ten times
over, which is friendly to cache and hostile to page-level contention in the same breath, and it is
not a shape a one-user-per-catchment generator produces. G5's catchment assignment has to model the
sharing, not just the size.

**Training runs against configuration only — no field data.** That makes it a **reference-data** test
rather than a transactional one: 50 to 100 devices, every one empty, every sync a full pull of the
same metadata at the same moment. Useful precisely because it isolates reference-data sync and the
`syncDetails` per-row cost from any catchment volume at all, and cheap to build because the dataset is
a bundle load with no generation step.

**"Rolling data" is still open.** For a state-level tenant it could mean volume grows without bound,
or that older data ages out and volume plateaus. With a one-year programme the question is what
happens in year two. The two produce different datasets and different index sizes.

**Two user roles, and they are not the same workload.**

- **Field worker.** One catchment, the subjects in it.
- **Supervisor.** Oversees many field workers, so the catchment is the union of theirs.

**This is very likely what Q3's 370× spread has been measuring.** Per-device row counts run from ~715
at the median to ~264,569 at the 99th percentile, and a single population does not do that. A
supervisor holding the union of many field workers' catchments is a different kind of user, not an
unusually heavy one — the same mistake the catchment sampler already avoids for program encounters,
which turned out to be two populations rather than one skewed one.

**So sampling one distribution for every user is wrong.** The generator must model two user classes
with their own catchment sizes and their own population ratio. The per-device tables give the catchment
sizes; the ratio is the part still missing, since the customer supplied a supervisor's span rather
than a count. **Q15 remains worth running** — not to size this deployment, which this document mostly
does, but because the
platform may host these tenants alongside the existing production skew, and whether production's own
population is bimodal decides how that co-tenant load should be generated.

**Growth is a test dimension.** The customer wants **day 60, day 120 and day 180** compared. That
makes the dataset a series rather than a single artefact, and the choke point may only appear at the
largest. Section H has to generate dated states, and G4's restore has to hold one per comparison
point.

**Fresh sync is 1% of syncs daily.** This is the mix E2 was missing. The full-sync path is rare but
it is the expensive one, and 1% of 1,000 workers is ten full syncs a day against a dataset that grows
to day 180.

**One assumption to carry explicitly**, the customer's: all of their organisations behave alike, so
one usage pattern covers them.

---

## What the generator has to produce

1. **Three datasets** — day 60, 120, 180 — differing only in encounter count.
2. **Ten tenants**: 2 × 500 field workers, 8 × 63, each with its own location hierarchy and catchments.
3. **Shared village catchments**, so 3 field workers per village pull the same rows.
4. **Two user classes**: field worker at one village, supervisor at one sub-centre of ~2.8 villages.
5. **Timestamps per Q14** — median age near two years, and program encounters written twice.
6. **Observation shape per Q6** — the measured key-count distributions, per form type.
7. **Production's tenant skew** for cases 6 and 7: 986 organisations, 48% empty, the largest holding
   21% of all subjects. Not optional — without it there is no hosting comparison, only a guess.

**Cases 5 and 6 must differ in exactly one thing.** Same generated tenants, same seed, same growth
point, same server build, same instance size — the only difference is whether the other 986
organisations are present. Any second difference and the delta stops being attributable, which is
the whole point of running both. Case 7 then differs from case 6 only by the co-tenant traffic.

**What to record for the comparison.** Sync duration at p50 and p95 is the headline, but on its own
it will not say *why*: add buffer cache hit ratio, rows read per index scan on the sync path, and
connection pool wait time (F1/F2). Case 6 moving the first two and not the third points at data
volume; case 7 moving the third points at contention.

**Datasets are held as recipes, not files.** A dataset is gigabytes and a pure function of its
inputs, so `tools/data-generator/datasets/` carries three small files per named dataset — the recipe
(every input, so it rebuilds exactly), the manifest (row count, size and content hash per table, as
the fingerprint a rebuild is checked against) and H5's verdict. All three datasets are committed.
Storing the output instead would discard the generator's schema guard, and the durable artefact for
run-to-run comparability is G4's database snapshot rather than a file in git.

**All seven are built** — `tools/data-generator`, 194 tests. It reproduces these totals exactly
(1,506,000 beneficiaries; 5.4 M encounters at day 180) at about **41,000 rows/sec**, so a full
day-180 dataset generates in roughly three minutes and lands around 2 GB on disk.

**Each tenant may carry its own bundle**, which is how H1's "cover the range of organisation size"
gets done rather than assumed: the number of entities a config defines is the number of rows posted
to `syncDetails`, and therefore the number of per-row queries `filterChangedEntities` runs — Q8
measured 79 tracked against 4 changed. A small configuration will not exercise that; a large one
will.

One thing remains: **H5's structural check run once for real**, which needs a loaded dataset.
**Item 7 is not built** — production's tenant skew is a separate generation run against a different
spec rather than a variation of this one. It is what case 6 needs, so the hosting comparison is
blocked on it.

---
