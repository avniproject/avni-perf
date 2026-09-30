#!/usr/bin/env bash
#
# G2 — everything that has to happen before a measured run, in order.
#
#   ./prepare-run.sh --url https://loadtest.avniproject.org \
#                    --dataset /tmp/states-day-180 --user <a syncing user> \
#                    [--org 10 --org 11] [--skip-reset]
#
# **Why a script rather than a checklist.** Seven things have to be true before a run is worth
# measuring, and six of them are invisible in the result if they are wrong. A run against an
# un-enrolled injector address fails as server errors and latency rather than as an access
# decision; a run against a database somebody else's run dirtied is not comparable with anything;
# a run whose statistics were not reset reports the previous run's queries alongside its own.
# None of that shows up in a Gatling report.
#
# **What it does not do.** It prints the SQL rather than running it, for the same reason the
# teardown does: the connection string belongs to whoever is at the keyboard, and the reset
# truncates tables across every organisation in the database.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URL=""; DATASET=""; USER_NAME=""; ORGS=(); SKIP_RESET=0
while [ $# -gt 0 ]; do
  case "$1" in
    --url)        URL="$2"; shift 2 ;;
    --dataset)    DATASET="$2"; shift 2 ;;
    --user)       USER_NAME="$2"; shift 2 ;;
    --org)        ORGS+=("$2"); shift 2 ;;
    --skip-reset) SKIP_RESET=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$URL" ] || { echo "usage: $0 --url <base-url> --dataset <dir> --user <username>" >&2; exit 2; }

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }
note() { printf '  %s\n' "$*"; }

bold "G2 — before a measured run"

# ---- 1. the reset ------------------------------------------------------------------------------
# G4's decision: TRUNCATE the transactional tables, then reload every dataset the database holds.
# Not DELETE -- that is three times slower at best and 50% slower again on a cycled table, so the
# cadence stops being predictable. Not a snapshot restore -- RDS cannot restore in place.
if [ "$SKIP_RESET" = "0" ]; then
  step "1. Reset the database (G4). Run these, in order:"
  note ""
  note "psql -d \$DB -c 'TRUNCATE individual, encounter, program_enrolment, program_encounter CASCADE'"
  if [ -n "$DATASET" ]; then
    for d in "$DATASET"/*/; do
      [ -f "$d/reload.sql" ] && note "psql -d \$DB -v ON_ERROR_STOP=1 -f ${d}reload.sql"
    done
    note ""
    note "reload.sql, not load.sql: the truncate leaves the structural rows alone, so the"
    note "full script would collide on all seven of them partway through a transaction."
  else
    note "# and each dataset's reload.sql -- pass --dataset to list them"
  fi
  note ""
  note "Every dataset in the database needs reloading, not just the one under test."
  note "TRUNCATE cannot distinguish tenants, which is the cost of it being one second."
else
  step "1. Reset — skipped"
  note "Only correct if the previous run did not push. Every case except 1 pushes."
fi

# ---- 2. statistics -----------------------------------------------------------------------------
step "2. Reset per-run statistics, so the collected data covers this run only:"
note ""
note "psql -d \$DB -c 'select pg_stat_statements_reset()'"
note "psql -d \$DB -c 'select pg_stat_reset()'   -- table and index scan counts"
note ""
note "Without this, pg_stat_statements attributes the previous run's queries to this one and"
note "the slowest statement in a report may belong to a run nobody is looking at."

# ---- 3. the injector's address -----------------------------------------------------------------
# F4 is a security group allowlist, so this is the one failure that looks like a server problem.
step "3. Is the injector enrolled? (F4)"
EGRESS="$(curl -s --max-time 10 https://checkip.amazonaws.com 2>/dev/null | tr -d '[:space:]')"
if [ -n "$EGRESS" ]; then
  note "this machine's public egress address: $EGRESS"
  note "confirm it is in the ALB security group and the WAF IP set before running."
  note "An un-enrolled address fails as 403s and latency, which Gatling reports as the"
  note "server failing — a corrupted run that looks like a finding."
else
  note "could not determine the egress address; check it by hand"
fi

# ---- 4. readiness ------------------------------------------------------------------------------
step "4. Environment readiness"
if [ -n "$USER_NAME" ]; then
  "$HERE/environment-check.sh" --url "$URL" --user "$USER_NAME" || {
    echo; bold "readiness check failed — fix that before running"; exit 1; }
else
  note "skipped — pass --user <a syncing user> to check auth, syncDetails and privileges"
fi

# ---- 5. sync statuses --------------------------------------------------------------------------
# G2 asked for the scenario's sync-status arrays to be generated per run by rewriting loadedSince
# on cached baselines. That is not a per-run step any more -- the simulation draws the window per
# user and per entity from Q2's measured inter-sync gaps, so there is nothing to pre-generate and
# nothing that can go stale between runs.
step "5. Sync statuses — nothing to prepare"
note "SYNC_MODE decides the window, per user and per entity, inside the run:"
note "  realistic  draws from Q2's measured gaps (p50 16 min, p75 12.5 h — two behaviours)"
note "  incremental / full / csv  a fixed window"
note "Set SYNC_MODE for the case. There are no cached baselines to rewrite."

# ---- 6. the two decisions ----------------------------------------------------------------------
# G2's cache policy and G3's autovacuum. Both change how a result reads and neither is visible in
# the run, so they are recorded rather than remembered.
step "6. Record the two decisions with the run"
cat <<'DECISIONS'
  The reset's own reload leaves the caches warm -- it has just written every page through
  shared_buffers and the OS page cache -- which is closer to production than a cold start, and
  closer than a snapshot restore could be. So: no separate warm-up, and the policy is named
  rather than assumed.

  Autovacuum stays on. Production runs it, and an autovacuum storm mid-run is a genuine
  production failure mode worth catching rather than engineering away. It is a known source of
  run-to-run variance, which is why it is recorded.

  Pass both to the run, or archiveRun will say they are unrecorded:

    ./gradlew gatlingRun -DBASE_URL=... \
        -DCACHE_POLICY=warm-from-reload -DAUTOVACUUM=on \
        -DDATASET_ID=<recipe and generator commit> -DSERVER_BUILD=<server sha>
DECISIONS

step "Then run the scenario, start observability capture, and leave it alone (G3)."
