"""Rank production's organisations by the load they put on the server, from AuthenticationFilter.

    python3 tools/org_load.py out.json     # reads /tmp/prod-logs/*.gz

Feeds `CoTenantLoad`'s measured concentration: 110 organisations make a device sync request in
eleven days, rank 1 holds 16% of them and the top 16 hold 84%.

Three separate questions, because an organisation can be large in one and absent in another:
  - how many requests it makes          (connection and dispatch pressure)
  - how much server time it consumes    (CPU and IO pressure)
  - how much of that is *device sync*   (what a co-tenant load is supposed to reproduce)

The last one is why this is not just a request count. An organisation whose traffic is
`executeQuery` or `/api/*` is an integration, not a fleet, and modelling it as co-tenant sync
load would reproduce contention that does not exist in that shape.
"""
import gzip, json, re, sys, glob
from collections import defaultdict

LINE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[.,]\d{3})"
    r".*?(?P<method>GET|POST|PUT|PATCH|DELETE)\s+(?P<uri>/\S*?)"
    r"(?:\?(?P<query>\S*))?\s+Status:\s*(?P<status>\d+)"
    r"\s+User:\s*(?P<user>\S+)"
    r".*?Time:\s*(?P<ms>\d+)\s*ms")

ents = json.load(open("src/gatling/resources/avni-entities.json"))
ents = ents if isinstance(ents, list) else ents.get("entities", ents)
SYNC_PATHS, PUSH_PATHS = set(), set()
for e in ents:
    for k in ("path", "slicePath"):
        if e.get(k):
            SYNC_PATHS.add(e[k].strip("/").lower())
    if e.get("pushPath"):
        PUSH_PATHS.add(e["pushPath"].strip("/").lower())

def classify(uri):
    p = uri.strip("/").lower()
    if p.startswith("api/"):      return "api"
    if p in ("syncdetails",):     return "syncDetails"
    if p in SYNC_PATHS:           return "pull"
    if p in PUSH_PATHS:           return "push"
    if p.startswith("executequery") or p.startswith("etl"): return "report"
    if p.startswith("media") or p.startswith("s3"):         return "media"
    return "other"

req   = defaultdict(int)
ms    = defaultdict(int)
users = defaultdict(set)
kind  = defaultdict(lambda: defaultdict(int))
kindms= defaultdict(lambda: defaultdict(int))
unparsed = 0; candidates = 0; total = 0

for path in sorted(glob.glob("/tmp/prod-logs/*.gz")):
    with gzip.open(path, "rt", errors="replace") as fh:
        for line in fh:
            if "Status:" not in line or "User:" not in line:
                continue
            candidates += 1
            m = LINE.match(line)
            if not m:
                unparsed += 1
                continue
            total += 1
            user = m.group("user")
            org = user.rsplit("@", 1)[1] if "@" in user else "(none)"
            k = classify(m.group("uri"))
            t = int(m.group("ms"))
            req[org] += 1; ms[org] += t; users[org].add(user)
            kind[org][k] += 1; kindms[org][k] += t

json.dump({"req": dict(req), "ms": dict(ms),
           "users": {k: len(v) for k, v in users.items()},
           "kind": {k: dict(v) for k, v in kind.items()},
           "kindms": {k: dict(v) for k, v in kindms.items()},
           "totals": {"parsed": total, "candidates": candidates, "unparsed": unparsed}},
          open(sys.argv[1], "w"))
print(f"parsed {total:,} of {candidates:,} candidate lines; {unparsed:,} unparsed "
      f"({unparsed/max(candidates,1):.1%})")
