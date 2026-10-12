#!/usr/bin/env bash
# Provision the co-tenant organisations named by a recipe, resumably.
#
#   ./tools/provision-co-tenants.sh --url https://loadtest.avniproject.org \
#       --recipe tools/data-generator/datasets/co-tenants-day-180.json \
#       --bundle-root ~/avni-perf-bundles --log provisioning.tsv
#
#   --from co-200     start at a tenant (the resume guard makes this optional)
#   --limit 10        stop after N, for a dry wade into it
#
# WHY RESUMABLE. At measured archetype timings -- 183 s large-pull-heavy, 72 s
# push-dominated, 110 s media-heavy -- 513 organisations is about 10.6 hours
# serial, and imports do not run concurrently. Ten hours unattended WILL be
# interrupted: a dropped connection, a sleeping laptop, the environment
# bouncing. A loop that cannot resume turns an interruption into starting over;
# one that resumes badly creates duplicate organisations.
#
# THE GUARD IS THE SERVER'S OWN LIST, not a local file. Before each tenant it
# re-reads GET /organisation and skips any name already present. That survives
# the log being lost, the script being edited, and two operators running it.
#
# WHAT IT LOGS, both free and both answering questions otherwise left to guess:
#   elapsed seconds per import -- turns "is provisioning superlinear in the
#     number of organisations?" into an observation rather than a hope
#   the assigned id -- needed anyway to map co-NNN -> real id, because the
#     recipe's 1001-1513 are placeholders and the server is assigning from 24.
#     unassigned_organisations() cannot catch that: those ids look assigned,
#     which is exactly how the pilot came to name four live organisations.
set -uo pipefail

URL=""; RECIPE=""; BUNDLE_ROOT=""; LOG="provisioning.tsv"; FROM=""; LIMIT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --url) URL="$2"; shift 2 ;;
    --recipe) RECIPE="$2"; shift 2 ;;
    --bundle-root) BUNDLE_ROOT="${2/#\~/$HOME}"; shift 2 ;;
    --log) LOG="$2"; shift 2 ;;
    --from) FROM="$2"; shift 2 ;;
    --limit) LIMIT="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$URL" ] && [ -n "$RECIPE" ] && [ -n "$BUNDLE_ROOT" ] || {
  echo "usage: $0 --url <base-url> --recipe <recipe.json> --bundle-root <dir> [--log f] [--from co-NNN] [--limit N]" >&2
  exit 2; }
[ -f "$RECIPE" ] || { echo "no recipe at $RECIPE" >&2; exit 2; }

# Every archetype must resolve BEFORE the first import. A missing bundle found
# at tenant 400 wastes eight hours; found now it costs nothing.
missing=""
for a in $(python3 -c "
import json,sys
d=json.load(open('$RECIPE'))
print('\n'.join(sorted({t.get('bundle_archetype','') for t in d['tenants']})))"); do
  [ -d "$BUNDLE_ROOT/$a" ] || missing="$missing $a"
done
[ -z "$missing" ] || { echo "bundle-root has no directory for:$missing" >&2; exit 2; }

[ -f "$LOG" ] || printf 'name\tarchetype\torg_id\telapsed_s\tstatus\tat\n' > "$LOG"

echo "recipe:      $RECIPE"
echo "bundle root: $BUNDLE_ROOT"
echo "log:         $LOG"
python3 -c "
import json,collections
d=json.load(open('$RECIPE'))
c=collections.Counter(t['bundle_archetype'] for t in d['tenants'])
est=sum({'large-pull-heavy':183,'push-dominated':72,'media-heavy':110}.get(a,72)*n for a,n in c.items())
print(f'  {len(d[\"tenants\"])} tenants: ' + ', '.join(f'{n} {a}' for a,n in sorted(c.items())))
print(f'  projected {est:,} s = {est/3600:.1f} h at measured archetype timings')"
echo

existing() { curl -s --max-time 60 "$URL/organisation?size=5000" \
               -H "Accept: application/json" -H "USER-NAME: ${AVNI_ADMIN:-admin}" 2>/dev/null; }

# The guard's own failure mode is the dangerous one: if the list comes back
# short -- server-side paging cap, a truncated response, a transient error --
# every name looks absent and the loop creates DUPLICATE organisations for the
# whole remainder. So count what comes back and refuse to continue if it is
# fewer than we already know exist. Verified returning a plain array of all 17
# at 17 organisations; untested at 500+, which is exactly why this check is here.
BASELINE=0
guard_count() { printf '%s' "$1" | grep -o '"id"[[:space:]]*:' | wc -l | tr -d ' '; }

done_n=0; skipped=0; failed=0; started=$(date +%s)
while IFS=$'\t' read -r NAME ARCH; do
  [ -n "$NAME" ] || continue
  if [ -n "$FROM" ]; then [ "$NAME" = "$FROM" ] && FROM="" || continue; fi
  [ "$LIMIT" -gt 0 ] && [ "$done_n" -ge "$LIMIT" ] && { echo "--limit $LIMIT reached"; break; }

  # Re-read the server's list each time: the guard must not depend on the log.
  LIST=$(existing)
  N=$(guard_count "$LIST")
  if [ "$N" -eq 0 ]; then
    echo "ABORT: GET /organisation returned no organisations. The resume guard is blind," >&2
    echo "       and continuing would create duplicates. Nothing provisioned this pass." >&2
    exit 3
  fi
  if [ "$BASELINE" -eq 0 ]; then BASELINE="$N"; fi
  if [ "$N" -lt $(( BASELINE + done_n )) ]; then
    echo "ABORT: the organisation list came back with $N entries, fewer than the" >&2
    echo "       $(( BASELINE + done_n )) we know exist. It is truncated or paged, so the guard" >&2
    echo "       cannot be trusted and continuing would create duplicates." >&2
    exit 3
  fi
  if printf '%s' "$LIST" | grep -q "\"name\"[[:space:]]*:[[:space:]]*\"$NAME\""; then
    skipped=$((skipped+1))
    [ $((skipped % 25)) -eq 1 ] && echo "   [$(date +%H:%M:%S)] skipping $NAME (already on the server)"
    continue
  fi

  t0=$(date +%s)
  out=$(./tools/provision-org.sh --url "$URL" --bundle "$BUNDLE_ROOT/$ARCH" --name "$NAME" 2>&1)
  rc=$?
  el=$(( $(date +%s) - t0 ))
  oid=$(printf '%s' "$out" | sed -n 's/.*created, id \([0-9]\{1,\}\).*/\1/p' | head -1)

  if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "formMapping"; then
    printf '%s\t%s\t%s\t%s\tok\t%s\n' "$NAME" "$ARCH" "${oid:-?}" "$el" "$(date -u +%FT%TZ)" >> "$LOG"
    done_n=$((done_n+1))
    echo "   [$(date +%H:%M:%S)] $NAME ($ARCH) id=${oid:-?} ${el}s   done=$done_n skipped=$skipped failed=$failed"
  else
    printf '%s\t%s\t%s\t%s\tFAILED\t%s\n' "$NAME" "$ARCH" "${oid:-?}" "$el" "$(date -u +%FT%TZ)" >> "$LOG"
    failed=$((failed+1))
    echo "   [$(date +%H:%M:%S)] $NAME FAILED after ${el}s (exit $rc)" >&2
    printf '%s\n' "$out" | tail -12 >&2
    # Keep going: one bad bundle should not end a ten-hour run. The log says
    # which failed, and re-running the script retries exactly those.
  fi
done < <(python3 -c "
import json
d=json.load(open('$RECIPE'))
for t in d['tenants']:
    print(t['name'] + '\t' + t['bundle_archetype'])")

echo
echo "provisioned $done_n, skipped $skipped, failed $failed in $(( ($(date +%s) - started) / 60 )) min"
[ "$failed" -eq 0 ] || { echo "re-run to retry the failures; the guard skips what succeeded" >&2; exit 1; }
