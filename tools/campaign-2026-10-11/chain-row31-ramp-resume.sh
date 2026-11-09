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
resize_all(){  # <app class> <db class>  (injector class comes from $C/injector-class.override)
  for attempt in 1 2 3; do "$C/resize-env.sh" "$1" "$2" m6g.large > $C/resize-$1.log 2>&1 && break
    if grep -q "no such host\|Cannot apply incomplete plan" $C/resize-$1.log && [ $attempt -lt 3 ]; then say "   resize hit a transient DNS miss; retrying in 60 s"; sleep 60; else tail -5 $C/resize-$1.log; say "ABORT: resize to $1 / $2 failed"; exit 1; fi
  done; tail -3 $C/resize-$1.log | sed 's/^/   /'
}
watch_stress(){  # <log>  -- ticks every 3 min; stop rule: interval failures > 1% on two consecutive ticks (~6 min)
  local L="$1" prev_t=0 prev_k=0 bad=0 line tot ko dt dk
  sleep 60
  while :; do
    D=$(sshinj "grep -c 'BUILD SUCCESSFUL\|BUILD FAILED' $L"); [ "${D:-0}" -ge 1 ] && break
    line=$(sshinj "grep '> Global' $L | tail -1"); tot=$(echo "$line" | awk -F'|' '{gsub(/[ ,]/,"",$2); print $2+0}'); ko=$(echo "$line" | awk -F'|' '{gsub(/[ ,]/,"",$4); print $4+0}')
    sshinj "grep 'waiting:' $L | tail -1" | sed "s/^/  [$(TZ=Asia/Kolkata date +%H:%M:%S)] /"
    if [ "${tot:-0}" -gt "$prev_t" ]; then dt=$((tot-prev_t)); dk=$((ko-prev_k))
      echo "           > Global | ${tot} | KO ${ko} | interval ${dt} req, ${dk} KO ($(awk -v a=$dk -v b=$dt 'BEGIN{printf "%.2f", 100*a/b}')%)"
      if awk -v a=$dk -v b=$dt 'BEGIN{exit !(b>0 && a/b>0.01)}'; then bad=$((bad+1)); else bad=0; fi
      prev_t=$tot; prev_k=$ko
      if [ $bad -ge 2 ]; then say "STOP RULE: interval failures above 1% for two consecutive ticks -- stopping the simulation"; sshinj "pkill -f AvniSyncSimulation"; fi
    fi
    sleep 180
  done
  sshinj "grep -A 14 'Global Information' $L | grep -E 'request count|95th|t < 800' | sed -E 's/ +/ /g'; grep 'BUILD' $L | tail -1"
  until sshinj "grep -q 'published. exit' $L"; do sleep 30; done; say "published"
}
ts_window(){  # <label> <log> <minutes>  -- timeslices from launch to launch + minutes
  local label="$1" L="$2" mins="$3" id from to
  id=$(sshinj "grep -m1 '^run ' $L | awk '{print \$2}'"); from=$(echo "${id:0:20}" | sed -E 's/T([0-9]{2})-([0-9]{2})-([0-9]{2})Z/T\1:\2:\3Z/')
  to=$(date -u -j -v+${mins}M -f '%Y-%m-%dT%H:%M:%SZ' "$from" +%Y-%m-%dT%H:%M:%SZ)
  export NEW_RELIC_API_KEY=$(aws ssm get-parameter --name /avni/loadtest/newrelic-user-key --with-decryption --query Parameter.Value --output text)
  ( cd $PERF && python3 tools/newrelic-export.py --account 8563864 --region eu --out nr-backup --timeslices --label "$label" --from "$from" --to "$to" 2>&1 | grep -v NRAK | tail -2 | sed 's/^/     /' )
  ( cd $PERF && aws s3 sync nr-backup/timeslices s3://avni-loadtest-936573213727/newrelic/timeslices --only-show-errors ) && say "timeslices $label captured ($from .. $to) and synced"
}

# Resumed 30 Oct ~13:55: the first launch failed at start-up (GATLING_HEAP replaced Gatling's --add-opens
# flags; fixed in 1ff23cc). The bed (pilot-day-180-10k) is loaded and verified, classes and jar are set,
# so this deploys the fixed harness and goes straight to the warm-up and the ramp.
session_ok || { say "ABORT: AWS session not valid"; exit 1; }
WANT=$(git -C $PERF rev-parse HEAD)
if [ "$(sshinj 'cat /opt/avni-perf/.harness-sha 2>/dev/null')" = "$WANT" ]; then say "ROW 31: injector already carries harness ${WANT:0:7}"; else
  say "ROW 31: deploying harness ${WANT:0:7} (GATLING_HEAP) to the injector"
  ( cd configure && ansible-playbook -i inventory/loadtest loadtest_injector.yml -e injector_harness_sha=$WANT > $C/injector-deploy-31.log 2>&1 ); rc=$?
  grep -E 'PLAY RECAP|failed=|unreachable=' $C/injector-deploy-31.log | tail -2 | sed 's/^/     /'
  [ $rc -eq 0 ] && [ "$(sshinj 'cat /opt/avni-perf/.harness-sha 2>/dev/null')" = "$WANT" ] || { say "ABORT: harness deploy failed (see $C/injector-deploy-31.log)"; exit 1; }
fi
say "ROW 31: jar"; "$C/deploy-jar.sh" "$JAR30" "$SHA30" 2>&1 | sed 's/^/   /' || { say "ABORT: jar deploy failed"; exit 1; }
TYPE=$(aws ec2 describe-instances --instance-ids $APP --query 'Reservations[].Instances[].InstanceType' --output text); DBT=$(aws rds describe-db-instances --db-instance-identifier avni-loadtest --query 'DBInstances[0].DBInstanceClass' --output text); IT=$(aws ec2 describe-instances --instance-ids $INJ --query 'Reservations[].Instances[].InstanceType' --output text)
[ "$TYPE/$DBT/$IT" = "m6g.4xlarge/db.m6g.4xlarge/m6g.2xlarge" ] || { say "ABORT: classes are $TYPE/$DBT/$IT"; exit 1; }
DEP=""; for i in 1 2 3; do DEP=$(sshapp 'sudo sha256sum /opt/avni_server/avni-server.jar' | cut -d' ' -f1); [ -n "$DEP" ] && break; sleep 10; done
[ "$DEP" = "$SHA30" ] || { say "ABORT: the release candidate is not deployed (sha ${DEP:-unreadable})"; exit 1; }
say "verified: $TYPE / $DBT / injector $IT, jar rc18.3 = 946553685"
say "1. warm-up, 900 s, result discarded"
WU=$(AVNI_WARMUP_BURST_SECONDS=900 provision/scripts/env-warmup.sh 2>&1); echo "$WU" | tail -2
echo "$WU" | grep -q "BUILD SUCCESSFUL in" || { say "   warm-up failed once (EICE?); retrying"; sleep 60; WU=$(AVNI_WARMUP_BURST_SECONDS=900 provision/scripts/env-warmup.sh 2>&1); echo "$WU" | grep -q "BUILD SUCCESSFUL in" || { say "ABORT: not warmed"; exit 1; }; }
NAME=case15-10k-row31-ramp-rc18.3-batch50
PROPS="-DDATASET_ID=pilot-day-180-10k -DSERVER_BUILD=946553685 -DPROFILE=stress \
-DSYNCS_PER_HOUR=10000 -DSTRESS_TO_SYNCS_PER_HOUR=40000 -DDURATION_MINUTES=120 \
-DSYNC_MODE=realistic -DSYNC_USERS=case5-users-pilot-10k-nosuppush.csv -DCUSTOMER_PUSH_DRAW=v3 -DPAGE_SIZE=1000 \
-DPUSH=on -DPUSH_MEDIA_PER_ENCOUNTER=8 -DMEDIA_MODEL=pause -DMEDIA_FILE_KB=500 -DMEDIA_UPLOAD_KBPS=125 \
-DCO_TENANTS=on -DCO_TENANT_SYNCS_PER_HOUR=792 -DCO_TENANT_SECONDS=7200 -DCO_TENANT_SEED=42 \
-DCO_TENANT_MEDIA_PER_ENCOUNTER=0.2306 -DUPLOAD_URL_BATCH=50 -DGATLING_HEAP=8G \
-DCACHE_POLICY=warm-after-discarded-warmup-$TYPE"
say "2. launching row 31's ramp as $NAME: 10,000 -> 40,000 syncs an hour over 120 min"
for attempt in 1 2; do
  provision/scripts/launch-run.sh "$NAME" $PROPS 2>&1 | tail -8 && sshinj 'ps -eo args | grep -c "[A]vniSyncSimulation"' | grep -q '^[1-9]' && break
  [ $attempt -eq 1 ] && { say "   launch did not start a simulation; retrying once"; sleep 30; } || { say "ABORT: ramp failed to launch"; exit 1; }
done
L="/opt/avni-perf/$NAME.log"; watch_stress "$L"
postrun "$NAME" "$L"; ts_window "$NAME" "$L" 145
say "ROW 31 ramp done. Environment left UP at m6g.4xlarge / db.m6g.4xlarge / injector m6g.2xlarge on pilot-day-180-10k; the steady pair is queued after the ramp is read"
