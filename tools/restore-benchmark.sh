#!/usr/bin/env bash
#
# G4 -- time the candidate reset mechanisms, because the choice is a timing question.
#
# **Day 9's number sets the cadence for everything after it.** A measured run is
# *restore + run + collect*, so if a reset is 40 minutes a 2-hour case is a half-day and a 4-hour
# case is a day. Phase 4 cannot be planned until this has been measured rather than estimated.
#
#   ./restore-benchmark.sh --db "postgres://..." --source avni_loaded --dataset /data/day-180 \
#                          --organisation 3 --id-base 1000000 --yes
#
# **It does not run itself.** Every candidate here creates or drops a database, or deletes rows.
# Nothing runs without --yes, and --source is never written to.
#
# The candidates, and what each costs beyond wall-clock:
#
#   template    CREATE DATABASE ... TEMPLATE. File-level page copy, so fast, but it needs the
#               source to have no other connections and holds a second full copy -- 2x the dataset
#               in headroom, which for ~70GB is a provisioning question for avni-infra#112.
#   dump        pg_dump -Fd then pg_restore --jobs. Slow, because every index is rebuilt and GIN
#               is the worst of them, but the artefact lives outside the instance so you can DROP
#               first and restore into the freed space: ~1x.
#   regenerate  psql -f load.sql. Specific to this project: the generator's bulk COPY is
#               pg_restore's data phase without a stored artefact. Same index-rebuild cost.
#   teardown    teardown_org.py then load.sql. Only meaningful for a single-organisation dataset,
#               and it is the one candidate that leaves dead tuples behind -- included because if
#               it is minutes where the others are an hour, that changes which of them is worth
#               paying for, and the bloat is measurable rather than assumed.
#
# **RDS snapshot restore is deliberately absent.** It cannot restore in place, and lazy loading
# leaves a restored instance with dramatically worse IO until every block has faulted in. It is for
# baseline creation and portability, not for a per-run reset. See the plan, section G4.
set -uo pipefail

DB=""; SOURCE=""; DATASET=""; ORG=""; ID_BASE=""; YES=0
ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --db)           DB="$2"; shift 2 ;;
    --source)       SOURCE="$2"; shift 2 ;;
    --dataset)      DATASET="$2"; shift 2 ;;
    --organisation) ORG="$2"; shift 2 ;;
    --id-base)      ID_BASE="$2"; shift 2 ;;
    --only)         ONLY="$2"; shift 2 ;;
    --yes)          YES=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

die() { printf '\033[31merror\033[0m: %s\n' "$*" >&2; exit 1; }
[ -n "$DB" ] || die "--db is required"
[ "$YES" = "1" ] || die "this creates and drops databases and deletes rows. Pass --yes when you have read what it does."

# A dataset directory holds the .tsv files and the load.sql that references them by absolute path.
TIMINGS=""
record() { TIMINGS="${TIMINGS}${1}|${2}|${3}\n"; }

# `time` around a command, in whole seconds, without depending on GNU date.
timed() {
  local start end
  start=$(date +%s)
  if "$@" >/tmp/g4-step.log 2>&1; then
    end=$(date +%s); echo $((end - start)); return 0
  fi
  end=$(date +%s)
  echo "  last 20 lines of output:" >&2; tail -20 /tmp/g4-step.log >&2
  echo $((end - start)); return 1
}

wants() { [ -z "$ONLY" ] || [ "$ONLY" = "$1" ]; }

echo "G4 reset benchmark"
echo

# ---- template ---------------------------------------------------------------------------------
# Needs an exclusive lock on the source: CREATE DATABASE ... TEMPLATE fails outright while another
# session is connected to it, which on a shared instance is a scheduling constraint rather than a
# cost, and is worth discovering here rather than on Day 12.
if wants template && [ -n "$SOURCE" ]; then
  echo "1. CREATE DATABASE ... TEMPLATE"
  psql "$DB" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS g4_template_copy" >/dev/null 2>&1
  if s=$(timed psql "$DB" -v ON_ERROR_STOP=1 \
           -c "CREATE DATABASE g4_template_copy TEMPLATE $SOURCE"); then
    echo "   ${s}s"
    record template "$s" "needs 2x storage; source must have no other connections"
  else
    echo "   failed after ${s}s -- commonly 'source database is being accessed by other users'"
    record template "-" "failed: see above"
  fi
  psql "$DB" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS g4_template_copy" >/dev/null 2>&1
else
  [ -n "$SOURCE" ] || echo "1. template -- skipped, no --source given"
fi

# ---- dump / restore ---------------------------------------------------------------------------
if wants dump && [ -n "$SOURCE" ]; then
  echo "2. pg_dump -Fd | pg_restore --jobs"
  OUT="$(mktemp -d "${TMPDIR:-/tmp}/g4dump.XXXXXX")"
  if s=$(timed pg_dump -d "$DB" -Fd -j 4 -f "$OUT/dump"); then
    echo "   dump ${s}s ($(du -sh "$OUT/dump" 2>/dev/null | cut -f1))"
    psql "$DB" -c "DROP DATABASE IF EXISTS g4_restore_copy" >/dev/null 2>&1
    psql "$DB" -c "CREATE DATABASE g4_restore_copy" >/dev/null 2>&1
    if r=$(timed pg_restore -d "${DB%/*}/g4_restore_copy" -j 4 "$OUT/dump"); then
      echo "   restore ${r}s"
      record dump "$((s + r))" "dump ${s}s + restore ${r}s; artefact outside the instance, ~1x"
    else
      echo "   restore failed after ${r}s"; record dump "-" "restore failed"
    fi
    psql "$DB" -c "DROP DATABASE IF EXISTS g4_restore_copy" >/dev/null 2>&1
  else
    echo "   dump failed after ${s}s"; record dump "-" "dump failed"
  fi
  rm -rf "$OUT"
fi

# ---- regenerate -------------------------------------------------------------------------------
# The load only, not the generation: generating runs on the injector and can happen while the
# previous run is still going, so it is off the critical path in a way the load is not.
#
# **It needs its target empty, and says so rather than discovering it.** load.sql has no truncate
# and no ON CONFLICT, so against an organisation that already holds the dataset it dies on the
# primary key seconds in -- a confusing failure that looks like a broken script rather than a
# benchmark run in the wrong order. Checked up front, because the point of this file is to produce
# a number and a failed candidate produces none.
if wants regenerate && [ -n "$DATASET" ]; then
  echo "3. regenerate (load.sql into an empty organisation)"
  [ -f "$DATASET/load.sql" ] || die "no load.sql under $DATASET"
  if [ -z "$ORG" ]; then
    echo "   skipped -- pass --organisation so the target can be checked for emptiness first"
    record regenerate "-" "skipped: no --organisation to check"
  else
    OCCUPIED=$(psql "$DB" -At -c \
      "select coalesce(sum(n), 0) from (
         select count(*) n from individual where organisation_id = $ORG
         union all select count(*) from encounter where organisation_id = $ORG) t" 2>/dev/null)
    if [ "${OCCUPIED:-0}" != "0" ]; then
      echo "   skipped -- organisation $ORG already holds ${OCCUPIED} rows."
      echo "   load.sql has no truncate, so this would fail on the primary key rather than time"
      echo "   anything. Run --only teardown, which tears down and reloads and times both, or"
      echo "   point --db at an empty database."
      record regenerate "-" "skipped: organisation $ORG is not empty"
    elif s=$(timed psql "$DB" -v ON_ERROR_STOP=1 -f "$DATASET/load.sql"); then
      echo "   ${s}s"
      record regenerate "$s" "load only; generation runs on the injector, off the critical path"
    else
      echo "   failed after ${s}s"; record regenerate "-" "failed"
    fi
  fi
fi

# ---- teardown + reload ------------------------------------------------------------------------
if wants teardown && [ -n "$DATASET" ] && [ -n "$ORG" ] && [ -n "$ID_BASE" ]; then
  echo "4. teardown_org.py + load.sql"
  HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  SQL="$(mktemp "${TMPDIR:-/tmp}/g4teardown.XXXXXX")"
  python3 "$HERE/data-generator/teardown_org.py" --organisation "$ORG" --id-base "$ID_BASE" > "$SQL" \
    || die "could not generate the teardown"
  if t=$(timed psql "$DB" -v ON_ERROR_STOP=1 -f "$SQL"); then
    if l=$(timed psql "$DB" -v ON_ERROR_STOP=1 -f "$DATASET/load.sql"); then
      echo "   teardown ${t}s + load ${l}s = $((t + l))s"
      record teardown "$((t + l))" "leaves dead tuples; measure bloat before trusting it between runs"
    else
      echo "   reload failed after ${l}s"; record teardown "-" "reload failed"
    fi
  else
    echo "   teardown failed after ${t}s"; record teardown "-" "teardown failed"
  fi
  rm -f "$SQL"
fi

echo
printf 'mechanism   seconds  notes\n'
printf -- "$TIMINGS" | while IFS='|' read -r m s n; do
  [ -n "$m" ] || continue
  printf '%-11s %7s  %s\n' "$m" "$s" "$n"
done

cat <<'NOTE'

A run is restore + run + collect, so the winner here sets Phase 4's cadence. Two things the
clock does not show and that belong in the decision:

  * peak storage -- template holds a second full copy, dump and regenerate do not
  * index state  -- template copies production-shaped indexes as they are; dump, regenerate and
                    teardown rebuild or reuse them, and a pristine index understates scan and
                    maintenance cost (the parity record already carries this deviation)

Record the winner, the number, and the date in the plan's G4 section. Re-time it when the dataset
size changes -- these do not scale alike.
NOTE
