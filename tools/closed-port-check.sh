#!/usr/bin/env bash
#
# D8.5 regression check: point the simulation at a port with nothing behind it and require that
# it fails fast and quietly.
#
# This exists because the defect it guards against was invisible to review and to every ordinary
# run. Both paged loops cleared their continue-flag only from a check on a 200, so any failure
# left the flag set and the virtual user reissued the same page forever. A one-user smoke run
# against a closed port produced 23,084,907 log lines and 1.4 GB in about two minutes, with no
# error, no assertion and no termination.
#
# The server misbehaving is not an edge case here - cases 9 and 10 exist to produce exactly that
# state - so the simulation's behaviour when requests fail is a property worth testing.
#
# Three assertions, in order of how much they would catch:
#   1. The run terminates. This is the one that catches a spin, and it catches it whatever the
#      log level happens to be.
#   2. The request count stays small. A spin issues millions; a correct run issues a handful.
#   3. The build fails. A green run against a closed port would mean the assertions are not
#      wired up, which is its own defect.

set -uo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-9}"
DEADLINE_SECONDS="${DEADLINE_SECONDS:-300}"
MAX_REQUESTS="${MAX_REQUESTS:-100}"
# GNU mktemp requires the XXXXXX; BSD does not. Without it this works on a developer's Mac
# and fails on the CI runner, which is the one place it has to work unattended.
LOG="$(mktemp "${TMPDIR:-/tmp}/closed-port-check.XXXXXX")"
trap 'rm -f "$LOG"' EXIT

# A port with something behind it would make this test pass for the wrong reason. Uses bash's
# own /dev/tcp rather than nc, so a runner without netcat cannot silently skip the guard.
if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
  echo "FAIL: something is listening on 127.0.0.1:$PORT, so this check would not be testing"
  echo "      the closed-port path. Set PORT to a free port and re-run."
  exit 1
fi

echo "Running the smoke profile against 127.0.0.1:$PORT (nothing listening)..."
./gradlew gatlingRun --simulation=org.avni.AvniSyncSimulation -q \
  -DBASE_URL="http://127.0.0.1:$PORT" -DPROFILE=smoke -DINJECTOR=closed-port-check \
  > "$LOG" 2>&1 &
GRADLE_PID=$!

# No `timeout` on macOS, so poll. The deadline is the assertion, not a convenience.
elapsed=0
while kill -0 "$GRADLE_PID" 2>/dev/null; do
  if [ "$elapsed" -ge "$DEADLINE_SECONDS" ]; then
    kill -9 "$GRADLE_PID" 2>/dev/null
    wait "$GRADLE_PID" 2>/dev/null
    echo "FAIL: still running after ${DEADLINE_SECONDS}s against a closed port."
    echo "      A failed page is being retried instead of ending the sync (D8.5)."
    echo "      Check that both paged loops still carry .exitHereIfFailed()."
    echo "      Log grew to $(wc -l < "$LOG" | tr -d ' ') lines."
    exit 1
  fi
  sleep 2
  elapsed=$((elapsed + 2))
done
wait "$GRADLE_PID"; EXIT_CODE=$?

REQUESTS=$(awk -F'|' '/^> request count/ {gsub(/ /,"",$2); print $2; exit}' "$LOG")

if [ -z "$REQUESTS" ]; then
  echo "FAIL: no request count in the Gatling summary - the run did not get far enough to"
  echo "      report. This check cannot tell a fast failure from a broken build; look at the log."
  tail -30 "$LOG"
  exit 1
fi

if [ "$REQUESTS" -gt "$MAX_REQUESTS" ]; then
  echo "FAIL: $REQUESTS requests against a closed port, ceiling is $MAX_REQUESTS."
  echo "      A failed page is being retried rather than ending the sync (D8.5)."
  exit 1
fi

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "FAIL: the build passed against a closed port, so every request failed and no assertion"
  echo "      fired. Check MAX_FAILED_PERCENT is still applied to this profile."
  exit 1
fi

echo "PASS: failed in ${elapsed}s after $REQUESTS requests, build exit $EXIT_CODE,"
echo "      log $(wc -l < "$LOG" | tr -d ' ') lines."
