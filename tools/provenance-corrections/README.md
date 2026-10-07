# Provenance corrections

One file per corrected run, named for its run id. Each is a copy of the
`provenance-correction.json` that sits in that run's own artefacts prefix.

**S3 is authoritative, this directory is the record.** The prefix is append-only
by IAM and a run's `run-metadata.json` is never rewritten — editing a completed
run's own record to say something it did not say would falsify it — so a field
found to be wrong afterwards is corrected alongside it. `update-run-log.sh`
reads the S3 copy, not this one.

What this directory adds is that a correction becomes reviewable. Written only
to S3, the file explains itself to anyone who goes looking, but nothing in the
repo says a correction was ever made, and the reasoning never passes through
review.

Every file here was verified byte-identical to its S3 object when committed.

| run | what was corrected |
|---|---|
| `2026-10-05T08-38-47Z-case1-f76d110` | harness commit recorded as `unknown` and the tree as dirty. The tarball delivery strips `.git`, so `git rev-parse` found nothing and the dirty check read its own "unknown" as uncommitted changes. Provenance only — the run is sound and stays in the table. |
| `2026-10-05T11-37-03Z-case1-burst60-d9eac3e` | **not a measurement.** Started 2m49s after the app server's JVM; 18.43 rps against 50.00 warm, nine timeouts. |
| `2026-10-05T11-41-10Z-case1-burst15-d9eac3e` | **not a measurement.** Same cold JVM, 6m56s old; 30.94 rps against 56.58. |
| `2026-10-06T04-55-47Z-case1-burst75-e7a130d` | **not a measurement.** The RDS-managed secret had rotated 32 minutes earlier and the server held the old password, so new pooled connections failed with HTTP 500. |
| `2026-10-07T08-38-32Z-case4-eb5e4b3` | **not a measurement.** The feeder lists 501 field workers before the first supervisor at row 502 and `circular()` reached 187 rows, so it re-measured case 2 rather than case 4's mix. |

A `notMeasurement` key moves the run out of the main table in `run-log.md` and
into "Runs that are not measurements", with its reason in the row. Without that
key the correction is provenance only and the run stays where it is.
