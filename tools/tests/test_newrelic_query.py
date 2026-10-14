"""Resolving a run to a UTC window, which is the only place this tool can be confidently wrong.

Everything else it does is arithmetic over events whose timestamps are facts. The window is
inferred, and a window that is wrong produces a table that looks entirely reasonable while
describing a different run -- the failure this exercise has hit most often. So the window is what
is tested.
"""
import datetime as dt
import gzip
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("nq", ROOT / "tools/newrelic-query.py")
nq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nq)

HEADER = ("| run | date (IST) | scenario | profile | users | arrival window | a | b | requests |\n"
          "|---|---|---|---|---|---|---|---|---|\n")


def _log(tmp_path, monkeypatch, rows):
    path = tmp_path / "run-log.md"
    path.write_text(HEADER + "".join(
        f"| [`{r}`](run-log-detail.md#x) | d | s | steady | 10 | {w} | ~0 | ~0 | 1 |\n"
        for r, w in rows))
    monkeypatch.setattr(nq, "RUN_LOG", path)
    return path


def test_the_arrival_window_is_read_in_minutes_and_seconds(tmp_path, monkeypatch):
    _log(tmp_path, monkeypatch, [("2026-10-06T05-38-32Z-case2-aaa", "240min @ 42/h"),
                                 ("2026-10-07T00-00-00Z-case1-bbb", "90s")])
    runs = nq.runs()
    s, e, _ = runs["2026-10-06T05-38-32Z-case2-aaa"]
    assert e - s == dt.timedelta(minutes=240)
    s, e, _ = runs["2026-10-07T00-00-00Z-case1-bbb"]
    assert e - s == dt.timedelta(seconds=90), "a burst in seconds must not be read as minutes"


def test_a_runs_tail_cannot_reach_into_the_next_run(tmp_path, monkeypatch):
    # Back-to-back on one box: pair C ends 5 minutes before pair D arrives, and the default
    # 20-minute tail would otherwise blend the two.
    _log(tmp_path, monkeypatch, [("2026-10-09T06-55-00Z-case11-pairC-a", "60min"),
                                 ("2026-10-09T08-00-00Z-case11-pairD-a", "60min")])
    _, since, until = nq.resolve("pairC", tail_min=20)
    assert until == dt.datetime(2026, 10, 9, 8, 0), "the next run's start is a hard ceiling"
    assert since == dt.datetime(2026, 10, 9, 6, 55)


def test_the_last_run_keeps_its_whole_tail(tmp_path, monkeypatch):
    _log(tmp_path, monkeypatch, [("2026-10-14T04-26-19Z-case6-a", "60min")])
    _, since, until = nq.resolve("case6", tail_min=20)
    assert until - since == dt.timedelta(minutes=80), "nothing follows it, so nothing bounds it"


def test_an_ambiguous_run_name_refuses_rather_than_taking_the_first(tmp_path, monkeypatch):
    _log(tmp_path, monkeypatch, [("2026-10-12T02-00-00Z-case9-12a-a", "45min"),
                                 ("2026-10-12T04-00-00Z-case9-12b-a", "45min")])
    try:
        nq.resolve("case9", tail_min=20)
    except SystemExit as exc:
        assert "matches 2 runs" in str(exc)
    else:
        raise AssertionError("'case9' names two runs; picking one silently misattributes a figure")


def test_a_run_with_no_parseable_window_is_a_point_not_a_guess(tmp_path, monkeypatch):
    _log(tmp_path, monkeypatch, [("2026-10-14T04-26-19Z-caseX-a", "-")])
    _, since, until = nq.resolve("caseX", tail_min=20)
    assert until - since == dt.timedelta(minutes=20), "only the tail, never an invented duration"


def test_only_the_hours_overlapping_the_window_are_opened(tmp_path, monkeypatch):
    out = tmp_path / "bk"
    for hour, ts in [("00", 0), ("05", 5), ("09", 9)]:
        p = out / "Transaction" / "2026-10-09" / f"{hour}.jsonl.gz"
        p.parent.mkdir(parents=True, exist_ok=True)
        base = int(dt.datetime(2026, 10, 9, ts, 30, tzinfo=dt.timezone.utc).timestamp() * 1000)
        with gzip.open(p, "wt") as fh:
            fh.write(json.dumps({"timestamp": base, "name": f"h{hour}", "duration": 0.1}) + "\n")
    rows = list(nq.read(out, "Transaction",
                        dt.datetime(2026, 10, 9, 4), dt.datetime(2026, 10, 9, 6)))
    assert [r["name"] for r in rows] == ["h05"], "hours outside the window must be skipped"


def test_summarise_reports_database_time_per_call(tmp_path):
    rows = [{"name": "x", "duration": 0.2, "databaseDuration": 0.05, "databaseCallCount": 25.0},
            {"name": "x", "duration": 0.3, "databaseDuration": 0.07, "databaseCallCount": 25.0}]
    [t] = nq.summarise(rows, "name")
    assert t["n"] == 2 and round(t["db_calls"], 1) == 25.0
    # The measure the co-tenant and soak findings turn on: db ms / call, not db ms alone.
    assert round(t["ms_per_call"], 2) == 2.40
