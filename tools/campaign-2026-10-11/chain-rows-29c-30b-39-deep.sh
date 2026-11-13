#!/usr/bin/env bash
# Rows 29c, 30b and 39, 13 Nov 2026 -- re-testing #1103 after its review, with the 18.1 control re-run first.
#   0. start without app hosts, database and injector to .large, reload pilot-day-180 from the injector;
#      one app host (m6g.large) -- app_instance_count 3 -> 1 deletes avni-server-2 and -3 (their logs are in S3)
#   1. control  anchor A  18.1 (789092feb)              case12-anchorA-v18.1-r3        against row 27's 3.90 +/- 0.07
#   2. 29c      anchor A  reviewed #1103 (b7ee734d2)    case12-anchorA-fix1103b-r1     A writes nothing: same bed
#   3. row 39   deep pages, one district-level user, full syncs, on 18.1, the reviewed jar, then the @Formula jar --
#               ONLY if row39-user.sql is approved (see below); same bed, A's classes
#   4. 29c      anchor B  reviewed #1103, app m6g.xlarge, UPLOAD_URL_BATCH=0 (row 29's #1103 shape)  same bed
#   5. 30b      anchor B  18.3 at 27e22ee0a, UPLOAD_URL_BATCH=50, fresh pilot-day-180 reload
#   6. 30b      anchor D  18.3 at 27e22ee0a, m6g.2xlarge / db.m6g.2xlarge, pilot-day-180-5k, UPLOAD_URL_BATCH=50
#   7. archive, database and app back to .large, stop. (New Relic export is run separately.)
# Each reload runs from the injector with the app host stopped. Harness 1ff23cc throughout, as rows 31-36
# (behaviourally the same as rows 27-30's 7205831). Anchor runs go through run-anchor-30.sh, which verifies the
# instance class, database class and deployed jar sha before it warms up and launches.
set -uo pipefail
ROW=rows-29c-30b-39; . $HOME/avni-campaign/lib-chain.sh
J=$C/jars
SHA181=87bf747b08a9d2a90f5fa3e9a91cd137a295643976fb6491ae433d550e5ba678; JAR181=$J/avni-server-18.1.0-789092feb.jar
SHA29C=dd4bb214d3bd008e47376b631b9caa1933efc63412629683b998854a441167d3; JAR29C=$J/avni-server-29c-b7ee734d2.jar
SHA30B=a10958324cb6e19b7e67a07fac043150485b50bb28b3af4bc0013f12afb5d650; JAR30B=$J/avni-server-30b-27e22ee0a.jar
SHAFRM=05372d0f56603210b184d03880cde29656b8185eb21339e95d2005bdafae9eab; JARFRM=$J/avni-server-1103-b4c611977.jar
for p in "$JAR181 $SHA181" "$JAR29C $SHA29C" "$JAR30B $SHA30B" "$JARFRM $SHAFRM"; do set -- $p
  [ "$(shasum -a 256 "$1" | cut -d' ' -f1)" = "$2" ] || { say "ABORT: $1 is not sha ${2:0:12}"; exit 1; }; done

deploy(){  # <jar> <sha>
  ensure_session
  "$C/deploy-jar.sh" "$1" "$2" 2>&1 | sed 's/^/   /' || { say "ABORT: jar deploy failed"; exit 1; }
}
anchor(){  # <A|B|D> <run number> [env assignments...] -- run-anchor-30.sh, then watch, archive, write-up
  local A="$1" N="$2" NAME OUT; shift 2
  ensure_session
  OUT=$(env "$@" "$C/run-anchor-30.sh" "$A" "$N" 2>&1); echo "$OUT" | grep -E "verified|ABORT|launching|launch-run:" | sed 's/^/   /'
  echo "$OUT" | grep -q "ABORT" && { say "ABORT: anchor $A did not launch"; exit 1; }
  NAME=$(echo "$OUT" | sed -n 's/.*launching anchor [A-D] run [0-9a-z]* as \([^ ]*\) on .*/\1/p' | head -1)
  [ -n "$NAME" ] && sshinj 'ps -eo args | grep -c "[A]vniSyncSimulation"' | grep -q '^[1-9]' || { say "ABORT: anchor $A run $N is not running"; exit 1; }
  say "$ROW: watching $NAME"
  watch_run "/opt/avni-perf/$NAME.log"
  ensure_session
  app_cpu_last 58 | sed 's/^/   run CPU, last 58 min: /'
  archive_logs "$NAME"
  writeup_bg "$NAME" "/opt/avni-perf/$NAME.log" 80
}
resize(){  # <app class> <db class> -- injector stays m6g.large, one app host
  ensure_session; echo m6g.large > $C/injector-class.override
  for attempt in 1 2 3; do CONFIGURE_VERSION=18.1.0-789092feb "$C/resize-env.sh" "$1" "$2" m6g.large 1 > $C/resize-$ROW-$1.log 2>&1 && break
    if grep -q "no such host\|Cannot apply incomplete plan\|InsufficientDBInstanceCapacity\|InsufficientInstanceCapacity" $C/resize-$ROW-$1.log && [ $attempt -lt 3 ]; then sleep 120; else tail -8 $C/resize-$ROW-$1.log; say "ABORT: resize to $1 / $2 failed"; exit 1; fi
  done; grep -E 'planning|app hosts|database:|done in|skipped' $C/resize-$ROW-$1.log | sed 's/^/   /'
}

# ---- row 39 -------------------------------------------------------------------------------------------
# **Writing to the database is gated.** row39-user.sql inserts one catchment, its mapping to District 1,
# one user and its group membership. It runs only if $C/row39-sql.approved holds the sha256 of the file as
# it is now -- written by a person after reading it, so an edit after approval withdraws it. Otherwise row
# 39 is skipped and the chain carries on.
row39_sql_approved(){ [ -s "$C/row39-sql.approved" ] && [ "$(tr -d ' \n' < $C/row39-sql.approved)" = "$(shasum -a 256 $C/row39-user.sql | cut -d' ' -f1)" ]; }
apply_row39_sql(){
  local DB SECRET TAG=row39-$(date +%H%M%S)
  DB=$(tofu -chdir=provision/tofu/envs/loadtest output -raw db_endpoint 2>/dev/null); DB=${DB%:*}
  SECRET=$(tofu -chdir=provision/tofu/envs/loadtest output -raw db_master_secret_arn 2>/dev/null)
  aws secretsmanager get-secret-value --secret-id "$SECRET" --query SecretString --output text </dev/null \
  | python3 -c 'import json,sys;pw=json.load(sys.stdin)["password"];print(pw.replace("\\","\\\\").replace(":","\\:"))' \
  | sshinj "umask 077; IFS= read -r P; printf '%s:5432:openchs:openchs:%s' '$DB' \"\$P\" > /tmp/.pgpass_$TAG; chmod 600 /tmp/.pgpass_$TAG"
  sshinj "PGPASSFILE=/tmp/.pgpass_$TAG psql -h $DB -U openchs -d openchs -w -v ON_ERROR_STOP=1 -f -" < $C/row39-user.sql > $C/row39-user.out 2>&1; local rc=$?
  sshinj "rm -f /tmp/.pgpass_$TAG"
  sed 's/^/   /' $C/row39-user.out
  [ $rc -eq 0 ] && grep -q "row39-district1@org10" $C/row39-user.out
}
row39_sync(){  # <jar tag> <SERVER_BUILD> <sync number> -- one full sync of the district user, 60-minute guard
  local NAME="row39-deep-district1-merged-$1-s$3" L t0
  ensure_session
  provision/scripts/launch-run.sh "$NAME" -DDATASET_ID=pilot-day-180 -DSERVER_BUILD=$2 -DPROFILE=smoke -DUSER_COUNT=1 \
    -DSYNC_MODE=full -DSYNC_USERS=row39-users-district1.csv -DPAGE_SIZE=1000 -DPUSH=off -DCO_TENANTS=off \
    -DCACHE_POLICY=warm-after-300s-warmup-m6g.large 2>&1 | grep -E "^Profile|confirmed|ERROR|refus" | head -3
  L="/opt/avni-perf/$NAME.log"; t0=$(date +%s)
  until sshinj "grep -q 'BUILD SUCCESSFUL\|BUILD FAILED' $L"; do
    if [ $(( $(date +%s) - t0 )) -gt 7200 ]; then say "   $NAME passed 120 minutes; stopping it"; sshinj "pkill -f AvniSyncSimulation"; sleep 60; break; fi
    sleep 60; done
  until sshinj "grep -q 'published. exit' $L"; do sleep 30; done
  say "   $NAME: $(( ($(date +%s) - t0) / 60 )) min, $(sshinj "grep -A 14 'Global Information' $L | grep -E 'request count' | sed -E 's/ +/ /g'")"
  writeup_bg "$NAME" "$L" 80
  LAST_SYNC_MIN=$(( ($(date +%s) - t0) / 60 ))
}
row39_merge_approved(){ [ -s "$C/row39-merge.approved" ] && [ "$(tr -d ' \n' < $C/row39-merge.approved)" = "$(shasum -a 256 $C/row39-merge-types.sql | cut -d' ' -f1)" ]; }
apply_sql_file(){  # <sql file> <output file> -- psql on the injector, as apply_row39_sql
  local DB SECRET TAG=sql-$(date +%H%M%S) rc
  DB=$(tofu -chdir=provision/tofu/envs/loadtest output -raw db_endpoint 2>/dev/null); DB=${DB%:*}
  SECRET=$(tofu -chdir=provision/tofu/envs/loadtest output -raw db_master_secret_arn 2>/dev/null)
  aws secretsmanager get-secret-value --secret-id "$SECRET" --query SecretString --output text </dev/null \
  | python3 -c 'import json,sys;pw=json.load(sys.stdin)["password"];print(pw.replace("\\","\\\\").replace(":","\\:"))' \
  | sshinj "umask 077; IFS= read -r P; printf '%s:5432:openchs:openchs:%s' '$DB' \"\$P\" > /tmp/.pgpass_$TAG; chmod 600 /tmp/.pgpass_$TAG"
  sshinj "PGPASSFILE=/tmp/.pgpass_$TAG psql -h $DB -U openchs -d openchs -w -v ON_ERROR_STOP=1 -f -" < "$1" > "$2" 2>&1; rc=$?
  sshinj "rm -f /tmp/.pgpass_$TAG"
  sed 's/^/   /' "$2"; return $rc
}
row39(){
  if ! row39_sql_approved; then say "$ROW: row 39 skipped -- row39-user.sql is not approved (no matching $C/row39-sql.approved)"; return 0; fi
  say "$ROW: row 39 -- creating the district-level user (approved row39-user.sql)"
  apply_row39_sql || { say "   row 39 skipped: the user SQL did not apply cleanly (see $C/row39-user.out)"; return 0; }
  if ! row39_merge_approved; then say "   row 39 skipped: row39-merge-types.sql is not approved"; return 0; fi
  say "$ROW: row 39 -- merging three of District 1's encounter types into one (approved row39-merge-types.sql)"
  apply_sql_file $C/row39-merge-types.sql $C/row39-merge.out || { say "   row 39 skipped: the merge did not apply (see $C/row39-merge.out)"; return 0; }
  grep -q "122964" $C/row39-merge.out || { say "   row 39 skipped: the merged stream is not 122,964 records (see $C/row39-merge.out)"; return 0; }
  # The feeder is not in the deployed harness 1ff23cc, which the anchors keep; the harness reads feeders from
  # its resources on the injector, so it is copied there.
  sshinj "cat > /opt/avni-perf/harness/src/gatling/resources/row39-users-district1.csv" < $PERF/src/gatling/resources/row39-users-district1.csv
  [ "$(sshinj 'grep -c row39-district1 /opt/avni-perf/harness/src/gatling/resources/row39-users-district1.csv')" = 1 ] \
    || { say "   row 39 skipped: the feeder is not in the harness's resources on the injector"; return 0; }
  for spec in "v18.1 789092feb $JAR181 $SHA181" "fix1103b b7ee734d2 $JAR29C $SHA29C" "formula1103 b4c611977 $JARFRM $SHAFRM"; do
    set -- $spec; local TAGJ=$1 SB=$2 JAR=$3 SHA=$4
    say "$ROW: row 39 on $TAGJ ($SB)"; deploy "$JAR" "$SHA"
    AVNI_WARMUP_BURST_SECONDS=300 provision/scripts/env-warmup.sh 2>&1 | tail -1 | sed 's/^/   /'
    row39_sync $TAGJ $SB 1
    if [ "${LAST_SYNC_MIN:-0}" -lt 45 ]; then row39_sync $TAGJ $SB 2; else say "   second sync on $TAGJ skipped: the first took ${LAST_SYNC_MIN} min"; fi
  done
}

# ---- deep pages first, 13 Nov 2026 ~14:45 -----------------------------------------------------------------
# Earlier today: the bed, the 18.1 control on A (3.88 CPU s per sync) and 29c on A (2.26). Row 39 is re-done first,
# deep: District 1's user plus three of its encounter types merged into one (122,964 records, ~123 pages), synced
# in full on 18.1, the reviewed #1103 and the @Formula jar. The app host is at m6g.xlarge from the stopped resume --
# page time is the database's, so row 39 runs there. The merge changes the bed, so a reload comes before each B.
ensure_session
DB_C=db.m6g.large; INJ_C=m6g.large
start_apps
say "$ROW: DEEP PAGES first"
row39

# ---- 4. 29c anchor B on a fresh bed --------------------------------------------------------------------------
say "$ROW: 4. row 29c -- anchor B on the reviewed #1103, fresh pilot-day-180"
reload_with_apps_stopped pilot-day-180; start_apps
deploy "$JAR29C" "$SHA29C"; anchor B 1 JAR_SHA=$SHA29C SB=b7ee734d2 TAGV=fix1103b

# ---- 5. 30b anchor B on a fresh bed ---------------------------------------------------------------------------
say "$ROW: 5. row 30b -- anchor B on 18.3 at 27e22ee0a, fresh pilot-day-180"
reload_with_apps_stopped pilot-day-180; start_apps
deploy "$JAR30B" "$SHA30B"; anchor B 1 JAR_SHA=$SHA30B SB=27e22ee0a TAGV=rc18.3b-batch50 EXTRA_PROPS=-DUPLOAD_URL_BATCH=50

# ---- 6. 30b anchor D ---------------------------------------------------------------------------------------
say "$ROW: 6. row 30b -- anchor D on 18.3 at 27e22ee0a (8 + 8, pilot-day-180-5k)"
AVNI_AWS_PROFILE=avni-load-test provision/scripts/env-teardown.sh stop-apps > $C/$ROW-stop-apps.log 2>&1
resize m6g.2xlarge db.m6g.2xlarge
reload_with_apps_stopped pilot-day-180-5k; start_apps
deploy "$JAR30B" "$SHA30B"; anchor D 1 JAR_SHA=$SHA30B SB=27e22ee0a TAGV=rc18.3b-batch50 EXTRA_PROPS=-DUPLOAD_URL_BATCH=50
wait_writeup

# ---- 7. back to small, stop ----------------------------------------------------------------------------------
say "$ROW: injector logs, then database and app back to .large and stop"
ensure_session
D0=$(date -u +%Y-%m-%d)
sshinj "cd /opt/avni-perf && tar czf - \$(find . -maxdepth 1 -name '*.log' -newermt '$D0 00:00' -printf '%P ')" > /tmp/injector-$ROW.tar.gz
[ -s /tmp/injector-$ROW.tar.gz ] && aws s3 cp /tmp/injector-$ROW.tar.gz s3://avni-loadtest-936573213727/logs/injector/$D0-$ROW.tar.gz --only-show-errors && say "   injector logs uploaded"; rm -f /tmp/injector-$ROW.tar.gz
resize m6g.large db.m6g.large
provision/scripts/env-teardown.sh stop 2>&1 | tail -n 4 | sed 's/^/     /'
say "ROWS 29c, 30b, 39 done. Environment stopped at m6g.large / db.m6g.large / injector m6g.large. New Relic export still to run."
