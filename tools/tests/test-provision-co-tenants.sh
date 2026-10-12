#!/usr/bin/env bash
# Tests the resume and stop behaviour of provision-co-tenants.sh against a stub
# server and a stub provision-org.sh. No AWS, no avni-server, no database.
#
#   ./tools/tests/test-provision-co-tenants.sh
#
# The cases that matter are the ones about a tenant interrupted mid-import: it
# is present by name and short on content, and the cost of getting it wrong is a
# silent hole in a 513-organisation dataset that nothing downstream checks for.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SUT="$HERE/../provision-co-tenants.sh"
[ -f "$SUT" ] || { echo "no provision-co-tenants.sh next to the tests" >&2; exit 2; }

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  \033[32mok\033[0m    %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  \033[31mFAIL\033[0m  %s\n' "$1"; [ $# -gt 1 ] && printf '        %s\n' "$2"; }
is()   { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1" "expected [$3], got [$2]"; fi; }
has()  { if printf '%s' "$2" | grep -q "$3"; then ok "$1"; else bad "$1" "no /$3/ in: $(printf '%s' "$2" | tr '\n' ' ' | cut -c1-160)"; fi; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/cotenant-test.XXXXXX")
trap 'kill $SRV 2>/dev/null; rm -rf "$WORK"' EXIT

# ---------------------------------------------------------------- stub server
cat > "$WORK/server.py" <<'PY'
import json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
STATE = sys.argv[1]
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        st = json.load(open(STATE))
        if self.path.startswith("/organisation"):
            body = [] if st.get("blind") else [
                {"id": o["id"], "name": o["name"], "uuid": o["uuid"]} for o in st["orgs"]]
            if st.get("truncate"):      # drop the tail, as a paged response would
                body = body[: st["truncate"]]
            out = json.dumps(body).encode()
        elif self.path.startswith("/concept/search/lastModified"):
            u = self.headers.get("ORGANISATION-UUID", "")
            n = next((o["concepts"] for o in st["orgs"] if o["uuid"] == u), 0)
            out = json.dumps({"page": {"totalElements": n}}).encode()
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers(); self.wfile.write(out)
HTTPServer(("127.0.0.1", int(sys.argv[2])), H).serve_forever()
PY

# ------------------------------------------------------------ stub provisioner
mkdir -p "$WORK/tools"
cp "$SUT" "$WORK/tools/provision-co-tenants.sh"
cat > "$WORK/tools/provision-org.sh" <<'PY'
#!/usr/bin/env bash
# Stands in for the real one: sleeps (so a signal can arrive mid-import), then
# appends the organisation to the stub server's state with the bundle's own
# concept count -- or with STUB_SHORT of them, to stage a half-finished import.
set -uo pipefail
while [ $# -gt 0 ]; do
  case "$1" in
    --url) shift 2 ;; --bundle) B="$2"; shift 2 ;; --name) N="$2"; shift 2 ;;
    *) shift ;;
  esac
done
sleep "${STUB_SLEEP:-0}"
[ "${STUB_FAIL:-}" = "$N" ] && { echo "import blew up"; exit 1; }
python3 - "$STATE" "$N" "$B" "${STUB_SHORT:-}" <<'EOP'
import json, sys
state, name, bundle, short = sys.argv[1:5]
st = json.load(open(state))
want = len(json.load(open(bundle + "/concepts.json")))
st["orgs"].append({"id": 100 + len(st["orgs"]), "name": name,
                   "uuid": "u-" + name, "concepts": int(short) if short else want})
json.dump(st, open(state, "w"))
print("   created, id %d" % (99 + len(st["orgs"])))
EOP
echo "  ok    formMapping      7 in the organisation, 7 in the bundle"
PY
chmod +x "$WORK/tools/provision-org.sh"

# ------------------------------------------------------------------- fixtures
for a in alpha beta; do
  mkdir -p "$WORK/bundles/$a"
  python3 -c "import json,sys; json.dump([{'n':i} for i in range(int(sys.argv[2]))], open(sys.argv[1],'w'))" \
    "$WORK/bundles/$a/concepts.json" "$([ "$a" = alpha ] && echo 10 || echo 20)"
done
python3 - "$WORK/recipe.json" <<'PY'
import json, sys
json.dump({"tenants": [{"name": "co-%03d" % i,
                        "bundle_archetype": "alpha" if i % 2 else "beta"}
                       for i in range(1, 7)]}, open(sys.argv[1], "w"))
PY

PORT=$(python3 -c "import socket;s=socket.socket();s.bind(('127.0.0.1',0));print(s.getsockname()[1]);s.close()")
STATE="$WORK/state.json"; export STATE
echo '{"orgs":[]}' > "$STATE"
python3 "$WORK/server.py" "$STATE" "$PORT" & SRV=$!
disown $SRV 2>/dev/null || true   # else the shell announces "Terminated" over the summary
for _ in $(seq 1 50); do curl -s "http://127.0.0.1:$PORT/organisation" >/dev/null 2>&1 && break; sleep 0.1; done

cd "$WORK"
run() { ./tools/provision-co-tenants.sh --url "http://127.0.0.1:$PORT" --recipe recipe.json \
          --bundle-root "$WORK/bundles" --log "$WORK/log.tsv" "$@" 2>&1; }
reset_state() { echo '{"orgs":[{"id":1,"name":"seed","uuid":"u-seed","concepts":1}]}' > "$STATE"; rm -f "$WORK"/log.tsv*; }

echo "provision-co-tenants.sh"

# 1 -------------------------------------------------- the happy path still works
reset_state
OUT=$(run); RC=$?
is  "provisions every tenant in the recipe"            "$(awk 'NR>1' log.tsv | wc -l | tr -d ' ')" "6"
is  "exits 0 when nothing failed"                      "$RC" "0"
is  "leaves no in-flight marker behind"                "$([ -e log.tsv.inflight ] && echo yes || echo no)" "no"
is  "removes its pidfile on exit"                      "$([ -e log.tsv.pid ] && echo yes || echo no)" "no"

# 2 ------------------------------------------- a second pass skips what is complete
OUT=$(run)
has "skips organisations already complete"             "$OUT" "skipping co-001"
is  "adds no duplicate rows"                           "$(awk 'NR>1' log.tsv | wc -l | tr -d ' ')" "6"
has "reports provisioned 0"                            "$OUT" "provisioned 0, skipped 6"

# 3 ------------------------------- a half-imported organisation is NOT skipped
reset_state
STUB_SHORT=3 run --limit 1 >/dev/null 2>&1      # co-001 lands with 3 of alpha's 10
rm -f log.tsv.inflight                           # the marker would catch it first; this tests the guard alone
OUT=$(run); RC=$?
is  "stops rather than skip a short organisation"      "$RC" "5"
has "names the organisation and both counts"           "$OUT" "co-001 is on the server carrying 3 of the bundle's 10"
is  "provisions nothing on that pass"                  "$(awk 'NR>1 && $1!="co-001"' log.tsv | wc -l | tr -d ' ')" "0"

# 4 ---------------------------------- an interrupted pass is refused, not resumed
reset_state
printf 'co-004\talpha\t2026-10-12T00:00:00Z\n' > log.tsv.inflight
OUT=$(run); RC=$?
is  "refuses to start with a marker present"           "$RC" "4"
has "names the interrupted tenant"                     "$OUT" "interrupted while provisioning co-004"
has "says how to clear it"                             "$OUT" "delete .*inflight and re-run"
rm -f log.tsv.inflight
OUT=$(run); RC=$?
is  "runs once the marker is cleared"                  "$RC" "0"

# 5 ------------------------------- SIGTERM finishes the tenant in hand, then stops
reset_state
STUB_SLEEP=2 run >"$WORK/slow.log" 2>&1 &
LOOP=$!
for _ in $(seq 1 50); do [ -s log.tsv.pid ] && break; sleep 0.1; done
sleep 2.5                                        # inside the second tenant's import
kill -TERM "$(cat log.tsv.pid)" 2>/dev/null
wait $LOOP; RC=$?
OUT=$(cat "$WORK/slow.log")
is  "exits 0 on a requested stop"                      "$RC" "0"
has "says it is finishing the tenant in hand"          "$OUT" "finishing the tenant in hand"
has "reports where it stopped"                         "$OUT" "stopped after co-00.*between tenants"
is  "leaves no in-flight marker"                       "$([ -e log.tsv.inflight ] && echo yes || echo no)" "no"
is  "stopped short of the whole recipe"                "$(awk 'NR>1' log.tsv | wc -l | tr -d ' ')" "2"
is  "every row it wrote is ok"                         "$(awk -F'\t' 'NR>1 && $5!="ok"' log.tsv | wc -l | tr -d ' ')" "0"
OUT=$(run)
has "the stopped run resumes cleanly"                  "$OUT" "provisioned 4, skipped 2"

# 6 --------------------------- a hard kill leaves the marker the next run catches
reset_state
STUB_SLEEP=5 run >/dev/null 2>&1 &
LOOP=$!
for _ in $(seq 1 50); do [ -s log.tsv.pid ] && break; sleep 0.1; done
sleep 1
kill -9 "$(cat log.tsv.pid)" 2>/dev/null; wait $LOOP 2>/dev/null
is  "a hard kill leaves the marker"                    "$([ -e log.tsv.inflight ] && echo yes || echo no)" "yes"
is  "the marker names the tenant in flight"            "$(cut -f1 log.tsv.inflight)" "co-001"
rm -f log.tsv.pid

# 7 ------------------------------------- the original duplicate guards still hold
reset_state
python3 -c "
import json,sys
st=json.load(open('$STATE')); st['blind']=True; json.dump(st,open('$STATE','w'))"
rm -f log.tsv.inflight
OUT=$(run); RC=$?
is  "still aborts when the list comes back empty"      "$RC" "3"
has "still says the guard is blind"                    "$OUT" "resume guard is blind"

# 8 ------------------------------------ a failed import is logged and not fatal
reset_state
OUT=$(STUB_FAIL=co-003 run); RC=$?
is  "keeps going past a failed tenant"                 "$(awk -F'\t' 'NR>1 && $5=="ok"' log.tsv | wc -l | tr -d ' ')" "5"
is  "records the failure"                              "$(awk -F'\t' 'NR>1 && $5=="FAILED"{print $1}' log.tsv)" "co-003"
is  "exits non-zero when something failed"             "$RC" "1"
is  "clears the marker even on failure"                "$([ -e log.tsv.inflight ] && echo yes || echo no)" "no"

echo
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
