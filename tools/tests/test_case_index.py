"""update-case-index.py owns the generated cells of a case table and nothing else.

The hand-written parts -- the variation cell, placeholder rows, prose -- are what make the index
worth reading, so the property under test is that a refresh never touches them, while every
generated cell follows the run log and a new run lands flagged rather than silently.
"""
import importlib.util, json
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "uci", Path(__file__).resolve().parents[1] / "update-case-index.py")
uci = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(uci)

RUN_LOG = """\
| run | date (IST) | scenario | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|
| [`2026-10-05T08-38-47Z-case1-aaaaaaa`](run-log-detail.md#2026-10-05t08-38-47z-case1-aaaaaaa) | x | case1 | 0.0% | 202 | 0.13 |
| [`2026-10-06T05-38-32Z-case2-bbbbbbb`](run-log-detail.md#2026-10-06t05-38-32z-case2-bbbbbbb) | x | case2 | 0.5% | 288 | 4.21 |

## not measurements

| run | date (IST) | arrival window | rps | p95 ms | why it is not a measurement |
|---|---|---|---|---|---|
| [`2026-10-05T11-37-03Z-case1-ccccccc`](run-log-detail.md#2026-10-05t11-37-03z-case1-ccccccc) | x | 60s | 1 | 2 | started cold, which costs two thirds of throughput |
"""
DETAIL = """\
## `2026-10-05T08-38-47Z-case1-aaaaaaa`
| dataset | tanuh-small-v2 |
## `2026-10-06T05-38-32Z-case2-bbbbbbb`
| dataset | states-day-180 |
## `2026-10-05T11-37-03Z-case1-ccccccc`
| dataset | tanuh-small-v2 |
"""
INDEX = """\
| case | what it tests | runs | findings |
|---|---|---|---|
| [**1**](#case-1) | Training | 1 | f |
| [**2**](#case-2) | Steady | 0 + 1 running | f |

<a id="case-1"></a>
## Case 1

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| [`2026-10-05 08:38`](run-log-detail.md#2026-10-05t08-38-47z-case1-aaaaaaa) | 15 min window | stale | 1 | 9.9% | 1 | 9.99 |

**Findings:** prose that must survive.

<a id="case-2"></a>
## Case 2

| run (UTC) | variation | dataset | syncs | failed | p95 ms | CPU s/sync |
|---|---|---|---|---|---|---|
| *row 9 — running* | hand-written placeholder | | | | | |

**Findings:** more prose.
"""


def _refresh(tmp_path):
    (tmp_path / "run-log.md").write_text(RUN_LOG)
    (tmp_path / "run-log-detail.md").write_text(DETAIL)
    (tmp_path / "cpu-per-sync.json").write_text(json.dumps(
        {"2026-10-05T08-38-47Z-case1-aaaaaaa": {"syncs": 100}}))
    runs, excl = uci.read_run_log(tmp_path)
    return uci.refresh(INDEX, runs, excl, uci.read_datasets(tmp_path), uci.read_syncs(tmp_path))


def test_generated_cells_follow_the_run_log_and_the_variation_does_not(tmp_path):
    text, rep = _refresh(tmp_path)
    row = next(l for l in text.splitlines() if "case1-aaaaaaa" in l)
    assert row == ("| [`2026-10-05 08:38`](run-log-detail.md#2026-10-05t08-38-47z-case1-aaaaaaa) "
                   "| 15 min window | tanuh-small-v2 | 100 | 0.0% | 202 | 0.13 |")
    assert "2026-10-05T08-38-47Z-case1-aaaaaaa" in rep["updated"]


def test_a_new_run_lands_in_its_case_flagged_and_a_placeholder_survives(tmp_path):
    text, rep = _refresh(tmp_path)
    lines = text.splitlines()
    new = next(l for l in lines if "case2-bbbbbbb" in l)
    assert uci.NEW_FLAG in new and "states-day-180" in new and "| — | 0.5% | 288 | 4.21 |" in new
    assert "| *row 9 — running* | hand-written placeholder |" in text
    # appended at the end of case 2's table, before its prose
    i = lines.index(new)
    assert lines[i - 1].startswith("| *row 9") and lines[i + 1] == ""
    assert "**Findings:** more prose." in text and "prose that must survive" in text


def test_an_excluded_run_renders_with_its_reason_and_is_not_counted(tmp_path):
    text, rep = _refresh(tmp_path)
    row = next(l for l in text.splitlines() if "case1-ccccccc" in l)
    assert "| — | — | — | **not a measurement** — started cold" in row
    # case 1 now holds one measured row and one excluded: the glance count stays 1
    assert "| [**1**](#case-1) | Training | 1 | f |" in text
    # a prose count is left alone
    assert "| [**2**](#case-2) | Steady | 0 + 1 running | f |" in text


def test_it_is_idempotent(tmp_path):
    text, _ = _refresh(tmp_path)
    (tmp_path / "x").mkdir()
    runs, excl = uci.read_run_log(tmp_path)
    again, rep = uci.refresh(text, runs, excl, uci.read_datasets(tmp_path), uci.read_syncs(tmp_path))
    assert again == text and rep["added"] == [] and rep["updated"] == []


def test_long_reasons_are_cut_at_a_word():
    r = uci.short("word " * 60)
    assert r.endswith(" …") and len(r) <= uci.REASON_CHARS + 2 and not r[:-2].endswith(" ")
