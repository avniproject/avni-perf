# Provenance corrections

**S3 is the source of truth; these are what gets uploaded.** `update-run-log.sh` reads a
`provenance-correction.json` from each run's own prefix in the artefacts bucket, so a correction
is an additive edit to an append-only record rather than a change to the script or to the run's
`run-metadata.json`, which is left exactly as written.

One file per run, named for the run id:

    aws s3 cp tools/provenance-corrections/<run-id>.json \
      s3://avni-loadtest-936573213727/artefacts/<run-id>/provenance-correction.json
    make run_log

**Why keep a copy here at all.** The reason text lands in `run-log.md` as one table cell, and the
rest — the evidence, the cause, what the run actually measured — lands nowhere a reader of this
repository can see it. A correction says a run is not what it claims to be, which is a claim worth
reviewing in a diff rather than taking on trust from a bucket.

**The risk is drift**, and it runs one way: a file edited here and not re-uploaded changes nothing,
while S3 keeps the old text. Upload on the same change that edits one.

`notMeasurement.reason` is the only key the script reads. The others are for whoever finds the run
later and wants to know what happened to it.
