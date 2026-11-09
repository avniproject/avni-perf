#!/usr/bin/env bash
# Row 37's dataset, 5 Nov 2026: pilot-day-180-25k, generated the way the 5k and 10k were on 23 Oct
# (customer bundle ~/avni-perf-bundles/tanuh, columns.json, refs-pilot-day-180.json, supervisors at push
# scale 0.0), split into case feeders with --variant pilot-25k-nosuppush, streamed to the datasets bucket,
# and the bulk removed locally. Feeders case4 (swap-dataset verification) and case5 (the runs) are copied
# into src/gatling/resources; summaries, manifests and every slice are kept in ~/avni-datasets/<name>.keep.
set -uo pipefail
say(){ echo "[$(TZ=Asia/Kolkata date +%H:%M:%S)] $*"; }
NAME=pilot-day-180-25k; VAR=pilot-25k-nosuppush
PERF=/Users/joy/projects/samanvay/avni/avni-perf; G=$PERF/tools/data-generator
B=$HOME/avni-perf-bundles/tanuh; OUT=$HOME/avni-datasets; DEST=s3://avni-loadtest-936573213727/datasets/$NAME.tar.gz
cd /Users/joy/projects/samanvay/avni/avni-infra && . provision/scripts/aws-session.sh avni-load-test </dev/null >/dev/null 2>&1; export AWS_REGION=ap-south-1
[ "$(aws sts get-caller-identity --query Account --output text 2>/dev/null)" = "936573213727" ] || { say "ABORT: no load-test session"; exit 1; }
aws s3 ls "$DEST" >/dev/null 2>&1 && { say "ABORT: $DEST already exists; not overwriting"; exit 1; }
[ -f "$B/organisationConfig.json" ] || { say "ABORT: bundle not at $B"; exit 1; }
FREE=$(df -g "$HOME" | awk 'NR==2{print $4}'); say "$NAME: ${FREE} GB free; ~30 GB expected (2.5x the 10k's 12 GB)"
[ "$FREE" -ge 40 ] || { say "ABORT: want 40 GB free, have $FREE"; exit 1; }
rm -rf "$OUT/$NAME"; mkdir -p "$OUT"
say "$NAME: generating at avni-perf $(cd $PERF && git rev-parse --short HEAD)"
t0=$(date +%s)
( cd "$G" && .venv/bin/python generate.py --recipe "datasets/$NAME.json" --columns columns.json --refs refs-pilot-day-180.json \
    --bundle "$B" --out "$OUT/$NAME" --supervisor-push-scale 0.0 ) > "$OUT/$NAME.generate.log" 2>&1; rc=$?
say "$NAME: generate exit $rc after $(( ($(date +%s) - t0) / 60 )) min; $(du -sh "$OUT/$NAME" 2>/dev/null | cut -f1) on disk"
sed -n '1,20p' "$OUT/$NAME.generate.log" | sed 's/^/    /'; tail -6 "$OUT/$NAME.generate.log" | sed 's/^/    /'
[ "$rc" -eq 0 ] || { say "ABORT: $NAME did not generate"; exit 1; }
say "$NAME: case feeders, variant $VAR"
( cd $PERF && python3 tools/scenario-feeders.py "$OUT/$NAME/sync-users.csv" --variant $VAR ) 2>&1 | sed 's/^/    /'
[ -s "$OUT/$NAME/case5-users-$VAR.csv" ] && [ -s "$OUT/$NAME/case4-users-$VAR.csv" ] || { say "ABORT: feeders not written"; exit 1; }
cp "$OUT/$NAME/case4-users-$VAR.csv" "$OUT/$NAME/case5-users-$VAR.csv" $PERF/src/gatling/resources/
say "$NAME: archiving to $DEST"
( cd "$OUT" && tar czf - "$NAME" ) | aws s3 cp - "$DEST" --only-show-errors --expected-size 15000000000 \
  && say "$NAME: archived $(aws s3 ls "$DEST" --human-readable | awk '{print $3$4}')" \
  || { say "ABORT: upload failed; local copy kept at $OUT/$NAME"; exit 1; }
mkdir -p "$OUT/$NAME.keep"
for d in "$OUT/$NAME"/*/; do t=$(basename "$d"); cp "$d/summary.txt" "$OUT/$NAME.keep/$t.summary.txt" 2>/dev/null; cp "$d/manifest.json" "$OUT/$NAME.keep/$t.manifest.json" 2>/dev/null; done
cp "$OUT/$NAME"/*.csv "$OUT/$NAME.keep/" 2>/dev/null
rm -rf "$OUT/$NAME"; say "$NAME: local bulk removed; summaries, manifests and feeders kept in $OUT/$NAME.keep"
say "done"
