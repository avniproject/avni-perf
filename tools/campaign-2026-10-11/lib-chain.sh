# Sourced by row chains from row 34 on. Not executable on its own.
#
#   ROW=row34; . ~/avni-campaign/lib-chain.sh
#   prepare_bed db.m6g.4xlarge m6g.2xlarge pilot-day-180-10k   # app hosts stay stopped
#   bring_up_apps m6g.4xlarge 2                                # resize/configure/start/jar/checks
#   warm_up; <launch and watch a run>; writeup_bg <name> <log> <minutes>
#   between_runs pilot-day-180-10k                             # app hosts stopped while it reloads
#   warm_up; <next run>
#   wait_writeup
#
# **Why this order (Nov 2026):** a 10k reload is ~80 minutes, and the app hosts used to idle
# through it because the first one was the reload's psql client. The injector is the client
# now (avni-perf swap-dataset.sh), so every app host stays stopped until the bed is ready and
# starts one at a time (env-teardown.sh start-apps). A run's JVM therefore always starts cold
# after a reload; the 900 s warm-up immediately before each measured run is what covers that.
# Helpers live in ~/avni-campaign (the scratchpad is swept by /tmp cleanup).
: "${ROW:?set ROW (e.g. row34) before sourcing lib-chain.sh}"

C=$HOME/avni-campaign; PERF=/Users/joy/projects/samanvay/avni/avni-perf
cd /Users/joy/projects/samanvay/avni/avni-infra
. provision/scripts/aws-session.sh avni-load-test </dev/null >/dev/null 2>&1
export AWS_REGION=ap-south-1
say(){ echo "[$(TZ=Asia/Kolkata date +%H:%M:%S)] $*"; }
PROXY="$PWD/configure/scripts/eice-ssh-proxy.sh"; INJ=i-041afc7c6e0761195; APP=i-044c88e15e8ea9e0f
# **Credentials before every connection** (14 Nov 2026). The chain holds the credentials it sourced; a refresh
# lands in the CLI cache, not in a running process. On 13 Nov a wait loop with no session check kept polling
# with credentials that had expired at 19:27, never saw the run end, and hung for 2.5 hours. creds_fresh is a
# date comparison, no network call; when the credentials are within 5 minutes of lapsing, ensure_session
# re-reads them, and waits for an MFA refresh if there is none yet.
creds_fresh(){ local e="${AWS_CREDENTIAL_EXPIRATION:-}" t; [ -n "$e" ] || return 0
  t=$(date -u -j -f '%Y-%m-%dT%H:%M:%S' "${e:0:19}" +%s 2>/dev/null) || return 0; [ "$(date -u +%s)" -lt $(( t - 300 )) ]; }
sshinj(){ creds_fresh || refresh >&2; ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 -o ServerAliveInterval=30 -o ProxyCommand="$PROXY %h" ubuntu@$INJ "$@" 2>/dev/null; }
. $C/app-hosts.sh
sshapp(){ creds_fresh || refresh >&2; ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 -o ProxyCommand="$PROXY %h" ubuntu@$APP "$@" 2>/dev/null; }
session_ok(){ [ "$(aws sts get-caller-identity --query Account --output text 2>/dev/null)" = "936573213727" ]; }
postrun(){  # <label substring> <log> [run id]  -- run log, CPU over the run's whole life, run log again
  # The run id is passed in when the caller recorded it at launch (run_id_of), so the write-up does not need the
  # injector and the environment can stop before it finishes. Without one it is read from the injector, as before.
  local run="$1" L="$2" id="${3:-}" start now tail
  ensure_session
  [ -n "$id" ] || id=$(sshinj "grep -m1 '^run ' $L | awk '{print \$2}'")
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
  until sshinj "grep -q 'published. exit' $L"; do ensure_session; sleep 30; done; say "published"
}
timeslices(){  # <label> <log>  -- the per-segment tree for the run's window: launch to +80 min
  local label="$1" L="$2" id from to
  id=$(sshinj "grep -m1 '^run ' $L | awk '{print \$2}'"); from=$(echo "${id:0:20}" | sed -E 's/T([0-9]{2})-([0-9]{2})-([0-9]{2})Z/T\1:\2:\3Z/')
  to=$(date -u -j -v+80M -f '%Y-%m-%dT%H:%M:%SZ' "$from" +%Y-%m-%dT%H:%M:%SZ)
  export NEW_RELIC_API_KEY=$(aws ssm get-parameter --name /avni/loadtest/newrelic-user-key --with-decryption --query Parameter.Value --output text)
  ( cd $PERF && python3 tools/newrelic-export.py --account 8563864 --region eu --out nr-backup --timeslices --label "$label" --from "$from" --to "$to" 2>&1 | grep -v NRAK | tail -2 | sed 's/^/     /' )
  ( cd $PERF && aws s3 sync nr-backup/timeslices s3://avni-loadtest-936573213727/newrelic/timeslices --only-show-errors ) && say "timeslices $label captured ($from .. $to) and synced"
}

JAR30=$HOME/avni-campaign/jars/avni-server-18.3-1097-1098-1100-1103-946553685.jar; SHA30=1315739bc1074820773fe19809e15fbf219d92f05bfff687f80804cead085729
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
  until sshinj "grep -q 'published. exit' $L"; do ensure_session; sleep 30; done; say "published"
}
ts_window(){  # <label> <log> <minutes> [run id]  -- timeslices from launch to launch + minutes
  local label="$1" L="$2" mins="$3" id="${4:-}" from to
  ensure_session
  [ -n "$id" ] || id=$(sshinj "grep -m1 '^run ' $L | awk '{print \$2}'"); from=$(echo "${id:0:20}" | sed -E 's/T([0-9]{2})-([0-9]{2})-([0-9]{2})Z/T\1:\2:\3Z/')
  to=$(date -u -j -v+${mins}M -f '%Y-%m-%dT%H:%M:%SZ' "$from" +%Y-%m-%dT%H:%M:%SZ)
  export NEW_RELIC_API_KEY=$(aws ssm get-parameter --name /avni/loadtest/newrelic-user-key --with-decryption --query Parameter.Value --output text)
  ( cd $PERF && python3 tools/newrelic-export.py --account 8563864 --region eu --out nr-backup --timeslices --label "$label" --from "$from" --to "$to" 2>&1 | grep -v NRAK | tail -2 | sed 's/^/     /' )
  ( cd $PERF && aws s3 sync nr-backup/timeslices s3://avni-loadtest-936573213727/newrelic/timeslices --only-show-errors ) && say "timeslices $label captured ($from .. $to) and synced"
}


WRITEUP_PID=""
# **Record a run's id the moment it launches.** $C/runids/<name> holds it for the write-up.
run_id_of(){  # <run name> -- read the id from the injector's log (three tries) and record it; echoes it
  local id="" i; mkdir -p $C/runids
  for i in 1 2 3 4 5 6; do id=$(sshinj "grep -m1 '^run ' /opt/avni-perf/$1.log 2>/dev/null | awk '{print \$2}'"); [ -n "$id" ] && break; sleep 10; done
  [ -n "$id" ] && echo "$id" > $C/runids/$1; echo "$id"
}
wait_writeup(){ [ -n "$WRITEUP_PID" ] && { say "   waiting for the previous write-up"; wait $WRITEUP_PID; grep -hE 'CPU s|recorded|captured|finished' $C/writeup-$ROW-*.log 2>/dev/null | tail -n 4 | sed 's/^/   /'; WRITEUP_PID=""; }; return 0; }

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




JAR_VERSION=18.3-1097-1098-1100-1103-946553685
DB_C=""; INJ_C=""
env_state(){ aws rds describe-db-instances --db-instance-identifier avni-loadtest --query 'DBInstances[0].DBInstanceStatus' --output text; }

prepare_bed(){  # <db class> <injector class> <dataset>  -- start without the app hosts, resize db+injector, reload
  DB_C="$1"; INJ_C="$2"; local set="$3"
  session_ok || { say "ABORT: AWS session not valid -- refresh it first"; exit 1; }
  if [ "$(env_state)" != "available" ]; then
    say "$ROW: starting the database and the injector; app hosts stay stopped"
    AVNI_START_APPS=no AVNI_AWS_PROFILE=avni-load-test provision/scripts/env-teardown.sh start > $C/$ROW-start.log 2>&1 \
      || { tail -8 $C/$ROW-start.log; say "ABORT: start failed (see $C/$ROW-start.log)"; exit 1; }
    grep -E 'accepts connections|left stopped' $C/$ROW-start.log | sed 's/^/   /'
  fi
  echo "$INJ_C" > $C/injector-class.override
  say "$ROW: database $DB_C, injector $INJ_C, app class kept"
  for attempt in 1 2 3; do "$C/resize-env.sh" keep "$DB_C" "$INJ_C" > $C/resize-$ROW-bed.log 2>&1 && break
    if grep -q "no such host\|Cannot apply incomplete plan" $C/resize-$ROW-bed.log && [ $attempt -lt 3 ]; then sleep 60; else tail -8 $C/resize-$ROW-bed.log; say "ABORT: resize failed"; exit 1; fi
  done; grep -E 'database:|injector:|done in' $C/resize-$ROW-bed.log | sed 's/^/   /'
  local want=1ff23cc5168d1414ae3f885e2b89a2793bcb68b9
  if [ "$(sshinj 'cat /opt/avni-perf/.harness-sha 2>/dev/null')" != "$want" ] || [ "$(sshinj 'command -v psql >/dev/null && echo yes')" != "yes" ]; then
    say "$ROW: injector playbook (harness ${want:0:7}, postgresql-client)"
    ( cd configure && ansible-playbook -i inventory/loadtest loadtest_injector.yml -e injector_harness_sha=$want > $C/injector-deploy-$ROW.log 2>&1 ) \
      && [ "$(sshinj 'command -v psql >/dev/null && echo yes')" = "yes" ] || { say "ABORT: injector playbook failed (see $C/injector-deploy-$ROW.log)"; exit 1; }
  fi
  say "$ROW: reloading $set from the injector"
  export SWAP_PARALLEL=1; load "$set"; unset SWAP_PARALLEL
}

bring_up_apps(){  # <app class> <count>  -- resize/create the copies, start them one at a time, jar, checks
  local cls="$1" n="$2" id t
  say "$ROW: app hosts to $n x $cls"
  for attempt in 1 2 3; do CONFIGURE_VERSION=$JAR_VERSION "$C/resize-env.sh" "$cls" "$DB_C" "$INJ_C" "$n" > $C/resize-$ROW-apps.log 2>&1 && break
    if grep -q "no such host\|Cannot apply incomplete plan" $C/resize-$ROW-apps.log && [ $attempt -lt 3 ]; then sleep 60; else tail -8 $C/resize-$ROW-apps.log; say "ABORT: app resize failed"; exit 1; fi
  done; grep -E 'app hosts|configuring|skipped|done in' $C/resize-$ROW-apps.log | sed 's/^/   /'
  start_apps
  say "$ROW: jar on every copy"; "$C/deploy-jar.sh" "$JAR30" "$SHA30" 2>&1 | sed 's/^/   /' || { say "ABORT: jar deploy failed"; exit 1; }
  for id in $(app_ids); do t=$(aws ec2 describe-instances --instance-ids $id --query 'Reservations[].Instances[].InstanceType' --output text); [ "$t" = "$cls" ] || { say "ABORT: $id is $t, not $cls"; exit 1; }; done
  [ "$(app_ids | wc -w | tr -d ' ')" = "$n" ] || { say "ABORT: expected $n app hosts, have $(app_ids_csv)"; exit 1; }
  same_everywhere
}

start_apps(){
  say "$ROW: starting the app hosts one at a time"
  AVNI_AWS_PROFILE=avni-load-test provision/scripts/env-teardown.sh start-apps > $C/$ROW-start-apps.log 2>&1 \
    || { tail -6 $C/$ROW-start-apps.log; say "ABORT: start-apps failed"; exit 1; }
  sed 's/^/   /' $C/$ROW-start-apps.log | tail -n 6
  targets_healthy
}

between_runs(){  # <dataset>  -- app hosts stopped while the injector reloads; started again after
  wait_writeup   # the write-up reads CloudWatch, not the hosts, but keeps the log in order
  say "$ROW: stopping the app hosts for the reload"
  AVNI_AWS_PROFILE=avni-load-test provision/scripts/env-teardown.sh stop-apps > $C/$ROW-stop-apps.log 2>&1 \
    || { tail -6 $C/$ROW-stop-apps.log; say "ABORT: stop-apps failed"; exit 1; }
  say "$ROW: reloading $1 from the injector"
  export SWAP_PARALLEL=1; load "$1"; unset SWAP_PARALLEL
  start_apps
  same_everywhere
}

warm_up(){  # 900 s through the load balancer, then the copies' spread (relative only: ~1% CPU each)
  local WU
  say "$ROW: warm-up, 900 s, through the load balancer"
  WU=$(AVNI_WARMUP_BURST_SECONDS=900 provision/scripts/env-warmup.sh 2>&1); echo "$WU" | tail -2
  echo "$WU" | grep -q "BUILD SUCCESSFUL in" || { say "   warm-up failed once; retrying"; sleep 60; WU=$(AVNI_WARMUP_BURST_SECONDS=900 provision/scripts/env-warmup.sh 2>&1); echo "$WU" | grep -q "BUILD SUCCESSFUL in" || { say "ABORT: not warmed"; exit 1; }; }
  check_spread "warm-up CPU" 14
}

writeup_bg(){  # <run name> <log> <timeslice minutes> [run id]
  wait_writeup
  local id="${4:-$(cat $C/runids/$1 2>/dev/null)}"
  ( postrun "$1" "$2" "$id"; ts_window "$1" "$2" "$3" "$id"; say "   write-up of $1 finished" ) > $C/writeup-$ROW-$1.log 2>&1 & WRITEUP_PID=$!
}

# ---- shared from rows 34-35 on (moved here 6 Nov 2026) -------------------------------------------
# The 12-hour MFA session can end mid-chain: re-read credentials before every stage and on every watch
# tick, and WAIT for a refresh rather than abort.
ensure_session(){
  session_ok && return 0
  local said=""
  while :; do
    unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
    . provision/scripts/aws-session.sh avni-load-test </dev/null >/dev/null 2>&1; export AWS_REGION=ap-south-1
    session_ok && { [ -n "$said" ] && say "   session refreshed; continuing"; return 0; }
    [ -z "$said" ] && { say "WAITING: the AWS session has lapsed -- refresh MFA and the chain continues"; said=1; }
    sleep 120
  done
}

refresh(){ unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN; . provision/scripts/aws-session.sh avni-load-test </dev/null >/dev/null 2>&1; export AWS_REGION=ap-south-1; ensure_session; }
watch_run(){  # watch_stress with a session check every tick
  local L="$1" prev_t=0 prev_k=0 bad=0 line tot ko dt dk D
  sleep 60
  while :; do
    ensure_session
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
  until sshinj "grep -q 'published. exit' $L"; do ensure_session; sleep 30; done; say "published"
}

inj_cpu(){
  aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization --dimensions Name=InstanceId,Value=$INJ \
    --start-time "$(date -u -v-$1M +%Y-%m-%dT%H:%M:%SZ)" --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --period 60 \
    --statistics Average Maximum --query 'Datapoints[].[Average,Maximum]' --output text \
    | awk '{s+=$1; n++; if($2>m)m=$2} END{if(n) printf "injector CPU over %s min: mean %.0f%%, peak %.0f%%\n", '"$1"', s/n, m}'
}

archive_logs(){  # <tag> -- each app host's server logs CHANGED SINCE ITS LAST ARCHIVE, before a scale-in can destroy it
  # **Only what is new.** A marker beside the logs records the last archive that reached S3; the next one
  # sends the files modified since (the live chs.log and any newly rotated chs.log.*.gz). The marker moves
  # only after the upload succeeds, so a failed upload is resent next time. A host with no marker yet
  # sends today's files once, as before. On 5 Nov every archive resent the whole day -- up to 685 files
  # and ~11 minutes a host, with the copies idle and billing.
  local tag="$1" id F n D=$(date -u +%Y-%m-%d) B=s3://avni-loadtest-936573213727 f
  for id in $(app_ids); do
    F=$(sshto_retry $id "cd /var/log/avni_server && sudo touch .archive-next && if [ -f .archive-marker ]; then sudo find . -maxdepth 1 -name 'chs.log*' -newer .archive-marker -printf '%P '; else ls chs.log.$D.*.gz 2>/dev/null | tr '\n' ' '; echo chs.log; fi")
    [ -n "${F// /}" ] || { say "   server logs $id: nothing new"; continue; }
    f=/tmp/avni-server-$tag-$id.tar.gz
    sshto $id "cd /var/log/avni_server && sudo tar czf - $F 2>/dev/null" > $f
    n=$(tar tzf $f 2>/dev/null | wc -l | tr -d ' ')
    if [ "${n:-0}" -gt 0 ] && aws s3 cp $f $B/logs/avni-server/$D-$tag-$id.tar.gz --only-show-errors; then
      sshto_retry $id "cd /var/log/avni_server && sudo mv .archive-next .archive-marker && echo ok" >/dev/null
      say "   server logs $id: $n new files"
    else say "   WARNING: server log archive for $id failed; it is resent next time"; fi
    rm -f $f
  done
}

launch_and_watch(){  # <name> <minutes for the run log window> <props...> -- launch (one retry), watch, CPU, logs, write-up
  local NAME="$1" MINS="$2"; shift 2
  ensure_session
  say "$ROW: launching $NAME on $(app_ids | wc -w | tr -d ' ') app hosts"
  for attempt in 1 2; do
    provision/scripts/launch-run.sh "$NAME" "$@" 2>&1 | grep -E "^Profile|confirmed|ERROR|refus" | head -3 && sshinj 'ps -eo args | grep -c "[A]vniSyncSimulation"' | grep -q '^[1-9]' && break
    [ $attempt -eq 1 ] && { say "   launch did not start a simulation; retrying once"; sleep 30; } || { say "ABORT: $NAME failed to launch"; exit 1; }
  done
  local L="/opt/avni-perf/$NAME.log"
  ( sleep 900; say "   spread 15 min into $NAME:"; app_cpu_last 5 | sed 's/^/     app CPU, last 5 min: /' ) &
  watch_run "$L"
  ensure_session
  app_cpu_last 58 | sed 's/^/   run CPU, last 58 min: /'; inj_cpu 60 | sed 's/^/   /'
  archive_logs "$NAME"
  writeup_bg "$NAME" "$L" "$MINS"
}

rds_cpu_mean(){  # <minutes back> <minutes long> -- the database's mean CPU over that window, integer
  aws cloudwatch get-metric-statistics --namespace AWS/RDS --metric-name CPUUtilization --dimensions Name=DBInstanceIdentifier,Value=avni-loadtest \
    --start-time "$(date -u -v-$1M +%Y-%m-%dT%H:%M:%SZ)" --end-time "$(date -u -v-$(( $1 - $2 ))M +%Y-%m-%dT%H:%M:%SZ)" --period 60 --statistics Average \
    --query 'Datapoints[].Average' --output text | tr '\t' '\n' | awk '{s+=$1;n++} END{if(n) printf "%.0f", s/n; else print 0}'
}

reload_with_apps_stopped(){  # <dataset>
  refresh
  if [ -n "$(aws ec2 describe-instances --instance-ids $(app_ids) --query 'Reservations[].Instances[?State.Name==`running`].InstanceId' --output text)" ]; then
    say "$ROW: stopping the app hosts for the reload"
    AVNI_AWS_PROFILE=avni-load-test provision/scripts/env-teardown.sh stop-apps > $C/$ROW-stop-apps.log 2>&1 || { tail -4 $C/$ROW-stop-apps.log; say "ABORT: stop-apps failed"; exit 1; }
  fi
  say "$ROW: reloading $1 from the injector"
  export SWAP_PARALLEL=1; load "$1"; unset SWAP_PARALLEL
  refresh
}
