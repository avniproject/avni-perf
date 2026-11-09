#!/usr/bin/env bash
# Row 33, Nov 2026: the scale-out gate. Helpers live in ~/avni-campaign (the scratchpad is swept by /tmp cleanup).
set -uo pipefail
C=$HOME/avni-campaign; PERF=/Users/joy/projects/samanvay/avni/avni-perf
cd /Users/joy/projects/samanvay/avni/avni-infra
. provision/scripts/aws-session.sh avni-load-test </dev/null >/dev/null 2>&1
export AWS_REGION=ap-south-1
say(){ echo "[$(TZ=Asia/Kolkata date +%H:%M:%S)] $*"; }
PROXY="$PWD/configure/scripts/eice-ssh-proxy.sh"; INJ=i-041afc7c6e0761195; APP=i-044c88e15e8ea9e0f
sshinj(){ ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 -o ServerAliveInterval=30 -o ProxyCommand="$PROXY %h" ubuntu@$INJ "$@" 2>/dev/null; }
. $C/app-hosts.sh
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
  ( cd $PERF && AVNI_APP_INSTANCE=$(app_ids_csv) python3 tools/cpu-per-sync.py --account 8563864 --region eu --run "$run" --tail-min "$tail" 2>&1 | grep -v NRAK | grep "$run" | head -2 )
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


WRITEUP_PID=""
wait_writeup(){ [ -n "$WRITEUP_PID" ] && { say "   waiting for the previous write-up"; wait $WRITEUP_PID; grep -hE 'CPU s|recorded|captured|finished' $C/writeup-row33-*.log 2>/dev/null | tail -n 4 | sed 's/^/   /'; WRITEUP_PID=""; }; return 0; }

app_cpu_last(){  # <minutes>  -- each app host's mean CPU over the last N minutes, "id pct" per line
  local m="$1" id v
  for id in $(app_ids); do
    v=$(aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization --dimensions Name=InstanceId,Value=$id \
          --start-time "$(date -u -v-$((m+1))M +%Y-%m-%dT%H:%M:%SZ)" --end-time "$(date -u -v-1M +%Y-%m-%dT%H:%M:%SZ)" \
          --period 60 --statistics Average --query 'Datapoints[].Average' --output text | tr '\t' '\n' | awk '{s+=$1;n++} END{if(n) printf "%.0f", s/n; else print "none"}')
    echo "$id $v"
  done
}
check_spread(){  # <label> <minutes>  -- every copy must have taken load: none below a third of the busiest, none idle
  local label="$1" m="$2" out
  out=$(app_cpu_last "$m"); echo "$out" | sed "s/^/   $label: /"
  echo "$out" | awk '{if($2=="none"){bad=1} else {v[NR]=$2; if($2>mx)mx=$2}} END{for(i in v) if(mx>=10 && v[i]<mx/3) bad=1; exit bad}' \
    || { say "ABORT: $label CPU is uneven or missing across the app hosts -- one copy is not taking load"; exit 1; }
}
targets_healthy(){  # every app host registered and healthy behind the load balancer
  local tg h
  tg=$(aws elbv2 describe-target-groups --names avni-loadtest-app --query 'TargetGroups[0].TargetGroupArn' --output text)
  for i in $(seq 1 20); do
    h=$(aws elbv2 describe-target-health --target-group-arn "$tg" --query 'TargetHealthDescriptions[].[Target.Id,TargetHealth.State]' --output text)
    [ "$(echo "$h" | awk '$2=="healthy"' | wc -l | tr -d ' ')" = "$(app_ids | wc -w | tr -d ' ')" ] && [ "$(echo "$h" | awk '$2!="healthy"' | wc -l | tr -d ' ')" = "0" ] && { echo "$h" | sed 's/^/   target /'; return 0; }
    sleep 15
  done
  echo "$h" | sed 's/^/   target /'; say "ABORT: not every app host is a healthy target"; exit 1
}
same_everywhere(){  # every copy: the release candidate's sha, New Relic attached, 5,120 MB heap
  local id sha cmd
  for id in $(app_ids); do
    sha=$(sshto_retry $id 'sudo sha256sum /opt/avni_server/avni-server.jar' | cut -d' ' -f1)
    cmd=$(sshto_retry $id 'ps -eo args | grep "[a]vni-server.jar"')
    [ "$sha" = "$SHA30" ] || { say "ABORT: $id runs ${sha:0:12}, not the release candidate"; exit 1; }
    echo "$cmd" | grep -q 'newrelic.jar' || { say "ABORT: $id has no New Relic agent"; exit 1; }
    echo "$cmd" | grep -q -- '-Xmx5120m' || { say "ABORT: $id heap is not -Xmx5120m"; exit 1; }
    say "   $id: sha ${sha:0:12}, New Relic attached, -Xmx5120m"
  done
}

steady(){  # <syncs per hour> <label> <timeslice minutes>
  local R="$1" TAG="$2" MINS="$3" NAME="case15-10k-row33-2x4xl-steady-$2-rc18.3-batch50" WU
  say "ROW 33 steady $TAG: reloading pilot-day-180-10k"
  export SWAP_PARALLEL=1; load pilot-day-180-10k; unset SWAP_PARALLEL
  same_everywhere
  say "ROW 33 steady $TAG: warm-up, 900 s, through the load balancer"
  WU=$(AVNI_WARMUP_BURST_SECONDS=900 provision/scripts/env-warmup.sh 2>&1); echo "$WU" | tail -2
  echo "$WU" | grep -q "BUILD SUCCESSFUL in" || { say "   warm-up failed once; retrying"; sleep 60; WU=$(AVNI_WARMUP_BURST_SECONDS=900 provision/scripts/env-warmup.sh 2>&1); echo "$WU" | grep -q "BUILD SUCCESSFUL in" || { say "ABORT: not warmed"; exit 1; }; }
  check_spread "warm-up CPU" 14
  PROPS="-DDATASET_ID=pilot-day-180-10k -DSERVER_BUILD=946553685 -DPROFILE=steady \
-DUSER_COUNT=$R -DSYNC_WINDOW_HOURS=1 -DDURATION_MINUTES=60 \
-DSYNC_MODE=realistic -DSYNC_USERS=case5-users-pilot-10k-nosuppush.csv -DCUSTOMER_PUSH_DRAW=v3 -DPAGE_SIZE=1000 \
-DPUSH=on -DPUSH_MEDIA_PER_ENCOUNTER=8 -DMEDIA_MODEL=pause -DMEDIA_FILE_KB=500 -DMEDIA_UPLOAD_KBPS=125 \
-DCO_TENANTS=on -DCO_TENANT_SYNCS_PER_HOUR=792 -DCO_TENANT_SECONDS=3600 -DCO_TENANT_SEED=42 \
-DCO_TENANT_MEDIA_PER_ENCOUNTER=0.2306 -DUPLOAD_URL_BATCH=50 -DGATLING_HEAP=8G \
-DCACHE_POLICY=warm-after-discarded-warmup-2x-m6g.4xlarge"
  say "ROW 33 steady $TAG: launching $NAME at $R syncs an hour for 60 min on $(app_ids | wc -w | tr -d ' ') app hosts"
  for attempt in 1 2; do
    AVNI_EXPECT_RATE="$R syncs/hour for 60 min" provision/scripts/launch-run.sh "$NAME" $PROPS 2>&1 | tail -6 && sshinj 'ps -eo args | grep -c "[A]vniSyncSimulation"' | grep -q '^[1-9]' && break
    [ $attempt -eq 1 ] && { say "   launch did not start a simulation; retrying once"; sleep 30; } || { say "ABORT: steady $TAG failed to launch"; exit 1; }
  done
  L="/opt/avni-perf/$NAME.log"; watch_stress "$L"
  app_cpu_last 58 | sed 's/^/   run CPU, last 58 min: /'
  wait_writeup; ( postrun "$NAME" "$L"; ts_window "$NAME" "$L" "$MINS"; say "   write-up of $NAME finished" ) > $C/writeup-row33-$TAG.log 2>&1 & WRITEUP_PID=$!
}


# Resume, 4 Nov 2026 14:2x: chain-row33.sh aborted at its warm-up spread check, whose 5% floor a 100-device
# warm-up cannot reach on 32 vCPU (both hosts rose together, ~1%). The bed is the 13:59 reload, untouched since
# but for that warm-up, which ended 14:14 -- so launch now, inside the 20 minutes known to stay warm.
session_ok || { say "ABORT: AWS session not valid"; exit 1; }
say "ROW 33 RESUME: launching on the 13:59 reload; warm-up ended 14:14"
targets_healthy
same_everywhere
R=27500; TAG=1.1x-of-row31; MINS=120; NAME="case15-10k-row33-2x4xl-steady-$TAG-rc18.3-batch50"
PROPS="-DDATASET_ID=pilot-day-180-10k -DSERVER_BUILD=946553685 -DPROFILE=steady \
-DUSER_COUNT=$R -DSYNC_WINDOW_HOURS=1 -DDURATION_MINUTES=60 \
-DSYNC_MODE=realistic -DSYNC_USERS=case5-users-pilot-10k-nosuppush.csv -DCUSTOMER_PUSH_DRAW=v3 -DPAGE_SIZE=1000 \
-DPUSH=on -DPUSH_MEDIA_PER_ENCOUNTER=8 -DMEDIA_MODEL=pause -DMEDIA_FILE_KB=500 -DMEDIA_UPLOAD_KBPS=125 \
-DCO_TENANTS=on -DCO_TENANT_SYNCS_PER_HOUR=792 -DCO_TENANT_SECONDS=3600 -DCO_TENANT_SEED=42 \
-DCO_TENANT_MEDIA_PER_ENCOUNTER=0.2306 -DUPLOAD_URL_BATCH=50 -DGATLING_HEAP=8G \
-DCACHE_POLICY=warm-after-discarded-warmup-2x-m6g.4xlarge"
say "ROW 33 steady $TAG: launching $NAME at $R syncs an hour for 60 min on $(app_ids | wc -w | tr -d ' ') app hosts"
for attempt in 1 2; do
  AVNI_EXPECT_RATE="$R syncs/hour for 60 min" provision/scripts/launch-run.sh "$NAME" $PROPS 2>&1 | tail -6 && sshinj 'ps -eo args | grep -c "[A]vniSyncSimulation"' | grep -q '^[1-9]' && break
  [ $attempt -eq 1 ] && { say "   launch did not start a simulation; retrying once"; sleep 30; } || { say "ABORT: steady $TAG failed to launch"; exit 1; }
done
L="/opt/avni-perf/$NAME.log"
( sleep 900; say "   spread 10 min into the run:"; app_cpu_last 5 | sed 's/^/   run CPU, last 5 min: /' ) &
watch_stress "$L"
app_cpu_last 58 | sed 's/^/   run CPU, last 58 min: /'
( postrun "$NAME" "$L"; ts_window "$NAME" "$L" "$MINS"; say "   write-up of $NAME finished" ) > $C/writeup-row33-$TAG.log 2>&1
grep -hE 'CPU s|recorded|captured|finished' $C/writeup-row33-$TAG.log | tail -n 4 | sed 's/^/   /'
say "ROW 33 done. Environment left UP at 2 x m6g.4xlarge / db.m6g.4xlarge / injector m6g.2xlarge"
