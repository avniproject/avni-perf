"""NRQL truncates a raw query at 5,000 rows and says nothing. These are the tests that the
exporter notices.

A backup that quietly holds a prefix of each hour is worse than no backup: it reads as complete,
and the data it is missing cannot be fetched again once retention has passed. So every case below
is about the guard rather than the download -- the fetch is given a fake Nrql whose answers are
known, and what is asserted is what the exporter *refuses* to call a complete window.
"""
import gzip
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("nx", ROOT / "tools/newrelic-export.py")
nx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nx)


class FakeNrql:
    """Serves events from a dict of timestamp -> n, honouring NRQL's row cap and half-open window."""

    def __init__(self, events, cap=nx.ROW_CAP, truncate_to=None):
        self.events, self.cap, self.truncate_to, self.queries = events, cap, truncate_to, 0

    def _in(self, a, b):
        return [{"timestamp": t, "i": i}
                for t in sorted(self.events) if a <= t < b for i in range(self.events[t])]

    def __call__(self, nrql, attempts=4):
        self.queries += 1
        since, until = nrql.split("SINCE ")[1].split(" UNTIL ")
        a, b = int(since), int(until.split()[0])
        rows = self._in(a, b)
        if nrql.startswith("SELECT count(*)"):
            return [{"count": len(rows)}]
        return rows[:self.truncate_to if self.truncate_to is not None else self.cap]


def _fetch(q, a, b):
    shortfalls = []
    rows = nx.fetch(q, "Transaction", a, b, nx.count(q, "Transaction", a, b), shortfalls)
    return rows, shortfalls


def test_a_window_under_the_cap_is_one_query_and_complete():
    q = FakeNrql({1000 + i: 1 for i in range(100)})
    rows, shortfalls = _fetch(q, 0, 10_000)
    assert len(rows) == 100 and shortfalls == []


def test_a_window_over_the_cap_is_bisected_until_every_piece_is_whole():
    # 12,000 events over 12,000 ms: one query would return 5,000 and look like an answer.
    q = FakeNrql({1000 + i: 1 for i in range(12_000)})
    rows, shortfalls = _fetch(q, 0, 20_000)
    assert len(rows) == 12_000, "bisection must return every event, not the first 5,000"
    assert shortfalls == []
    assert len({r["timestamp"] for r in rows}) == 12_000, "no event counted twice at a boundary"


def test_events_packed_into_one_millisecond_are_reported_not_silently_cut():
    # The one case bisection cannot solve: the window is already indivisible.
    q = FakeNrql({1234: 6_000})
    rows, shortfalls = _fetch(q, 1000, 2000)
    assert len(shortfalls) == 1
    assert shortfalls[0]["expected"] == 6_000 and shortfalls[0]["got"] == nx.ROW_CAP
    assert "cannot be split" in shortfalls[0]["why"]


def test_a_query_returning_less_than_its_count_is_a_shortfall():
    q = FakeNrql({1000 + i: 1 for i in range(200)}, truncate_to=150)
    rows, shortfalls = _fetch(q, 0, 10_000)
    assert len(rows) == 150
    assert len(shortfalls) == 1 and shortfalls[0]["expected"] == 200
    assert shortfalls[0]["got"] == 150


def test_the_exporter_is_not_told_how_many_events_there_are():
    """fetch() takes the count as an argument; it must come from count(*), not from a guess."""
    q = FakeNrql({1000 + i: 1 for i in range(9_000)})
    shortfalls = []
    # An understated expectation must not become a quietly truncated export.
    rows = nx.fetch(q, "Transaction", 0, 20_000, 100, shortfalls)
    assert len(shortfalls) == 1, "a count that disagrees with the query has to surface"


def test_an_hour_is_written_as_readable_gzipped_jsonl(tmp_path):
    rows = [{"timestamp": 1, "name": "WebTransaction/x"}, {"timestamp": 2, "duration": 0.18}]
    path = tmp_path / "Transaction/2026-10-12/02.jsonl.gz"
    digest = nx.write(path, rows)
    with gzip.open(path, "rt") as fh:
        back = [json.loads(line) for line in fh]
    assert back == rows
    assert len(digest) == 64
    assert not list(path.parent.glob("*.partial")), "no half-written hour is left behind"


def test_write_is_atomic_so_a_broken_run_leaves_no_complete_looking_hour(tmp_path, monkeypatch):
    path = tmp_path / "Transaction/2026-10-12/03.jsonl.gz"
    boom = [{"timestamp": 1}, object()]       # not JSON-serialisable: fails mid-write
    try:
        nx.write(path, boom)
    except TypeError:
        pass
    assert not path.exists(), "the final path must not appear unless the whole hour was written"


def test_hours_covers_the_window_without_gaps_or_overlap():
    import datetime as dt
    spans = list(nx.hours(dt.datetime(2026, 10, 12, 2, 30), dt.datetime(2026, 10, 12, 6)))
    assert spans[0][0] == dt.datetime(2026, 10, 12, 2), "a partial hour is taken from its start"
    assert [b for _, b in spans[:-1]] == [a for a, _ in spans[1:]], "no gap, no overlap"
    assert spans[-1][1] == dt.datetime(2026, 10, 12, 6)
