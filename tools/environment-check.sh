#!/usr/bin/env bash
#
# Is this environment ready for a load run?
#
# Three environment windows produced three failures, each found one at a time by a human running
# a simulation and reading a stack trace: a null `version` on a `user_group` row, missing AWS
# credentials, and a user with no catchment. Every one of them was a single request away from
# being visible. This asks all the questions in one pass, before anyone spends a window on it.
#
#   ./environment-check.sh --url https://loadtest.avniproject.org --user loadtest@openchs
#
# Database checks are opt-in and off by default: pass --db <conninfo> to run them, otherwise the
# SQL is printed for you to run. The script is useful without database access and should not
# require it.
#
# Exit is non-zero if anything failed, so it can gate a run.

set -uo pipefail

URL=""; USER_NAME=""; DB=""; WAF=""; WAF_N=600; PASS=0; FAIL=0; WARN=0
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

while [ $# -gt 0 ]; do
  case "$1" in
    --url)  URL="$2"; shift 2 ;;
    --user) USER_NAME="$2"; shift 2 ;;
    --db)   DB="$2"; shift 2 ;;
    --waf)  WAF=1; shift ;;
    --waf-requests) WAF_N="$2"; shift 2 ;;
    *) echo "unknown argument: $1"; exit 2 ;;
  esac
done
# --user is optional on purpose. The users the scenarios run as come from the dataset generator,
# which needs a bundle and two files dumped from the target database, so requiring one here would
# mean this check could only run after the expensive thing it exists to de-risk. Without a user it
# runs everything that does not need one and says clearly what it skipped.
#
#   python3 tools/data-generator/bootstrap_user.py --organisation N --username X | psql ...
#
# gives you one, with no dataset behind it.
[ -n "$URL" ] || {
  echo "usage: $0 --url <base-url> [--user <username>] [--db <conninfo>] [--waf]"; exit 2; }

ok()   { printf '  \033[32mPASS\033[0m  %-34s %s\n' "$1" "${2:-}"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %-34s %s\n' "$1" "${2:-}"; FAIL=$((FAIL+1)); }
warn() { printf '  \033[33mWARN\033[0m  %-34s %s\n' "$1" "${2:-}"; WARN=$((WARN+1)); }
skip() { printf '  ----  %-34s %s\n' "$1" "${2:-}"; }

HOST="$(printf '%s' "$URL" | sed -E 's#^https?://##; s#[:/].*$##')"
PORT="$(printf '%s' "$URL" | grep -qi '^https' && echo 443 || echo 80)"

echo
echo "Environment check — $URL${USER_NAME:+ as $USER_NAME}"
echo

# ---------------------------------------------------------------- network
echo "Network"
if getent hosts "$HOST" >/dev/null 2>&1 || host "$HOST" >/dev/null 2>&1 \
   || python3 -c "import socket,sys; socket.gethostbyname('$HOST')" 2>/dev/null; then
  ok "DNS resolves" "$HOST"
else
  bad "DNS resolves" "$HOST does not resolve from here"
fi

# The injector must be able to connect. A refusal here means the allowlist is wrong or the app is
# down; a timeout usually means the security group is blocking. They look alike and are not.
CONNECT=$(curl -s -o /dev/null -w '%{time_connect}' --max-time 10 "$URL/ping" 2>/dev/null)
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$URL/ping" 2>/dev/null)
if [ "$CODE" = "200" ]; then
  ok "/ping answers" "HTTP 200, connect ${CONNECT}s"
elif [ -z "$CODE" ] || [ "$CODE" = "000" ]; then
  bad "/ping answers" "no response — blocked, or nothing listening"
else
  bad "/ping answers" "HTTP $CODE"
fi

# Round-trip time. A sync is ~109 requests, so this is paid 109 times: 25 ms is 2.7 s on a 14.1 s
# median. Runs from positions with materially different RTT are not comparable.
RTT=$(python3 - "$HOST" "$PORT" <<'PY' 2>/dev/null
import socket, sys, time
host, port = sys.argv[1], int(sys.argv[2])
best = []
for _ in range(5):
    s = socket.socket(); s.settimeout(3)
    try:
        t = time.perf_counter(); s.connect((host, port)); best.append((time.perf_counter()-t)*1000)
    except Exception: pass
    finally: s.close()
print(f"{min(best):.1f}" if best else "")
PY
)
if [ -n "$RTT" ]; then
  OVERHEAD=$(python3 -c "print(f'{$RTT*109/1000:.1f}')")
  ok "round-trip time" "${RTT} ms min — ${OVERHEAD}s per sync across 109 requests"
else
  warn "round-trip time" "could not measure"
fi

# ---------------------------------------------------------------- application
echo
echo "Application"
if [ -z "$USER_NAME" ]; then
  skip "auth under IdpType.none" "no --user given"
  skip "syncDetails responds" "no --user given"
  skip "privilege resolution" "no --user given"
  skip "entity coverage" "no --user given"
  echo
  echo "      No user supplied, so the application checks were skipped — and they are the ones"
  echo "      that found every failure so far. To get one without a dataset:"
  echo
  echo "        python3 tools/data-generator/bootstrap_user.py \\"
  echo "          --organisation <id> --username <name> | psql \"\$DB\""
  echo
else
BODY=$(curl -s --max-time 30 -X POST \
  "$URL/v2/syncDetails?includeUserSubjectType=true&deviceId=environment-check" \
  -H 'Content-Type: application/json' -H 'Accept: application/json' \
  -H "USER-NAME: $USER_NAME" -d '[]' 2>/dev/null)
SD_CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 -X POST \
  "$URL/v2/syncDetails?includeUserSubjectType=true&deviceId=environment-check" \
  -H 'Content-Type: application/json' -H 'Accept: application/json' \
  -H "USER-NAME: $USER_NAME" -d '[]' 2>/dev/null)

if [ "$SD_CODE" = "200" ]; then
  ok "auth under IdpType.none" "USER-NAME header accepted"
  ok "syncDetails responds" "HTTP 200"
else
  # Name the three failures already seen, so the reader does not have to recognise them again.
  HINT="HTTP $SD_CODE"
  case "$BODY" in
    *NoCatchmentFound*)        HINT="$HINT — user has no catchment (G5)" ;;
    *AmazonS3Exception*)       HINT="$HINT — S3 credentials missing; syncDetails lists extension files" ;;
    *"of primitive type"*)     HINT="$HINT — a NULL in a column mapped to a primitive, usually version" ;;
    *AuthenticationException*|*Unauthorized*) HINT="$HINT — user not found or auth misconfigured" ;;
    *"permission denied for"*)
      # The trap that looks like an application fault and is not. A new organisation gets its own
      # db_user, and without grants its reads fail while /ping stays green and the instance looks
      # entirely healthy. The symptom points at the server; the cause is one missing grant.
      HINT="$HINT — the organisation's db_user lacks grants. Run select grant_all_on_all('<db_user>'), via provision/scripts/db-bootstrap.sh with AVNI_DB_SQL=<file>" ;;
  esac
  bad "syncDetails responds" "$HINT"
fi

# The check that would have caught the group-membership defect: does this user resolve privileges?
# Without a user_group row every entity carrying field data is silently dropped and the sync still
# succeeds, so a 200 alone proves nothing.
if [ "$SD_CODE" = "200" ]; then
  # Via a file, not interpolated into the heredoc: a server error body is a Java stack trace
  # full of quotes and newlines, and inlining it gives a syntax error instead of a diagnosis.
  BODY_FILE="$(mktemp "${TMPDIR:-/tmp}/envcheck.XXXXXX")"
  printf %s "$BODY" > "$BODY_FILE"
  # The python runs in a subshell and cannot touch PASS/FAIL, so it reports through its exit
  # status instead. An earlier version printed FAIL and the script still exited 0 - a check that
  # reports a failure and then says "ready" is worse than no check at all.
  python3 - "$REPO" "$BODY_FILE" <<'PY'
import json, sys
raw = open(sys.argv[2]).read()
try:
    body = json.loads(raw)
except Exception:
    body = None

GREEN, RED, YELLOW, OFF = "\033[32m", "\033[31m", "\033[33m", "\033[0m"
gated = {"Individual","SubjectMigration","SubjectProgramEligibility","IndividualRelationship",
         "GroupSubject","Session","AttendanceRecord","Comment","CommentThread","Encounter",
         "ProgramEncounter","ProgramEnrolment","Checklist","ChecklistItem"}
served = {d.get("entityName") for d in (body or {}).get("syncDetails", [])}
# Two flags rather than one severity number. An earlier version used max(), which
# ranked the warning above the failure and reported a broken environment as ready.
failed = warned = False

# `syncDetails` returns only entities that have *changed*, so an entity with no rows is filtered
# out whatever the privileges say. On an empty organisation every field-data entity is absent for
# that reason alone, and reading it as a privilege failure is a false alarm — which is what this
# check did on its first real use.
#
# `MyGroups` is the discriminator. It is served when the user has group rows, and those are the
# same rows that carry `has_all_privileges`, so its presence means membership resolved even
# before any subject data exists.
membership = "MyGroups" in served or "Groups" in served

if body is None:
    print(f"  {YELLOW}WARN{OFF}  {'privilege resolution':<34} response was not JSON")
    warned = True
elif gated & served:
    print(f"  {GREEN}PASS{OFF}  {'privilege resolution':<34} "
          f"{len(gated & served)} field-data entities served")
elif membership:
    print(f"  {YELLOW}WARN{OFF}  {'privilege resolution':<34} no field-data entities yet, but "
          "group membership resolved (MyGroups is served). Expected on an organisation with no "
          "data loaded — entities with no rows are filtered out whatever the privileges say. "
          "Re-check after the dataset loads; only then does an absence mean anything")
    warned = True
else:
    print(f"  {RED}FAIL{OFF}  {'privilege resolution':<34} no field-data entities and no "
          "MyGroups. The user is in no group carrying has_all_privileges — a run would go green "
          "and measure reference data only (G5)")
    failed = True

if body is not None:
    table = json.load(open(sys.argv[1] + "/src/gatling/resources/avni-entities.json"))
    wanted = {e["entityName"] for e in table["entities"] if e["pullRequired"]}
    missing = sorted(wanted - served)
    if missing:
        # Not necessarily a defect: an entity with no rows is filtered out of the response, so on
        # an empty organisation most of the table is legitimately absent.
        # **`gated & served` was the wrong discriminator and withheld the note exactly where it
        # was needed.** `Encounter` is keyed on encounter type rather than on `subjectTypeUuid`, so
        # it never applies the registration-location filter and is served by an organisation
        # holding no rows at all. That made `gated & served` non-empty for an empty organisation,
        # the explanation was suppressed, and a bare "47 absent" read as a broken scope -- a
        # config-only organisation in exactly the state case 1 wants, diagnosed on 5 Oct 2026 as a
        # regression of the 30 Sep scope bug.
        # `not (scoped & served)`, not `scoped - served`: the note is about an *ambiguous*
        # response, and one scoped entity being served resolves the ambiguity on its own -- the
        # intersection cannot be empty if Individual came back. The first version of this fired on
        # a populated organisation too, where it reads as a warning about a scope that is visibly
        # fine.
        scoped = {"Individual", "ProgramEnrolment", "ProgramEncounter"}
        if not (scoped & served) and "Encounter" in served:
            note = ("— Individual, ProgramEnrolment and ProgramEncounter are keyed by "
                    "subjectTypeUuid and are dropped both when the catchment's scope intersection "
                    "is empty and when the organisation simply holds no subjects. Encounter is "
                    "keyed on encounter type, never applies that filter, and is served either "
                    "way, so its presence does not tell the two apart. Load one subject at a "
                    "permitted address level and re-check: if Individual appears, the scope was "
                    "always fine and the organisation was empty")
        elif not (gated & served):
            note = ("— expected while the organisation has no data; it means something only "
                    "after a dataset is loaded")
        else:
            note = ""
        print(f"  {YELLOW}WARN{OFF}  {'entity coverage':<34} {len(served)} served, {len(missing)} "
              f"the simulation pulls are absent {note}")
        warned = True
    else:
        print(f"  {GREEN}PASS{OFF}  {'entity coverage':<34} all {len(wanted)} pulled entities served")

# The shell reads this to decide whether the environment is ready. Without an explicit exit the
# script printed FAIL and then reported "0 failed".
sys.exit(1 if failed else 2 if warned else 0)
PY
  case $? in
    0) PASS=$((PASS+2)) ;;
    1) FAIL=$((FAIL+1)); WARN=$((WARN+1)) ;;
    2) WARN=$((WARN+1)); PASS=$((PASS+1)) ;;
  esac
  rm -f "$BODY_FILE"
else
  skip "privilege resolution" "needs syncDetails"
  skip "entity coverage" "needs syncDetails"
fi

fi

# ---------------------------------------------------------------- database
echo
echo "Database"
SQL="select current_setting('server_version') as version,
       (select count(*) from pg_extension where extname='pg_stat_statements') as pg_stat_statements,
       current_setting('log_min_duration_statement') as slow_query_log,
       current_setting('autovacuum') as autovacuum;"
if [ -n "$DB" ]; then
  if OUT=$(psql "$DB" -At -F'|' -c "$SQL" 2>&1); then
    ok "database reachable" "$OUT"
  else
    bad "database reachable" "$(printf '%s' "$OUT" | head -1)"
  fi
else
  skip "database checks" "not run — pass --db <conninfo>, or run the SQL below yourself"
  printf '\n%s\n\n' "$SQL" | sed 's/^/      /'
  echo "      Also confirm from the AWS console, since SQL cannot see them:"
  echo "        - storage autoscaling is OFF and the volume is not on burst credits"
  echo "        - the parameter group matches production's, autovacuum settings included"
  echo "        - a manual snapshot exists and survives a tofu destroy"
fi

# ---------------------------------------------------------------- waf
# Last, and opt-in, because it deliberately generates enough traffic to trip a rate rule — and if
# the injector turns out not to be exempted, everything after it would be blocked for the rest of
# the window and report nonsense.
echo
echo "WAF"
if [ -z "$WAF" ]; then
  skip "injector exempt from rate rule" "not run — pass --waf"
  echo
  echo "      Worth running once from the machine that will drive the load. \`avni-infra\`"
  echo "      measured production's rate rule at 550 requests per five minutes, about 1.8 a"
  echo "      second. A load run is far above that, so an un-exempted injector is throttled and"
  echo "      **Gatling reports the WAF's 403s as the server failing**. That is a corrupted run"
  echo "      that looks like a finding."
else
  printf '  ....  %-34s firing %s requests...' "injector exempt from rate rule" "$WAF_N" >&2
  BLOCKED=0; SENT=0
  for _ in $(seq 1 "$WAF_N"); do
    C=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$URL/ping" 2>/dev/null)
    SENT=$((SENT+1))
    [ "$C" = "403" ] && BLOCKED=$((BLOCKED+1))
  done
  printf '\r%*s\r' 80 '' >&2
  if [ "$BLOCKED" -eq 0 ]; then
    ok "injector exempt from rate rule" "$SENT requests, none blocked"
  else
    bad "injector exempt from rate rule" \
        "$BLOCKED of $SENT returned 403 — this injector is NOT exempted. A load run will be throttled and Gatling will read it as the server failing. Exempt it by scope-down statement, never by an allow rule, which would terminate evaluation and skip the rest of the rules production pays for"
  fi
fi

# ---------------------------------------------------------------- verdict
echo
printf 'Result: %d passed, %d failed, %d warnings\n' "$PASS" "$FAIL" "$WARN"
if [ "$FAIL" -gt 0 ]; then
  echo "Not ready. Fix the failures above before spending an environment window on a run."
  exit 1
fi
[ "$WARN" -gt 0 ] && echo "Ready, with warnings worth reading."
exit 0
