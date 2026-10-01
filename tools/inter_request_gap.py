"""What the gap between a client's requests actually is, from the server's own logs.

    python3 tools/inter_request_gap.py server.log
    python3 tools/inter_request_gap.py server.log --user state-1-u201000001@org10
    zcat prod-logs/*.gz | python3 tools/inter_request_gap.py -

**Why this exists.** `BASE_MS_PER_RECORD` is fitted, not measured. F7 fits it so the simulation's
total duration matches production's observed slope, which makes durations right and says nothing
about whether the *shape* is right -- 8.5 s between pages may be the client's real think time or
may be the simulation standing in for a server slower than this one. D7's client telemetry would
settle it and is deferred on fleet rollout.

**But the server already logs it.** `AuthenticationFilter` records, per request, at INFO:

    GET /encounter?...page=3&size=1000 Status: 200 User: x@org Organisation: y Time: 62 ms

With the log timestamp, consecutive requests from one user give

    gap = t[n+1] - t[n] - server_time[n]

which is the client's parse-and-persist plus one network round trip. That is the quantity the
storage model exists to represent, measured from the far end, and it needs no client change and no
fleet rollover.

**Validate it here before trusting it on production.** Run it against this environment's logs for a
run whose pauses are known -- the simulation reports them per sync in `build/sync-durations.csv`.
If the recovered gap matches the modelled pause, the method is sound and can be pointed at
production. If it does not, the method is wrong and production's numbers would be too.

**What the gap is not.** It includes one network round trip, so a device on a slow link reads as a
slower client. It also cannot see a client that pipelines or parallelises: Avni's client syncs
entities in sequence, so consecutive requests from one user really are consecutive, but a run that
shows negative or near-zero gaps is evidence that assumption has broken rather than evidence of an
infinitely fast client.
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime

# Spring Boot's default pattern puts the timestamp first at millisecond precision, and
# AuthenticationFilter's own format supplies the rest. Tolerant of whatever sits between them --
# thread name, logger, MDC -- because that varies by deployment and none of it is needed.
LINE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[.,]\d{3})"
    r".*?(?P<method>GET|POST|PUT|PATCH|DELETE)\s+(?P<uri>/\S*?)"
    r"(?:\?(?P<query>\S*))?\s+Status:\s*(?P<status>\d+)"
    r"\s+User:\s*(?P<user>\S+)"
    r".*?Time:\s*(?P<ms>\d+)\s*ms"
)


# A line that carries this but does not parse is a format mismatch, not an irrelevant line. The
# distinction is the whole point of counting: a log is mostly Hibernate, Spring and Tomcat noise
# that should be skipped without comment, while an AuthenticationFilter line the regex misses means
# the format moved and every number below it is drawn from whatever happened to still match.
FILTER_MARKER = "Status:"


def parse(fh, stats: dict | None = None):
    """Records from a log, skipping lines that are not AuthenticationFilter's completed requests.

    `stats` is updated in place with `lines`, `matched`, `unparsed` and up to a few `samples` of
    lines that looked like they should have parsed and did not. **Skipping is expected; skipping
    silently is not** -- a format change would otherwise leave this reporting a tiny unrepresentative
    sample as though it were three months of production.
    """
    st = stats if stats is not None else {}
    st.setdefault("lines", 0)
    st.setdefault("matched", 0)
    st.setdefault("unparsed", 0)
    st.setdefault("samples", [])
    for raw in fh:
        st["lines"] += 1
        m = LINE.search(raw)
        if not m:
            if FILTER_MARKER in raw:
                st["unparsed"] += 1
                if len(st["samples"]) < 3:
                    st["samples"].append(raw.strip()[:200])
            continue
        st["matched"] += 1
        d = m.groupdict()
        ts = datetime.strptime(d["ts"].replace(",", ".").replace("T", " "),
                               "%Y-%m-%d %H:%M:%S.%f")
        q = d.get("query") or ""
        size = re.search(r"(?:^|&)size=(\d+)", q)
        page = re.search(r"(?:^|&)page=(\d+)", q)
        yield {
            "ts": ts,
            "user": d["user"],
            "entity": d["uri"].strip("/").split("/")[0] or "(root)",
            "uri": d["uri"],
            "status": int(d["status"]),
            "server_ms": int(d["ms"]),
            "size": int(size.group(1)) if size else None,
            "page": int(page.group(1)) if page else None,
        }


def gaps(records):
    """Per user, the gap between each request and the one before it, net of server time.

    Buffers, so it is for a log small enough to hold -- one run, or one day. Use `stream_gaps` for
    production's three months: a hundred million requests of these dicts is not going to fit, and
    the percentiles do not need them all.
    """
    by_user = defaultdict(list)
    for r in records:
        by_user[r["user"]].append(r)

    out = []
    for user, rs in by_user.items():
        rs.sort(key=lambda r: r["ts"])
        for prev, cur in zip(rs, rs[1:]):
            wall = (cur["ts"] - prev["ts"]).total_seconds() * 1000
            # The previous request's server time is inside that wall-clock gap, so netting it out
            # leaves the client's own work plus one round trip. Attributed to the request that
            # *preceded* the gap, because that is the page the client was persisting.
            out.append({**prev, "user": user, "next": cur,
                        "gap_ms": wall - prev["server_ms"], "wall_ms": wall})
    return out


# A log is not sorted by user, so streaming needs the previous request per user held open. Bounded
# because production has thousands of users over three months and only a few hundred are ever mid
# sync: an entry older than this is a sync that ended, and the next request from that user starts a
# new one rather than continuing the old.
STALE_AFTER_SECONDS = 600


def stream_gaps(records, *, stale_after=STALE_AFTER_SECONDS):
    """The same gaps, one at a time, holding only the last request per active user.

    **Assumes the log is in time order per user**, which a server's own log is. A gap is emitted
    only when the previous request from that user is recent enough to be the same sync -- a user
    whose last request was an hour ago is starting a new one, and the hour between them is not a
    client persisting a page.
    """
    last: dict[str, dict] = {}
    seen = 0
    for r in records:
        seen += 1
        prev = last.get(r["user"])
        last[r["user"]] = r
        if prev is not None:
            wall = (r["ts"] - prev["ts"]).total_seconds() * 1000
            if 0 <= wall <= stale_after * 1000 or wall < 0:
                yield {**prev, "next": r,
                       "gap_ms": wall - prev["server_ms"], "wall_ms": wall}
        # Prune occasionally rather than every line: the dict is the only unbounded thing here.
        if seen % 1_000_000 == 0:
            cutoff = r["ts"]
            last = {u: v for u, v in last.items()
                    if (cutoff - v["ts"]).total_seconds() <= stale_after}


def match_report(stats: dict) -> tuple[list[str], bool]:
    """What was read and what was skipped, so an empty or thin result has a visible cause."""
    lines, matched = stats.get("lines", 0), stats.get("matched", 0)
    unparsed, samples = stats.get("unparsed", 0), stats.get("samples", [])
    out = [f"  read {lines:,} lines, matched {matched:,} "
           f"({matched / lines * 100:.1f}%)" if lines else "  read nothing"]
    if not unparsed:
        return out, True
    # Suspicious rather than fatal below a handful: a truncated line at the end of a rotated file
    # is ordinary, a tenth of the log is not.
    share = unparsed / max(matched + unparsed, 1)
    out += ["",
            f"  {unparsed:,} lines carry {FILTER_MARKER!r} and did not parse "
            f"({share * 100:.1f}% of candidates). The format may have moved -- three months of",
            "  logs span deployments. Samples:"]
    out += [f"    {x}" for x in samples]
    return out, share < 0.10


def confirmed_full_pages(gap_records):
    """Gaps where the page just persisted is known to have been **full**.

    **`size` is what the client asked for, not what came back**, and an incremental sync mostly
    returns empty pages -- so dividing a gap by `size` is meaningless in general. That was the
    first reading of this log and it was wrong by orders of magnitude.
    
    But a client only requests `page=N+1` if page N came back full: that is what paging means. So
    when the next request from the same user is the next page of the same entity at the same size,
    the gap before it covers exactly `size` records. The response size is not in the log; this
    infers it from the client's own behaviour instead.
    """
    out = []
    for g in gap_records:
        nxt = g.get("next")
        if not nxt or g["size"] is None or g["page"] is None:
            continue
        if (nxt["entity"] == g["entity"] and nxt["size"] == g["size"]
                and nxt["page"] == g["page"] + 1 and g["gap_ms"] >= 0):
            out.append(g)
    return out


def report(records, *, model_base=2.78, model_page=112.0, stats=None) -> tuple[str, bool]:
    if stats:
        head, format_ok = match_report(stats)
    else:
        head, format_ok = [], True
    if not records:
        return ("No AuthenticationFilter lines matched. It logs at INFO, so confirm the level is "
                "not raised in this deployment, and that the pattern carries a millisecond "
                "timestamp.", False)

    g = gaps(records)
    if not g:
        return (f"{len(records):,} requests parsed but no user made two, so there is no gap to "
                f"measure. A single sync per user is enough -- check the log covers one.", False)

    lines = [f"Inter-request gaps from {len(records):,} requests, "
             f"{len({r['user'] for r in records})} users", ""] + head + [""]

    # Negative gaps mean requests overlapped, which breaks the one-at-a-time assumption the whole
    # measurement rests on. Reported rather than filtered away.
    overlapping = [x for x in g if x["gap_ms"] < 0]
    if overlapping:
        lines += [f"  {len(overlapping):,} of {len(g):,} gaps are negative -- requests from one "
                  f"user overlapped.", "  The client is not issuing these one at a time, so a "
                  "per-page gap is not meaningful for them.", ""]

    paged = [x for x in g if x["size"] and x["gap_ms"] >= 0]
    lines += [f"  {'entity':<26} {'n':>5} {'median gap':>11} {'per record':>11}  modelled"]
    for entity in sorted({x["entity"] for x in paged}):
        xs = [x for x in paged if x["entity"] == entity]
        med = statistics.median(x["gap_ms"] for x in xs)
        size = statistics.median(x["size"] for x in xs)
        per = med / size if size else float("nan")
        # What the simulation would pause for a page of this size at weight 3, the observation
        # tier. Entities on lighter tiers will read as over-modelled here, which is expected.
        modelled = model_page + size * 3.0 * model_base
        lines.append(f"  {entity:<26} {len(xs):>5} {med:>9,.0f}ms {per:>9.2f}ms  "
                     f"{modelled:>8,.0f}ms at weight 3")

    full = confirmed_full_pages(g)
    if full:
        lines += ["", "  Confirmed full pages — the client asked for the next page, so the one",
                  "  before it returned `size` records. This is the measurement that means",
                  "  something; the table above divides by a size that may not have been sent.",
                  "",
                  f"  {'entity':<22} {'size':>5} {'n':>5} {'p50 gap':>9} {'p50/rec':>9} "
                  f"{'p90/rec':>9}  modelled/rec"]
        groups = defaultdict(list)
        for x in full:
            groups[(x["entity"], x["size"])].append(x["gap_ms"])
        for (entity, size), xs in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:12]:
            xs.sort()
            p50, p90 = statistics.median(xs), xs[int(len(xs) * 0.9)]
            modelled = (model_page + size * 3.0 * model_base) / size
            lines.append(f"  {entity:<22} {size:>5} {len(xs):>5} {p50:>7,.0f}ms "
                         f"{p50 / size:>7.2f}ms {p90 / size:>7.2f}ms  {modelled:>9.2f}ms")

    # Bounded by the same staleness rule the streaming path uses: a user whose previous request
    # was hours ago started a new sync, and counting that silence as think time put a 17-hour gap
    # in this summary on the first real log.
    allgaps = sorted(x["gap_ms"] for x in g
                     if 0 <= x["gap_ms"] <= STALE_AFTER_SECONDS * 1000)
    if allgaps:
        lines += ["", f"  all gaps: p50 {statistics.median(allgaps):,.0f}ms, "
                      f"p90 {allgaps[int(len(allgaps) * 0.9)]:,.0f}ms, "
                      f"max {allgaps[-1]:,.0f}ms"]
    srv = sorted(r["server_ms"] for r in records)
    lines += [f"  server time: p50 {statistics.median(srv):,.0f}ms, "
              f"p90 {srv[int(len(srv) * 0.9)]:,.0f}ms  "
              f"(MS_PER_PAGE is {model_page:,.0f}, which should exceed this or it double-counts)"]
    return "\n".join(lines), format_ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("log", help="a server log file, or - for stdin")
    ap.add_argument("--user", help="only this username")
    ap.add_argument("--base", type=float, default=2.78,
                    help="BASE_MS_PER_RECORD to compare against")
    a = ap.parse_args(argv)

    stats: dict = {}
    fh = sys.stdin if a.log == "-" else open(a.log, errors="replace")
    try:
        records = list(parse(fh, stats))
    finally:
        if fh is not sys.stdin:
            fh.close()
    if a.user:
        records = [r for r in records if r["user"] == a.user]

    text, ok = report(records, model_base=a.base, stats=stats)
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
