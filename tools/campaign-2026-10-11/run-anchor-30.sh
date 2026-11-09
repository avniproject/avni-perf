#!/usr/bin/env bash
# Row 27: one run of anchor A or B on the 18.1.0 baseline.   ./run-anchor.sh A|B <n>
#   A: case 12 -- 1,682 users over 1 h, PUSH=off, co-tenants off, m6g.large / db.m6g.large (row 22's control shape)
#   B: case 15 at ten a day -- 1,500 users over 1 h, v3 draw, nosuppush feeder, 8 files, co-tenants 792/h, m6g.xlarge (row 24's shape)
# Verifies the instance type and the deployed jar's sha256 against what the anchor demands, runs the
# 900 s warm-up burst (always: every anchor run starts from the same warmth), then launches.
set -uo pipefail
ANCHOR="${1:?A or B}"; N="${2:?run number}"
# BUILD=17.3 is row 28, the drift check: the same anchor on the old jar (2c0215679), named -drift.
# A fix jar is named by environment: JAR_SHA (sha256 of the deployed jar), SB (SERVER_BUILD, its commit), TAGV (the run-name tag).
if [ -n "${JAR_SHA:-}" ]; then SHA_18="$JAR_SHA"; SB="${SB:?SB (SERVER_BUILD) is required with JAR_SHA}"; TAGV="${TAGV:?TAGV is required with JAR_SHA}"; else
case "${BUILD:-18.1}" in
  18.1) SHA_18=87bf747b08a9d2a90f5fa3e9a91cd137a295643976fb6491ae433d550e5ba678; SB=789092feb; TAGV=v18.1;;
  17.3) SHA_18=73d458d2a4a814e17225a9564cdc38ed9a7602c44b3e7c9c131962bf86ed471d; SB=2c0215679; TAGV=v17.3-drift;;
  *) echo "BUILD must be 18.1 or 17.3" >&2; exit 2;;
esac
fi
cd /Users/joy/projects/samanvay/avni/avni-infra
. provision/scripts/aws-session.sh avni-load-test >/dev/null 2>&1; export AWS_REGION=ap-south-1
[ "$(aws sts get-caller-identity --query Account --output text 2>/dev/null)" = "936573213727" ] || { echo "wrong account" >&2; exit 1; }
say(){ echo "[$(TZ=Asia/Kolkata date +%H:%M:%S)] $*"; }
PROXY="$PWD/configure/scripts/eice-ssh-proxy.sh"; APP=i-044c88e15e8ea9e0f
sshapp(){ ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 -o ProxyCommand="$PROXY %h" ubuntu@$APP "$@" 2>/dev/null; }
case "$ANCHOR" in
  A) WANT=m6g.large;  NAME="case12-anchorA-$TAGV-r$N";          RATE="1682 syncs/hour for 60 min"
     PROPS="-DDATASET_ID=pilot-day-180 -DSERVER_BUILD=$SB -DPROFILE=steady \
-DUSER_COUNT=1682 -DSYNC_WINDOW_HOURS=1 -DDURATION_MINUTES=60 \
-DSYNC_MODE=realistic -DSYNC_USERS=case5-users-pilot.csv -DPAGE_SIZE=1000 \
-DPUSH=off -DCO_TENANTS=off";;
  B) WANT=m6g.xlarge; NAME="case15-tenaday-anchorB-$TAGV-r$N"; RATE="1500 syncs/hour for 60 min"
     PROPS="-DDATASET_ID=pilot-day-180 -DSERVER_BUILD=$SB -DPROFILE=steady \
-DUSER_COUNT=1500 -DSYNC_WINDOW_HOURS=1 -DDURATION_MINUTES=60 \
-DSYNC_MODE=realistic -DSYNC_USERS=case5-users-pilot-nosuppush.csv -DCUSTOMER_PUSH_DRAW=v3 -DPAGE_SIZE=1000 \
-DPUSH=on -DPUSH_MEDIA_PER_ENCOUNTER=8 \
-DMEDIA_MODEL=pause -DMEDIA_FILE_KB=500 -DMEDIA_UPLOAD_KBPS=125 \
-DCO_TENANTS=on -DCO_TENANT_SYNCS_PER_HOUR=792 -DCO_TENANT_SECONDS=3600 -DCO_TENANT_SEED=42 \
-DCO_TENANT_MEDIA_PER_ENCOUNTER=0.2306";;
  C) WANT=m6g.large;  NAME="case13-anchorC-$TAGV-r$N";          RATE="1682 syncs/hour for 60 min"
     # case 13 = case 12 plus the co-tenants at 792/h (row 21's shape: customers PUSH=off, co-tenants push with media 0.2306)
     PROPS="-DDATASET_ID=pilot-day-180 -DSERVER_BUILD=$SB -DPROFILE=steady \
-DUSER_COUNT=1682 -DSYNC_WINDOW_HOURS=1 -DDURATION_MINUTES=60 \
-DSYNC_MODE=realistic -DSYNC_USERS=case5-users-pilot.csv -DPAGE_SIZE=1000 \
-DPUSH=off -DCO_TENANTS=on -DCO_TENANT_SYNCS_PER_HOUR=792 -DCO_TENANT_SECONDS=3600 -DCO_TENANT_SEED=42 \
-DCO_TENANT_MEDIA_PER_ENCOUNTER=0.2306";;
  D) WANT=m6g.2xlarge; WANTDB=db.m6g.2xlarge; NAME="case15-5k-anchorD-$TAGV-r$N"; RATE="5000 syncs/hour for 60 min"
     # case 15 scaled: row 25's shape -- 5,000 users on pilot-day-180-5k, 8 + 8 vCPU
     PROPS="-DDATASET_ID=pilot-day-180-5k -DSERVER_BUILD=$SB -DPROFILE=steady \
-DUSER_COUNT=5000 -DSYNC_WINDOW_HOURS=1 -DDURATION_MINUTES=60 \
-DSYNC_MODE=realistic -DSYNC_USERS=case5-users-pilot-5k-nosuppush.csv -DCUSTOMER_PUSH_DRAW=v3 -DPAGE_SIZE=1000 \
-DPUSH=on -DPUSH_MEDIA_PER_ENCOUNTER=8 \
-DMEDIA_MODEL=pause -DMEDIA_FILE_KB=500 -DMEDIA_UPLOAD_KBPS=125 \
-DCO_TENANTS=on -DCO_TENANT_SYNCS_PER_HOUR=792 -DCO_TENANT_SECONDS=3600 -DCO_TENANT_SEED=42 \
-DCO_TENANT_MEDIA_PER_ENCOUNTER=0.2306";;
  *) echo "anchor must be A, B, C or D" >&2; exit 2;;
esac
WANTDB="${WANTDB:-db.m6g.large}"
TYPE=$(aws ec2 describe-instances --instance-ids "$APP" --query 'Reservations[].Instances[].InstanceType' --output text)
[ "$TYPE" = "$WANT" ] || { say "ABORT: anchor $ANCHOR runs on $WANT; the app is $TYPE"; exit 1; }
DBT=$(aws rds describe-db-instances --db-instance-identifier avni-loadtest --query 'DBInstances[0].DBInstanceClass' --output text)
[ "$DBT" = "$WANTDB" ] || { say "ABORT: anchor $ANCHOR runs on $WANTDB; the database is $DBT"; exit 1; }
# One ssh through the EICE proxy can fail on its own (29 Oct: an empty sha read aborted a launch); read up to three times.
DEPLOYED=""; for i in 1 2 3; do DEPLOYED=$(sshapp 'sudo sha256sum /opt/avni_server/avni-server.jar' | cut -d" " -f1); [ -n "$DEPLOYED" ] && break; sleep 10; done
[ "$DEPLOYED" = "$SHA_18" ] || { say "ABORT: the $TAGV jar ($SB) is not deployed (sha ${DEPLOYED:-unreadable})"; exit 1; }
say "verified: $TYPE / $DBT, jar $TAGV = $SB"
say "1. warm-up, 900 s, result discarded"
WU=$(AVNI_WARMUP_BURST_SECONDS=900 provision/scripts/env-warmup.sh 2>&1); echo "$WU" | tail -2
case "$WU" in *"Not warmed"*|*"Skipped"*) say "ABORT: not warmed"; exit 1;; esac
echo "$WU" | grep -q "BUILD SUCCESSFUL" || { say "ABORT: warm-up did not report BUILD SUCCESSFUL"; exit 1; }
say "2. launching anchor $ANCHOR run $N as $NAME on $TYPE"
# EXTRA_PROPS: further -D properties for a run that models a client change (e.g. -DUPLOAD_URL_BATCH=50 for #1100).
AVNI_EXPECT_RATE="$RATE" provision/scripts/launch-run.sh "$NAME" $PROPS ${EXTRA_PROPS:-} -DCACHE_POLICY=warm-after-discarded-warmup-$TYPE 2>&1 | tail -8
