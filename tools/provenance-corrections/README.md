# Provenance corrections

**S3 is the source of truth; these are what gets uploaded.** `update-run-log.sh` reads a
`provenance-correction.json` from each run's own prefix in the artefacts bucket, so a correction is
an additive edit to an append-only record rather than a change to the script or to the run's
`run-metadata.json`, which is left exactly as written.

One file per run, named for the run id:

    aws s3 cp tools/provenance-corrections/<run-id>.json \
      s3://avni-loadtest-936573213727/artefacts/<run-id>/provenance-correction.json
    make run_log

## Two kinds of claim, and they are not interchangeable

**`notMeasurement` — the run is not what it claims to be.** The row leaves the main table and
appears under *Runs that are not measurements* with its reason, because a row standing beside
comparable runs reads as comparable. Kept rather than deleted: two of these are the evidence for
the cold-start finding, and case 4's is the evidence that a role-ordered feeder re-measured case 2.

```json
{"notMeasurement": {"reason": "one sentence, lower case, no full stop — it lands in a table cell"}}
```

**`actual` — the run is sound and its record is wrong.** The row stays in the main table; the
corrected value is shown in `run-log-detail.md` as **corrected**, beside what the run recorded, and
a caveat on `run-log.md` points at this file. The first case 1 run is the example: the injector
receives the harness as a `git archive` tarball with no `.git`, so `git rev-parse` failed and
`archiveRun` wrote `gitSha=unknown` with `gitDirty=true` — a missing value and a false positive on
a run that was in fact clean at `f76d110`.

```json
{"actual": {"simulation.gitSha": "<full sha>", "simulation.gitDirty": false}}
```

**A run can need both**, and nothing stops one file carrying both keys. Reach for `notMeasurement`
only when the numbers do not describe what the case says they describe — a wrong sha is not that.

## What the script reads, and what the rest is for

Only `notMeasurement.reason`, `actual.simulation.gitSha` and `actual.simulation.gitDirty` reach the
run log. Every other key in these files — the evidence, the cause, what the run actually measured,
the commit that fixed it — is read by people rather than by the script, and that is the point: the
reason text surfaces as one table cell, and without the rest a reader finding this run in six
months has the verdict and none of the working.

## Why a copy lives here

A correction asserts that a run is not what it claims to be, which is worth reviewing in a diff
rather than taking on trust from a bucket.

**The risk is drift, and it runs one way:** a file edited here and not re-uploaded changes nothing,
while S3 keeps the old text and the run log keeps rendering it. Upload on the same change that
edits one.
