#!/usr/bin/env bash
# Rows 34 (steady pair) and 35, 5 Nov 2026, after row 34's ramp has been read:
#   ./chain-rows34-35.sh <0.9x syncs/h> <1.1x syncs/h>
# Order chosen so row 35 finishes today: row 35 needs only row 34's 0.9x rate, not its 1.1x.
#   1. row 34 steady 0.9x  on 2 x m6g.4xlarge
#   2. row 35              on 4 x m6g.2xlarge  at the same 0.9x rate
#   3. row 35              on 1 x m6g.8xlarge  at the same 0.9x rate
#   4. row 34 steady 1.1x  on 2 x m6g.4xlarge
# Each on a fresh reload from the injector with every app host stopped; each copy's server log archived
# before the next scale-in can destroy it; the environment stopped at the end, then the New Relic export.
# The 12-hour MFA session ends mid-chain: credentials are re-read before every stage and on every watch
# tick, and a lapsed session makes the chain WAIT for a refresh rather than abort.
set -uo pipefail
R09="${1:?0.9x rate}"; R11="${2:?1.1x rate}"
ROW=rows34-35; . $HOME/avni-campaign/lib-chain.sh
DB_C=db.m6g.4xlarge; INJ_C=m6g.2xlarge
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
  until sshinj "grep -q 'published. exit' $L"; do sleep 30; done; say "published"
}
archive_logs(){  # <tag> -- every app host's server log for today, before a scale-in can destroy the host
  local tag="$1" id F n D=$(date -u +%Y-%m-%d) B=s3://avni-loadtest-936573213727
  for id in $(app_ids); do
    F=$(sshto_retry $id "cd /var/log/avni_server && ls chs.log.$D.*.gz 2>/dev/null | tr '\n' ' '")" chs.log"
    sshto $id "cd /var/log/avni_server && sudo tar czf - $F 2>/dev/null" > /tmp/avni-server-$tag-$id.tar.gz
    n=$(tar tzf /tmp/avni-server-$tag-$id.tar.gz 2>/dev/null | wc -l | tr -d ' ')
    [ "${n:-0}" -gt 0 ] && aws s3 cp /tmp/avni-server-$tag-$id.tar.gz $B/logs/avni-server/$D-$tag-$id.tar.gz --only-show-errors && say "   server logs $id: $n files" || say "   WARNING: server log archive for $id failed"
    rm -f /tmp/avni-server-$tag-$id.tar.gz
  done
}
inj_cpu(){
  aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization --dimensions Name=InstanceId,Value=$INJ \
    --start-time "$(date -u -v-$1M +%Y-%m-%dT%H:%M:%SZ)" --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --period 60 \
    --statistics Average Maximum --query 'Datapoints[].[Average,Maximum]' --output text \
    | awk '{s+=$1; n++; if($2>m)m=$2} END{if(n) printf "injector CPU over %s min: mean %.0f%%, peak %.0f%%\n", '"$1"', s/n, m}'
}
steady_run(){  # <syncs/h> <name> <shape tag>
  local R="$1" NAME="$2" SHAPE="$3" PROPS L
  PROPS="-DDATASET_ID=pilot-day-180-10k -DSERVER_BUILD=946553685 -DPROFILE=steady \
-DUSER_COUNT=$R -DSYNC_WINDOW_HOURS=1 -DDURATION_MINUTES=60 \
-DSYNC_MODE=realistic -DSYNC_USERS=case5-users-pilot-10k-nosuppush.csv -DCUSTOMER_PUSH_DRAW=v3 -DPAGE_SIZE=1000 \
-DPUSH=on -DPUSH_MEDIA_PER_ENCOUNTER=8 -DMEDIA_MODEL=pause -DMEDIA_FILE_KB=500 -DMEDIA_UPLOAD_KBPS=125 \
-DCO_TENANTS=on -DCO_TENANT_SYNCS_PER_HOUR=792 -DCO_TENANT_SECONDS=3600 -DCO_TENANT_SEED=42 \
-DCO_TENANT_MEDIA_PER_ENCOUNTER=0.2306 -DUPLOAD_URL_BATCH=50 -DGATLING_HEAP=16G \
-DCACHE_POLICY=warm-after-discarded-warmup-$SHAPE"
  ensure_session
  say "$ROW: launching $NAME at $R syncs an hour for 60 min on $(app_ids | wc -w | tr -d ' ') app hosts"
  for attempt in 1 2; do
    AVNI_EXPECT_RATE="$R syncs/hour for 60 min" provision/scripts/launch-run.sh "$NAME" $PROPS 2>&1 | tail -4 && sshinj 'ps -eo args | grep -c "[A]vniSyncSimulation"' | grep -q '^[1-9]' && break
    [ $attempt -eq 1 ] && { say "   launch did not start a simulation; retrying once"; sleep 30; } || { say "ABORT: $NAME failed to launch"; exit 1; }
  done
  L="/opt/avni-perf/$NAME.log"
  ( sleep 900; say "   spread 15 min into $NAME:"; app_cpu_last 5 | sed 's/^/     app CPU, last 5 min: /' ) &
  watch_run "$L"
  ensure_session
  app_cpu_last 58 | sed 's/^/   run CPU, last 58 min: /'; inj_cpu 60 | sed 's/^/   /'
  archive_logs "$NAME"
  writeup_bg "$NAME" "$L" 120
}
stage(){  # <app class> <count> <syncs/h> <name> <shape tag> <first?>
  refresh
  if [ "$6" != first ]; then
    say "$ROW: stopping the app hosts for the reload"
    AVNI_AWS_PROFILE=avni-load-test provision/scripts/env-teardown.sh stop-apps > $C/$ROW-stop-apps.log 2>&1 || { tail -4 $C/$ROW-stop-apps.log; say "ABORT: stop-apps failed"; exit 1; }
  fi
  say "$ROW: reloading pilot-day-180-10k from the injector"
  export SWAP_PARALLEL=1; load pilot-day-180-10k; unset SWAP_PARALLEL
  refresh
  bring_up_apps "$1" "$2"
  refresh
  warm_up
  steady_run "$3" "$4" "$5"
}
ensure_session
[ "$(env_state)" = "available" ] || { say "ABORT: the database is not up (row 34's ramp chain leaves it up)"; exit 1; }
say "$ROW: 0.9x = $R09, 1.1x = $R11 syncs an hour"
stage m6g.4xlarge 2 "$R09" case15-10k-row34-2x4xl-steady-0.9x-rc18.3-batch50 2x-m6g.4xlarge first
stage m6g.2xlarge 4 "$R09" case15-10k-row35-4x2xl-steady-row34-0.9x-rc18.3-batch50 4x-m6g.2xlarge next
stage m6g.8xlarge 1 "$R09" case15-10k-row35-1x8xl-steady-row34-0.9x-rc18.3-batch50 1x-m6g.8xlarge next
stage m6g.4xlarge 2 "$R11" case15-10k-row34-2x4xl-steady-1.1x-rc18.3-batch50 2x-m6g.4xlarge next
wait_writeup
refresh
say "$ROW: injector logs, then stopping the environment at its classes"
sshinj "cd /opt/avni-perf && tar czf - \$(find . -maxdepth 1 -name '*.log' -newermt '2026-11-05 00:00' -printf '%P ')" > /tmp/injector-rows34-35.tar.gz
[ -s /tmp/injector-rows34-35.tar.gz ] && aws s3 cp /tmp/injector-rows34-35.tar.gz s3://avni-loadtest-936573213727/logs/injector/2026-11-05-rows34-35.tar.gz --only-show-errors && say "   injector logs uploaded"; rm -f /tmp/injector-rows34-35.tar.gz
provision/scripts/env-teardown.sh stop 2>&1 | tail -n 4 | sed 's/^/     /'
LASTH=$(date -u +%H); until [ "$(date -u +%H)" != "$LASTH" ] && [ "$(date -u +%M)" -ge 1 ]; do sleep 300; done
refresh
export NEW_RELIC_API_KEY=$(aws ssm get-parameter --name /avni/loadtest/newrelic-user-key --with-decryption --query Parameter.Value --output text)
( cd $PERF && python3 tools/newrelic-export.py --account 8563864 --region eu --out nr-backup --since 2026-11-05 --s3 2>&1 | grep -v NRAK | grep -vE 'fewer rows|single millisecond' | tail -n 3 | sed 's/^/     /' )
say "ROWS 34-35 done. Environment stopped at $(app_ids | wc -w | tr -d ' ') x m6g.4xlarge / db.m6g.4xlarge / injector m6g.2xlarge"
