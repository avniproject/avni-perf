#!/usr/bin/env bash
# 12 Nov 2026: start the stopped database, resize it THROUGH TOFU to db.m6g.large, stop it again -- so AWS's
# 7-day auto-start (due ~13 Nov 15:16 IST, at db.m6g.8xlarge) is reset, and the next one comes up small.
# Every other variable is passed at the class the environment has now, so the plan touches only the database
# (and the parity report); it refuses anything else.
set -uo pipefail
cd /Users/joy/projects/samanvay/avni/avni-infra
. provision/scripts/aws-session.sh avni-load-test </dev/null >/dev/null 2>&1; export AWS_REGION=ap-south-1
say(){ echo "[$(TZ=Asia/Kolkata date +%H:%M:%S)] $*"; }
st(){ aws rds describe-db-instances --db-instance-identifier avni-loadtest --query 'DBInstances[0].DBInstanceStatus' --output text; }
[ "$(aws sts get-caller-identity --query Account --output text)" = 936573213727 ] || { say "ABORT: no load-test session"; exit 1; }
say "database is $(st); starting"
[ "$(st)" = stopped ] && aws rds start-db-instance --db-instance-identifier avni-loadtest --query 'DBInstance.DBInstanceStatus' --output text
until [ "$(st)" = available ]; do sleep 30; done; say "database available"
V=(-var app_instance_class=m6g.4xlarge -var app_instance_count=3 -var injector_instance_class=m6g.2xlarge -var db_instance_class=db.m6g.large)
tofu -chdir=provision/tofu/envs/loadtest plan "${V[@]}" -no-color -out=/tmp/db-small.tfplan > /tmp/db-small.plan.txt 2>&1 || { tail -20 /tmp/db-small.plan.txt; say "ABORT: plan failed"; exit 1; }
grep -E "will be|must be|Plan:" /tmp/db-small.plan.txt | sed 's/^/   /'
OTHER=$(grep -E "^  # .* (will be|must be)" /tmp/db-small.plan.txt | grep -vE 'aws_db_instance\.this will be updated in-place|local_file\.parity')
[ -z "$OTHER" ] || { say "ABORT: the plan changes more than the database:"; echo "$OTHER"; exit 1; }
grep -q 'aws_db_instance.this will be updated in-place' /tmp/db-small.plan.txt || { say "ABORT: the plan does not resize the database"; exit 1; }
say "applying: database to db.m6g.large"
tofu -chdir=provision/tofu/envs/loadtest apply -no-color -auto-approve /tmp/db-small.tfplan > /tmp/db-small.apply.txt 2>&1 || { tail -8 /tmp/db-small.apply.txt; say "ABORT: apply failed"; exit 1; }
until [ "$(st)" = available ]; do sleep 30; done
say "database now $(aws rds describe-db-instances --db-instance-identifier avni-loadtest --query 'DBInstances[0].DBInstanceClass' --output text); stopping"
aws rds stop-db-instance --db-instance-identifier avni-loadtest --query 'DBInstance.DBInstanceStatus' --output text
until [ "$(st)" = stopped ]; do sleep 60; done
say "database stopped; next automatic start ~7 days from now, at db.m6g.large"
aws rds describe-events --source-type db-instance --source-identifier avni-loadtest --duration 120 --query 'Events[].[Date,Message]' --output text | tail -4 | sed 's/^/   /'
