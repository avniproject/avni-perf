"""The gap measurement. Run: make test_tools"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import inter_request_gap as irg

FMT = ("{ts}  INFO 1 --- [http-nio-8021-exec-3] o.a.s.f.s.AuthenticationFilter : "
       "GET {uri}?page={page}&size={size} Status: 200 User: {user} Organisation: org Time: {ms} ms")


def log(gap_ms, server_ms=62, size=1000, pages=6, user="u@org", uri="/individual"):
    t = datetime(2026, 10, 1, 12, 0, 0)
    out = []
    for page in range(pages):
        out.append(FMT.format(ts=f"{t:%Y-%m-%d %H:%M:%S}.{t.microsecond // 1000:03d}",
                              uri=uri, page=page, size=size, user=user, ms=server_ms))
        t += timedelta(milliseconds=server_ms + gap_ms)
    return out


def test_it_recovers_the_gap_it_was_given():
    """Netting the server's own time out of the wall-clock interval is the whole arithmetic, and
    getting it backwards would overstate the client by the server's response time."""
    g = irg.gaps(list(irg.parse(log(8452, server_ms=62))))
    assert len(g) == 5
    assert all(abs(x["gap_ms"] - 8452) < 1 for x in g)


def test_the_server_time_is_subtracted_not_added():
    slow = irg.gaps(list(irg.parse(log(1000, server_ms=500))))
    assert all(abs(x["gap_ms"] - 1000) < 1 for x in slow), "a slow server must not inflate the gap"


def test_gaps_are_per_user_not_across_the_log():
    """Two users interleaved in one log must not produce a gap between them -- that would measure
    the arrival rate of the fleet rather than one client's think time."""
    a, b = log(5000, user="a@org"), log(5000, user="b@org")
    merged = [x for pair in zip(a, b) for x in pair]
    g = irg.gaps(list(irg.parse(merged)))
    assert {x["user"] for x in g} == {"a@org", "b@org"}
    assert all(abs(x["gap_ms"] - 5000) < 1 for x in g)


def test_overlapping_requests_are_reported_rather_than_hidden():
    """A negative gap means one user had two requests in flight, which breaks the assumption the
    measurement rests on. Averaging it away would turn a broken premise into a fast client.

    It takes a *slow* previous request to produce one: the second request has to arrive before the
    first finished being served. A second request merely arriving soon after is a small gap, not a
    negative one -- which is what the first version of this test got wrong.
    """
    lines = [
        FMT.format(ts="2026-10-01 12:00:00.000", uri="/individual", page=0, size=1000,
                   user="u@org", ms=500),
        FMT.format(ts="2026-10-01 12:00:00.100", uri="/encounter", page=0, size=1000,
                   user="u@org", ms=62),
    ]
    g = irg.gaps(list(irg.parse(lines)))
    assert g and g[0]["gap_ms"] < 0, "500ms of serving against a 100ms interval is an overlap"
    text, ok = irg.report(list(irg.parse(lines)))
    assert "negative" in text


def test_a_log_with_no_matching_lines_says_so():
    text, ok = irg.report(list(irg.parse(["some unrelated line", "2026-01-01 nope"])))
    assert not ok and "AuthenticationFilter" in text


def test_a_single_request_per_user_is_not_a_measurement():
    text, ok = irg.report(list(irg.parse(log(5000, pages=1))))
    assert not ok and "no gap to measure" in text


def test_it_flags_ms_per_page_double_counting_the_server():
    """MS_PER_PAGE was 174 and the server took 62 of it. The report puts both side by side so the
    same mistake is visible rather than needing to be remembered."""
    text, _ = irg.report(list(irg.parse(log(8452, server_ms=62))))
    assert "double-counts" in text and "server time: p50 62ms" in text


# --- skipping is expected; skipping silently is not -------------------------------------------
#
# A production log is mostly Hibernate, Spring and Tomcat noise, and those lines should go without
# comment. But an AuthenticationFilter line the regex misses means the format moved, and three
# months of logs span deployments -- so the tool would otherwise report whatever still matched as
# though it were the fleet.

def test_irrelevant_lines_are_skipped_without_comment():
    stats = {}
    recs = list(irg.parse(["some hibernate line", "o.s.b.w.e.t.TomcatWebServer started", ""],
                          stats))
    assert recs == []
    assert stats["lines"] == 3 and stats["matched"] == 0 and stats["unparsed"] == 0


def test_a_candidate_line_that_fails_to_parse_is_counted_and_sampled():
    """`Status:` is what AuthenticationFilter's completed-request line carries, so a line with it
    that does not parse is the format having moved rather than an unrelated line."""
    stats = {}
    list(irg.parse(["GARBLED Status: 200 User: missing the rest"], stats))
    assert stats["unparsed"] == 1
    assert stats["samples"] and "GARBLED" in stats["samples"][0]


def test_the_match_rate_is_reported():
    stats = {}
    recs = list(irg.parse(log(8452) + ["unrelated"], stats))
    text, ok = irg.report(recs, stats=stats)
    assert ok
    assert f"read {stats['lines']:,} lines, matched {stats['matched']:,}" in text


def test_a_log_whose_format_moved_fails_rather_than_reporting_a_thin_sample():
    """Two parseable requests out of a log that is mostly unparseable candidates is not a
    measurement of production, and returning zero would say it was."""
    stats = {}
    bad = [f"GARBLED {i} Status: 200 x" for i in range(50)]
    recs = list(irg.parse(log(8452, pages=2) + bad, stats))
    text, ok = irg.report(recs, stats=stats)
    assert not ok, "96% of candidates unparsed should not report success"
    assert "format may have moved" in text


def test_a_few_truncated_lines_do_not_fail_the_run():
    """A rotated file's last line is routinely half-written. That is not a format change."""
    stats = {}
    recs = list(irg.parse(log(8452, pages=40) + ["TRUNCATED Status: 2"], stats))
    _, ok = irg.report(recs, stats=stats)
    assert ok


# --- streaming, for three months of logs -------------------------------------------------------

def test_streaming_finds_the_same_gaps_as_buffering():
    recs = list(irg.parse(log(5000, pages=8)))
    assert [round(x["gap_ms"]) for x in irg.stream_gaps(recs)] == \
           [round(x["gap_ms"]) for x in irg.gaps(recs)]


def test_streaming_keeps_users_apart():
    a, b = log(5000, user="a@org"), log(7000, user="b@org")
    merged = sorted(irg.parse([x for pair in zip(a, b) for x in pair]), key=lambda r: r["ts"])
    got = {}
    for x in irg.stream_gaps(merged):
        got.setdefault(x["user"], []).append(round(x["gap_ms"]))
    assert all(abs(v - 5000) < 2 for v in got["a@org"])
    assert all(abs(v - 7000) < 2 for v in got["b@org"])


def test_a_long_silence_is_not_a_client_persisting_a_page():
    """Two syncs hours apart from one user are two syncs. Counting the interval between them as
    think time would put an hour of idleness into the per-record cost."""
    first = log(5000, pages=3, user="u@org")
    later = log(5000, pages=3, user="u@org")
    later = [l.replace("12:00:", "15:00:") for l in later]
    recs = sorted(irg.parse(first + later), key=lambda r: r["ts"])
    gaps = [x["gap_ms"] for x in irg.stream_gaps(recs)]
    assert max(gaps) < irg.STALE_AFTER_SECONDS * 1000
    assert len(gaps) == 4, "two syncs of three requests give two gaps each, not five"
