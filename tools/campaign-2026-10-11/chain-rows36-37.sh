#!/usr/bin/env bash
# Rows 36 and 37, prepared 6 Nov 2026: 50,000 syncs an hour.
#   1. row 36 steady  50,000/h for 60 min   3 x m6g.4xlarge (48 app vCPU), db.m6g.8xlarge (32 vCPU), pilot-day-180-10k
#   2. row 36 ramp    50,000 -> 70,000/h over 60 min, same shape, fresh reload (stop rule: >1% two ticks)
#   (row 37 held off on 6 Nov; to run another day if row 36's database sits above 50%)
# 3 x m6g.4xlarge because row 35 found size and count equal on CPU per sync, a single large copy pins its own
# 100-connection pool, and 4xlarge keeps rows 33-34's shape. Injector m6g.2xlarge (peaked 25% at 53,000/h),
# GATLING_HEAP=16G. Every reload from the injector with the app hosts stopped; the environment stops at the end.
set -uo pipefail
ROW=rows36-37; . $HOME/avni-campaign/lib-chain.sh
base_props(){  # <dataset> <feeder> <shape tag>
  echo "-DDATASET_ID=$1 -DSERVER_BUILD=946553685 -DSYNC_MODE=realistic -DSYNC_USERS=$2 -DCUSTOMER_PUSH_DRAW=v3 -DPAGE_SIZE=1000 \
-DPUSH=on -DPUSH_MEDIA_PER_ENCOUNTER=8 -DMEDIA_MODEL=pause -DMEDIA_FILE_KB=500 -DMEDIA_UPLOAD_KBPS=125 \
-DCO_TENANTS=on -DCO_TENANT_SYNCS_PER_HOUR=792 -DCO_TENANT_SECONDS=3600 -DCO_TENANT_SEED=42 \
-DCO_TENANT_MEDIA_PER_ENCOUNTER=0.2306 -DUPLOAD_URL_BATCH=50 -DGATLING_HEAP=16G -DCACHE_POLICY=warm-after-discarded-warmup-$3"
}
F10=case5-users-pilot-10k-nosuppush.csv; F25=case5-users-pilot-25k-nosuppush.csv; SHAPE=3x-m6g.4xlarge

ensure_session
# 1. row 36 steady
# prepare_bed, with the third app host created and configured IN PARALLEL with the reload: started 3 minutes in,
# once the teardown is running detached and polled with retries, so its ssh traffic does not meet the reload's
# single-shot steps (EICE refuses bursts). It starts the new copy against a database mid-teardown -- validation
# only, nothing it does reads pilot data -- and stops it again once configured, so it does not idle through the load.
DB_C=db.m6g.8xlarge; INJ_C=m6g.2xlarge
if [ "$(env_state)" != "available" ]; then
  say "$ROW: starting the database and the injector; app hosts stay stopped"
  AVNI_START_APPS=no AVNI_AWS_PROFILE=avni-load-test provision/scripts/env-teardown.sh start > $C/$ROW-start.log 2>&1 \
    || { tail -8 $C/$ROW-start.log; say "ABORT: start failed (see $C/$ROW-start.log)"; exit 1; }
  grep -E 'accepts connections|left stopped' $C/$ROW-start.log | sed 's/^/   /'
fi
echo "$INJ_C" > $C/injector-class.override
say "$ROW: database to $DB_C, injector $INJ_C, app class kept"
for attempt in 1 2 3; do "$C/resize-env.sh" keep "$DB_C" "$INJ_C" > $C/resize-$ROW-bed.log 2>&1 && break
  if grep -q "no such host\|Cannot apply incomplete plan\|InsufficientDBInstanceCapacity" $C/resize-$ROW-bed.log && [ $attempt -lt 3 ]; then sleep 60; else tail -8 $C/resize-$ROW-bed.log; say "ABORT: resize failed"; exit 1; fi
done; grep -E 'database:|injector:|done in' $C/resize-$ROW-bed.log | sed 's/^/   /'
[ "$(sshinj 'command -v psql >/dev/null && echo yes')" = "yes" ] || { say "ABORT: no psql on the injector"; exit 1; }
( sleep 180; refresh >/dev/null
  CONFIGURE_VERSION=$JAR_VERSION "$C/resize-env.sh" m6g.4xlarge "$DB_C" "$INJ_C" 3 > $C/resize-$ROW-apps.log 2>&1 || exit 1
  AVNI_AWS_PROFILE=avni-load-test provision/scripts/env-teardown.sh stop-apps >> $C/resize-$ROW-apps.log 2>&1 ) & H3=$!
say "$ROW: reloading pilot-day-180-10k from the injector; third app host being created alongside"
export SWAP_PARALLEL=1; load pilot-day-180-10k; unset SWAP_PARALLEL
wait $H3 || { tail -8 $C/resize-$ROW-apps.log; say "ABORT: creating the third app host failed (see $C/resize-$ROW-apps.log)"; exit 1; }
grep -E 'app hosts|configuring|done in|stopped' $C/resize-$ROW-apps.log | sed 's/^/   /'
refresh
bring_up_apps m6g.4xlarge 3
warm_up
launch_and_watch case15-10k-row36-3x4xl-db8xl-steady-50k-rc18.3-batch50 120 \
  $(base_props pilot-day-180-10k $F10 $SHAPE) -DPROFILE=steady -DUSER_COUNT=50000 -DSYNC_WINDOW_HOURS=1 -DDURATION_MINUTES=60
# the database's mean over the steady part of that hour: 12 to 56 minutes after the run's own start time
rds_cpu_run(){  # <run name>
  local id st; id=$(sshinj "grep -m1 '^run ' /opt/avni-perf/$1.log | awk '{print \$2}'")
  st=$(date -u -j -f '%Y-%m-%dT%H-%M-%SZ' "${id:0:20}" +%s 2>/dev/null) || { echo 0; return; }
  aws cloudwatch get-metric-statistics --namespace AWS/RDS --metric-name CPUUtilization --dimensions Name=DBInstanceIdentifier,Value=avni-loadtest \
    --start-time "$(date -u -r $(( st + 720 )) +%Y-%m-%dT%H:%M:%SZ)" --end-time "$(date -u -r $(( st + 3360 )) +%Y-%m-%dT%H:%M:%SZ)" --period 60 --statistics Average \
    --query 'Datapoints[].Average' --output text | tr '\t' '\n' | awk '{s+=$1;n++} END{if(n) printf "%.0f", s/n; else print 0}'
}
DBM=$(rds_cpu_run case15-10k-row36-3x4xl-db8xl-steady-50k-rc18.3-batch50); say "$ROW: row 36 steady hour, database CPU mean ${DBM}% over minutes 12-56 (row 37 runs only above 50%)"

# 2. row 36 ramp
reload_with_apps_stopped pilot-day-180-10k
start_apps; same_everywhere; warm_up
launch_and_watch case15-10k-row36-3x4xl-db8xl-ramp-50k-70k-rc18.3-batch50 80 \
  $(base_props pilot-day-180-10k $F10 $SHAPE) -DPROFILE=stress -DSYNCS_PER_HOUR=50000 -DSTRESS_TO_SYNCS_PER_HOUR=70000 -DDURATION_MINUTES=60

# 3. row 37: held off on 6 Nov 2026 -- to run another day if required. The decision figure
# (row 36's database mean over its steady hour) is still logged above, for that call.
say "$ROW: row 37 not run today (held off); row 36 steady database mean was ${DBM}% against the plan's 50% threshold"
wait_writeup

refresh
say "$ROW: injector logs, then stopping the environment at its classes"
D0=$(date -u +%Y-%m-%d)
sshinj "cd /opt/avni-perf && tar czf - \$(find . -maxdepth 1 -name '*.log' -newermt '$D0 00:00' -printf '%P ')" > /tmp/injector-$ROW.tar.gz
[ -s /tmp/injector-$ROW.tar.gz ] && aws s3 cp /tmp/injector-$ROW.tar.gz s3://avni-loadtest-936573213727/logs/injector/$D0-$ROW.tar.gz --only-show-errors && say "   injector logs uploaded"; rm -f /tmp/injector-$ROW.tar.gz
provision/scripts/env-teardown.sh stop 2>&1 | tail -n 4 | sed 's/^/     /'
LASTH=$(date -u +%H); until [ "$(date -u +%H)" != "$LASTH" ] && [ "$(date -u +%M)" -ge 1 ]; do sleep 300; done
refresh
export NEW_RELIC_API_KEY=$(aws ssm get-parameter --name /avni/loadtest/newrelic-user-key --with-decryption --query Parameter.Value --output text)
( cd $PERF && python3 tools/newrelic-export.py --account 8563864 --region eu --out nr-backup --since $D0 --s3 2>&1 | grep -v NRAK | grep -vE 'fewer rows|single millisecond' | tail -n 3 | sed 's/^/     /' )
say "ROWS 36 done (37 held). Environment stopped at 3 x m6g.4xlarge / db.m6g.8xlarge / injector m6g.2xlarge"
