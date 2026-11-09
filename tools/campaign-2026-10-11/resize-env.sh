#!/usr/bin/env bash
# Resize app, database and injector together, THROUGH TOFU.
#   ./resize-env.sh <app class> <db class> <injector class> [app count]
# The app count (rows 32+) defaults to the count the environment has now. Added copies come up
# bare: they are configured with CONFIGURE_VERSION's published jar (one at a time, serial: 1),
# and deploy-jar.sh then puts the measured jar on every copy.
# App class `keep` leaves the app hosts' class as it is -- for resizing the database and the
# injector before a reload while the app hosts stay stopped (Nov 2026: the injector is the
# reload's psql client). App hosts that are not running are skipped by every check here;
# `env-teardown.sh start-apps` brings them up afterwards.
# Plans with all three, refuses a plan that would replace any host or the database,
# applies with a retry while the AZ refuses capacity, then waits for the database to
# accept connections and the app to serve. Everything comes back cold.
# Recreated 28 Oct 2026 after /tmp cleanup removed the 23 Oct original.
set -uo pipefail
APP_C="${1:?app class}"; DB_C="${2:?db class}"; INJ_C="${3:?injector class}"
. /Users/joy/avni-campaign/app-hosts.sh
APP_N="${4:-$(app_ids | wc -w | tr -d ' ')}"
OVR=/Users/joy/avni-campaign/injector-class.override
[ -s "$OVR" ] && { INJ_C=$(cat "$OVR"); echo "resize: injector class overridden to $INJ_C by $OVR"; }
cd /Users/joy/projects/samanvay/avni/avni-infra
. provision/scripts/aws-session.sh avni-load-test </dev/null >/dev/null 2>&1
export AWS_REGION=ap-south-1
say(){ echo "[$(TZ=Asia/Kolkata date +%H:%M:%S)] resize: $*"; }
PROXY="$PWD/configure/scripts/eice-ssh-proxy.sh"
APP=$APP_FIRST; INJ=i-041afc7c6e0761195
running(){ [ "$(aws ec2 describe-instances --instance-ids "$1" --query 'Reservations[0].Instances[0].State.Name' --output text)" = "running" ]; }
if [ "$APP_C" = "keep" ]; then
  APP_C=$(aws ec2 describe-instances --instance-ids $APP_FIRST --query 'Reservations[0].Instances[0].InstanceType' --output text)
  [ -n "$APP_C" ] && [ "$APP_C" != "None" ] || { echo "resize: cannot read the app class to keep" >&2; exit 1; }
  echo "resize: app class kept at $APP_C"
fi
sshapp(){ ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 -o ProxyCommand="$PROXY %h" ubuntu@$APP "$@" 2>/dev/null; }
sshinj(){ ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 -o ProxyCommand="$PROXY %h" ubuntu@$INJ "$@" 2>/dev/null; }
BUSY=$(sshinj 'ps -eo args | grep -c "[A]vniSyncSimulation"'); [ "${BUSY:-1}" = "0" ] || { say "ABORT: a simulation is running on the injector"; exit 1; }
VARS=(-var "app_instance_class=$APP_C" -var "db_instance_class=$DB_C" -var "injector_instance_class=$INJ_C" -var "app_instance_count=$APP_N")
t0=$(date +%s); deadline=$(( t0 + 1800 )); attempt=1
while :; do
  say "planning $APP_N x $APP_C / $DB_C / $INJ_C (attempt $attempt)"
  tofu -chdir=provision/tofu/envs/loadtest plan "${VARS[@]}" -out=/tmp/resize-env.tfplan -no-color > /tmp/resize-env.plan.txt 2>&1
  grep -E "will be|must be replaced|Plan:" /tmp/resize-env.plan.txt | sed 's/^/     /'
  if grep -qE 'aws_instance\.host\[.*\] must be replaced|aws_db_instance\.this must be replaced' /tmp/resize-env.plan.txt; then say "ABORT: the plan would REPLACE a host or the database"; exit 1; fi
  # Scaling in may destroy avni-server-2..N; it must never touch the original app host, the
  # injector or the database.
  if grep -qE 'aws_instance\.host\["(avni-server|injector|loader|avni-etl)"\] will be destroyed|aws_db_instance\.this will be destroyed' /tmp/resize-env.plan.txt; then say "ABORT: the plan would DESTROY an original host or the database"; exit 1; fi
  if grep -q "no such host\|Cannot apply incomplete plan\|Error:" /tmp/resize-env.plan.txt && [ $attempt -lt 3 ]; then say "plan hit an error (DNS?); retrying in 60s"; attempt=$((attempt+1)); sleep 60; continue; fi
  say "applying"
  tofu -chdir=provision/tofu/envs/loadtest apply -auto-approve -no-color /tmp/resize-env.tfplan > /tmp/resize-env.apply.txt 2>&1; rc=$?
  tail -3 /tmp/resize-env.apply.txt | sed 's/^/     /'
  [ $rc -eq 0 ] && break
  if grep -q "InsufficientDBInstanceCapacity\|InsufficientInstanceCapacity" /tmp/resize-env.apply.txt && [ "$(date +%s)" -lt "$deadline" ]; then
    say "the AZ refused capacity; retrying in 120s"; attempt=$((attempt+1)); sleep 120; continue
  fi
  say "ABORT: apply failed (see /tmp/resize-env.apply.txt)"; exit 1
done
say "waiting for the database"
until [ "$(aws rds describe-db-instances --db-instance-identifier avni-loadtest --query 'DBInstances[0].DBInstanceStatus' --output text)" = "available" ]; do sleep 20; done
HOST=$(aws rds describe-db-instances --db-instance-identifier avni-loadtest --query 'DBInstances[0].[DBInstanceClass,Endpoint.Address]' --output text); say "database: $HOST"
# Probed from the injector, which is always up for a resize and now reaches 5432 itself.
until sshinj "timeout 5 bash -c 'exec 3<>/dev/tcp/${HOST##*	}/5432' 2>/dev/null"; do sleep 10; done; say "database accepts connections"
# The hosts as tofu has them, written for every helper and chain after this.
IDS=$(tofu -chdir=provision/tofu/envs/loadtest output -json app_instance_ids | python3 -c 'import json,sys; print(",".join(json.load(sys.stdin)))')
[ "$(echo "$IDS" | tr ',' '\n' | grep -c .)" = "$APP_N" ] || { say "ABORT: tofu reports app hosts '$IDS', expected $APP_N"; exit 1; }
echo "$IDS" > "$APP_IDS_FILE"; say "app hosts: $IDS"
# A copy without a jar was just created: configure it, one host at a time.
for id in $(app_ids); do
  running "$id" || { say "app $id is not running; skipped here (start-apps brings it up)"; continue; }
  for i in $(seq 1 40); do sshto "$id" true && break; sleep 15; done
  if [ "$(sshto_retry "$id" 'test -f /opt/avni_server/avni-server.jar && echo yes')" != "yes" ]; then
    [ -n "${CONFIGURE_VERSION:-}" ] || { say "ABORT: $id is new and CONFIGURE_VERSION (a published jar version) is unset"; exit 1; }
    say "configuring new app host $id with $CONFIGURE_VERSION"
    ( cd configure && make loadtest-configure-server VERSION="$CONFIGURE_VERSION" LIMIT="$id" ) > /Users/joy/avni-campaign/configure-$id.log 2>&1 \
      || { say "ABORT: configuring $id failed (see /Users/joy/avni-campaign/configure-$id.log)"; exit 1; }
    tail -4 /Users/joy/avni-campaign/configure-$id.log | sed 's/^/     /'
  fi
done
say "waiting for the app and the injector"
for id in $(app_ids); do
  running "$id" || continue
  for i in $(seq 1 60); do [ "$(ping_of $id)" = "200" ] && break; sleep 15; done
  say "app $id: $(aws ec2 describe-instances --instance-ids $id --query 'Reservations[].Instances[].InstanceType' --output text), $(sshto_retry $id nproc) vCPU, /ping $(ping_of $id)"
done
for i in $(seq 1 40); do sshinj true && break; sleep 15; done
say "injector: $(aws ec2 describe-instances --instance-ids $INJ --query 'Reservations[].Instances[].InstanceType' --output text), harness $(sshinj 'cat /opt/avni-perf/.harness-sha | cut -c1-7')"
say "done in $(( $(date +%s) - t0 ))s -- everything is COLD"
