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

## Not built yet

This is the first increment. Still to come, all from section H:

- Row generation for subjects, enrolments and encounters, with the catchment volumes Q3 measured —
  a p50 device holds ~715 rows and a p99 holds ~264,569, so the tail is what has to be reproduced
- Temporal spread of `last_modified_date_time`, without which no incremental scenario means anything
- Address level hierarchy — four levels branching around 9 (Q13)
- `COPY` output, index build and `ANALYZE` (H4)
- The structural and statistical checks that gate a dataset (H5)
- Multiple organisations with a realistic size distribution (H1, I2)
