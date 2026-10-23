#!/usr/bin/env bash
# Swap the pilot organisations (10-19) to a different growth dataset.
#
#   tools/swap-dataset.sh pilot-day-120
#   tools/swap-dataset.sh pilot-day-180-span20
#
# Tears down organisations 10-19, loads the named archive from the environment's
# S3 bucket, and verifies the result against the case 4 feeder. The archive must
# already be staged under `datasets/` -- this moves the database between
# generated datasets, it does not generate one.
#
# Environment: AVNI_INFRA overrides where the avni-infra checkout is found
# (default: beside this repository). SWAP_LOG_DIR overrides where the phase
# timings are written (default: $TMPDIR). The app host and the database address
# are read from tofu's state, not configured here.
#
# WRITTEN FROM WHAT WENT WRONG ON 15 OCT, and each guard is here because its
# absence cost time:
#
#   * EVERY long phase runs detached with an rc file and is POLLED. The first
#     attempt held psql open on an ssh session; the ssh returned while psql kept
#     running, and the script advanced to the next phase mid-teardown. The load
#     then failed on a duplicate key because the rows it collided with had not
#     been deleted yet.
#   * VACUUM BETWEEN TEARDOWN AND LOAD. teardown_org.py proves an organisation
#     has no rows in a table by scanning it; against millions of unreclaimed
#     dead tuples that preflight stalled for 75 minutes and deleted nothing.
#     With a vacuum first the same teardown took 11.
#   * NO `cmd | grep` ON ANYTHING WHOSE STATUS MATTERS. The shell reports the
#     last command in a pipeline, so a psql failing under ON_ERROR_STOP=1
#     passed through as success.
#   * The dataset is proved to target exactly 10-19 BEFORE anything is deleted.
#   * The feeder is checked against the loaded users afterwards: a different
#     dataset can carry different usernames, and a feeder matching nothing
#     produces a run that completes and measures the wrong thing.
set -uo pipefail
SET="${1:-}"
case "$SET" in pilot-day-*) ;; *) echo "usage: $(basename "$0") pilot-day-120|pilot-day-365|pilot-day-180-span20|pilot-day-180-5k|pilot-day-180-10k" >&2; exit 2;; esac
# **The feeder follows the dataset, and getting it wrong is the trap this whole
# naming scheme exists to stop.** `pilot-day-180-span20` is also a ten-tenant
# pilot, so its slices carry the same case numbers as span 8.4's -- 526 users
# where the pilot has 561. Checking a span-20 load against `case4-users-pilot.csv`
# would report 561 missing users and look like a broken load; worse, a RUN
# pointed at the pilot feeder would complete and measure users that are not there.
# The 5k and 10k sets (plan rows 25-26) have their own users entirely, generated with
# supervisors at pushScale 0, so their feeders carry the -nosuppush suffix.
case "$SET" in *-span20) FEEDVAR=span20 ;; *-5k) FEEDVAR=pilot-5k-nosuppush ;; *-10k) FEEDVAR=pilot-10k-nosuppush ;; *) FEEDVAR=pilot ;; esac
# **Paths are derived rather than written in.** This script lived in a
# scratchpad directory until a tmp clean emptied it, which is why it is tracked
# now -- and tracked means it cannot assume one person's checkout. avni-infra is
# expected beside avni-perf; AVNI_INFRA overrides that.
PERF=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INFRA="${AVNI_INFRA:-$(dirname "$PERF")/avni-infra}"
[ -f "$INFRA/provision/scripts/aws-session.sh" ] \
  || { echo "no avni-infra checkout at $INFRA -- set AVNI_INFRA" >&2; exit 2; }
cd "$INFRA"
# Credentials are resolved with RETRY and the reason is never silenced. A
# concurrent call to `aws configure export-credentials` can fail transiently,
# and a swallowed error reads as "wrong account", which sends the reader looking
# for a profile problem that is not there.
for attempt in 1 2 3; do
  # **The profile is named explicitly.** `.` inherits the caller's positional
  # parameters, and aws-session.sh reads its profile from $1 -- so sourcing it
  # from a script invoked as `swap-dataset.sh pilot-day-120` makes it try to
  # resolve a profile called "pilot-day-120". It then falls back to the default
  # profile, which is the PRODUCTION account, and the guard below is all that
  # stands between that and acting on it.
  . provision/scripts/aws-session.sh avni-load-test > /tmp/.sess.$$ 2>&1
  ACC=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
  [ "$ACC" = "936573213727" ] && break
  echo "  credentials attempt $attempt gave '${ACC:-none}':" >&2
  sed 's/^/    /' /tmp/.sess.$$ >&2
  sleep 5
done
rm -f /tmp/.sess.$$
export AWS_REGION=ap-south-1
[ "$ACC" = "936573213727" ] || { echo "wrong account after 3 attempts -- refusing" >&2; exit 1; }
TAG="swap-${SET#pilot-}-$(date +%H%M%S)"
PROXY="$PWD/configure/scripts/eice-ssh-proxy.sh"
# **The host and the database come from the state that built them.** Writing an
# instance id into a tracked file means the first `tofu apply` that replaces the
# instance leaves this pointing at something that no longer exists -- and the
# failure would be an ssh timeout, which reads as a network problem.
# A function rather than a variable holding a command: unquoted expansion of
# `tofu -chdir=...` splits into words under bash and does not under zsh, so the
# variable form resolves to empty for anyone who runs this from a zsh prompt.
tofu_out(){ tofu -chdir=provision/tofu/envs/loadtest output "$@" 2>/dev/null; }
DB=$(tofu_out -raw db_endpoint); DB=${DB%:*}
APP=$(tofu_out -json instance_ids \
      | python3 -c 'import json,sys;print(json.load(sys.stdin)["avni-server"])' 2>/dev/null)
[ -n "$DB" ] && [ -n "$APP" ] \
  || { echo "could not resolve db_endpoint and instance_ids from tofu -- refusing" >&2; exit 1; }
# Phase timings land here. Not the repository: they are per-run facts, and the
# ones worth keeping are quoted into execution-plan.md by hand.
S="${SWAP_LOG_DIR:-${TMPDIR:-/tmp}}"
sshapp(){ ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
  -o ConnectTimeout=30 -o ServerAliveInterval=30 -o ProxyCommand="$PROXY %h" ubuntu@"$APP" "$@" 2>/dev/null; }
say(){ echo "[$(TZ=Asia/Kolkata date +%H:%M:%S)] $*"; }
: > $S/$TAG.timings; phase(){ echo "$1 $(( $(date +%s) - $2 ))s" >> $S/$TAG.timings; }

SECRET=$(tofu -chdir=provision/tofu/envs/loadtest output -raw db_master_secret_arn 2>/dev/null)
aws secretsmanager get-secret-value --secret-id "$SECRET" --query SecretString --output text </dev/null \
| python3 -c 'import json,sys;pw=json.load(sys.stdin)["password"];print(pw.replace("\\","\\\\").replace(":","\\:"))' \
| sshapp "umask 077; IFS= read -r P; printf '%s:5432:openchs:openchs:%s' '$DB' \"\$P\" > /tmp/.pgpass_$TAG; chmod 600 /tmp/.pgpass_$TAG"
PSQL="PGPASSFILE=/tmp/.pgpass_$TAG psql -h $DB -U openchs -d openchs -w -v ON_ERROR_STOP=1"
Q="PGPASSFILE=/tmp/.pgpass_$TAG psql -h $DB -U openchs -d openchs -w -At"

# run a long statement detached, poll its rc, return its exit status
detached(){ # $1 label, $2 sql path
  sshapp "rm -f /tmp/$TAG.$1.rc /tmp/$TAG.$1.log
    setsid nohup bash -c '$PSQL -f $2 > /tmp/$TAG.$1.log 2>&1; echo \$? > /tmp/$TAG.$1.rc' >/dev/null 2>&1 </dev/null & sleep 2"
  local t0=$(date +%s) rc=''
  while :; do
    rc=$(sshapp "cat /tmp/$TAG.$1.rc 2>/dev/null"); [ -n "$rc" ] && break
    # **A teardown cannot report progress, and two attempts at one have now failed.**
    # "rows copied" showed nothing because a teardown emits no COPY lines.
    # `n_tup_del` then showed 0 for all 13 minutes of a delete of 12.4 M rows,
    # because Postgres buffers a backend's statistics locally and does not flush
    # them to the collector until the transaction commits -- and this is one
    # transaction by design. Counting the rows that remain fails for the same
    # reason from the other side: MVCC hands the polling session a snapshot
    # taken before the delete, so it would read 1,506,000 until the moment it
    # reads 0.
    #
    # So report what can be known from outside: that the backend is alive, how
    # long its transaction has run, and whether it is waiting on a lock. That
    # last one is the failure actually worth catching -- a teardown queued
    # behind an ACCESS EXCLUSIVE lock looks exactly like a slow one.
    if [ "$1" = "td" ]; then
      echo "     [$(( ($(date +%s)-t0)/60 ))m] $(sshapp "$Q -c \"SELECT coalesce(state, '?') || coalesce(' waiting on ' || wait_event_type || ':' || wait_event, ', not waiting') || ', ' || date_trunc('second', now() - xact_start) || ' into the transaction' FROM pg_stat_activity WHERE application_name = 'psql' AND pid <> pg_backend_pid() AND xact_start IS NOT NULL ORDER BY xact_start LIMIT 1;\"")"
    else
      echo "     [$(( ($(date +%s)-t0)/60 ))m] $(sshapp "awk '/^COPY /{n+=\$2} END{print n+0}' /tmp/$TAG.$1.log") rows copied"
    fi
    sleep 60
  done
  echo "     $1 exit $rc after $(( ($(date +%s)-t0)/60 ))m $(( ($(date +%s)-t0)%60 ))s"
  return "${rc:-1}"
}

t=$(date +%s); say "1. fetch $SET and prove it targets 10-19"
B=$(tofu -chdir=provision/tofu/envs/loadtest output -raw bucket 2>/dev/null)
URL=$(aws s3 presign "s3://$B/datasets/$SET.tar.gz" --expires-in 10800)
sshapp "rm -rf /tmp/$SET; curl -sSf -o /tmp/$SET.tgz '$URL' && tar -C /tmp -xzf /tmp/$SET.tgz 2>/dev/null && rm -f /tmp/$SET.tgz && echo \"   extracted \$(du -sh /tmp/$SET | cut -f1)\""
# **The archive's load.sql names its TSVs by the absolute path the generator was given.** The
# earlier datasets were generated into /tmp/<name> and so matched this extraction root by luck;
# pilot-day-180-5k was generated into ~/avni-datasets and its first load died in three seconds on
# "/Users/joy/avni-datasets/pilot-day-180-5k/ngo-1/address_level_type.tsv: No such file or
# directory" (23 Oct 2026) -- after the teardown had already emptied organisations 10-19. Whatever
# the generator was given, the files are at /tmp/$SET here, so say so.
sshapp "sed -i -E \"s|FROM '[^']*/$SET/|FROM '/tmp/$SET/|g\" /tmp/$SET/*/load.sql; echo \"   load.sql paths: \$(grep -ohE \"FROM '[^']*/$SET/\" /tmp/$SET/*/load.sql | sort -u | tr '\\n' ' ')\""
sshapp "python3 -c \"
import json,glob
want={10,11,12,13,14,15,16,17,18,19}; got=set()
for m in glob.glob('/tmp/$SET/*/manifest.json'): got|=set(json.load(open(m))['target']['organisations'])
print('   targets', sorted(got)); raise SystemExit(0 if got==want else 1)\"" \
  || { echo "ABORT: $SET does not target exactly 10-19" >&2; exit 1; }
# Reported, not asserted, and it is reported for the reader rather than for the
# teardown. The manifest carries an id_base PER TENANT -- ten of them, not one --
# and `teardown_org.py` no longer uses the value at all: "id_base is accepted and
# recorded, not used: the cut is by provenance now" (teardown_org.py:214). The
# range cut was removed because `id >= id_base` also took the bundle's own
# bundleloader@ user. So --id-base below is inert, and this line exists so that
# nobody reading the log infers otherwise.
sshapp "python3 -c \"
import json,glob
b=set()
for m in glob.glob('/tmp/$SET/*/manifest.json'):
    t=json.load(open(m))['target']
    b.add(t.get('id_base'))
print('   incoming id_base', sorted(x for x in b if x is not None) or 'not in the manifest')\""
phase fetch $t

t=$(date +%s); say "2. FK scaffolding indexes"
sshapp "$PSQL -c 'CREATE INDEX IF NOT EXISTS tmp_sw_enc_filled_by ON encounter (filled_by_id);' -c 'CREATE INDEX IF NOT EXISTS tmp_sw_pe_filled_by ON program_encounter (filled_by_id);'" >/dev/null || exit 1
phase index_create $t

t=$(date +%s); say "3. teardown of organisations 10-19"
( cd "$PERF/tools/data-generator" && python3 teardown_org.py \
    --organisation 10 --organisation 11 --organisation 12 --organisation 13 --organisation 14 \
    --organisation 15 --organisation 16 --organisation 17 --organisation 18 --organisation 19 \
    --id-base 201000000 --scope data ) | sshapp "cat > /tmp/$TAG.td.sql"
detached td "/tmp/$TAG.td.sql" || { echo "TEARDOWN FAILED" >&2; sshapp "tail -12 /tmp/$TAG.td.log"; exit 1; }
sshapp "grep -a 'organisation(s)' /tmp/$TAG.td.log | tail -1" | sed 's/^/     /'
E=$(sshapp "$Q -c \"SELECT count(*) FROM individual WHERE organisation_id BETWEEN 10 AND 19;\"")
[ "${E:-1}" = "0" ] || { echo "ABORT: pilot still has $E individuals after teardown" >&2; exit 1; }
echo "     pilot individuals: 0"
phase teardown $t

t=$(date +%s); say "4. VACUUM ANALYZE (before the load, and before the next teardown)"
sshapp "$PSQL -c 'VACUUM ANALYZE;'" >/dev/null || exit 1
phase vacuum_after_teardown $t

t=$(date +%s); say "5. drop the FK scaffolding indexes"
sshapp "$PSQL -c 'DROP INDEX IF EXISTS tmp_sw_enc_filled_by;' -c 'DROP INDEX IF EXISTS tmp_sw_pe_filled_by;'" >/dev/null || exit 1
phase index_drop $t

t=$(date +%s); say "6. load $SET, per-tenant ANALYZE stripped, one at the end"
sshapp "sed -i 's/^ANALYZE;\$/-- ANALYZE moved to the end of the driver/' /tmp/$SET/*/load.sql
  { echo '\\timing on'; for d in \$(ls -d /tmp/$SET/*/ | sort); do echo \"\\\\echo === TENANT \$(basename \$d) ===\"; echo \"\\\\i \${d}load.sql\"; done; echo 'ANALYZE;'; } > /tmp/$TAG.load.sql"
detached load "/tmp/$TAG.load.sql" || { echo "LOAD FAILED" >&2; sshapp "tail -12 /tmp/$TAG.load.log"; exit 1; }
phase load $t

t=$(date +%s); say "7. VACUUM ANALYZE"; sshapp "$PSQL -c 'VACUUM ANALYZE;'" >/dev/null; phase vacuum $t
t=$(date +%s); say "8. REINDEX"
for tb in individual encounter program_encounter program_enrolment address_level catchment catchment_address_mapping users user_group groups; do
  sshapp "$PSQL -c 'REINDEX TABLE $tb;'" >/dev/null || { echo "REINDEX $tb failed" >&2; exit 1; }; done
phase reindex $t

say "9. verification"
sshapp "$Q -F'|' -c \"
SELECT 'pilot individuals', count(*) FROM individual WHERE organisation_id BETWEEN 10 AND 19
UNION ALL SELECT 'pilot encounters', count(*) FROM encounter WHERE organisation_id BETWEEN 10 AND 19
UNION ALL SELECT 'co-tenant rows (want 0)', count(*) FROM individual WHERE organisation_id >= 24
UNION ALL SELECT 'org 3 individuals (must survive)', count(*) FROM individual WHERE organisation_id = 3
UNION ALL SELECT 'tmp_ indexes left (want 0)', count(*) FROM pg_indexes WHERE indexname LIKE 'tmp_%';\"" | sed 's/^/     /'
say "10. case 4 feeder ($FEEDVAR) against the loaded users"
python3 -c "
import csv
rows=list(csv.DictReader(open('$PERF/src/gatling/resources/case4-users-$FEEDVAR.csv')))
vals=','.join(\"('\"+r['userName'].replace(\"'\",\"''\")+\"')\" for r in rows)
print('''WITH feeder(username) AS (VALUES '''+vals+''')
SELECT 'feeder rows', count(*) FROM feeder
UNION ALL SELECT 'present', count(*) FROM feeder f JOIN users u ON u.username=f.username
UNION ALL SELECT 'MISSING', count(*) FROM feeder f LEFT JOIN users u ON u.username=f.username WHERE u.id IS NULL
UNION ALL SELECT 'without catchment', count(*) FROM feeder f JOIN users u ON u.username=f.username WHERE u.catchment_id IS NULL;''')
" | sshapp "cat > /tmp/$TAG.fd.sql; $Q -F'|' -f /tmp/$TAG.fd.sql" | sed 's/^/     /'
echo "=== phase timings ==="; cat $S/$TAG.timings | sed 's/^/     /'
sshapp "rm -f /tmp/.pgpass_$TAG"
say "done -- $SET is loaded and verified"
