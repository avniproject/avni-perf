#!/usr/bin/env python3
"""Two or three timeslice captures side by side: where the server's time went, by segment.

    ./tools/compare-timeslices.py nr-backup/timeslices/<control>.json nr-backup/timeslices/<test>.json [<third>.json]
        [--per-sync N,N[,N]]  [--top 25]

A capture (newrelic-export.py --timeslices) is every metricTimesliceName the agent reported in a
run's window, with the summed value and the sample count. Segment metrics are wall seconds;
`CPU/User Time` is CPU seconds; `GC/<collector>` is collector seconds; `Threads/State/<pool>/
<STATE>/Count` and `Threads/Count/<pool>/<Blocked|Waited>Count` are counts; `Memory/*` are KB
averaged over samples.

WHAT IT PRINTS. A totals block (request time, CPU, database, GC, threads, heap), the datastore
statements with the largest absolute change, the request types with the largest change, and the
largest changes overall with the agent's own bookkeeping filtered out. --per-sync divides every
seconds figure by the run's sync count, which is what makes two runs of different length or
different completion comparable.

WHAT IT CANNOT DO. Segment time is wall time on the request thread, not CPU; a drop in
`Datastore/statement/Postgres/gender/select` says how long the request waited on that query, not
how much CPU the interceptor cost. CPU is one number per run (`CPU/User Time`) and splits only by
subtraction. And a metric the agent did not emit in one run is reported at zero, which is what
"absent" should read as for an interceptor's query, and what a renamed metric would read as too.
"""
import json, re, sys


def load(path):
    d = json.load(open(path))
    out = {}
    for r in d["queries"]["segments"]["results"]:
        out[r["metricTimesliceName"]] = (float(r["value"]), int(r["samples"]))
    return d["label"], out, d.get("truncated")


NOISE = re.compile(r"^(Supportability|Agent|Apdex|Instance|JmxBuiltIn|MemoryPool|Errors/all|"
                   r"Java/org\.springframework|Spring/Java|Instrumentation)")


def fmt(v):
    return f"{v:>10,.1f}"


def main(argv):
    paths = [a for a in argv if a.endswith(".json")]
    per_sync = None
    if "--per-sync" in argv:
        per_sync = [int(x) for x in argv[argv.index("--per-sync") + 1].split(",")]
    top = int(argv[argv.index("--top") + 1]) if "--top" in argv else 25
    runs = [load(p) for p in paths]
    labels = [r[0] for r in runs]
    data = [r[1] for r in runs]
    for lab, _, trunc in runs:
        if trunc:
            print(f"NOTE: {lab} capture was truncated at the metric limit; small segments may be missing")
    names = set().union(*[set(d) for d in data])
    scale = [1.0 / n for n in per_sync] if per_sync else [1.0] * len(runs)

    def val(i, n):
        return data[i].get(n, (0.0, 0))[0] * scale[i]

    def cnt(i, n):
        return data[i].get(n, (0.0, 0))[1]

    def avg(i, n):
        v, s = data[i].get(n, (0.0, 0)); return v / s if s else 0.0

    def row(label, vals, unit=""):
        cells = "".join(fmt(v) for v in vals)
        delta = ""
        if len(vals) >= 2 and vals[0]:
            delta = f"   {(vals[1] - vals[0]) / vals[0] * 100:+6.1f}%"
        print(f"  {label:58s}{cells}{unit and ' ' + unit}{delta}")

    hdr = "".join(f"{l[:10]:>10s}" for l in labels)
    print(f"\n{'per sync' if per_sync else 'totals, seconds'}{'':50s}{hdr}   test vs control")
    print("--- where request time went " + "-" * 60)
    for n, lab in (("WebTransactionTotalTime", "request time, all transactions"),
                   ("HttpDispatcher", "HttpDispatcher (web time)"),
                   ("Datastore/all", "database, all"),
                   ("Java/other", "Java/other (uninstrumented app code)"),
                   ("External/all", "external calls (S3)")):
        row(lab, [val(i, n) for i in range(len(runs))])
    print("--- CPU, GC, heap " + "-" * 70)
    row("CPU/User Time (CPU seconds)", [val(i, "CPU/User Time") for i in range(len(runs))])
    row("CPU/System Time (CPU seconds)", [val(i, "CPU/System Time") for i in range(len(runs))])
    for n in sorted(x for x in names if x.startswith("GC/")):
        row(f"{n} (collector seconds)", [val(i, n) for i in range(len(runs))])
    row("Memory/Heap/Used, mean MB", [avg(i, "Memory/Heap/Used") for i in range(len(runs))])
    row("Memory/Heap/Committed, mean MB", [avg(i, "Memory/Heap/Committed") for i in range(len(runs))])
    print("--- request threads (http-nio pool) " + "-" * 52)
    for st in ("RUNNABLE", "BLOCKED", "WAITING", "TIMED_WAITING"):
        n = f"Threads/State/http-nio-#-exec-#/{st}/Count"
        row(f"threads {st}, mean per sample", [avg(i, n) for i in range(len(runs))])
    for n, lab in (("Threads/Count/http-nio-#-exec-#/BlockedCount", "thread blocked events (sum)"),
                   ("Threads/Count/http-nio-#-exec-#/WaitedCount", "thread waited events (sum)")):
        row(lab, [data[i].get(n, (0.0, 0))[0] for i in range(len(runs))])

    def biggest(prefix, title, k=top):
        cands = [n for n in names if n.startswith(prefix) and not NOISE.match(n)]
        cands.sort(key=lambda n: -abs(val(1, n) - val(0, n)))
        print(f"--- {title}: largest change, test vs control " + "-" * 30)
        for n in cands[:k]:
            vals = [val(i, n) for i in range(len(runs))]
            calls = "/".join(f"{cnt(i, n):,}" for i in range(len(runs)))
            row(n.replace(prefix, "")[:56], vals, f" calls {calls}")

    biggest("Datastore/statement/Postgres/", "database statements")
    biggest("WebTransactionTotalTime/", "request types", 15)
    cands = [n for n in names if not NOISE.match(n) and not n.startswith(("Datastore/statement/", "WebTransaction", "Memory", "Threads", "MemoryPool"))]
    cands.sort(key=lambda n: -abs(val(1, n) - val(0, n)))
    print("--- everything else: largest change " + "-" * 50)
    for n in cands[:top]:
        row(n[:56], [val(i, n) for i in range(len(runs))])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
