#!/usr/bin/env bash
# Reload the 513 co-tenant organisations' transactional data.
#
#   tools/restore-co-tenants.sh --plan     # compute and print the load set, touch nothing
#   tools/restore-co-tenants.sh
#
# The organisations, their users and their imported bundles SURVIVE a Block C
# reset -- only the transactional rows are emptied -- so this is a load, not a
# re-provision. Provisioning them took ~11 hours; this takes ~40 minutes.
#
# TWO ARCHIVES, AND THE SECOND EXTRACTS OVER THE FIRST.
# `co-tenants-day-180.tar.gz` holds all 513 tenants, including a generation of
# eleven that was found stale on 13 Oct 2026 and torn down.
# `co-tenants-day-180-regen11.tar.gz` holds the corrected eleven -- and its
# top-level directory is *also* `co-tenants-day-180`, so extracting it second
# replaces those eleven tenant directories in place. The merged tree is then the
# whole correct dataset and every tenant in it is loaded.
#
# **Order is therefore load-bearing, and the result is verified rather than
# assumed.** If the regen archive failed to download, the base extraction would
# sit there looking complete while holding the stale generation of eleven
# tenants -- the exact fault that cost a teardown and reload on 13 Oct. So the
# eleven are named here, their presence is checked, and their files must be
# newer than the base tenants' or the script refuses to load.
#
# The eleven are co-001 and the ten `large-pull-heavy` tenants. Note that
# docs/co-tenant-provisioning.tsv lists only the ten: it has 511 rows for 513
# organisations because co-001 and co-002 are missing from it. The archives are
# authoritative here, not the TSV.
set -uo pipefail
PLAN=0
[ "${1:-}" = "--plan" ] && PLAN=1

PERF=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INFRA="${AVNI_INFRA:-$(dirname "$PERF")/avni-infra}"
[ -f "$INFRA/provision/scripts/aws-session.sh" ] \
  || { echo "no avni-infra checkout at $INFRA -- set AVNI_INFRA" >&2; exit 2; }
cd "$INFRA"
# profile named explicitly: `.` inherits this script's $1 -- see aws-session.sh's header
for attempt in 1 2 3; do
  . provision/scripts/aws-session.sh avni-load-test >/dev/null 2>&1
  ACC=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
  [ "$ACC" = "936573213727" ] && break
  sleep 5
done
export AWS_REGION=ap-south-1
[ "$ACC" = "936573213727" ] || { echo "wrong account '${ACC:-none}' -- refusing" >&2; exit 1; }

tofu_out(){ tofu -chdir=provision/tofu/envs/loadtest output "$@" 2>/dev/null; }
DB=$(tofu_out -raw db_endpoint); DB=${DB%:*}
APP=$(tofu_out -json instance_ids | python3 -c 'import json,sys;print(json.load(sys.stdin)["avni-server"])' 2>/dev/null)
B=$(tofu_out -raw bucket)
[ -n "$DB" ] && [ -n "$APP" ] && [ -n "$B" ] || { echo "could not resolve tofu outputs -- refusing" >&2; exit 1; }

TAG="cot-$(date +%H%M%S)"
S="${RESTORE_LOG_DIR:-${TMPDIR:-/tmp}}"
PROXY="$PWD/configure/scripts/eice-ssh-proxy.sh"
sshapp(){ ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
  -o ConnectTimeout=30 -o ServerAliveInterval=30 -o ProxyCommand="$PROXY %h" ubuntu@"$APP" "$@" 2>/dev/null; }
say(){ echo "[$(TZ=Asia/Kolkata date +%H:%M:%S)] $*"; }
: > "$S/$TAG.timings"; phase(){ echo "$1 $(( $(date +%s) - $2 ))s" >> "$S/$TAG.timings"; }

REGEN="co-001 co-004 co-005 co-006 co-007 co-008 co-009 co-011 co-012 co-013 co-019"

t=$(date +%s); say "1. fetch the base archive, then extract the regen archive OVER it"
sshapp "rm -rf /tmp/co-tenants-day-180"
# **Retried, because the usual failure is not the fetch.** This runs over an
# SSH session from a laptop, and a laptop that sleeps drops the connection
# mid-transfer: ssh returns non-zero and an un-retried guard aborts a restore
# that was working. That cost a run on 20 Oct 2026. The load phase below is
# already immune -- it runs detached under setsid on the host and is polled --
# so the fetch was the only part that could be lost this way.
for A in co-tenants-day-180 co-tenants-day-180-regen11; do
  ok=0
  for attempt in 1 2 3; do
    URL=$(aws s3 presign "s3://$B/datasets/$A.tar.gz" --expires-in 10800)
    if sshapp "curl -sSf -o /tmp/$A.tgz '$URL' && tar -C /tmp -xzf /tmp/$A.tgz && rm -f /tmp/$A.tgz && echo \"   $A extracted\""; then
      ok=1; break
    fi
    echo "   $A: attempt $attempt did not complete, retrying" >&2
    sleep 10
  done
  [ "$ok" = "1" ] || { echo "ABORT: $A did not fetch and extract after 3 attempts" >&2; exit 1; }
done
sshapp "du -sh /tmp/co-tenants-day-180 | sed 's/^/   merged tree: /'"
phase fetch $t

say "2. prove the regen generation is the one on disk"
sshapp "python3 - <<'PY'
import os, glob
root = '/tmp/co-tenants-day-180'
regen = '''$REGEN'''.split()
missing = [t for t in regen if not os.path.exists(os.path.join(root, t, 'load.sql'))]
if missing:
    raise SystemExit('ABORT: regen tenants absent from the tree: ' + ', '.join(missing))
def mt(t): return os.path.getmtime(os.path.join(root, t, 'load.sql'))
others = [os.path.basename(os.path.dirname(f)) for f in glob.glob(root + '/*/load.sql')]
others = [t for t in others if t not in regen]
newest_base = max(mt(t) for t in others)
oldest_regen = min(mt(t) for t in regen)
print('   base tenants newest : %s' % __import__('time').strftime('%F %T', __import__('time').gmtime(newest_base)))
print('   regen tenants oldest: %s' % __import__('time').strftime('%F %T', __import__('time').gmtime(oldest_regen)))
if oldest_regen <= newest_base:
    raise SystemExit('ABORT: the regen tenants are not newer than the base ones -- '
                     'the second extract did not take effect, and this tree holds the stale generation')
print('   OK: all %d regen tenants are newer than every base tenant' % len(regen))
PY" || { echo "ABORT: regen verification failed" >&2; exit 1; }

say "3. the load set is every tenant in the merged tree"
sshapp "ls -d /tmp/co-tenants-day-180/*/ | grep -v '/\._' | sed 's:/$::' > /tmp/$TAG.dirs
  wc -l < /tmp/$TAG.dirs | sed 's/^/   tenant dirs to load: /'" 

say "4. the co-tenant organisations must be empty before loading"
SECRET=$(tofu_out -raw db_master_secret_arn)
aws secretsmanager get-secret-value --secret-id "$SECRET" --query SecretString --output text </dev/null \
| python3 -c 'import json,sys;pw=json.load(sys.stdin)["password"];print(pw.replace("\\","\\\\").replace(":","\\:"))' \
| sshapp "umask 077; IFS= read -r P; printf '%s:5432:openchs:openchs:%s' '$DB' \"\$P\" > /tmp/.pgpass_$TAG; chmod 600 /tmp/.pgpass_$TAG"
PSQL="PGPASSFILE=/tmp/.pgpass_$TAG psql -h $DB -U openchs -d openchs -w -v ON_ERROR_STOP=1"
Q="PGPASSFILE=/tmp/.pgpass_$TAG psql -h $DB -U openchs -d openchs -w -At"
EXISTING=$(sshapp "$Q -c \"SELECT count(*) FROM individual WHERE organisation_id >= 24;\"")
echo "     co-tenant individuals now: ${EXISTING:-?}"
[ "${EXISTING:-1}" = "0" ] || { echo "ABORT: co-tenants already hold $EXISTING individuals -- this loader does not merge" >&2; sshapp "rm -f /tmp/.pgpass_$TAG"; exit 1; }

if [ "$PLAN" = "1" ]; then
  say "--plan: stopping here, nothing written"
  sshapp "rm -f /tmp/.pgpass_$TAG"
  exit 0
fi

# **LEAVE THE INDEXES AND TRIGGERS ALONE.** An earlier version of this script
# dropped the GIN indexes before the load and rebuilt them after, on the theory
# that index maintenance was what made program_encounter slow. It is not, and
# dropping them makes things dramatically WORSE. Measured 20 Oct 2026 on
# co-002's 136,381 program_encounter rows:
#
#   indexes dropped, program_encounter already holding 413k rows     13 rows/s
#   indexes present, same load                                    4,570 rows/s
#
# 350x slower without them. Something fires per row and does a lookup; without
# its index that becomes a sequential scan over a table that grows as the load
# proceeds, so the cost climbs with every tenant. The same mistake also makes a
# teardown quadratic -- deleting a parent row checks every child table, and
# without the child-side index that is a scan per row. A cleanup that took 3.4
# seconds with the indexes present had not finished in 26 minutes without them.
#
# The one change that genuinely matters is that the per-tenant BEGIN...COMMIT is
# gone, so each table commits on its own. See the note in copy_writer.py.
# **No per-tenant ANALYZE either.** One was added on 20 Oct on the theory that
# stale statistics on the freshly-loaded FK parents were the problem. An A/B
# test disproved that, and the mitigation was left in anyway: it re-analysed
# `individual` on every tenant and grew from 2.7 s to 39 s as the table filled,
# reaching ~16 s average -- about two hours across 513 tenants, against twelve
# minutes of actual copying for the rows that remained. The single VACUUM
# ANALYZE after the load is where that work belongs.
t=$(date +%s); say "5. load all tenants -- indexes, triggers and all"
sshapp "sed -i 's/^ANALYZE;\$/-- ANALYZE moved to the end of the driver/' /tmp/co-tenants-day-180*/*/load.sql
  { echo '\\timing on'; while read -r d; do echo \"\\\\echo === TENANT \$(basename \$d) ===\"; echo \"\\\\i \${d}/load.sql\"; done < /tmp/$TAG.dirs; echo 'ANALYZE;'; } > /tmp/$TAG.load.sql
  wc -l < /tmp/$TAG.load.sql | sed 's/^/     driver lines: /'"
sshapp "rm -f /tmp/$TAG.rc
  setsid nohup bash -c '$PSQL -f /tmp/$TAG.load.sql > /tmp/$TAG.log 2>&1; echo \$? > /tmp/$TAG.rc' >/dev/null 2>&1 </dev/null & sleep 2"
t0=$(date +%s)
while :; do
  rc=$(sshapp "cat /tmp/$TAG.rc 2>/dev/null"); [ -n "$rc" ] && break
  echo "     [$(( ($(date +%s)-t0)/60 ))m] $(sshapp "grep -ac '=== TENANT' /tmp/$TAG.log") tenants, $(sshapp "awk '/^COPY /{n+=\$2} END{print n+0}' /tmp/$TAG.log") rows"
  sleep 60
done
echo "     load exit $rc after $(( ($(date +%s)-t0)/60 ))m"
[ "$rc" = "0" ] || { echo "LOAD FAILED" >&2; sshapp "tail -15 /tmp/$TAG.log"; sshapp "rm -f /tmp/.pgpass_$TAG"; exit 1; }
phase load $t

t=$(date +%s); say "6. VACUUM ANALYZE"; sshapp "$PSQL -c 'VACUUM ANALYZE;'" >/dev/null; phase vacuum $t

say "7. verification"
sshapp "$Q -F'|' -c \"
SELECT 'co-tenant organisations with data', count(DISTINCT organisation_id) FROM individual WHERE organisation_id >= 24
UNION ALL SELECT 'co-tenant individuals', count(*) FROM individual WHERE organisation_id >= 24
UNION ALL SELECT 'co-tenant encounters', count(*) FROM encounter WHERE organisation_id >= 24
UNION ALL SELECT 'pilot individuals (must survive)', count(*) FROM individual WHERE organisation_id BETWEEN 10 AND 19
UNION ALL SELECT 'org 3 individuals (must survive)', count(*) FROM individual WHERE organisation_id = 3;\"" | sed 's/^/     /'
echo "=== phase timings ==="; sed 's/^/     /' "$S/$TAG.timings"
sshapp "rm -f /tmp/.pgpass_$TAG"
say "done"
