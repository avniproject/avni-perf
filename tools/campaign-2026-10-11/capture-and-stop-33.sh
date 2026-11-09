#!/usr/bin/env bash
# Row 33 capture and stop, Nov 2026. Helpers live in ~/avni-campaign.
set -uo pipefail
C=$HOME/avni-campaign; PERF=/Users/joy/projects/samanvay/avni/avni-perf
cd /Users/joy/projects/samanvay/avni/avni-infra
. provision/scripts/aws-session.sh avni-load-test </dev/null >/dev/null 2>&1
export AWS_REGION=ap-south-1
say(){ echo "[$(TZ=Asia/Kolkata date +%H:%M:%S)] $*"; }
PROXY="$PWD/configure/scripts/eice-ssh-proxy.sh"; INJ=i-041afc7c6e0761195; APP=i-044c88e15e8ea9e0f
sshinj(){ ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 -o ServerAliveInterval=30 -o ProxyCommand="$PROXY %h" ubuntu@$INJ "$@" 2>/dev/null; }
sshapp_unused(){ ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 -o ProxyCommand="$PROXY %h" ubuntu@$APP "$@" 2>/dev/null; }
. $C/app-hosts.sh
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

# Row 33: after chain-row33.sh exits cleanly -- gate on the run's artefacts, archive every app host's server log
# and the injector's for the days that exist, keep both app hosts and their classes (row 34
# reuses them), stop, then the New Relic export.
#   ./capture-and-stop-33.sh <first day YYYY-MM-DD>
DAY0="${1:?first day of row 33, YYYY-MM-DD}"
B=s3://avni-loadtest-936573213727; NAME=case15-10k-row33-2x4xl-steady-1.1x-of-row31-rc18.3-batch50; L="/opt/avni-perf/$NAME.log"
say "capture: waiting for the row 33 chain to exit"; while pgrep -f 'chain-row33.sh' >/dev/null; do sleep 30; done
say "capture: chain exited: $(tail -n1 $C/row33.log | cut -c1-120)"
tail -n1 $C/row33.log | grep -q 'ROW 33 done' || { say "ABORT: the row 33 chain did not end cleanly; not stopping"; exit 1; }
session_ok || { say "ABORT: no valid session"; exit 1; }
R=$(sshinj "grep -m1 '^run ' $L | awk '{print \$2}'")
N=$(aws s3 ls "$B/artefacts/$R/" --recursive | wc -l | tr -d ' '); Z=$(aws s3 ls "$B/artefacts/$R/$R.zip" --human-readable | awk '{print $3 $4}')
say "capture: artefacts in S3 ($R): $N objects, zip ${Z:-MISSING}"
[ "$N" -gt 100 ] && [ -n "$Z" ] || { say "ABORT: artefacts are not in S3; not stopping"; exit 1; }
TODAY=$(date -u +%Y-%m-%d)
for id in $(app_ids); do
  D=$DAY0
  while [[ ! "$D" > "$TODAY" ]]; do
    F=$(sshto_retry $id "cd /var/log/avni_server && ls chs.log.$D.*.gz 2>/dev/null | tr '\n' ' '")
    [ "$D" = "$TODAY" ] && F="$F chs.log"
    if [ -n "${F// /}" ]; then
      sshto $id "cd /var/log/avni_server && sudo tar czf - $F" > /tmp/avni-server-$D-$id.tar.gz
      n=$(tar tzf /tmp/avni-server-$D-$id.tar.gz 2>/dev/null | wc -l | tr -d ' ')
      [ "${n:-0}" -gt 0 ] && aws s3 cp /tmp/avni-server-$D-$id.tar.gz $B/logs/avni-server/$D-$id.tar.gz --only-show-errors && say "capture: server logs $D on $id: $n files uploaded" || say "   WARNING: server log archive for $D on $id failed"
      rm -f /tmp/avni-server-$D-$id.tar.gz
    fi
    D=$(date -u -j -v+1d -f %Y-%m-%d "$D" +%Y-%m-%d)
  done
done
sshinj "cd /opt/avni-perf && tar czf - \$(find . -maxdepth 1 -name '*.log' -newermt '$DAY0 00:00' -printf '%P ')" > /tmp/injector-row33.tar.gz
tar tzf /tmp/injector-row33.tar.gz | sed 's/^/     /'
[ -s /tmp/injector-row33.tar.gz ] && aws s3 cp /tmp/injector-row33.tar.gz $B/logs/injector/$DAY0-row33.tar.gz --only-show-errors && say "capture: injector logs uploaded" || say "   WARNING: injector log archive failed"; rm -f /tmp/injector-row33.tar.gz
# No resize before the stop: each chain resizes for its own runs. Row 34 uses these same classes
# (2 x m6g.4xlarge, db.m6g.4xlarge, injector m6g.2xlarge), so the environment stops as it ran.
say "capture: stopping at the run's classes; the next chain resizes if it needs to"
say "capture: stopping the environment"
provision/scripts/env-teardown.sh stop 2>&1 | tail -n 10 | sed 's/^/     /'
say "capture: status:"; provision/scripts/env-teardown.sh status 2>&1 | tail -n 8 | sed 's/^/     /'
LASTH=$(date -u +%H); until [ "$(date -u +%H)" != "$LASTH" ] && [ "$(date -u +%M)" -ge 1 ]; do sleep 300; done
export NEW_RELIC_API_KEY=$(aws ssm get-parameter --name /avni/loadtest/newrelic-user-key --with-decryption --query Parameter.Value --output text)
[ -n "$NEW_RELIC_API_KEY" ] || { say "ABORT: no New Relic key"; exit 1; }
say "capture: New Relic hourly export since $DAY0"
( cd $PERF && python3 tools/newrelic-export.py --account 8563864 --region eu --out nr-backup --since $DAY0 --s3 2>&1 | grep -v NRAK | grep -vE 'fewer rows|single millisecond' | tail -n 4 | sed 's/^/     /' )
say "capture: done"
