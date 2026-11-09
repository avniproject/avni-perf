#!/usr/bin/env bash
# Row 29, 28 Oct 2026: #1097 and #1098, each built on 18.3 plus its fix alone, on anchors A and B.
# Grouped to cost two reloads and two resizes for four runs: reload -> 1097 A -> 1098 A -> app to
# m6g.xlarge -> 1097 B -> reload -> 1098 B -> app back to m6g.large. A writes nothing, so the two A
# runs share one fresh bed; every B run gets its own. Every run: 900 s warm-up, watch, run log +
# CPU + case index, timeslices. Helpers live in ~/avni-campaign (the scratchpad is swept by /tmp cleanup).
set -uo pipefail
C=$HOME/avni-campaign; PERF=/Users/joy/projects/samanvay/avni/avni-perf
cd /Users/joy/projects/samanvay/avni/avni-infra
. provision/scripts/aws-session.sh avni-load-test </dev/null >/dev/null 2>&1
export AWS_REGION=ap-south-1
say(){ echo "[$(TZ=Asia/Kolkata date +%H:%M:%S)] $*"; }
PROXY="$PWD/configure/scripts/eice-ssh-proxy.sh"; INJ=i-041afc7c6e0761195; APP=i-044c88e15e8ea9e0f
sshinj(){ ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 -o ServerAliveInterval=30 -o ProxyCommand="$PROXY %h" ubuntu@$INJ "$@" 2>/dev/null; }
sshapp(){ ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 -o ProxyCommand="$PROXY %h" ubuntu@$APP "$@" 2>/dev/null; }
session_ok(){ [ "$(aws sts get-caller-identity --query Account --output text 2>/dev/null)" = "936573213727" ]; }
postrun(){  # <label substring> <log>  -- run log, CPU over the run's whole life, run log again
  local run="$1" L="$2" id start now tail
  session_ok || { say "ABORT: AWS session expired before $run's write-up"; exit 1; }
  id=$(sshinj "grep -m1 '^run ' $L | awk '{print \$2}'")
  start=$(date -u -j -f '%Y-%m-%dT%H-%M-%SZ' "${id:0:20}" +%s 2>/dev/null || echo 0)
  now=$(date +%s); tail=$(( (now - start) / 60 - 60 + 1 ))
  { [ "$start" -gt 0 ] && [ "$tail" -ge 3 ] && [ "$tail" -le 120 ]; } || tail=25
  ( cd $PERF && ./tools/update-run-log.sh 2>&1 | tail -2 )
  export NEW_RELIC_API_KEY=$(aws ssm get-parameter --name /avni/loadtest/newrelic-user-key --with-decryption --query Parameter.Value --output text)
  ( cd $PERF && python3 tools/cpu-per-sync.py --account 8563864 --region eu --run "$run" --tail-min "$tail" 2>&1 | grep -v NRAK | grep "$run" | head -2 )
  ( cd $PERF && ./tools/update-run-log.sh 2>&1 | tail -1 )
  say "$run ($id): run log and CPU recorded, window = injection + ${tail} min"
}
load(){  # <dataset>  -- swap-dataset.sh, strict on its exit status and its own closing line
  local set="$1" log="$C/swap-$1.log" rc
  session_ok || { say "ABORT: AWS session expired before loading $set"; exit 1; }
  ( cd $PERF && SWAP_LOG_DIR=$C ./tools/swap-dataset.sh "$set" ) > "$log" 2>&1; rc=$?
  grep -E "^\[|ABORT|done --" "$log" | tail -14 | sed 's/^/    /'
  [ $rc -eq 0 ] && grep -q "done -- $set is loaded and verified" "$log" || { say "ABORT: $set did not load and verify (exit $rc; see $log)"; exit 1; }
  say "$set loaded and verified"
}
watch(){  # <log path>
  local L="$1"; sleep 60
  while :; do D=$(sshinj "grep -c 'BUILD SUCCESSFUL\|BUILD FAILED' $L"); [ "${D:-0}" -ge 1 ] && break
    sshinj "grep 'waiting:' $L | tail -1 | sed 's/^/  [$(TZ=Asia/Kolkata date +%H:%M:%S)] /'; grep '> Global' $L | tail -1 | sed -E 's/ +/ /g; s/^/           /'"; sleep 180; done
  sshinj "grep -A 14 'Global Information' $L | grep -E 'request count|95th|t < 800' | sed -E 's/ +/ /g'; grep 'BUILD' $L | tail -1"
  until sshinj "grep -q 'published. exit' $L"; do sleep 30; done; say "published"
}
timeslices(){  # <label> <log>  -- the per-segment tree for the run's window: launch to +80 min
  local label="$1" L="$2" id from to
  id=$(sshinj "grep -m1 '^run ' $L | awk '{print \$2}'"); from=$(echo "${id:0:20}" | sed -E 's/T([0-9]{2})-([0-9]{2})-([0-9]{2})Z/T\1:\2:\3Z/')
  to=$(date -u -j -v+80M -f '%Y-%m-%dT%H:%M:%SZ' "$from" +%Y-%m-%dT%H:%M:%SZ)
  export NEW_RELIC_API_KEY=$(aws ssm get-parameter --name /avni/loadtest/newrelic-user-key --with-decryption --query Parameter.Value --output text)
  ( cd $PERF && python3 tools/newrelic-export.py --account 8563864 --region eu --out nr-backup --timeslices --label "$label" --from "$from" --to "$to" 2>&1 | grep -v NRAK | tail -2 | sed 's/^/     /' )
  ( cd $PERF && aws s3 sync nr-backup/timeslices s3://avni-loadtest-936573213727/newrelic/timeslices --only-show-errors ) && say "timeslices $label captured ($from .. $to) and synced"
}

# 28 Oct 2026, end of day: once the #1100 chain exits, finish #1100's write-up if the chain tripped on
# its expired credentials (this script sources fresh ones), confirm its artefacts, archive the day's
# server and injector logs, stop the environment, then run the day's New Relic export.
B=s3://avni-loadtest-936573213727; DAY=2026-10-29; NAME=case13-anchorC-rc18.3-r1; L="/opt/avni-perf/$NAME.log"
say "capture: waiting for the row 30 A/C chain to exit"; while pgrep -f 'chain-row30-AC-recover.sh' >/dev/null; do sleep 30; done
say "capture: chain exited: $(tail -n1 $C/row30-AC-recover.log | cut -c1-120)"
tail -n1 $C/row30-AC-recover.log | grep -q 'ROW 30 (A, C) done' || { say "ABORT: the chain did not end cleanly; not stopping"; exit 1; }
session_ok || { say "ABORT: no valid session"; exit 1; }
R=$(sshinj "grep -m1 '^run ' $L | awk '{print \$2}'")
N=$(aws s3 ls "$B/artefacts/$R/" --recursive | wc -l | tr -d ' '); Z=$(aws s3 ls "$B/artefacts/$R/$R.zip" --human-readable | awk '{print $3 $4}')
say "capture: C's artefacts in S3 ($R): $N objects, zip ${Z:-MISSING}"
[ "$N" -gt 100 ] && [ -n "$Z" ] || { say "ABORT: C's artefacts are not in S3; not stopping"; exit 1; }
say "capture: server logs for $DAY -> S3"
sshapp "cd /var/log/avni_server && sudo tar czf /tmp/avni-server-$DAY.tar.gz chs.log chs.log.$DAY.*.gz 2>/dev/null && sudo chown ubuntu /tmp/avni-server-$DAY.tar.gz && cat /tmp/avni-server-$DAY.tar.gz && sudo rm -f /tmp/avni-server-$DAY.tar.gz" > /tmp/avni-server-$DAY.tar.gz
[ -s /tmp/avni-server-$DAY.tar.gz ] && aws s3 cp /tmp/avni-server-$DAY.tar.gz $B/logs/avni-server/$DAY.tar.gz --only-show-errors && rm -f /tmp/avni-server-$DAY.tar.gz && say "   uploaded" || say "   WARNING: server log archive failed"
say "capture: injector run logs for $DAY -> S3"
sshinj "cd /opt/avni-perf && tar czf - \$(find . -maxdepth 1 -name '*.log' -newermt '$DAY 00:00' -printf '%P ')" > /tmp/injector-$DAY.tar.gz
tar tzf /tmp/injector-$DAY.tar.gz | sed 's/^/     /'
[ -s /tmp/injector-$DAY.tar.gz ] && aws s3 cp /tmp/injector-$DAY.tar.gz $B/logs/injector/$DAY.tar.gz --only-show-errors && rm -f /tmp/injector-$DAY.tar.gz && say "   uploaded" || say "   WARNING: injector log archive failed"
aws s3 ls $B/logs/ --recursive --human-readable | grep "$DAY" | awk '{print "     "$3$4"  "$5}'
say "capture: stopping the environment (classes as left: app $(aws ec2 describe-instances --instance-ids $APP --query 'Reservations[].Instances[].InstanceType' --output text), db.m6g.large, injector m6g.large)"
provision/scripts/env-teardown.sh stop 2>&1 | tail -n 12 | sed 's/^/     /'
say "capture: status:"; provision/scripts/env-teardown.sh status 2>&1 | tail -n 8 | sed 's/^/     /'
until [ "$(date -u +%H%M)" -ge 1901 ]; do say "capture: waiting for the 18Z hour (C's end) to complete before the New Relic export"; sleep 300; done
export NEW_RELIC_API_KEY=$(aws ssm get-parameter --name /avni/loadtest/newrelic-user-key --with-decryption --query Parameter.Value --output text)
[ -n "$NEW_RELIC_API_KEY" ] || { say "ABORT: no New Relic key"; exit 1; }
say "capture: New Relic hourly export since $DAY"
( cd $PERF && python3 tools/newrelic-export.py --account 8563864 --region eu --out nr-backup --since $DAY --s3 2>&1 | grep -v NRAK | grep -vE 'fewer rows|single millisecond' | tail -n 4 | sed 's/^/     /' )
( cd $PERF && for et in Transaction SqlTrace TransactionTrace; do printf "     %-17s %s\n" $et "$(ls nr-backup/$et/$DAY/ 2>/dev/null | tr '\n' ' ')"; done )
say "capture: done"
