#!/usr/bin/env bash
#
# H5 step 1 and 2: can the client read this dataset at all?
#
# Runs the simulation against a loaded dataset in full-sync mode, one virtual user per role, and
# fails on any error. That is a stricter bar than a load run: a load run tolerates an error budget
# because at scale something always fails and the question is the rate. This asks whether the data
# is readable, so one bad datatype or one dangling reference is a defective dataset however rare.
#
# Steps 3 and 4 -- pointing a real client at a field worker and a supervisor, and reading its logs
# for rule failures -- cannot be automated from here and stay a manual sign-off. The simulation
# proves the server responded; only the client proves a generated observation satisfies the form's
# own rules.
#
#   ./structural_check.sh --users sync-users.csv --url http://localhost:8021 [--recipe name]
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
URL="${URL:-http://localhost:8021}"
USERS=""
RECIPE=""
OUT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --users)  USERS="$2"; shift 2 ;;
    --url)    URL="$2";   shift 2 ;;
    --recipe) RECIPE="$2"; shift 2 ;;
    --out)    OUT="$2";   shift 2 ;;
    -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

[ -n "$USERS" ] || { echo "error: --users is required (the dataset's own sync-users.csv)" >&2; exit 2; }
[ -f "$USERS" ] || { echo "error: no such user file: $USERS" >&2; exit 2; }

# One virtual user per role. More would measure contention, which is not what this checks.
ROLES=$(awk -F, 'NR==1 {for(i=1;i<=NF;i++) if ($i=="role") c=i; next} c {print $c}' "$USERS" \
        | sort -u | grep -v '^$' || true)
[ -n "$ROLES" ] || ROLES="(no role column)"
COUNT=$(printf '%s\n' "$ROLES" | grep -c . || echo 1)

echo "H5 structural check"
echo "  server   $URL"
echo "  users    $USERS"
echo "  roles    $(printf '%s ' $ROLES)"
echo "  running  $COUNT virtual user(s), full sync, zero error budget"
echo

cp "$USERS" "$REPO/src/gatling/resources/sync-users.csv"

set +e
( cd "$REPO" && ./gradlew gatlingRun \
    -DBASE_URL="$URL" \
    -DSYNC_MODE=full \
    -DSTRUCTURAL_CHECK=true \
    -DUSER_COUNT="$COUNT" \
    -DRAMP_PERIOD=1 )
STATUS=$?
set -e

echo
if [ $STATUS -eq 0 ]; then
  echo "PASS  every request returned 200 and every paged entity terminated."
  echo
  echo "Steps 3 and 4 remain, and are manual:"
  echo "  - point a real client at one field worker and one supervisor account"
  echo "  - confirm the sync completes, subjects list, a profile and an encounter form render"
  echo "  - read the client log for rule failures, which surface nowhere else"
else
  echo "FAIL  the dataset is not readable. Check the Gatling report for the failing entity:"
  echo "      a non-200 is usually a reference the generated data does not satisfy."
fi

if [ -n "$OUT" ]; then
  cat > "$OUT" <<JSON
{
  "check": "structural",
  "recipe": ${RECIPE:+\"$RECIPE\"}${RECIPE:-null},
  "checked_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "server": "$URL",
  "users": "$USERS",
  "steps_1_2": "$([ $STATUS -eq 0 ] && echo pass || echo fail)",
  "steps_3_4_manual_client_check": "not done",
  "note": "Steps 3 and 4 need a real client and are not automated. A dataset is only fully blessed once someone records them here."
}
JSON
  echo
  echo "  written to $OUT"
fi

exit $STATUS
