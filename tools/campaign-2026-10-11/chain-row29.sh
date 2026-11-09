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

JAR1097=$HOME/Downloads/avni-server-1097-5ed93de7c.jar; SHA1097=4a8e9a8870e44b99017ea1effc4fa0b066aef46a3de280cab5537745475302a3
JAR1098=$HOME/Downloads/avni-server-1098-3fb5046f7.jar; SHA1098=27c287b916cd2518fe2d64c705e8b1f39580920ea8ba921ac17180f6a6699d48
run_fix(){  # <1097|1098> <A|B>  -- deploy that fix's jar if needed, run the anchor, watch, write up, timeslices
  local fix="$1" a="$2" jar sha sb name log
  case "$fix" in 1097) jar=$JAR1097; sha=$SHA1097; sb=5ed93de7c;; 1098) jar=$JAR1098; sha=$SHA1098; sb=3fb5046f7;; esac
  "$C/deploy-jar.sh" "$jar" "$sha" 2>&1 | sed 's/^/   /' || { say "ABORT: deploy of $fix failed"; exit 1; }
  case "$a" in A) name="case12-anchorA-fix$fix-r1";; B) name="case15-tenaday-anchorB-fix$fix-r1";; esac
  JAR_SHA=$sha SB=$sb TAGV=fix$fix "$C/run-anchor.sh" "$a" 1 2>&1 || { say "ABORT: $fix on $a failed to launch"; exit 1; }
  log="/opt/avni-perf/$name.log"; watch "$log"; postrun "$name" "$log"; timeslices "$name" "$log"
}
resize(){  # <app class>
  for attempt in 1 2 3; do "$C/resize-env.sh" "$1" db.m6g.large m6g.large > $C/resize-$1.log 2>&1 && break
    if grep -q "no such host\|Cannot apply incomplete plan" $C/resize-$1.log && [ $attempt -lt 3 ]; then say "   resize hit a transient DNS miss; retrying in 60 s"; sleep 60; else tail -5 $C/resize-$1.log; say "ABORT: resize to $1 failed"; exit 1; fi
  done; tail -3 $C/resize-$1.log | sed 's/^/   /'
}
say "ROW 29: waiting for any resize in flight"; while pgrep -f 'resize-env.sh' >/dev/null; do sleep 20; done
T=$(aws ec2 describe-instances --instance-ids $APP --query 'Reservations[].Instances[].InstanceType' --output text); [ "$T" = "m6g.large" ] || { say "app is $T; resizing to m6g.large for anchor A"; resize m6g.large; }
say "ROW 29: reloading pilot-day-180 (the bed carries row 27's B r2 pushes)"
export SWAP_PARALLEL=1; load pilot-day-180; unset SWAP_PARALLEL
say "ROW 29: #1097 on anchor A"; run_fix 1097 A
say "ROW 29: #1098 on anchor A (A writes nothing; same bed)"; run_fix 1098 A
say "ROW 29: app -> m6g.xlarge for anchor B"; resize m6g.xlarge
say "ROW 29: #1097 on anchor B"; run_fix 1097 B
say "ROW 29: reloading pilot-day-180 -- B pushed"
export SWAP_PARALLEL=1; load pilot-day-180; unset SWAP_PARALLEL
say "ROW 29: #1098 on anchor B"; run_fix 1098 B
say "ROW 29: app back to m6g.large"; resize m6g.large
say "ROW 29 done for #1097 and #1098: A and B each. Environment left UP (m6g.large / db.m6g.large / m6g.large), jar on the host is #1098's"
