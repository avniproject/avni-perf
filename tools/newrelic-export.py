"""Back up New Relic event data before retention deletes it.

    export NEW_RELIC_API_KEY=NRAK-...
    python3 tools/newrelic-export.py --account 8563864 --out nr-backup
    python3 tools/newrelic-export.py --account 8563864 --out nr-backup --s3

**`Transaction` events are retained for 8 days and the boundary slides by the minute.** Everything
this suite reads per request -- `databaseDuration`, `databaseCallCount`, `name`, `duration` -- lives
only there, and once an hour falls off nothing can bring it back: the environment that produced it
has been destroyed, so the run cannot be repeated. `Metric` timeslices survive far longer and are
how cases 1 and 2 remain readable at all, but they carry no per-request detail.

So this exists to turn a perishable window into a file. Run it at least weekly; after every run is
better, because an hour lost is lost for the length of the exercise.

**The count guard is the point, not the download.** NRQL caps a raw event query at 5,000 rows and
says nothing when it truncates -- a silent prefix, exactly the failure mode the feeders had. Every
window here is counted first, exported second, and the two are asserted equal; a window over the
cap is bisected until each piece fits, and the children must sum to the parent. A window that
cannot be split far enough is recorded as a shortfall and the exit code is non-zero. Nothing is
reported as backed up on the strength of a query that returned.

Output is one gzipped JSONL file per event type per UTC hour, which makes the export resumable
(an hour already complete in the manifest is skipped), incremental (tomorrow's run writes only new
hours) and sliceable by run, since every event carries `timestamp` and run windows are in
`run-log.md`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# NRQL returns at most this many rows for a non-aggregate query, and truncates in silence.
ROW_CAP = 5000

# The account's own billing, metadata and audit streams are not measurements of the server under
# test; Entity/EntityRelationship describe the monitoring, not the run.
DEFAULT_EVENT_TYPES = [
    "Transaction",        # per-request detail -- the perishable one, and the reason for this tool
    "TransactionError",   # the 0.54% that failed in 12a
    "TransactionTrace",   # whole-trace breakdowns, only cut above apdex_f
    "SqlTrace",           # slow statements, which is where scopeBasedSyncService shows up
    "ErrorTrace",
    "Metric",             # timeslices: longer retention, and all that remains of cases 1 and 2
]

ENDPOINTS = {"us": "https://api.newrelic.com/graphql", "eu": "https://api.eu.newrelic.com/graphql"}


class Nrql:
    def __init__(self, key: str, account: int, region: str, verbose: bool = False):
        self.key, self.account, self.url, self.verbose = key, account, ENDPOINTS[region], verbose
        self.queries = 0

    def __call__(self, nrql: str, attempts: int = 4):
        gql = ("{actor{account(id:%d){nrql(query:%s,timeout:120){results}}}}"
               % (self.account, json.dumps(nrql)))
        body = json.dumps({"query": gql}).encode()
        for attempt in range(attempts):
            req = urllib.request.Request(
                self.url, body, {"Content-Type": "application/json", "Api-Key": self.key})
            try:
                payload = json.load(urllib.request.urlopen(req, timeout=180))
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                # 401/403 are the key, not the network; retrying them just burns the rate limit.
                if isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403):
                    raise SystemExit(f"{exc.code} from New Relic -- check NEW_RELIC_API_KEY is a "
                                     f"user key (NRAK-) and --region {('eu', 'us')} is right")
                if attempt == attempts - 1:
                    raise
                time.sleep(2 ** attempt)
                continue
            self.queries += 1
            if "errors" in payload:
                raise SystemExit("NRQL error: " + json.dumps(payload["errors"])[:500])
            return payload["data"]["actor"]["account"]["nrql"]["results"]
        raise AssertionError("unreachable")


def window(since_ms: int, until_ms: int) -> str:
    return f"SINCE {since_ms} UNTIL {until_ms}"


def count(q: Nrql, event_type: str, a: int, b: int) -> int:
    return int(q(f"SELECT count(*) FROM {event_type} {window(a, b)}")[0]["count"])


def fetch(q: Nrql, event_type: str, a: int, b: int, expected: int, shortfalls: list) -> list:
    """Every event in [a, b), or a recorded shortfall -- never a silent prefix."""
    if expected == 0:
        return []
    if expected <= ROW_CAP:
        rows = q(f"SELECT * FROM {event_type} {window(a, b)} LIMIT MAX")
        if len(rows) != expected:
            shortfalls.append({"eventType": event_type, "since": a, "until": b,
                               "expected": expected, "got": len(rows),
                               "why": "query returned fewer rows than count(*)"})
        return rows
    if b - a <= 1:
        # Cannot narrow further: more than ROW_CAP events share one millisecond.
        shortfalls.append({"eventType": event_type, "since": a, "until": b,
                           "expected": expected, "got": ROW_CAP,
                           "why": f"{expected} events in a single millisecond, above the "
                                  f"{ROW_CAP}-row cap, and the window cannot be split"})
        return q(f"SELECT * FROM {event_type} {window(a, b)} LIMIT MAX")
    mid = a + (b - a) // 2
    left, right = count(q, event_type, a, mid), count(q, event_type, mid, b)
    if left + right != expected:
        # The halves must account for the parent, or SINCE/UNTIL is not the half-open interval
        # this walk assumes and events are falling between the two.
        shortfalls.append({"eventType": event_type, "since": a, "until": b,
                           "expected": expected, "got": left + right,
                           "why": "bisection lost events at the boundary"})
    return (fetch(q, event_type, a, mid, left, shortfalls)
            + fetch(q, event_type, mid, b, right, shortfalls))


def hours(a: dt.datetime, b: dt.datetime):
    h = a.replace(minute=0, second=0, microsecond=0)
    while h < b:
        yield h, h + dt.timedelta(hours=1)
        h += dt.timedelta(hours=1)


def ms(t: dt.datetime) -> int:
    return int(t.replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def write(path: Path, rows: list) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    tmp = path.with_suffix(path.suffix + ".partial")
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        for row in rows:
            line = json.dumps(row, sort_keys=True, separators=(",", ":"))
            digest.update(line.encode() + b"\n")
            fh.write(line + "\n")
    tmp.replace(path)          # never leave a half-written hour looking complete
    return digest.hexdigest()


def export(q: Nrql, out: Path, event_types: list, since: dt.datetime, until: dt.datetime,
           force: bool) -> dict:
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"hours": {}}
    done, shortfalls, totals = manifest["hours"], [], {}

    for event_type in event_types:
        available = q(f"SELECT earliest(timestamp) FROM {event_type} SINCE 90 days ago")
        earliest = available[0].get("earliest.timestamp") if available else None
        if not earliest:
            print(f"  {event_type}: nothing retained", file=sys.stderr)
            continue
        start = max(since, dt.datetime.utcfromtimestamp(earliest / 1000))
        kept = dt.datetime.utcnow() - start
        print(f"  {event_type}: retained from {start:%Y-%m-%d %H:%M}Z "
              f"({kept.days}d {kept.seconds // 3600}h)", file=sys.stderr)
        n_total = 0
        for a, b in hours(start, until):
            key = f"{event_type}/{a:%Y-%m-%d}/{a:%H}"
            path = out / event_type / f"{a:%Y-%m-%d}" / f"{a:%H}.jsonl.gz"
            if not force and key in done and done[key]["expected"] == done[key]["written"] \
                    and path.exists():
                n_total += done[key]["written"]
                continue
            expected = count(q, event_type, ms(a), ms(b))
            if expected == 0:
                done[key] = {"expected": 0, "written": 0, "sha256": None}
                continue
            rows = fetch(q, event_type, ms(a), ms(b), expected, shortfalls)
            done[key] = {"expected": expected, "written": len(rows),
                         "sha256": write(path, rows), "bytes": path.stat().st_size}
            n_total += len(rows)
            print(f"    {a:%Y-%m-%d %H}Z  {len(rows):>7,} events", file=sys.stderr)
        totals[event_type] = n_total

    manifest.update({
        "account": q.account, "exportedAt": dt.datetime.utcnow().isoformat() + "Z",
        "totals": totals, "shortfalls": shortfalls, "hours": done,
    })
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))
    return manifest


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--account", type=int, required=True)
    p.add_argument("--region", default="eu", choices=sorted(ENDPOINTS))
    p.add_argument("--out", default="nr-backup", help="local directory (gitignored)")
    p.add_argument("--event-types", default=",".join(DEFAULT_EVENT_TYPES))
    p.add_argument("--since", help="UTC YYYY-MM-DD; default is everything still retained")
    p.add_argument("--until", help="UTC YYYY-MM-DD; default is now")
    p.add_argument("--force", action="store_true", help="re-export hours already complete")
    p.add_argument("--s3", action="store_true", help="sync --out to the artefacts bucket after")
    p.add_argument("--bucket", help="default: avni-loadtest-<aws account id>")
    p.add_argument("--prefix", default="newrelic")
    args = p.parse_args(argv)

    key = os.environ.get("NEW_RELIC_API_KEY", "")
    if not key.startswith("NRAK-"):
        print("set NEW_RELIC_API_KEY to a user key (NRAK-...). An ingest/query key (NRIQ-...) is "
              "not accepted by NerdGraph and returns 401.", file=sys.stderr)
        return 2

    since = (dt.datetime.strptime(args.since, "%Y-%m-%d") if args.since
             else dt.datetime.utcnow() - dt.timedelta(days=90))
    until = (dt.datetime.strptime(args.until, "%Y-%m-%d") if args.until else dt.datetime.utcnow())
    out = Path(args.out)

    q = Nrql(key, args.account, args.region)
    print(f"exporting to {out}/ from account {args.account} ({args.region})", file=sys.stderr)
    manifest = export(q, out, [t.strip() for t in args.event_types.split(",") if t.strip()],
                      since, until, args.force)

    print(f"\n{q.queries} queries", file=sys.stderr)
    for event_type, n in sorted(manifest["totals"].items()):
        print(f"  {event_type:<18} {n:>9,} events", file=sys.stderr)

    if manifest["shortfalls"]:
        print(f"\n{len(manifest['shortfalls'])} INCOMPLETE window(s) -- this backup has holes:",
              file=sys.stderr)
        for s in manifest["shortfalls"][:10]:
            print(f"  {s['eventType']} {s['since']}-{s['until']}: "
                  f"{s['got']}/{s['expected']} -- {s['why']}", file=sys.stderr)
        return 1

    if args.s3:
        bucket = args.bucket
        if not bucket:
            acct = subprocess.run(["aws", "sts", "get-caller-identity", "--query", "Account",
                                   "--output", "text"], capture_output=True, text=True).stdout.strip()
            bucket = f"avni-loadtest-{acct}"
        dest = f"s3://{bucket}/{args.prefix}/"
        print(f"\nsyncing to {dest}", file=sys.stderr)
        rc = subprocess.run(["aws", "s3", "sync", str(out), dest, "--only-show-errors"]).returncode
        if rc != 0:
            return rc
        print(f"done -- {dest}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
