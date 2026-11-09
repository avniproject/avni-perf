#!/usr/bin/env bash
# Row 34, 5 Nov 2026: the database's limit on one 16-vCPU instance. 2 x m6g.4xlarge (32 app vCPU), db.m6g.4xlarge,
# injector m6g.2xlarge, release candidate, pilot-day-180-10k: a stress ramp 25,000 -> 60,000 syncs an hour over
# 120 min (stop rule: interval failures >1% two ticks running). The first chain on lib-chain.sh: the bed is reloaded
# from the injector with every app host stopped. After the ramp the app hosts are stopped again while it is read;
# the steady pair at 0.9x / 1.1x of its knee is a separate chain.
set -uo pipefail
ROW=row34; . $HOME/avni-campaign/lib-chain.sh
inj_cpu(){  # <minutes>  -- the injector's mean and peak CPU: the harness must not be the limit (plan: <40%)
  aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization --dimensions Name=InstanceId,Value=$INJ \
    --start-time "$(date -u -v-$1M +%Y-%m-%dT%H:%M:%SZ)" --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --period 60 \
    --statistics Average Maximum --query 'Datapoints[].[Average,Maximum]' --output text \
    | awk '{s+=$1; n++; if($2>m)m=$2} END{if(n) printf "injector CPU over %s min: mean %.0f%%, peak %.0f%%\n", '"$1"', s/n, m}'
}
# Resume, 5 Nov 11:5x: the first attempt aborted at the jar step (the local jar had left ~/Downloads); the 11:45
# reload is untouched, so pick up at the app bring-up, which is idempotent.
DB_C=db.m6g.4xlarge; INJ_C=m6g.2xlarge
say "ROW 34 RESUME: from the app bring-up, on the 11:45 reload"
bring_up_apps m6g.4xlarge 2
warm_up
NAME=case15-10k-row34-2x4xl-ramp-rc18.3-batch50
PROPS="-DDATASET_ID=pilot-day-180-10k -DSERVER_BUILD=946553685 -DPROFILE=stress \
-DSYNCS_PER_HOUR=25000 -DSTRESS_TO_SYNCS_PER_HOUR=60000 -DDURATION_MINUTES=120 \
-DSYNC_MODE=realistic -DSYNC_USERS=case5-users-pilot-10k-nosuppush.csv -DCUSTOMER_PUSH_DRAW=v3 -DPAGE_SIZE=1000 \
-DPUSH=on -DPUSH_MEDIA_PER_ENCOUNTER=8 -DMEDIA_MODEL=pause -DMEDIA_FILE_KB=500 -DMEDIA_UPLOAD_KBPS=125 \
-DCO_TENANTS=on -DCO_TENANT_SYNCS_PER_HOUR=792 -DCO_TENANT_SECONDS=7200 -DCO_TENANT_SEED=42 \
-DCO_TENANT_MEDIA_PER_ENCOUNTER=0.2306 -DUPLOAD_URL_BATCH=50 -DGATLING_HEAP=16G \
-DCACHE_POLICY=warm-after-discarded-warmup-2x-m6g.4xlarge"
say "ROW 34: launching $NAME: 25,000 -> 60,000 syncs an hour over 120 min on $(app_ids | wc -w | tr -d ' ') app hosts"
for attempt in 1 2; do
  provision/scripts/launch-run.sh "$NAME" $PROPS 2>&1 | tail -6 && sshinj 'ps -eo args | grep -c "[A]vniSyncSimulation"' | grep -q '^[1-9]' && break
  [ $attempt -eq 1 ] && { say "   launch did not start a simulation; retrying once"; sleep 30; } || { say "ABORT: ramp failed to launch"; exit 1; }
done
L="/opt/avni-perf/$NAME.log"
( for m in 30 60 90 115; do sleep $(( m == 30 ? 1800 : (m == 115 ? 1500 : 1800) )); say "   at ~$m min:"; app_cpu_last 5 | sed 's/^/     app CPU, last 5 min: /'; inj_cpu 5 | sed 's/^/     /'; done ) &
watch_stress "$L"
inj_cpu 130 | sed 's/^/   /'
writeup_bg "$NAME" "$L" 140; wait_writeup
say "ROW 34: stopping the app hosts while the ramp is read"
AVNI_AWS_PROFILE=avni-load-test provision/scripts/env-teardown.sh stop-apps 2>&1 | tail -1 | sed 's/^/   /'
say "ROW 34 ramp done. Database and injector UP (db.m6g.4xlarge / m6g.2xlarge), app hosts stopped; steady pair next"
