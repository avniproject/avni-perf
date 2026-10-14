"""Query the New Relic backup offline, the way NRQL queried the live account.

    python3 tools/newrelic-query.py --list-runs
    python3 tools/newrelic-query.py --run case3
    python3 tools/newrelic-query.py --run case6 --facet name --where "r['error']"
    python3 tools/newrelic-query.py --since 2026-10-12T02:00 --until 2026-10-12T03:00

**The backup is only worth having if the questions already asked can still be asked.** Every
finding drawn from New Relic so far -- the 25.5% database move between cases 5 and 6, the flat
db-per-call through case 10's soak, the 278.8 ms per request in case 3 -- is a facet by
transaction name over a run's window, reporting duration and the database split. That is what this
does, against gzipped JSONL instead of NRQL, with no account, no key and no retention window.

**Runs are resolved to UTC windows from `run-log-detail.md`**, so `--run case3` means the same
thing here as it does in the findings. The run id supplies the start; the injection line supplies
the arrival window and ramp. A tail is added because syncs finish after the last arrival, and the
window actually used is always printed -- a figure quoted from the wrong window is the error this
is most likely to produce, so it is never left implicit.

For ad-hoc work beyond this, the files are ordinary JSONL and DuckDB reads them in place:

    SELECT name, count(*), avg(duration)*1000 AS ms
    FROM read_json_auto('nr-backup/Transaction/**/*.jsonl.gz', union_by_name=true)
    WHERE timestamp BETWEEN 1791526554000 AND 1791533754000
    GROUP BY name ORDER BY 2 DESC;
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_LOG = ROOT / "docs/run-log.md"

# A sync's requests continue after the last device arrives; case 3's longest ran 223 s and the
# stressed runs far longer. Short enough not to swallow the next run, generous enough not to cut
# the tail off a slow one -- and overridable.
DEFAULT_TAIL_MIN = 20

# Each event type names its transaction differently, and facetting on the wrong attribute produces
# one "(absent)" row rather than an error -- a table that is empty without saying why.
FACET_BY = {
    "Transaction": "name",
    "TransactionTrace": "path",
    "SqlTrace": "databaseMetricName",
    "TransactionError": "transactionName",
    "ErrorTrace": "error.class",
}

# SqlTrace measures a statement rather than a request: totalCallTime over callCount, where
# Transaction has duration over databaseCallCount. Same shape, different names.
DURATION_KEYS = ("duration", "totalCallTime")
CALLS_KEYS = ("databaseCallCount", "callCount")


def runs() -> dict:
    """run id -> (start, end) in UTC.

    The window comes from `run-log.md`'s `arrival window` column, which is generated per run from
    its metadata. **Not from `run-log-detail.md`'s `injection` line**, which carries the configured
    defaults rather than what ran -- it reports "120min @ 140/h, ramp 33640 s" against case 1
    bursts that lasted 15 seconds, and a window read from it is wrong by hours.
    """
    if not RUN_LOG.exists():
        return {}
    rows = []
    for line in RUN_LOG.read_text().splitlines():
        if not line.startswith("| [`"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        run_id = cells[0].split("`")[1]
        stamp = re.match(r"(\d{4}-\d{2}-\d{2})T(\d{2})-(\d{2})-(\d{2})Z", run_id)
        if not stamp:
            continue
        start = dt.datetime.strptime(f"{stamp[1]} {stamp[2]}:{stamp[3]}:{stamp[4]}",
                                     "%Y-%m-%d %H:%M:%S")
        window = re.search(r"(\d+)\s*(min|s)\b", cells[5]) if len(cells) > 5 else None
        minutes = 0.0
        if window:
            minutes = int(window[1]) / (1 if window[2] == "min" else 60)
        rows.append((run_id, start, start + dt.timedelta(minutes=minutes)))
    rows.sort(key=lambda r: r[1])
    out = {}
    for i, (run_id, start, end) in enumerate(rows):
        # Back-to-back runs share a box, so a generous tail would attribute one run's slow finish
        # to the next run's start. The next arrival is a hard ceiling.
        ceiling = rows[i + 1][1] if i + 1 < len(rows) else None
        out[run_id] = (start, end, ceiling)
    return out


def resolve(needle: str, tail_min: int):
    found = {k: v for k, v in runs().items() if needle.lower() in k.lower()}
    if not found:
        raise SystemExit(f"no run in run-log.md matches {needle!r}; --list-runs shows them")
    if len(found) > 1:
        # Case names repeat across reruns, and silently taking the first would attribute a figure
        # to the wrong run -- the mistake this whole exercise keeps finding.
        raise SystemExit(f"{needle!r} matches {len(found)} runs, name one:\n  "
                         + "\n  ".join(sorted(found)))
    run_id, (start, end, ceiling) = next(iter(found.items()))
    end += dt.timedelta(minutes=tail_min)
    return run_id, start, min(end, ceiling) if ceiling else end


def read(out: Path, event_type: str, since: dt.datetime, until: dt.datetime):
    a, b = (int(t.replace(tzinfo=dt.timezone.utc).timestamp() * 1000) for t in (since, until))
    pattern = str(out / event_type / "**" / "*.jsonl.gz")
    files = sorted(glob.glob(pattern, recursive=True))
    if not files:
        raise SystemExit(f"no files under {out / event_type}/ -- run `make newrelic_export` first")
    seen = 0
    for path in files:
        # The filename is the UTC hour, so whole files outside the window are skipped unopened.
        day, hour = Path(path).parent.name, Path(path).stem.split(".")[0]
        try:
            h0 = dt.datetime.strptime(f"{day} {hour}", "%Y-%m-%d %H")
        except ValueError:
            h0 = None
        if h0 and (h0 + dt.timedelta(hours=1) <= since or h0 >= until):
            continue
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                if a <= row.get("timestamp", 0) < b:
                    seen += 1
                    yield row
    if not seen:
        print(f"warning: no {event_type} events in the window -- retention may have taken them "
              f"before the backup ran; check manifest.json", file=sys.stderr)


def pct(values: list, p: float):
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, int(round((p / 100) * (len(s) - 1))))]


def first(row: dict, keys):
    for k in keys:
        if row.get(k) is not None:
            return float(row[k])
    return None


def summarise(rows, facet: str | None):
    groups = {}
    for r in rows:
        key = r.get(facet, "(absent)") if facet else "all"
        groups.setdefault(key, []).append(r)
    table = []
    for key, members in groups.items():
        dur = [v for r in members if (v := first(r, DURATION_KEYS)) is not None]
        db = [r["databaseDuration"] for r in members if r.get("databaseDuration") is not None]
        calls = [v for r in members if (v := first(r, CALLS_KEYS)) is not None]
        mean = lambda v: sum(v) / len(v) if v else None
        table.append({
            "facet": key, "n": len(members),
            "errors": sum(1 for r in members if r.get("error")),
            "mean_ms": mean(dur) and mean(dur) * 1000,
            "p50_ms": pct(dur, 50) and pct(dur, 50) * 1000,
            "p95_ms": pct(dur, 95) and pct(dur, 95) * 1000,
            "p99_ms": pct(dur, 99) and pct(dur, 99) * 1000,
            "db_ms": mean(db) and mean(db) * 1000,
            "db_calls": mean(calls),
            # The measure the co-tenant and soak findings turn on: database time per call, which
            # separates "more queries" from "slower queries" at constant call count. For SqlTrace,
            # which has no databaseDuration, the same ratio falls out of its own totalCallTime.
            "ms_per_call": ((mean(db or dur) * 1000 / mean(calls))
                            if (db or dur) and calls and mean(calls) else None),
        })
    return sorted(table, key=lambda t: -t["n"])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", default="nr-backup")
    p.add_argument("--event-type", default="Transaction")
    p.add_argument("--run", help="substring of a run id, e.g. case3")
    p.add_argument("--since"), p.add_argument("--until")
    p.add_argument("--tail-min", type=int, default=DEFAULT_TAIL_MIN,
                   help=f"minutes kept after the last arrival (default {DEFAULT_TAIL_MIN})")
    p.add_argument("--facet", help="attribute to group by, or 'none'; default is per event type "
                                   "(" + ", ".join(f"{k}={v}" for k, v in FACET_BY.items()) + ")")
    p.add_argument("--where", help="python expression over the row dict `r`")
    p.add_argument("--top", type=int, default=15)
    p.add_argument("--csv", action="store_true")
    p.add_argument("--list-runs", action="store_true")
    args = p.parse_args(argv)

    if args.list_runs:
        for run_id, (s, e, c) in sorted(runs().items()):
            end = min(e + dt.timedelta(minutes=args.tail_min), c or dt.datetime.max)
            print(f"{run_id}  {s:%Y-%m-%d %H:%M}Z -> {end:%H:%M}Z "
                  f"({(end - s).total_seconds() / 60:.0f} min)")
        return 0

    if args.run:
        run_id, since, until = resolve(args.run, args.tail_min)
        print(f"{run_id}", file=sys.stderr)
    elif args.since and args.until:
        run_id = None
        since, until = (dt.datetime.fromisoformat(x) for x in (args.since, args.until))
    else:
        p.error("need --run, or --since with --until")

    print(f"window {since:%Y-%m-%d %H:%M}Z -> {until:%Y-%m-%d %H:%M}Z "
          f"({(until - since).total_seconds() / 60:.0f} min, incl. {args.tail_min} min tail)",
          file=sys.stderr)

    rows = read(Path(args.out), args.event_type, since, until)
    if args.where:
        expr = compile(args.where, "<--where>", "eval")
        rows = (r for r in rows if eval(expr, {"__builtins__": {}}, {"r": r}))

    facet = args.facet or FACET_BY.get(args.event_type, "name")
    table = summarise(rows, None if facet == "none" else facet)
    if not table:
        return 1

    if args.csv:
        w = csv.DictWriter(sys.stdout, fieldnames=list(table[0]))
        w.writeheader(), w.writerows(table)
        return 0

    fmt = lambda v, d=1: "-" if v is None else f"{v:,.{d}f}"
    width = min(60, max(len(str(t["facet"])) for t in table[:args.top]))
    print(f"\n{'transaction':<{width}} {'n':>7} {'err':>5} {'mean':>8} {'p50':>8} {'p95':>8} "
          f"{'p99':>8} {'db ms':>8} {'calls':>7} {'ms/call':>8}")
    for t in table[:args.top]:
        print(f"{str(t['facet'])[:width]:<{width}} {t['n']:>7,} {t['errors']:>5,} "
              f"{fmt(t['mean_ms']):>8} {fmt(t['p50_ms']):>8} {fmt(t['p95_ms']):>8} "
              f"{fmt(t['p99_ms']):>8} {fmt(t['db_ms']):>8} {fmt(t['db_calls']):>7} "
              f"{fmt(t['ms_per_call'], 2):>8}")
    total = sum(t["n"] for t in table)
    print(f"\n{total:,} events, {len(table)} transaction names"
          + (f", {len(table) - args.top} not shown" if len(table) > args.top else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
