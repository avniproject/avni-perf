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

JAR30=$HOME/Downloads/avni-server-18.3-1097-1098-1100-1103-946553685.jar; SHA30=1315739bc1074820773fe19809e15fbf219d92f05bfff687f80804cead085729
run30(){  # <A|B|C|D>  -- the combined jar; B and D with the batched client (what ships); one launch retry if the injector never started
  local a="$1" name extra="" tag log
  "$C/deploy-jar.sh" "$JAR30" "$SHA30" 2>&1 | sed 's/^/   /' || { say "ABORT: deploy of the combined jar failed"; exit 1; }
  case "$a" in A) name="case12-anchorA-rc18.3-r1"; tag=rc18.3;; B) name="case15-tenaday-anchorB-rc18.3-batch50-r1"; extra="-DUPLOAD_URL_BATCH=50"; tag=rc18.3-batch50;; C) name="case13-anchorC-rc18.3-r1"; tag=rc18.3;; D) name="case15-5k-anchorD-rc18.3-batch50-r1"; extra="-DUPLOAD_URL_BATCH=50"; tag=rc18.3-batch50;; esac
  for attempt in 1 2; do
    JAR_SHA=$SHA30 SB=946553685 TAGV=$tag EXTRA_PROPS="$extra" "$C/run-anchor-30.sh" "$a" 1 2>&1 && break
    if [ $attempt -eq 1 ] && [ "$(sshinj 'ps -eo args | grep -c "[A]vniSyncSimulation"')" = "0" ]; then say "   launch did not start a simulation (lost ssh?); retrying once"; sleep 30; else say "ABORT: combined jar on $a failed to launch"; exit 1; fi
  done
  log="/opt/avni-perf/$name.log"; watch "$log"
  # The write-up needs only S3, CloudWatch and New Relic, so it overlaps the next run's deploy and warm-up;
  # write-ups edit the same run-log files, so each waits for the previous one (and the chain waits at the end).
  wait_writeup; ( postrun "$name" "$log"; timeslices "$name" "$log"; say "   write-up of $name finished" ) > $C/writeup-$name.log 2>&1 & WRITEUP_PID=$!
}
WRITEUP_PID=""
wait_writeup(){ [ -n "$WRITEUP_PID" ] && { say "   waiting for the previous write-up"; wait $WRITEUP_PID; cat $C/writeup-*.log 2>/dev/null | grep -E 'CPU s|recorded|captured|finished' | tail -n 4 | sed 's/^/   /'; WRITEUP_PID=""; }; return 0; }
resize_all(){  # <app class> <db class>
  for attempt in 1 2 3; do "$C/resize-env.sh" "$1" "$2" m6g.large > $C/resize-$1.log 2>&1 && break
    if grep -q "no such host\|Cannot apply incomplete plan" $C/resize-$1.log && [ $attempt -lt 3 ]; then say "   resize hit a transient DNS miss; retrying in 60 s"; sleep 60; else tail -5 $C/resize-$1.log; say "ABORT: resize to $1 / $2 failed"; exit 1; fi
  done; tail -3 $C/resize-$1.log | sed 's/^/   /'
}
# Row 30, 29 Oct 2026 evening: the release candidate on A then C -- both on m6g.large / db.m6g.large; A writes nothing,
# so C runs on the same fresh bed. Queued behind row 29b's resume chain.
say "ROW 30: waiting for row 29b to finish"; while pgrep -f 'chain-row29b-1098-resume.sh' >/dev/null; do sleep 60; done
tail -n1 $C/row29b-1098-resume.log | grep -q 'ROW 29b done' || { say "ABORT: row 29b did not end cleanly -- $(tail -n1 $C/row29b-1098-resume.log | cut -c1-120)"; exit 1; }
session_ok || { say "ABORT: AWS session not valid"; exit 1; }
T=$(aws ec2 describe-instances --instance-ids $APP --query 'Reservations[].Instances[].InstanceType' --output text); [ "$T" = "m6g.large" ] || { say "app is $T; resizing to m6g.large"; resize_all m6g.large db.m6g.large; }
say "ROW 30: reloading pilot-day-180 (the bed carries row 29b's B pushes)"
export SWAP_PARALLEL=1; load pilot-day-180; unset SWAP_PARALLEL
say "ROW 30: release candidate on anchor A"; run30 A
say "ROW 30: release candidate on anchor C (case 13; A wrote nothing, same bed)"; run30 C
wait_writeup; say "ROW 30 (A, C) done. Environment left UP at m6g.large / db.m6g.large / m6g.large; B and D follow (chain-row30-BD.sh)"
