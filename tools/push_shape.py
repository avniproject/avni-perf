"""Per-entity push volumes from production's own logs, to PushVolume's contract.

    python3 tools/push_shape.py            # reads /tmp/prod-logs/*.gz

**Why this exists beside Q17.** Q17 measured the same thing from `sync_telemetry`, which is the
client's report of what it pushed. This counts `POST` requests in `AuthenticationFilter`'s log,
which is what the server actually handled -- a retried push is one record and two requests, and the
server pays for both. The simulation issues one request per record, so for a load test the
server-side count is the one that reproduces the work.

It gets a larger answer: 11.2 records a sync against Q17's 6.5, with every entity's probability and
conditional mean up by 1.4 to 1.7x. `PushProfiles.coTenant()` carries the result; `production()`
keeps Q17's, which is what the customer profile borrows for registrations and enrolments.

**A sync is reconstructed from the log** by grouping a user's requests with a ten-minute gap. Avni's
client syncs entities in sequence, so a gap that size is a session boundary rather than an arbitrary
cut -- production's median sync is 14.1 s end to end.
"""
import gzip, json, re, sys, glob, statistics
from collections import defaultdict
from datetime import datetime, timedelta
sys.path.insert(0, "tools")
import inter_request_gap as irg

ents = json.load(open("src/gatling/resources/avni-entities.json"))
ents = ents if isinstance(ents, list) else ents.get("entities", ents)
PULL = {e[k].strip("/").lower() for e in ents for k in ("path","slicePath") if e.get(k)}
PUSH = {e["pushPath"].strip("/").lower(): e["entityName"] for e in ents if e.get("pushPath")}
WANT = {"Individual", "ProgramEnrolment", "ProgramEncounter", "Encounter"}
GAP = timedelta(minutes=10)

by_user = defaultdict(list)
for path in sorted(glob.glob("/tmp/prod-logs/*.gz")):
    with gzip.open(path, "rt", errors="replace") as fh:
        for line in fh:
            if "Status:" not in line or "User:" not in line: continue
            m = irg.LINE.match(line)
            if not m: continue
            p = m.group("uri").strip("/").lower()
            ent = PUSH.get(p)
            k = "pull" if p in PULL else ("push" if ent else None)
            if k is None: continue
            ts = datetime.strptime(m.group("ts").replace(",",".").replace("T"," ")[:23],
                                   "%Y-%m-%d %H:%M:%S.%f")
            by_user[m.group("user")].append((ts, k, ent))

per_entity = defaultdict(list)   # entity -> count in each sync (0 included)
syncs = 0
for u, rs in by_user.items():
    rs.sort(key=lambda r: r[0])
    cur = defaultdict(int); last = None; any_req = False
    def flush():
        global syncs
        if not any_req: return
        syncs += 1
        for e in WANT: per_entity[e].append(cur.get(e, 0))
    for ts, k, ent in rs + [(None, None, None)]:
        if last is not None and (ts is None or ts - last > GAP):
            flush(); cur = defaultdict(int); any_req = False
        if ts is None: break
        if ent: cur[ent] += 1
        any_req = True; last = ts
    # trailing session handled by the sentinel

print(f"{syncs:,} syncs\n")
print(f'{"entity":18s} {"prob":>6s} {"min":>4s} {"p50":>5s} {"p95":>5s} {"max":>6s} {"mean":>6s}')
tot = 0.0
for e in ("Individual","ProgramEnrolment","ProgramEncounter","Encounter"):
    v = per_entity[e]; nz = sorted(x for x in v if x)
    if not nz:
        print(f"{e:18s} {'0':>6s}   --    --    --     --     --"); continue
    prob = len(nz)/len(v)
    mean = sum(nz)/len(nz)
    tot += prob*mean
    print(f"{e:18s} {prob:6.4f} {nz[0]:4d} {statistics.median(nz):5.0f} "
          f"{nz[int(len(nz)*.95)]:5d} {nz[-1]:6d} {mean:6.1f}")
print(f"\nrecords per sync, summed: {tot:.1f}   (current production profile: 6.5)")
