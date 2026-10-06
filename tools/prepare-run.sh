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
# truncates tables across every organisation in the database. The reset itself lives in
# reset-transactional.sql so the benchmark measures the same thing a run performs.
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
  note "psql -d \$DB -v ON_ERROR_STOP=1 -f $HERE/reset-transactional.sql"
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
  note ""
  note "The reset clears the audit rows the truncate orphans, which is why it is a file and"
  note "not one line. \`audit\` is not truncated and must not be: 42 foreign keys point at it"
  note "from the metadata tables, so CASCADE there would empty concept, form and the rest,"
  note "and reload.sql restores only transactional rows. The file explains the rest."
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

# ---- 6. warm the app server ---------------------------------------------------------------------
#
# **Measured 5 Oct 2026: a restarted server delivers a third of its warm throughput**, and the
# decision from that day is that every measured run is a warm one. The two runs started 2m49s
# after the JVM came up managed 18.43 rps against 50.00 for the same window twenty minutes later,
# with nine times the p95 and the only failures this environment has produced.
#
# It is the JVM, not the database and not the reset's reload. RDS ReadIOPS and ReadLatency were
# 0.0 throughout, so the buffer cache had already refilled; the cold runs sat at 99.2% app CPU and
# simply bought less with it. That is why the old advice here -- "the reset's own reload leaves the
# caches warm, so no separate warm-up" -- was true about the database and silent about the part
# that mattered.
#
# **Warmth has to be produced, not declared.** All ten runs that day passed
# `-DCACHE_POLICY=warm-incidental-no-reset`, including the two it was false for, and nothing could
# contradict it. A discarded pass makes the claim true before it is made.
step "6. Confirm the app server is warm"
cat <<'WARMUP'
  Every measured run is a warm run. **Starting the environment now warms it for you**:
  avni-infra's `env-teardown.sh start` runs `env-warmup.sh` once the instances are up, pushing
  ~4,300 requests over a 180 s window and discarding them. It invokes ./gradlew rather than
  run-scenario.sh, so the pass never reaches the artefacts prefix.

  So this step is a check, not a task -- unless one of these is true:

    * the app server has restarted since the environment started: a deploy, a crash, a manual
      bounce. Nothing re-warms it, and in production that window *is* a deploy, which is a
      finding in its own right rather than a state to measure a ceiling in
    * AVNI_SKIP_WARMUP was set when the environment came up
    * a long gap since the last run. **How long warm lasts is unmeasured** -- twenty minutes and
      two saturating runs was warm, 2m49s was not, and nothing establishes where it crosses

  Warm by hand in any of those cases:

    ./gradlew gatlingRun -DBASE_URL=$URL -DPROFILE=burst -DBURST_SECONDS=180 \
        -DSYNC_USERS=case1-users.csv -DUSER_COUNT=100 -DCACHE_POLICY=discarded-warmup

  180 s matches the automated pass. Before a campaign where the numbers matter, 900 s is the
  shape measured on 5 Oct -- the minimum sufficient warm-up is unmeasured, so the longer pass is
  the conservative one rather than the known-correct one.
WARMUP

# ---- 7. the two decisions ----------------------------------------------------------------------
# G2's cache policy and G3's autovacuum. Both change how a result reads and neither is visible in
# the run, so they are recorded rather than remembered.
step "7. Record the two decisions with the run"
cat <<'DECISIONS'
  Cache policy is `warm-after-discarded-warmup` once step 6 has run. Name what was actually done:
  the value is the only record that the run was warm, and on 5 Oct a wrong one survived into the
  archive for every run of the day.

  Autovacuum stays on. Production runs it, and an autovacuum storm mid-run is a genuine
  production failure mode worth catching rather than engineering away. It is a known source of
  run-to-run variance, which is why it is recorded.

  Pass both to the run, or archiveRun will say they are unrecorded:

    ./gradlew gatlingRun -DBASE_URL=... \
        -DCACHE_POLICY=warm-after-discarded-warmup -DAUTOVACUUM=on \
        -DDATASET_ID=<recipe and generator commit> -DSERVER_BUILD=<server sha>
DECISIONS

step "Then run the scenario, start observability capture, and leave it alone (G3)."
