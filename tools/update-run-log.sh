#!/usr/bin/env bash
#
# Regenerate docs/run-log.md from the artefacts bucket.
#
#   ./tools/update-run-log.sh [--bucket avni-loadtest-<account>] [--prefix artefacts]
#   make run_log
#
# **GENERATED, NOT APPENDED.** The doc is rewritten wholesale from what is in S3
# every time. That is deliberate:
#
#   * The artefacts prefix is append-only by IAM -- the injector's instance
#     profile has PutObject and NOT DeleteObject -- so S3 is the source of truth
#     and a generated view cannot drift from it.
#   * A run whose upload died half way cannot leave half a row.
#   * Runs nobody remembered to log still appear, because they are in the bucket.
#   * Re-running is idempotent, so it is safe in a make target or a hook.
#
# **Why not append from the injector.** That host has no git credentials on
# purpose -- the harness reaches it as a tarball of one commit precisely so a
# disposable instance never holds a deploy key -- and it is destroyed between
# campaigns. run-scenario.sh prints the command to run this instead.
#
# **WHERE THE NUMBERS COME FROM, AND WHY IT IS NOT JSON.** Gatling 3.15 writes no
# machine-readable statistics file. There is no js/global_stats.json; js/stats.js
# is report UI code. The authoritative figures are the "Global Information" block
# Gatling prints at the end of a run, which run-scenario.sh captures into
# gradle.log. Parsing a console table is not pretty, but inventing percentiles
# from simulation.log would be worse: these are the numbers Gatling itself
# reports, and they are what anyone reading the HTML report will see.
set -euo pipefail

BUCKET=""; PREFIX="artefacts"; OUT="docs/run-log.md"
while [ $# -gt 0 ]; do
  case "$1" in
    --bucket) BUCKET="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --out)    OUT="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$BUCKET" ]; then
  ACCT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || {
    echo "No AWS credentials, and no --bucket given." >&2; exit 1; }
  BUCKET="avni-loadtest-${ACCT}"
fi

WORK=$(mktemp -d "${TMPDIR:-/tmp}/runlog.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

echo "reading s3://$BUCKET/$PREFIX/ ..." >&2
RUNS=$(aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "${PREFIX}/" --delimiter / \
         --query 'CommonPrefixes[].Prefix' --output text 2>/dev/null | tr '\t' '\n' \
       | sed "s#^${PREFIX}/##; s#/\$##" | grep -v '^$' | sort || true)

[ -n "$RUNS" ] || { echo "no runs under s3://$BUCKET/$PREFIX/" >&2; exit 1; }
echo "$RUNS" | sed 's/^/  /' >&2

for r in $RUNS; do
  mkdir -p "$WORK/$r"
  # run-metadata.json is small. gradle.log is ~1 MB, and only its tail is needed,
  # but S3 range requests on a text file whose length is unknown are more trouble
  # than the megabyte is worth.
  aws s3 cp --only-show-errors "s3://$BUCKET/$PREFIX/$r/run-metadata.json" "$WORK/$r/" 2>/dev/null || true
  aws s3 cp --only-show-errors "s3://$BUCKET/$PREFIX/$r/gradle.log"        "$WORK/$r/" 2>/dev/null || true
  # Additive corrections. A completed run's own run-metadata.json is never
  # rewritten -- editing it to say something it did not say would falsify the
  # record -- so a field found to be wrong afterwards is corrected alongside it.
  aws s3 cp --only-show-errors "s3://$BUCKET/$PREFIX/$r/provenance-correction.json" "$WORK/$r/" 2>/dev/null || true
done

RUNS="$RUNS" WORK="$WORK" BUCKET="$BUCKET" PREFIX="$PREFIX" OUT="$OUT" python3 - <<'PY'
import json, os, pathlib, re, datetime

runs  = os.environ['RUNS'].split()
work  = pathlib.Path(os.environ['WORK'])
bucket, prefix, out = os.environ['BUCKET'], os.environ['PREFIX'], os.environ['OUT']

def jload(p):
    try: return json.loads(p.read_text())
    except Exception: return None

def at(d, path, default=None):
    """Exact dotted path. Verified against a real run-metadata.json rather than
    guessed, so a miss means the harness changed shape and should be noticed."""
    cur = d
    for k in path.split('.'):
        if not isinstance(cur, dict) or k not in cur: return default
        cur = cur[k]
    return cur if cur not in (None, '') else default

NUM = r'\|\s*([0-9,.]+|-)\s*\|\s*([0-9,.]+|-)\s*\|\s*([0-9,.]+|-)\s*$'
def gatling_stats(log):
    """Parse the console 'Global Information' table. Returns the OK column."""
    if not log.exists(): return {}
    try: text = log.read_text(errors='replace')
    except Exception: return {}
    block = re.search(r'-+ Global Information -+.*?(?====|\Z)', text, re.S)
    if not block: return {}
    out, b = {}, block.group(0)
    def grab(label, key):
        m = re.search(re.escape(label) + r'.*?' + NUM, b, re.M)
        if m:
            v = m.group(2).replace(',', '')
            if v != '-':
                out[key] = float(v) if '.' in v else int(v)
    grab('request count', 'requests')
    grab('mean response time', 'mean_ms')
    grab('response time 50th percentile', 'p50_ms')
    grab('response time 95th percentile', 'p95_ms')
    grab('response time 99th percentile', 'p99_ms')
    grab('max response time', 'max_ms')
    grab('mean throughput', 'rps')
    ko = re.search(r'^> KO\s+([0-9,]+)\s+\(\s*([0-9.]+)%\)', b, re.M)
    if ko:
        out['failed'] = int(ko.group(1).replace(',', ''))
        out['failed_pct'] = float(ko.group(2))
    return out

rows, details, problems = [], [], []
for r in runs:
    meta  = jload(work/r/'run-metadata.json')
    stats = gatling_stats(work/r/'gradle.log')
    corr  = jload(work/r/'provenance-correction.json')
    link  = f"s3://{bucket}/{prefix}/{r}/"

    # The run id is this repo's own construction: <utc>-<label>-<sha7>. It is
    # reliable even when a run died before the harness wrote metadata.
    m = re.match(r'(\d{4}-\d{2}-\d{2})T(\d{2})-(\d{2})-\d{2}Z-(.+)-([0-9a-f]{7})$', r)
    date  = f"{m.group(1)} {m.group(2)}:{m.group(3)}" if m else ''
    label = m.group(4) if m else r
    sha7  = m.group(5) if m else '?'

    if not meta:   problems.append((r, "no run-metadata.json — the run died before archiveRun, or the upload was incomplete"))
    if not stats:  problems.append((r, "no Global Information block in gradle.log — the simulation did not reach its summary"))
    if meta and at(meta, 'simulation.gitSha', 'unknown') == 'unknown':
        if corr:
            fixed = (corr.get('actual') or {}).get('simulation.gitSha', '?')
            problems.append((r, f"harness commit was recorded as `unknown`; **corrected to "
                                f"`{fixed[:7]}`** by `provenance-correction.json` in the same "
                                f"prefix. The run's own metadata is left as written — see that "
                                f"file for the basis and the cause"))
        else:
            problems.append((r, f"harness commit recorded as `unknown` (the run id says `{sha7}`) — "
                                "the tarball delivery strips .git, so `git rev-parse` inside the "
                                "harness finds nothing and also reports the tree as dirty"))

    # **The arrival window is what distinguishes two otherwise identical runs.**
    # Case 1 ran twice on 2026-10-05 with the same 100 users, the same feeder and
    # the same 4,300 requests, and p95 went from 202 ms to 2,242 ms -- because the
    # first spread arrivals over 15 minutes and the second over 60 seconds. Leaving
    # that out of the table makes the two rows look like a regression.
    #
    # The field was renamed burstMinutes -> burstSeconds when the harness changed
    # the default, so both are read: a run is described in the units it recorded.
    bs = at(meta, 'settings.injection.burstSeconds') if meta else None
    bm = at(meta, 'settings.injection.burstMinutes') if meta else None
    users_n = at(meta, 'settings.injection.userCount') if meta else None
    if bs is not None:
        window = f"{bs}s"
    elif bm is not None:
        window = f"{bm}min"
    else:
        window = '—'
    # **Concurrency measured from the run, not estimated from a constant.**
    #
    # This was `users / window * 6.0` -- Little's law against the harness's ~6s
    # reference-data sync, which is the duration measured when nothing was
    # contending. Under load the sync stretches and open injection turns that into
    # more overlap, so the estimate understates exactly where concurrency matters:
    # it read ~10 and ~40 for runs that ran at ~27 and ~80 devices.
    #
    # `rps * mean` needs no constant and is exact: it is the server's mean queue
    # depth in requests, which is what p95 actually responds to. It is **requests,
    # not devices** -- a device issues ~43 of them in sequence with a modelled
    # storage pause between, so it is not in flight continuously, and the two
    # differ by that duty cycle.
    #
    # Devices are deliberately not computed here. `arrival_rate * requests * mean`
    # looks like it would, and breaks in saturation: for the 15s run it gives 359
    # against a population of 100, because once arrival x service exceeds the
    # cohort the cohort is the limit and the formula does not know that. Getting it
    # right needs the per-sync durations the simulation writes to
    # sync-durations.csv, which the artefacts do not yet carry.
    #
    # Two decimal-free digits would print run 1 as `0`, which reads as a missing
    # value rather than an idle server, so this keeps one decimal below 10.
    try:
        depth = float(stats['rps']) * float(stats['mean_ms']) / 1000.0
        inflight = f"~{depth:.1f}" if depth < 10 else f"~{depth:.0f}"
    except (KeyError, TypeError, ValueError):
        inflight = '—'

    rows.append(dict(
        run=r, date=date, label=label,
        profile=at(meta,'settings.injection.profile','—'),
        users=at(meta,'settings.injection.userCount','—'),
        mode=at(meta,'settings.sync.syncMode','—'),
        window=window, inflight=inflight,
        requests=stats.get('requests','—'),
        failed_pct=stats.get('failed_pct','—'),
        p95=stats.get('p95_ms','—'),
        rps=stats.get('rps','—'),
        link=link,
    ))
    details.append((r, link, meta, stats, sha7, corr))

now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
L = []
L.append("# Run log\n")
L.append(f"Generated from `s3://{bucket}/{prefix}/` by `tools/update-run-log.sh` "
         f"(`make run_log`) — last refreshed {now}.\n")
L.append("**Do not edit by hand.** Rewritten wholesale on every run of that script. The "
         "artefacts prefix is append-only by IAM, so S3 is the source of truth and this is a "
         "view of it. An edit here is lost on the next refresh; a run missing from this table "
         "means its upload did not happen, not that the log is stale.\n")
L.append("Artefacts are **not** copied into the repo. Each run directory holds Gatling's "
         "`simulation.log`, the HTML report and `run-metadata.json`, plus the environment "
         "context captured at run time — `parity-report.md`, `pg_settings.csv`, `stats.json`. "
         "Those are what make a number interpretable once the environment that produced it has "
         "been destroyed.\n")
L.append("Findings drawn from these runs are written up separately, by hand, in "
         "`findings-case1.md` and its siblings — this file is the index, not the analysis.\n")
L.append("| run | date | scenario | profile | users | arrival window | ~requests in flight | requests | failed | p95 ms | rps |")
L.append("|---|---|---|---|---|---|---|---|---|---|---|")
for x in rows:
    L.append(f"| [`{x['run']}`]({x['link']}) | {x['date']} | {x['label']} | {x['profile']} | "
             f"{x['users']} | {x['window']} | {x['inflight']} | {x['requests']} | "
             f"{x['failed_pct']}% | {x['p95']} | {x['rps']} |")
L.append("")

if problems:
    L.append("## Caveats on the runs above\n")
    L.append("Listed rather than left blank, because a blank column reads as a measurement "
             "and not as a missing one:\n")
    for r, why in problems:
        L.append(f"- `{r}` — {why}")
    L.append("")

L.append("## Detail\n")
for r, link, meta, stats, sha7, corr in details:
    L.append(f"### `{r}`\n")
    L.append(f"Artefacts: `{link}`\n")
    L.append("| | |")
    L.append("|---|---|")
    if stats:
        L.append(f"| requests (ok) | {stats.get('requests','—')} |")
        L.append(f"| failed | {stats.get('failed','—')} ({stats.get('failed_pct','—')}%) |")
        L.append(f"| response time p50 / p95 / p99 / max ms | "
                 f"{stats.get('p50_ms','—')} / {stats.get('p95_ms','—')} / "
                 f"{stats.get('p99_ms','—')} / {stats.get('max_ms','—')} |")
        L.append(f"| mean ms | {stats.get('mean_ms','—')} |")
        L.append(f"| mean throughput rps | {stats.get('rps','—')} |")
    if meta:
        cs = (corr.get('actual') or {}).get('simulation.gitSha') if corr else None
        cd = (corr.get('actual') or {}).get('simulation.gitDirty') if corr else None
        if cs:
            L.append(f"| harness commit | `{cs}` — **corrected**, the run recorded "
                     f"`{at(meta,'simulation.gitSha','—')}` |")
        else:
            L.append(f"| harness commit | {at(meta,'simulation.gitSha','—')} "
                     f"(run id says `{sha7}`) |")
        if cd is not None:
            L.append(f"| tree dirty | {cd} — **corrected**, the run recorded "
                     f"`{at(meta,'simulation.gitDirty','—')}` |")
        else:
            L.append(f"| tree dirty | {at(meta,'simulation.gitDirty','—')} |")
        L.append(f"| target | {at(meta,'target.baseUrl','—')} |")
        L.append(f"| server build | {at(meta,'target.serverBuild','—')} |")
        L.append(f"| dataset | {at(meta,'dataset','—')} |")
        L.append(f"| injector | {at(meta,'settings.injector.label','—')} "
                 f"({at(meta,'settings.injector.os','—')}, {at(meta,'settings.injector.cpus','—')} cpu, "
                 f"heap {at(meta,'settings.injector.maxHeapMb','—')} MB) |")
        L.append(f"| injector RTT min / median ms | {at(meta,'settings.injector.rtt.minMillis','—')} / "
                 f"{at(meta,'settings.injector.rtt.medianMillis','—')} |")
        L.append(f"| est. sync overhead s | {at(meta,'settings.injector.rtt.estimatedSyncOverheadSeconds','—')} |")
        L.append(f"| injection | profile {at(meta,'settings.injection.profile','—')}, "
                 f"{at(meta,'settings.injection.userCount','—')} users arriving over "
                 f"{window}, ~{inflight.lstrip('~')} requests in flight (rps x mean), "
                 f"ramp {at(meta,'settings.injection.rampPeriodSeconds','—')} s |")
        L.append(f"| sync | mode {at(meta,'settings.sync.syncMode','—')}, "
                 f"feeder {at(meta,'settings.sync.feeder','—')} "
                 f"({at(meta,'settings.sync.feederRows','—')} rows), "
                 f"auth {at(meta,'settings.sync.authMode','—')}, "
                 f"page {at(meta,'settings.sync.pageSize','—')} |")
        L.append(f"| entities | {at(meta,'entityTable.pulled','—')} pulled of "
                 f"{at(meta,'entityTable.total','—')} ({at(meta,'entityTable.source','—')}) |")
        L.append(f"| push / co-tenants | {at(meta,'settings.push.enabled','—')} / "
                 f"{at(meta,'settings.coTenants.enabled','—')} |")
        L.append(f"| cache policy | {at(meta,'environment.cachePolicy','—')} |")
        L.append(f"| autovacuum | {at(meta,'environment.autovacuum','—')} |")
    L.append("")

pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
pathlib.Path(out).write_text("\n".join(L))
print(f"wrote {out}: {len(rows)} run(s), {len(problems)} caveat(s)")
PY
