"""What one sync costs the application server in CPU seconds.

    export NEW_RELIC_API_KEY=NRAK-...
    python3 tools/cpu-per-sync.py --account 8563864           # refresh every run
    python3 tools/cpu-per-sync.py --account 8563864 --run case3
    python3 tools/cpu-per-sync.py --table                     # print the cache, no account needed

**CPU is the constraint; wall-clock is not.** Every saturated run names application CPU, with the
database at a fifth of its capacity. `serverMs` measures how long a request took, which conflates
work with queueing -- under load it inflates without any more work being done. CPU seconds measure
the work, and they are **additive**, which wall-clock is not:

    devices an hour = available CPU seconds per hour / CPU seconds per sync

That is the arithmetic capacity planning needs, and nothing else in this repository produces it.

`apm.service.cpu.usertime` is absolute CPU seconds, not a percentage. It cross-checks against the
utilisation series exactly: 702.42 s over case4-span20 against 2.43% x 2 vCPU x 14,400 s = 700.

**This is an attribution, not a measurement.** It is whole-server CPU over a run's window divided
by the syncs in it, so it carries the health checks, the background jobs and anything else on the
box. On a dedicated load-test server during a run that is mostly the run. It also spans the ramp
and the tail, where CPU is low and syncs still count, so it reads slightly low.

**There is no per-sync CPU, so a distribution needs a weight.** The metric is whole-server. To
report percentiles the way the run log does for duration, this spreads a run's CPU across its syncs
in proportion to **`serverMs`** -- the only per-sync measure of server work that is recorded, being
the sum of that sync's response times. A sync that asked the server for twice as much is charged
twice as much.

**That weighting is sound while the server is healthy and not while it is saturated**, because
`serverMs` then carries queueing that is not CPU, and a sync that happened to queue is
over-charged. On a saturated run read the run-level `cpuPerSync` and ignore the percentiles. Where
`serverMs` is missing the weight falls back to `records`.

**Full and incremental are reported separately**, as the run log does for duration, because they
are different sizes of work: an incremental sync pulls 69% of what a full one pulls.

**Mixed-cohort runs are split rather than skipped.** A co-tenant sync is far smaller than a
customer one, so a mean across both is meaningless -- case 7 reads 2.01 against case 6's 3.85 only
because 1,584 of its 1,864 syncs are co-tenants. `sync-durations.csv` carries `userName`, and
co-tenant users are prefixed `co-`, so **`cpuPerCustomerSync` charges all the CPU to the customer
syncs alone**. That is the number capacity planning wants: what one customer sync costs on a
server that is also carrying production's other tenants.

The cache at `docs/cpu-per-sync.json` is committed so the run log can be regenerated without New
Relic access or a key.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import importlib.util
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "docs/cpu-per-sync.json"
ENDPOINTS = {"us": "https://api.newrelic.com/graphql", "eu": "https://api.eu.newrelic.com/graphql"}

_spec = importlib.util.spec_from_file_location("nq", ROOT / "tools/newrelic-query.py")
nq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nq)


def nrql(key: str, account: int, region: str, query: str):
    gql = ('{actor{account(id:%d){nrql(query:%s,timeout:120){results}}}}'
           % (account, json.dumps(query)))
    req = urllib.request.Request(ENDPOINTS[region], json.dumps({"query": gql}).encode(),
                                 {"Content-Type": "application/json", "Api-Key": key})
    payload = json.load(urllib.request.urlopen(req, timeout=180))
    if "errors" in payload:
        raise SystemExit("NRQL error: " + json.dumps(payload["errors"])[:400])
    return payload["data"]["actor"]["account"]["nrql"]["results"]


def percentile(values: list, p: float):
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, int(round((p / 100) * (len(s) - 1))))]


def summarise(cpus: list):
    if not cpus:
        return None
    return {"n": len(cpus),
            "mean": round(sum(cpus) / len(cpus), 2),
            "p50": round(percentile(cpus, 50), 2),
            "p95": round(percentile(cpus, 95), 2)}


def read_syncs(run_id: str, artefacts: Path | None):
    """One row per completed sync, or None if the artefacts are not here."""
    if not artefacts:
        return None
    paths = glob.glob(str(artefacts / run_id / "sync-durations.csv"))
    if not paths:
        return None
    rows = []
    with open(paths[0]) as fh:
        for row in csv.DictReader(fh):
            def num(key):
                try:
                    return float(row.get(key) or 0)
                except ValueError:
                    return 0.0
            rows.append({"user": row.get("userName") or "",
                         "records": num("records"),
                         "serverMs": num("serverMs"),
                         "full": str(row.get("fullSync", "")).strip().lower() == "true"})
    return rows


def distribute(cpu_total: float, rows: list):
    """Spread the run's CPU across its syncs, weighted by serverMs (records as fallback)."""
    weights = [r["serverMs"] for r in rows]
    weight_key = "serverMs"
    if sum(weights) <= 0:
        weights = [r["records"] for r in rows]
        weight_key = "records"
    total = sum(weights)
    if total <= 0:
        return None
    for row, w in zip(rows, weights):
        row["cpu"] = cpu_total * w / total

    customer = [r for r in rows if not r["user"].startswith("co-")]
    out = {"weightedBy": weight_key,
           "all": summarise([r["cpu"] for r in rows]),
           "incremental": summarise([r["cpu"] for r in rows if not r["full"]]),
           "full": summarise([r["cpu"] for r in rows if r["full"]])}
    if len(customer) != len(rows):
        out["customer"] = summarise([r["cpu"] for r in customer])
        out["coTenant"] = summarise([r["cpu"] for r in rows if r["user"].startswith("co-")])
    return out


def syncs_from_run_log(run_id: str):
    """Fallback: the sync count the run log already prints. No cohort split available."""
    import re
    detail = (ROOT / "docs/run-log-detail.md").read_text()
    for block in detail.split("\n## ")[1:]:
        if block.split("\n")[0].strip().strip("`") != run_id:
            continue
        m = re.search(r"\((\d+) syncs\)", block)
        return int(m.group(1)) if m else None
    return None


# **App memory comes from New Relic and RDS from CloudWatch, because that is where each one
# is.** The app host has no CloudWatch agent, so EC2 publishes CPU and nothing else; the JVM's
# heap is only visible through the agent. RDS publishes both, plus the two numbers that say
# whether its memory was actually under pressure -- FreeableMemory and SwapUsage. Reporting
# "memory" without those is reporting a number nobody can act on.
APP_MEMORY_TIMESLICES = {
    "appHeapUsedMb": "Memory/Heap/Used",
    "appHeapCommittedMb": "Memory/Heap/Committed",
    "appHeapMaxMb": "Memory/Heap/Max",
    "appPhysicalMemMb": "Memory/Physical",
}


def app_memory(key, account, region, app, start, until):
    """Average and peak heap over the run window, in MB."""
    out = {}
    window = (f"SINCE '{start:%Y-%m-%d %H:%M:%S}+0000' "
              f"UNTIL '{until:%Y-%m-%d %H:%M:%S}+0000'")
    for field, timeslice in APP_MEMORY_TIMESLICES.items():
        rows = nrql(key, account, region,
                    f"SELECT average(newrelic.timeslice.value) AS avg, "
                    f"max(newrelic.timeslice.value) AS max FROM Metric "
                    f"WHERE appName='{app}' AND metricTimesliceName='{timeslice}' {window}")
        if rows and rows[0].get("avg") is not None:
            out[field] = round(rows[0]["avg"], 1)
            if field == "appHeapUsedMb" and rows[0].get("max") is not None:
                out["appHeapUsedMbMax"] = round(rows[0]["max"], 1)
    return out


def cloudwatch(namespace, metric, dim_name, dim_value, start, until, stat):
    """One CloudWatch statistic over the window. Shelling out to the CLI rather than taking a
    boto3 dependency, which is what the rest of this repository does."""
    import subprocess
    r = subprocess.run(
        ["aws", "cloudwatch", "get-metric-statistics", "--namespace", namespace,
         "--metric-name", metric, "--dimensions", f"Name={dim_name},Value={dim_value}",
         "--start-time", f"{start:%Y-%m-%dT%H:%M:%SZ}", "--end-time", f"{until:%Y-%m-%dT%H:%M:%SZ}",
         "--period", "300", "--statistics", stat,
         "--query", f"Datapoints[].{stat}", "--output", "text"],
        capture_output=True, text=True)
    vals = [float(v) for v in r.stdout.split() if v not in ("", "None")]
    if not vals:
        return None
    return max(vals) if stat == "Maximum" else sum(vals) / len(vals)


def infrastructure(app_instance, db_instance, start, until):
    """CPU and memory for both tiers. Absent metrics are omitted rather than reported as zero."""
    out = {}
    MB = 1024 * 1024
    pairs = [
        ("appCpuAvg", "AWS/EC2", "CPUUtilization", "InstanceId", app_instance, "Average", 1),
        ("appCpuMax", "AWS/EC2", "CPUUtilization", "InstanceId", app_instance, "Maximum", 1),
        ("rdsCpuAvg", "AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", db_instance, "Average", 1),
        ("rdsCpuMax", "AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", db_instance, "Maximum", 1),
        ("rdsFreeableMemMbMin", "AWS/RDS", "FreeableMemory", "DBInstanceIdentifier", db_instance, "Minimum", MB),
        ("rdsSwapMbMax", "AWS/RDS", "SwapUsage", "DBInstanceIdentifier", db_instance, "Maximum", MB),
    ]
    for field, ns, metric, dname, dvalue, stat, divisor in pairs:
        if not dvalue:
            continue
        v = cloudwatch(ns, metric, dname, dvalue, start, until, stat)
        if v is not None:
            out[field] = round(v / divisor, 1)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--account", type=int)
    p.add_argument("--region", default="eu", choices=sorted(ENDPOINTS))
    p.add_argument("--app", default="avni-loadtest")
    p.add_argument("--run", help="substring of a run id; default is every run")
    p.add_argument("--artefacts", help="directory of downloaded run artefacts, for the cohort "
                                       "split (each run a subdirectory with sync-durations.csv)")
    p.add_argument("--tail-min", type=int, default=20)
    p.add_argument("--app-instance", default=os.environ.get("AVNI_APP_INSTANCE", "i-044c88e15e8ea9e0f"),
                   help="EC2 instance id for app CPU; AVNI_APP_INSTANCE overrides")
    p.add_argument("--db-instance", default=os.environ.get("AVNI_DB_INSTANCE", "avni-loadtest"),
                   help="RDS identifier for database CPU and memory")
    p.add_argument("--no-infra", action="store_true",
                   help="skip the CloudWatch and heap lookups (New Relic CPU only)")
    p.add_argument("--table", action="store_true", help="print the cache and exit")
    args = p.parse_args(argv)

    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    if not args.table:
        key = os.environ.get("NEW_RELIC_API_KEY", "")
        if not key.startswith("NRAK-"):
            print("set NEW_RELIC_API_KEY to a user key (NRAK-...)", file=sys.stderr)
            return 2
        if not args.account:
            print("--account is required unless --table", file=sys.stderr)
            return 2
        artefacts = Path(args.artefacts) if args.artefacts else None

        runs = nq.runs()
        wanted = {r: v for r, v in runs.items() if not args.run or args.run.lower() in r.lower()}
        for run_id, (start, end, ceiling) in sorted(wanted.items(), key=lambda kv: kv[1][0]):
            until = min(end + dt.timedelta(minutes=args.tail_min), ceiling or dt.datetime.max)
            rows = nrql(key, args.account, args.region,
                        f"SELECT sum(apm.service.cpu.usertime) AS cpu FROM Metric "
                        f"WHERE appName='{args.app}' "
                        f"SINCE '{start:%Y-%m-%d %H:%M:%S}+0000' UNTIL '{until:%Y-%m-%d %H:%M:%S}+0000'")
            cpu = rows[0].get("cpu") if rows else None
            if not cpu:
                continue
            rows = read_syncs(run_id, artefacts)
            total = len(rows) if rows is not None else syncs_from_run_log(run_id)
            entry = {"window": [f"{start:%Y-%m-%dT%H:%M:%S}Z", f"{until:%Y-%m-%dT%H:%M:%S}Z"],
                     "cpuSeconds": round(cpu, 1), "syncs": total}
            if total:
                entry["cpuPerSync"] = round(cpu / total, 2)
            if rows:
                customer = [r for r in rows if not r["user"].startswith("co-")]
                entry["customerSyncs"] = len(customer)
                entry["coTenantSyncs"] = len(rows) - len(customer)
                if customer:
                    # All the CPU, charged to the customer syncs alone -- what one customer sync
                    # costs on a server also carrying production's other tenants.
                    entry["cpuPerCustomerSync"] = round(cpu / len(customer), 2)
                entry["distribution"] = distribute(cpu, rows)
            if not args.no_infra:
                entry.update(app_memory(key, args.account, args.region, args.app, start, until))
                entry.update(infrastructure(args.app_instance, args.db_instance, start, until))
            cache[run_id] = entry
            extra = ""
            if entry.get("appCpuAvg") is not None and entry.get("rdsCpuAvg") is not None:
                extra = (f"  app {entry['appCpuAvg']:.0f}%/rds {entry['rdsCpuAvg']:.0f}%"
                         f"  heap {entry.get('appHeapUsedMb', float('nan')):,.0f} MB")
            print(f"  {run_id}  {cpu:,.0f} CPU s{extra}", file=sys.stderr)
        CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n")
        print(f"\nwrote {CACHE.relative_to(ROOT)} ({len(cache)} runs)", file=sys.stderr)

    if not cache:
        return 1
    def cell(d, key):
        return "-" if not d else f"{d[key]:.2f}"

    print(f"\n{'run':<40} {'syncs':>6} {'CPU s':>8} {'/sync':>6} "
          f"{'incr p50':>9} {'incr p95':>9} {'full p50':>9} {'full p95':>9}")
    for run_id, e in sorted(cache.items()):
        d = e.get("distribution") or {}
        print(f"{run_id[:40]:<40} {e.get('syncs') or '-':>6} {e['cpuSeconds']:>8,.0f} "
              f"{e.get('cpuPerSync', '-'):>6} "
              f"{cell(d.get('incremental'), 'p50'):>9} {cell(d.get('incremental'), 'p95'):>9} "
              f"{cell(d.get('full'), 'p50'):>9} {cell(d.get('full'), 'p95'):>9}")
    if not any(e.get("distribution") for e in cache.values()):
        print("\nNo percentiles: pass --artefacts <dir> with each run's sync-durations.csv.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
