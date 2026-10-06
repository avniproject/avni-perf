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
  # One row per completed sync, archived from runs after 5 Oct 2026. It is what makes
  # device concurrency and the per-sync spread measured rather than derived; absent
  # for earlier runs, and the columns read as absent rather than being invented.
  aws s3 cp --only-show-errors "s3://$BUCKET/$PREFIX/$r/sync-durations.csv" "$WORK/$r/" 2>/dev/null || true
done

RUNS="$RUNS" WORK="$WORK" BUCKET="$BUCKET" PREFIX="$PREFIX" OUT="$OUT" python3 - <<'PY'
import json, os, pathlib, re, datetime

runs  = os.environ['RUNS'].split()
work  = pathlib.Path(os.environ['WORK'])
bucket, prefix, out = os.environ['BUCKET'], os.environ['PREFIX'], os.environ['OUT']

def jload(p):
    try: return json.loads(p.read_text())
    except Exception: return None

def sync_durations(path, sync_mode=None):
    """Mean and p95 of a run's per-sync durations, in seconds, from sync-durations.csv.

    Returns None where the file is absent -- every run before 5 Oct 2026 -- so the caller can
    print nothing rather than a figure derived from an aggregate. The spread matters as much as
    the mean here: a cohort's question is what the device that arrived mid-herd experienced, and
    that is invisible in a per-request percentile.
    """
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return None
    ms, full = [], []
    for line in lines[1:]:
        c = line.split(',')
        if len(c) < 6:
            continue
        try:
            v = int(c[2])
        except ValueError:
            continue
        ms.append(v)
        # Column 7 from 6 Oct 2026.
        if len(c) >= 7:
            if c[6].strip().lower() == 'true':
                full.append(v)
        elif sync_mode == 'full':
            # **Back-calculated, and exactly rather than approximately.** A file without the
            # column predates it, and under SYNC_MODE=full every entity of every sync pulls from
            # 1900 -- so every row in it is a full sync and the figure is the same arithmetic over
            # the same numbers. All ten runs to 6 Oct 2026 were mode full, which is why this is
            # worth doing rather than leaving seven runs blank.
            #
            # Only `full` is recoverable this way. `incremental` and pre-6-Oct `realistic` produced
            # no full syncs at all, which is a different statement from "unknown" and is made
            # separately below. `csv` decides per user from the feeder, so the split cannot be
            # recovered from this file alone.
            full.append(v)
    if not ms:
        return None
    pct = lambda xs, q: sorted(xs)[min(int(len(xs) * q), len(xs) - 1)] / 1000.0
    out = dict(n=len(ms), mean=sum(ms) / len(ms) / 1000.0,
               p50=pct(ms, 0.50), p95=pct(ms, 0.95))
    if full:
        out.update(full_n=len(full), full_p50=pct(full, 0.50), full_p95=pct(full, 0.95),
                   full_source=('recorded' if any(len(l.split(',')) >= 7 for l in lines[1:])
                                else 'back-calculated from SYNC_MODE=full'))
    elif sync_mode in ('incremental', 'realistic'):
        out['full_none'] = sync_mode
    return out


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
    # **Shown in IST, because that is when the people who ran it were in the room.** The run id
    # stays UTC and is the identifier; this column is for reading, and a reader reconciling a row
    # against a Slack message or a CloudWatch graph they opened at the time is doing arithmetic in
    # their head otherwise. +5:30 crosses a date boundary for anything before 18:30 UTC, so the
    # date is converted with the time rather than carried over from the id.
    if m:
        _utc = datetime.datetime.strptime(f"{m.group(1)}T{m.group(2)}:{m.group(3)}",
                                          "%Y-%m-%dT%H:%M").replace(tzinfo=datetime.timezone.utc)
        date = _utc.astimezone(datetime.timezone(datetime.timedelta(hours=5, minutes=30))) \
                   .strftime('%Y-%m-%d %H:%M')
    else:
        date = ''
    run_label = m.group(4) if m else r
    sha7  = m.group(5) if m else '?'

    # **The scenario column names the case and nothing else.** Run ids carry what distinguished one
    # invocation from another -- `case1-burst15`, `case1-burst60-warm` -- and those appendages are
    # already columns: the arrival window has its own, and cache policy is in the detail. Repeating
    # them in the scenario made `case1` look like six scenarios, and sorting or grouping by it
    # separated runs of the same case.
    #
    # The full label stays available in `run_label` for the checks below, which read it for
    # markers like `warmup` that have nowhere else to live.
    case_m = re.match(r'(case\d+)', run_label)
    label = case_m.group(1) if case_m else run_label

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
    # Devices are not computed from the aggregates. `arrival_rate * requests * mean`
    # looks like it would, and breaks in saturation: for the 15s run it gives 359
    # against a population of 100, because once arrival x service exceeds the
    # cohort the cohort is the limit and the formula does not know that.
    #
    # `sync-durations.csv` is archived from runs after 5 Oct 2026. Where it is present
    # the device figure is measured rather than derived -- the mean sync duration
    # times the arrival rate, capped by the cohort -- and where it is not, the column
    # reads as absent, which is the honest answer. The three case 1 runs that predate
    # it keep their derived figures in findings-case1.md, where the derivation is
    # shown and reconciled against the request depth.
    #
    # This paragraph described behaviour that did not exist for one commit. It does now.
    #
    # Two decimal-free digits would print run 1 as `0`, which reads as a missing
    # value rather than an idle server, so this keeps one decimal below 10.
    # One decimal below 20, because at these magnitudes the first one carries meaning: the
    # difference between 1.0 and 1.7 devices is the difference between two arrival windows.
    fmt = lambda v: f"~{v:.1f}" if v < 20 else f"~{v:.0f}"
    try:
        wall = float(stats['requests']) / float(stats['rps'])
        depth = float(stats['rps']) * float(stats['mean_ms']) / 1000.0
        inflight = fmt(depth)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        wall, inflight = None, '—'

    # **Both figures are means over the whole run, which is what makes them comparable.**
    #
    # `users x duration / wall`, not `arrival_rate x duration`. The second is the steady-state
    # concurrency during the arrival window and is the larger number -- 13.1 against 11.8 for the
    # 90 s run -- because it ignores the drain after arrivals stop. `rps x mean` beside it is a
    # run-mean, so pairing it with a steady-state figure would make the duty cycle between the two
    # columns incoherent, and that ratio is the thing that shows a device moving from waiting on
    # its own storage pause to waiting on the server.
    #
    # The cap cannot bind on a run-mean -- wall is at least the arrival window plus one sync, so
    # duration/wall is at most 1 -- and is kept as a guard against a malformed pair of inputs
    # rather than as a correction.
    syncs = sync_durations(work / r / 'sync-durations.csv',
                           at(meta, 'settings.sync.syncMode'))
    if syncs and wall and users_n:
        indevices = fmt(min(users_n * syncs['mean'] / wall, users_n))
    else:
        indevices = '—'

    # **A warm-up is a state change, not a measurement.**
    #
    # Step 6 and avni-infra's env-warmup.sh both run ./gradlew directly, so a discarded pass does
    # not reach this prefix at all and normally none of these rows is one. This catches the case
    # where somebody warms through run-scenario.sh instead, which publishes. Worth catching rather
    # than assuming: a warm-up is deliberately gentle, so its numbers look *good*, and a row that
    # is not broken in any visible way is the kind most likely to be read as a point on a curve.
    if 'warmup' in run_label.lower() or 'warmup' in str(at(meta, 'environment.cachePolicy', '')).lower():
        problems.append((r, "is a **warm-up**, not a measurement — a deliberately gentle pass run "
                            "to take the cold-JVM penalty off the first real run. It belongs to no "
                            "curve, and is normally discarded rather than published"))

    # **A run that breached its own gate reads as a data point unless something says so.**
    #
    # `case1-burst60-d9eac3e` failed 0.21% of requests against a recorded gate of 0.05%, and
    # completed 91 syncs where it had 100 users -- so its 4,183 requests and 18.43 rps sit in the
    # table beside complete runs at 4,300. Gatling asserted and failed at the time; nothing
    # downstream remembered. The gate is in the metadata, so the check costs nothing and does not
    # depend on anyone recalling what it was.
    gate = at(meta, 'settings.gates.maxFailedPercent')
    try:
        if gate is not None and float(stats['failed_pct']) > float(gate):
            problems.append((r, f"**failed {stats['failed_pct']}% of requests against its own "
                                f"`MAX_FAILED_PERCENT` gate of {gate}%** — Gatling asserted and "
                                f"failed at the time. Read its throughput and latency as a run "
                                f"that broke, not as a point on a curve"))
    except (KeyError, TypeError, ValueError):
        pass

    # Fewer completed syncs than users is the same thing from the device's side: the requests that
    # happened are real, but the run did not do what its row says it did.
    if syncs and users_n and syncs['n'] < users_n:
        problems.append((r, f"only **{syncs['n']} of {users_n} devices completed a sync** — the "
                            f"per-sync figures describe the ones that finished, and the request "
                            f"count is short of a full cohort by the rest"))

    # Each of these changes how a result reads and is invisible in the run itself. archiveRun
    # prints a NOTE when one is missing; this is the half of that which survives the run.
    absent = [k for k, v in (('CACHE_POLICY', at(meta, 'environment.cachePolicy')),
                             ('AUTOVACUUM', at(meta, 'environment.autovacuum')),
                             ('DATASET_ID', at(meta, 'dataset')),
                             ('SERVER_BUILD', at(meta, 'target.serverBuild')))
              if v in (None, 'unrecorded')]
    if absent:
        problems.append((r, "recorded no " + ", ".join(f"`{k}`" for k in absent)
                            + " — so it cannot be compared with a run that differs in it"))

    # **The whole-sync figure, over full syncs only.**
    #
    # Every other latency column here is per request, and a device's wait is the sum of forty-odd
    # of them plus its storage pauses -- a p95 of 202 ms sat inside a sync that took ten seconds.
    # Restricted to full syncs because the cases mix the two (2 to 7 are "incremental, 1% full"),
    # and a mean across both describes neither: a catch-up and a first pull differ by more than an
    # order of magnitude. Blank where the run recorded no full syncs, and blank for runs before
    # 6 Oct 2026, which recorded no split at all.
    fullp95 = f"{syncs['full_p95']:.1f}" if syncs and 'full_p95' in syncs else '—'

    # **A run the record says is not a measurement comes out of the table.**
    #
    # Two runs of 5 Oct were started against a JVM under three minutes old and lost roughly two
    # thirds of throughput to it. Caveats alone were not enough: they still occupied rows between
    # runs of the same case and window, so the table read as though a 60 s window had produced
    # both 18.43 and 52.44 rps, and the reader had to reach the footnotes to learn it had not.
    # They are listed below the table instead, with what is wrong with them, because they are the
    # evidence for the cold-start finding and deleting them would cost that.
    #
    # Driven by a `notMeasurement` key in the prefix's own provenance-correction.json rather than
    # by anything this script knows, so marking a run is an additive edit to the append-only
    # record and not a change here.
    excluded = (corr or {}).get('notMeasurement')

    rows.append(dict(
        run=r, date=date, label=label, indevices=indevices, syncs=syncs, fullp95=fullp95,
        excluded=excluded,
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

now = datetime.datetime.now(
    datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime('%Y-%m-%d %H:%M IST')
INDEX_NAME = pathlib.Path(out).name
DETAIL_NAME = pathlib.Path(out).stem + "-detail" + pathlib.Path(out).suffix


def anchor(run_id):
    """GitHub's slug for `### \u0060<run id>\u0060`: lowercased, backticks dropped, dots and other
    punctuation dropped, spaces to hyphens. Run ids are already hyphen-separated and carry dots in
    neither position, so this is the whole rule for them."""
    return "".join(c for c in run_id.lower() if c.isalnum() or c == "-")


L = []
L.append("# Run log\n")
L.append(f"Generated from `s3://{bucket}/{prefix}/` by `tools/update-run-log.sh` "
         f"(`make run_log`) — last refreshed {now}.\n")
L.append("**Do not edit by hand.** Rewritten wholesale on every run of that script. The "
         "artefacts prefix is append-only by IAM, so S3 is the source of truth and this is a "
         "view of it. An edit here is lost on the next refresh; a run missing from this table "
         "means its upload did not happen, not that the log is stale.\n")
# Said once, here, rather than left to the reader to notice: the two are 5h30m apart and both
# appear in every row, so a row looks internally inconsistent until you know which is which.
L.append("**Times are IST; run ids are UTC.** The id is the identifier and keeps the `Z` it was "
         "minted with — `...T11-37-03Z...` is the 17:07 row. Dates are converted with the time, "
         "so anything before 18:30 UTC lands on the same IST day but a late-evening run will "
         "not.\n")
L.append("Artefacts are **not** copied into the repo. Each run directory holds Gatling's "
         "`simulation.log`, the HTML report and `run-metadata.json`, plus the environment "
         "context captured at run time — `parity-report.md`, `pg_settings.csv`, `stats.json` — "
         "and `sync-durations.csv`, one row per completed sync. "
         "Those are what make a number interpretable once the environment that produced it has "
         "been destroyed.\n")
L.append("Findings drawn from these runs are written up separately, by hand, in "
         "`findings-case1.md` and its siblings — this file is the index, not the analysis.\n")
# Two concurrency columns because they answer different questions. Requests in flight is the
# server's queue depth, exact from `rps x mean`, and it is what p95 responds to. Devices in flight
# is the scenario's narrative -- how much of the cohort is mid-sync -- and needs the archived
# per-sync durations, so it is blank for runs before 5 Oct 2026 rather than guessed at.
L.append("| run | date (IST) | scenario | profile | users | arrival window | ~requests in flight "
         "| ~devices in flight | requests | failed | p95 ms | full sync p95 s | rps |")
L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for x in [y for y in rows if not y.get('excluded')]:
    # The run id links to its detail section rather than to S3: the bucket is where the
    # artefacts are, and the detail file is where a reader can actually look something up.
    # The S3 prefix is one line down in that section.
    L.append(f"| [`{x['run']}`]({DETAIL_NAME}#{anchor(x['run'])}) | {x['date']} | {x['label']} | "
             f"{x['profile']} | {x['users']} | {x['window']} | {x['inflight']} | "
             f"{x['indevices']} | {x['requests']} | {x['failed_pct']}% | {x['p95']} | "
             f"{x['fullp95']} | {x['rps']} |")
L.append("")
# **The detail is a separate file, because the index has to stay readable.** One run contributes
# a dozen rows of settings and environment, so at thirty runs this file would be four hundred
# lines of which the first forty are the part anyone reads. The index answers "what has been run
# and how did it do"; the detail answers "what exactly was that run", which is a question about
# one run at a time and belongs where it can be linked to. Placed here rather than at the foot:
# it tells the reader where to go next, and the caveats below are about the table above it.
L.append(f"Per-run settings and environment are in [`{DETAIL_NAME}`]({DETAIL_NAME}), linked "
         "from each run id in the table.\n")

# Excluded runs carry their own section with the full reason, so repeating their caveats under a
# heading that says "the runs above" would point at rows that are no longer there.
_excluded_ids = {y['run'] for y in rows if y.get('excluded')}
problems = [(r, why) for r, why in problems if r not in _excluded_ids]

_ex = [y for y in rows if y.get('excluded')]
if _ex:
    L.append("## Runs that are not measurements\n")
    L.append("Kept rather than deleted — these are the evidence for a finding of their own — but "
             "out of the table above, because a row beside comparable runs reads as comparable:\n")
    L.append("| run | date (IST) | arrival window | rps | p95 ms | why it is not a measurement |")
    L.append("|---|---|---|---|---|---|")
    for x in _ex:
        L.append(f"| [`{x['run']}`]({DETAIL_NAME}#{anchor(x['run'])}) | {x['date']} | "
                 f"{x['window']} | {x['rps']} | {x['p95']} | {x['excluded'].get('reason','—')} |")
    L.append("")
    L.append("Each carries a `provenance-correction.json` in its own prefix with the evidence, the "
             "cause and what it was recorded as. The runs' own `run-metadata.json` is left exactly "
             "as written.\n")

if problems:
    L.append("## Caveats on the runs above\n")
    L.append("Listed rather than left blank, because a blank column reads as a measurement "
             "and not as a missing one:\n")
    for r, why in problems:
        L.append(f"- `{r}` — {why}")
    L.append("")

D = []
D.append("# Run log — detail\n")
D.append(f"Generated from `s3://{bucket}/{prefix}/` by `tools/update-run-log.sh` "
         f"(`make run_log`) — last refreshed {now}.\n")
D.append("**Do not edit by hand.** Rewritten wholesale on every run of that script, as "
         f"[`{INDEX_NAME}`]({INDEX_NAME}) is. That file is the index and carries the results "
         "table and any caveats; this one records what each run was configured with and what "
         "environment it met, which is what makes a number interpretable once the environment "
         "is gone.\n")
for r, link, meta, stats, sha7, corr in details:
    D.append(f"## `{r}`\n")
    D.append(f"Artefacts: `{link}`\n")
    D.append("| | |")
    D.append("|---|---|")
    if stats:
        D.append(f"| requests (ok) | {stats.get('requests','—')} |")
        D.append(f"| failed | {stats.get('failed','—')} ({stats.get('failed_pct','—')}%) |")
        D.append(f"| response time p50 / p95 / p99 / max ms | "
                 f"{stats.get('p50_ms','—')} / {stats.get('p95_ms','—')} / "
                 f"{stats.get('p99_ms','—')} / {stats.get('max_ms','—')} |")
        D.append(f"| mean ms | {stats.get('mean_ms','—')} |")
        D.append(f"| mean throughput rps | {stats.get('rps','—')} |")
    if meta:
        cs = (corr.get('actual') or {}).get('simulation.gitSha') if corr else None
        cd = (corr.get('actual') or {}).get('simulation.gitDirty') if corr else None
        if cs:
            D.append(f"| harness commit | `{cs}` — **corrected**, the run recorded "
                     f"`{at(meta,'simulation.gitSha','—')}` |")
        else:
            D.append(f"| harness commit | {at(meta,'simulation.gitSha','—')} "
                     f"(run id says `{sha7}`) |")
        if cd is not None:
            D.append(f"| tree dirty | {cd} — **corrected**, the run recorded "
                     f"`{at(meta,'simulation.gitDirty','—')}` |")
        else:
            D.append(f"| tree dirty | {at(meta,'simulation.gitDirty','—')} |")
        D.append(f"| target | {at(meta,'target.baseUrl','—')} |")
        D.append(f"| server build | {at(meta,'target.serverBuild','—')} |")
        D.append(f"| dataset | {at(meta,'dataset','—')} |")
        D.append(f"| injector | {at(meta,'settings.injector.label','—')} "
                 f"({at(meta,'settings.injector.os','—')}, {at(meta,'settings.injector.cpus','—')} cpu, "
                 f"heap {at(meta,'settings.injector.maxHeapMb','—')} MB) |")
        D.append(f"| injector RTT min / median ms | {at(meta,'settings.injector.rtt.minMillis','—')} / "
                 f"{at(meta,'settings.injector.rtt.medianMillis','—')} |")
        D.append(f"| est. sync overhead s | {at(meta,'settings.injector.rtt.estimatedSyncOverheadSeconds','—')} |")
        D.append(f"| injection | profile {at(meta,'settings.injection.profile','—')}, "
                 f"{at(meta,'settings.injection.userCount','—')} users arriving over "
                 f"{window}, ~{inflight.lstrip('~')} requests in flight (rps x mean), "
                 f"ramp {at(meta,'settings.injection.rampPeriodSeconds','—')} s |")
        D.append(f"| sync | mode {at(meta,'settings.sync.syncMode','—')}, "
                 f"feeder {at(meta,'settings.sync.feeder','—')} "
                 f"({at(meta,'settings.sync.feederRows','—')} rows), "
                 f"auth {at(meta,'settings.sync.authMode','—')}, "
                 f"page {at(meta,'settings.sync.pageSize','—')} |")
        D.append(f"| entities | {at(meta,'entityTable.pulled','—')} pulled of "
                 f"{at(meta,'entityTable.total','—')} ({at(meta,'entityTable.source','—')}) |")
        D.append(f"| push / co-tenants | {at(meta,'settings.push.enabled','—')} / "
                 f"{at(meta,'settings.coTenants.enabled','—')} |")
        syncs = next((x['syncs'] for x in rows if x['run'] == r), None)
        if syncs:
            # **Per *sync*, not per request.** Every percentile above is a request; a cohort's
            # question is what a device experienced, and the two diverge once requests queue.
            D.append(f"| sync duration p50 / mean / p95 s | {syncs['p50']:.1f} / "
                     f"{syncs['mean']:.1f} / {syncs['p95']:.1f} ({syncs['n']} syncs) |")
            if 'full_p95' in syncs:
                D.append(f"| full syncs p50 / p95 s | {syncs['full_p50']:.1f} / "
                         f"{syncs['full_p95']:.1f} ({syncs['full_n']} of {syncs['n']}, "
                         f"{syncs['full_source']}) |")
            elif 'full_none' in syncs:
                D.append(f"| full syncs | none — `SYNC_MODE={syncs['full_none']}` produced no "
                         f"sync that pulled from 1900 |")
            else:
                D.append("| full syncs | unknown — the run recorded no split and its mode does "
                         "not settle it |")
        else:
            D.append("| sync duration | not archived — predates sync-durations.csv (5 Oct 2026) |")
        D.append(f"| cache policy | {at(meta,'environment.cachePolicy','—')} |")
        D.append(f"| autovacuum | {at(meta,'environment.autovacuum','—')} |")
    D.append("")

pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
pathlib.Path(out).write_text("\n".join(L))
detail_path = pathlib.Path(out).with_name(DETAIL_NAME)
detail_path.write_text("\n".join(D))
print(f"wrote {out}: {len(rows)} run(s), {len(problems)} caveat(s)")
print(f"wrote {detail_path}: {len(details)} run(s)")
PY
