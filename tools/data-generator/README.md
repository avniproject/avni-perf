# Test data generator

Generates the transactional data a load test needs — subjects, enrolments, encounters and their
observations — from an Avni implementation bundle. Section **H** of
[the sync simulation plan](../../docs/sync-simulation-plan.md).

Avni is metadata-driven. An observation is a JSONB map keyed by concept UUID, and what counts as a
valid value depends on that concept's datatype and, for coded concepts, on its own answer set. So
nothing can be generated without first reading the organisation's form configuration.

**The bundle is a parameter, never a fixture.** No implementation's configuration belongs in this
repository. Tests run against a synthetic bundle built in `tests/fixture.py`. Point the tools at
whatever bundle a run is meant to represent, and record which one in the run metadata.

## Surveying a bundle

Before choosing a configuration, see what it can actually produce:

```
python3 survey.py /path/to/bundle
```

It reports live concepts, forms and mappings, then generates a sample and compares the result
against production's measured shape. Two things it catches immediately:

- **Form types with no live mapping.** Rows of that kind cannot be generated at all. A bundle whose
  `ProgramEncounter` mappings are voided cannot populate production's largest table.
- **Forms too small to reach production's spread.** A form with 2 elements cannot produce a p95 of
  29 keys whatever the fill rate, so the resulting index is smaller and hotter than production's.

## What it generates

`bundle.py` reads the bundle and resolves each form mapping to the elements an observation may be
keyed on. Dropped along the way: voided concepts, forms, element groups, elements and mappings —
around 40% of elements in a real bundle are voided — plus media datatypes, which imply S3 objects
that section D5 puts out of scope, and coded concepts with no answers.

`observations.py` generates the values. Two properties matter more than the values themselves, both
from section H3:

**Key count is a distribution, not a constant.** `KeyCount` fits a lognormal to a measured median
and 95th percentile, so both are reproduced by construction. A generator emitting a fixed key count
builds a GIN index of the wrong shape even when the mean matches.

The targets live in a **profile**, not in code — `profiles/production-2026-09.json` holds what Q6
measured:

| Form type | Table | p50 keys | p95 keys | Mean bytes |
|---|---|---|---|---|
| `ProgramEncounter` | `program_encounter` | 12 | 34 | 879 |
| `IndividualProfile` | `individual` | 7 | 29 | 742 |
| `Encounter` | `encounter` | 4 | 22 | 526 |
| `ProgramEnrolment` | `program_enrolment` | 2 | 20 | 360 |

Kept as data for three reasons. The numbers are measurements and will move when production is
measured again. A run has to be able to record which shape it targeted (A11). And a run that
deliberately targets something heavier than today's production should say so in a file rather than a
patch. Pass an alternative with `--profile`:

```
python3 survey.py /path/to/bundle --profile profiles/my-target.json
```

**Which concepts appear varies row to row.** Mandatory elements are filled first, then the rest are
drawn at random. Always filling the same elements produces a narrower index than production's
regardless of key count.

## How many rows a user carries

Q3 measured each device's own row count. The profile carries the percentiles, and
`distribution.Quantiles` samples from them:

| Entity | p50 | p90 | p99 |
|---|---|---|---|
| Subjects | 464 | 5,685 | 42,519 |
| Enrolments | 100 | 1,653 | 15,254 |
| Program encounters | 89 | 11,762 | 153,126 |
| Encounters | 62 | 3,167 | 53,670 |

**A 370× spread between the median device and the 99th.** Reproduce the tail: a generator giving
every user a typical catchment produces no heavy syncs at all, and the heavy tail is where the choke
points are.

**These are interpolated, not fitted.** A lognormal fitted to two of the percentiles reproduces
subjects and enrolments within a few percent and misses program encounters by 54%. Program
encounters rise 132× from the median to the 90th percentile and only 13× from there to the 99th,
which is not one population — programme enrolment is optional, so most devices carry almost no
programme activity and a minority carry a great deal. Interpolating the measured quantiles in log
space reproduces all three points exactly and assumes nothing about the shape between them. A test
records the lognormal's failure so the approach is not reinstated.

## One input is still a guess

**The age spread of `last_modified_date_time` has never been measured.** H3 warns that getting it
wrong invalidates every incremental scenario: rows sharing one timestamp make incremental sync
return either everything or nothing. Query **Q14** was added to cover it and has not been run.

Until it is, the profile carries a placeholder marked `unmeasured`, and `Profile.unmeasured_inputs`
reports it so a run can state that it used a guess. **Run Q14 before treating any incremental
result as meaningful.**

## Concept cardinality is a platform property

Production carries **5,623 distinct observation keys**, but that figure spans all 986 organisations —
the query behind it has no organisation filter. A single bundle reaches a few hundred. **Total
cardinality comes from tenant count, not from inflating any one organisation.** Generating one
organisation with thousands of concepts would be as wrong as generating one with a dozen.

## Running the tests

```
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest tests -q
```

## Locations and catchments

`hierarchy.py` builds a tenant's location tree from the real state establishment in plan section E0 —
State, District, Block, PHC, Sub-Centre, Village — using its measured branching factors: 75 districts
to a state, 11.3 blocks to a district, down to 2.8 villages per sub-centre.

It works **upward from the leaf count**, because that is the number everything else depends on. A
tenant's village count sets its field worker count, its beneficiary count and its encounter volume,
so scaling a state's 59,000 villages downward by a ratio would land wherever the rounding fell.

**Six levels, where Q13 measured production at four for 84% of its locations.** That is two levels
deeper than production's typical, and `lineage` is an `ltree` walked by both catchment scope
resolution and reference-table RLS, so a generated tenant's lookups cost more than a typical
production one's.

`catchments.py` assigns catchments and users. Two things it gets right that a simpler generator would
not:

**Field workers in a village share its catchment.** Three ASHAs to a village, all three pulling every
row recorded there. So the same rows are read three times over, and a field worker's sync volume
tracks the village's activity rather than their own.

**A catchment holds many locations.** `catchment_address_mapping` is a many-to-many and real
configuration uses it — the bundles examined for this work carry catchments of three locations each.
The server expands every declared location down its own subtree through
`virtual_catchment_address_mapping_table`, so the expanded set is the union of those subtrees, and
descendants are never written as declared rows. That is also why Q15 counts the expanded set.

**The generator declares one location per catchment by default, and that is an assumption rather than
a constraint** — a village for a field worker, a sub-centre for a supervisor. `declare_leaves=True`
declares the villages instead. Both reach the same villages, which is where subjects live, but they
write a different number of mapping rows: 227 against 334 for a pilot tenant. Which shape production
uses has not been measured.

A pilot state tenant at 167 villages comes out at **501 field workers and 60 supervisors**, against
E6's 500 and 62.

## What a bulk load bypasses, and what it does not

H4 loads with `COPY`, which skips the application entirely. So the question is what the application
would otherwise have maintained. Checked against the migrations rather than assumed:

**`virtual_catchment_address_mapping_table` needs nothing.** It is a plain view over a SQL function,
not a table and not materialised, so there is nothing to populate or refresh. The function splits each
location's `lineage` and joins every element against `catchment_address_mapping`, which means a
location belongs to a catchment when **any point in its lineage** is declared against it. A test
asserts the generator's descendant walk agrees with that definition.

**There are no materialised views and no triggers on the four transactional tables.** So nothing else
is recomputed behind a write.

**`lineage` is guarded, but only partly.** `address_level` carries a check constraint,
`lineage_parent_consistency`, requiring the path to end `.parent_id.id` — so a `COPY` with a wrong
immediate parent is rejected outright. Its own comment notes it validates the parent-child link and
**not the whole tree**, so a wrong *ancestor* would load cleanly and hand catchment expansion the
wrong scope with no error anywhere. Nothing but the generator guards that, and two tests cover it: one
for the constraint as written, one for the full ancestor chain.

**What the generator does have to write itself** is the denormalised columns the application would
have set, because the sync indexes cover them: `address_id` on all four tables, `individual_id` on
`program_encounter`, and `sync_concept_1_value` / `sync_concept_2_value` from the subject's own
registration observation. Leaving any of them null loads without complaint and quietly stops the
generated data from touching the index paths production uses.

## Writing the load

`copy_writer.py` turns rows into `COPY` input and emits the script that loads them. Four things it
handles that a naive writer would not:

**The column list comes from the target database.** Rows are column-keyed dicts, projected onto a
column list the caller reads from `information_schema.columns`. A hardcoded list here would rot as
migrations accumulate and produce a `COPY` that either fails or — far worse — shifts every value one
column left and loads silently. **A row key that is not a column raises** rather than dropping the
value quietly.

**Explicit ids leave sequences behind.** The generator assigns its own ids so it can wire foreign keys
without round-tripping the database, and `COPY` does not advance a serial's sequence. Without a
`setval` per table, the first application insert after a load collides on the primary key.

**`\copy`, not `COPY`.** Server-side `COPY FROM` reads a path on the *database* host and needs
superuser or `pg_read_server_files`. `\copy` streams the file from wherever `psql` runs.

**Load order is load-bearing.** None of Avni's foreign keys are declared `DEFERRABLE` — checked, zero
across every migration — so `SET CONSTRAINTS ALL DEFERRED` would achieve nothing and a child row
loaded before its parent fails on the spot. `LOAD_ORDER` is the only guard, and a test asserts it.

Escaping gets its own tests because two layers stack on observations: `json.dumps` turns a tab into
backslash-t, then `COPY` escaping turns that backslash into two. Postgres unwraps one layer and the
`jsonb` parser the other. The backslash has to be escaped first or everything after it
double-escapes.

## Keeping up with Flyway

The schema moves — 484 migrations so far. Three of the four ways that can break a bulk load already
fail loudly:

| Change | What happens |
|---|---|
| Column renamed or removed | `project()` refuses a row key that is not a column |
| Column added `NOT NULL` with no default | the `COPY` fails |
| Column type changed incompatibly | the `COPY` fails on the first bad value |
| **Column added, nullable** | **silently arrives empty** |

The fourth is the dangerous one, and it has a precedent. `sync_concept_1_value` was added by
**V1_208** to carry attribute-based sync; `sync_3` and `sync_4` index it. A generator predating that
migration would have loaded cleanly while producing data that never touched those index paths, and
every number would have come out optimistic with nothing to show why.

So `schema.py` requires **every column in the target to be accounted for** — either written, or
declared unwritten with a reason. An unrecognised column raises `SchemaDrift` and the load stops:

```
individual: columns the generator has never heard of: ['sync_concept_3_value'].
A migration since V1_410 probably added them. For each one, decide whether the generator should
write it -- if sync reads or indexes it, the answer is yes -- and either populate it or record it
in `unwritten` with the reason.
```

`load_script` verifies before emitting anything, and stamps the migration it was checked against
into the script. `CHECKED_AGAINST_MIGRATION` is the watermark to bump when the contract is reviewed,
so drift can be dated rather than guessed at.

**A reason is required, and enforced.** A test rejects any `unwritten` entry short enough to be a
hand-wave — it caught seven of its own on the first run. "Audit only" does not explain why a column
can be left alone; "audit column, and this table is never itself synced" does.

## H5 — is the dataset good enough to measure against?

Section H6 rules out an anonymised production clone, so **the generated dataset is the only
dataset**. Nothing else will catch a generator producing plausible row counts and unrealistic
cardinality, which makes this a gate rather than a nicety. Run it before a dataset is used, and again
whenever the generator changes.

### The statistical check

```
psql -d <generated_db> -A -F',' -f validate.sql     # after loading and ANALYZE
python3 validate.py stats.json                       # exit 1 on any failure
```

**The checks are ordered by how hard they are to fake**, and that ordering is the point:

| Check | Tolerance | What it proves |
|---|---|---|
| Row count | 0.1% | Only that the loader wrote what the generator produced |
| Observation keys, median | 20% | Weak — the generator targets this directly |
| Observation keys, p95 | 25% | **A constant key count passes the median and fails here** |
| Observation mean bytes | 30% | Payload size |
| Index bytes per row | 35% | That production's index definitions are present (G4) |
| **GIN bytes per row** | **35%** | **Observation cardinality. The generator cannot target this** |

**GIN bytes per row is the one that matters.** It falls out of how many distinct keys each row
actually carries, so it cannot be reached by getting row counts right. Production's figures, from Q7c
normalised per row: `individual` 99 B, `program_encounter` 69 B, `encounter` 59 B,
`program_enrolment` 54 B.

A generated index an order of magnitude lighter means the cardinality is wrong, the index sits in
cache, and every push figure comes out optimistic — with nothing in the run to show why. **An index
heavier than production's fails too**, because that makes the server look worse than it is, which is
a different way of not measuring production.

Failures block; warnings do not. A statistic that was not measured **warns rather than passing
quietly**, because a silently absent check is the same as no check.

### The structural check

Catches what statistics cannot: a datatype the client cannot parse, a reference to a UUID that does
not exist, a rule that throws.

**Steps 1 and 2 are automated.**

```
make structural_check USERS=/data/pilot-day-180/state-1/sync-users.csv URL=http://host:8021
```

It runs the simulation against the loaded dataset in `full` mode, one virtual user per role found in
the user file, and **asserts zero failures**. That is a stricter bar than a load run on purpose: a
load run tolerates an error budget because at scale something always fails and the question is the
rate, whereas this asks whether the data is readable at all, so one dangling reference is a defective
dataset however rare. `--out` writes the result alongside the dataset's other records.

**Steps 3 and 4 are manual, and cannot be automated from here.**

3. Point a real client at one field worker and one supervisor account. Confirm the sync completes,
   subjects list, and a subject's profile and an encounter form render.
4. Read the client's log for rule failures.

**Step 3 is the one worth not skipping.** The simulation only proves the server responded. The client
is what proves the data is *valid* rather than merely well-shaped — a generated observation that
violates a form's skip logic surfaces there and nowhere else, because nothing server-side evaluates
the rule. Device automation is the Android plan's territory, not this one's.

So a dataset that passes steps 1–2 is **loadable**, not **blessed**. The verdict file records the two
separately, and says the manual half is outstanding until someone fills it in.

### What neither check covers

**Per-organisation concept cardinality is compared against the bundle, not against production's
platform-wide figure.** Q6's 5,623 distinct keys spans all 986 organisations — the query has no
organisation filter — and a single bundle reaches a few hundred. Comparing one generated tenant
against 5,623 would fail a correct dataset.

## Assembling a deployment

`deployment.py` turns E6's specification into files a `COPY` can load. `pilot_deployment(days, ref)`
gives its shape with its numbers as defaults — two state tenants of 500 field workers, eight NGO
tenants sharing 500 — and reproduces E6's totals:

| Day | Beneficiaries | Encounters | Total rows |
|---|---|---|---|
| 60 | 1,506,000 | 1,795,200 | 3,301,200 |
| 120 | 1,506,000 | 3,590,400 | 5,096,400 |
| 180 | 1,506,000 | 5,385,600 | **6,891,600** |

Only encounter volume grows between the three, because beneficiary population does not grow with
programme activity.

**Measured throughput: ~41,000 rows/sec**, so the full day-180 dataset takes about three minutes to
generate and lands around 2 GB on disk.

Two things the driver handles that the per-tenant pieces do not:

**Ids cannot collide.** Every tenant writes into the same tables, so each gets a disjoint range
100 million wide — enough that a tenant ten times its planned size still cannot reach its
neighbour's. A test checks the stride against the largest planned tenant, and another checks that
no encounter references another tenant's subject, which would break RLS and sync scope alike.

**Nothing is held in memory.** Rows stream to per-table files as they are produced, so peak cost is
one village's subjects rather than the deployment's 6.9 million rows.

It also writes `load.sql`, a `manifest.txt` recording what was produced, and — via `feeder_csv` —
one `sync-users.csv` spanning every tenant, which is what E4 needs.

**Two ratios in it are weaker than they look.** `enrolment_rate` (0.22) and
`program_encounter_share` (0.59) come from Q3's per-device medians — 100 enrolments to 464 subjects,
89 program encounters to 62 encounters. Those are ratios of medians, not measurements of enrolment
rate, and the customer has supplied neither. Both are parameters.

## Datasets are recipes here, not files

A generated dataset runs to gigabytes and is a pure function of its inputs, so this repository holds
three small files per named dataset instead of the output.

| File | What it is |
|---|---|
| `datasets/<name>.json` | **The recipe.** Every input, so the dataset can be rebuilt exactly |
| `manifest.json` | **The fingerprint.** Row count, byte size and SHA-256 per table |
| `verdict.json` | **The H5 gate result**, recording that the dataset was blessed and against which profile |

`datasets/` carries the three E6 datasets — `pilot-day-60`, `pilot-day-120`, `pilot-day-180` — differing only
in growth point, which a test asserts.

**Storing the output instead would discard the only safety property the generator has.** `schema.py`
refuses to generate against a schema it does not recognise; a committed `.tsv` carries no such guard,
so a dataset built against an older migration loads into a newer database either confusingly or with
a column silently empty. And the durable artefact for run-to-run comparability is a **database
snapshot restored before each run** (G4), which lives in infrastructure rather than in git.

**The recipe records the bundle, because reproducibility depends on it and it is deliberately not in
this repository.** `bundle_fingerprint` hashes `concepts.json`, `formMappings.json` and `forms/` —
only those three, so an unrelated dashboard or translation edit does not look like a change to the
dataset. `check_bundle()` then says whether the bundle on disk is the one a recipe was built from.
The committed recipes leave it unset on purpose, and say so, so they cannot be mistaken for
complete.

**The manifest hashes content, not just counts**, because most changes to the generator keep the row
counts and alter what is in them. `Manifest.differences()` reports a rebuild that diverges, and
distinguishes "different row count" from "same count, different content".

## Co-tenants, for the hosting comparison

Test cases 6 and 7 put the customer's tenants on a database that also holds everyone else's data,
and the delta against case 5 is the shared-versus-separate hosting decision. `co_tenants.py` builds
that other half.

**The shape is Q12's**: 986 organisations, **473 of them holding nothing**, the largest holding 21%
of all subjects, the top ten 63%, the top fifty over 90%. The skew is the point — multi-tenancy costs
scale with what is in the tables rather than with who is querying, so 986 equal organisations would
misrepresent production about as badly as no co-tenants at all.

**Sizes are interpolated through the measured ranks, not fitted.** A power law does not hold across
the range: the exponent between ranks 1 and 10 is 0.84 and between 1 and 156 it is 1.57, so any
single curve is wrong somewhere. Interpolating in log-log space through the ranks Q12 returned
reproduces every share within two points.

| | |
|---|---|
| Generated tenants | 513 |
| Rows-only organisations | 473 |
| Subjects | 2,548,061 |
| Encounters at day 180 | 3,128,954 |
| Villages | 1,259 |

**Two things the build had to get right.**

Empty organisations are **rows, not generated tenants** — half of production's are in this state, and
generating a hierarchy, catchment and user for each would be work to model nothing. They still
matter, because RLS predicates evaluate against the full organisation set and the planner's
statistics span it, so `empty_rows()` emits them directly.

And **villages hold the organisation's actual subjects rather than a standard 3,000**. The first
version rounded every organisation up to at least one full village, which inflated production's
513th organisation from one subject to three thousand and added a million subjects across the tail
that the co-tenant set does not have.

Loaded together, cases 6 and 7 carry about **1.8× case 5's rows**.

## Getting the column list

The one step that needs a live database. Rows are projected onto the target's own columns, so dump
them first:

```
psql -d <target_db> -At -f columns.sql > columns.json
```

Read from the database rather than hardcoded, for the reason in **Keeping up with Flyway** above.
`schema.py` then refuses to proceed if that list contains anything it has not accounted for.

## Generating

```
psql -d <db> -At -f columns.sql > columns.json      # the target's own columns
psql -d <db> -At -f refs.sql    > refs.json         # its subject type, programme and encounter ids
python3 generate.py --recipe datasets/pilot-day-180.json \
                    --columns columns.json --refs refs.json \
                    --bundle /path/to/bundle --out /data/pilot-day-180
```

Both dumps come from the target rather than from anything committed here — 484 migrations have
already moved this schema, and the ids belong to whichever bundle was loaded. `refs.sql` gates each
sync concept on its `_usable` flag, because that is what the server does: reporting a concept the
flag disables would make the generator write a `sync_concept` value no query ever reads.

It refuses to start if the bundle is not the one the recipe names, if the schema contains a column
the contract has not accounted for, or if a tenant has no subject type of its own — that last one
would otherwise produce subjects of another tenant's type, which loads cleanly and is wrong in a way
no statistic would catch.

**Generating is not the gate.** Load the dataset, then run `validate.py`. H5 is the gate.

### Each tenant may have its own bundle

Set `bundle_path` on a tenant in the recipe and it is built from that configuration instead of the
deployment's. This is how H1's "cover the range of organisation size" is done rather than assumed:
**the number of entities a config defines is the number of rows the client posts to `syncDetails`,
and therefore the number of per-row queries `filterChangedEntities` runs** (D1.1, where Q8 measured
79 entities tracked against 4 changed). A small configuration will not exercise that; a large one
will.

Distinct bundles are loaded once however many tenants share them, and each gets its own fingerprint
in the recipe, so substituting one tenant's configuration is caught.

### Ids are written explicitly

`COPY` applies a column's default for anything left out of its list, so omitting `id` would let the
sequence assign it. But then nothing could reference the row — the generator has to write
`program_enrolment.individual_id` and `program_encounter.program_enrolment_id`, and it cannot know an
id the database is about to choose. Reading ids back mid-generation needs the round trip that
streaming to disk avoids; resolving them afterwards costs an `UPDATE … SELECT` per child table across
millions of rows.

Applied per table, not blanket: **`catchment_address_mapping.id` is left to the sequence**, because
nothing references it. It is the only one. The tax is a `setval` per table in `load.sql`, without
which the first application insert after a load collides on the primary key.

## What is left

- **Within-class catchment variation.** The two user classes are modelled, and E0's figures give
  every village 3,000 beneficiaries uniformly. Q3 measured a 370× spread between the median device
  and the 99th percentile, and Q15 found catchment breadth and per-location density vary
  independently. Whether that variation matters here depends on the answer to "which tier
  supervises" in [open-questions.md](../../docs/open-questions.md) — at sub-centre level the two
  classes may be the whole story.
- **The structural check, run once for real** (H5). The statistical gate is built; the client
  round-trip has not been done because no dataset has been loaded yet.
