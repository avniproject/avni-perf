#!/usr/bin/env python3
"""Refresh the run tables in docs/case-index.md from the run log.

    ./tools/update-case-index.py [--docs docs] [--check]

Run by update-run-log.sh after every refresh, so a run that lands in the run log lands here
in the same pass. What it owns and what it leaves alone:

  generated, per run row   the link and its UTC date, dataset, syncs, failed, p95, CPU s/sync,
                           and the "not a measurement" cell with the run log's reason
  kept verbatim            the *variation* cell of every existing row, every row that has no
                           run link (the hand-written "row 22 -- running" placeholders), and
                           all prose
  added                    a row for any run in the run log that no case table holds yet,
                           at the end of its case's table, with the variation cell flagged
                           *(new -- describe the variation)* until someone writes it
  at a glance              the "runs" count, only where the cell is a plain integer; a cell
                           like "1 + 1 running" is prose and stays

Rows are keyed by run id, so this is idempotent: a flagged variation survives until edited and
a run is never added twice. A run whose label names no case (see CASE_OF) is reported and not
placed, rather than guessed into a section.

Sources, all generated upstream: run-log.md's main table (failed, p95, CPU s/sync) and its
"not a measurement" table (the reason), run-log-detail.md (dataset), cpu-per-sync.json (syncs).
"""
import json, re, sys
from pathlib import Path

# run label -> the <a id="..."> of the section whose table holds it
CASE_OF = [
    (re.compile(r"-case(\d+)-"), lambda m: f"case-{m[1]}"),
    (re.compile(r"-media-hour-"), lambda m: "case-15"),   # the run label predates the number
]
NEW_FLAG = "*(new — describe the variation)*"
NOT_A_MEASUREMENT = "**not a measurement**"


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def read_run_log(docs):
    """run id -> dict(link, failed, p95, cpu) from the main table; id -> reason from the other."""
    runs, excluded = {}, {}
    header = None
    for line in (docs / "run-log.md").read_text().splitlines():
        if line.startswith("| run |"):
            header = cells(line); continue
        if line.startswith("|---") or not line.startswith("| [`"):
            continue
        row = dict(zip(header, cells(line)))
        m = re.match(r"\[`([^`]+)`\]\((run-log-detail\.md#[^)]+)\)", row["run"])
        if not m:
            continue
        rid, href = m[1], m[2]
        if "why it is not a measurement" in row:
            excluded[rid] = (href, row["why it is not a measurement"])
        else:
            runs[rid] = dict(href=href, failed=row.get("failed", "—"), p95=row.get("p95 ms", "—"),
                             cpu=row.get("CPU s/sync", "—"))
    return runs, excluded


def read_datasets(docs):
    out, cur = {}, None
    for line in (docs / "run-log-detail.md").read_text().splitlines():
        m = re.match(r"## `([^`]+)`", line)
        if m:
            cur = m[1]; continue
        if cur and line.startswith("| dataset |"):
            out[cur] = cells(line)[1]
    return out


def read_syncs(docs):
    p = docs / "cpu-per-sync.json"
    if not p.exists():
        return {}
    return {k: v.get("syncs") for k, v in json.loads(p.read_text()).items()}


def utc_label(rid):
    m = re.match(r"(\d{4}-\d{2}-\d{2})T(\d{2})-(\d{2})-\d{2}Z", rid)
    return f"{m[1]} {m[2]}:{m[3]}" if m else rid


def case_of(rid):
    for rx, f in CASE_OF:
        m = rx.search(rid)
        if m:
            return f(m)
    return None


REASON_CHARS = 180


def short(reason):
    """The run log's reasons run to a paragraph; a table cell wants the first clause of one."""
    if len(reason) <= REASON_CHARS:
        return reason
    cut = reason[:REASON_CHARS].rsplit(" ", 1)[0]
    return cut.rstrip(",;:—- ") + " …"


def render(rid, href, variation, dataset, syncs, run, reason):
    link = f"[`{utc_label(rid)}`]({href})"
    if reason is not None:
        return f"| {link} | {variation} | {dataset} | — | — | — | {NOT_A_MEASUREMENT} — {short(reason)} |"
    s = f"{syncs}" if syncs else "—"
    return f"| {link} | {variation} | {dataset} | {s} | {run['failed']} | {run['p95']} | {run['cpu']} |"


def refresh(text, runs, excluded, datasets, syncs):
    """Return (new text, report). Pure: the caller decides whether to write."""
    lines = text.split("\n")
    report = dict(updated=[], added=[], unplaced=[], placeholders=[])
    section, in_table, table_end, seen = None, False, {}, set()
    out = []
    for line in lines:
        m = re.match(r'<a id="([^"]+)"></a>', line)
        if m:
            section = m[1]
        is_run_row = line.startswith("| [`") and section
        if is_run_row:
            c = cells(line)
            lm = re.match(r"\[`[^`]*`\]\((run-log-detail\.md#([^)]+))\)", c[0])
            rid = next((r for r in list(runs) + list(excluded)
                        if (runs.get(r, {}).get("href") or excluded.get(r, ("",))[0]) == lm[1]), None) if lm else None
            if rid:
                seen.add(rid)
                variation = c[1] if len(c) > 1 else NEW_FLAG
                if rid in excluded:
                    new = render(rid, excluded[rid][0], variation, datasets.get(rid, "—"), None, None, excluded[rid][1])
                else:
                    new = render(rid, runs[rid]["href"], variation, datasets.get(rid, "—"), syncs.get(rid), runs[rid], None)
                if new != line:
                    report["updated"].append(rid)
                out.append(new); in_table = True; continue
        if section and line.startswith("| *"):
            report["placeholders"].append((section, cells(line)[0]))
        # The section's run table is its first markdown table: any "|" line opens it, and the
        # first line that is not one closes it. Tracking only run rows missed a table that
        # held nothing but a hand-written placeholder, which is exactly the table a new run
        # most needs to land in.
        if section and line.startswith("|") and section not in table_end:
            in_table = True
        if in_table and not line.startswith("|"):
            table_end[section] = len(out)   # first non-table line after the section's run table
            in_table = False
        out.append(line)
    if in_table:
        table_end[section] = len(out)
    # append runs no table holds, newest last, each at the end of its section's table
    missing = [r for r in list(runs) + list(excluded) if r not in seen]
    for rid in sorted(missing):
        sec = case_of(rid)
        if sec not in table_end:
            report["unplaced"].append(rid); continue
        if rid in excluded:
            row = render(rid, excluded[rid][0], NEW_FLAG, datasets.get(rid, "—"), None, None, excluded[rid][1])
        else:
            row = render(rid, runs[rid]["href"], NEW_FLAG, datasets.get(rid, "—"), syncs.get(rid), runs[rid], None)
        at = table_end[sec]
        out.insert(at, row)
        for s in table_end:
            if table_end[s] >= at and s != sec:
                table_end[s] += 1
        table_end[sec] += 1
        report["added"].append(rid)
    out = glance_counts(out)
    return "\n".join(out), report


def glance_counts(lines):
    """The 'runs' column of the at-a-glance table, where it is a bare integer: measured rows."""
    measured = {}
    section = None
    for line in lines:
        m = re.match(r'<a id="([^"]+)"></a>', line)
        if m:
            section = m[1]; continue
        if section and line.startswith("| [`"):
            measured[section] = measured.get(section, 0) + (0 if NOT_A_MEASUREMENT in line else 1)
    fixed = []
    for line in lines:
        m = re.match(r"\| \[\*\*[^*]+\*\*\]\(#([^)]+)\) \| ([^|]*) \| (\d+) \| ", line)
        if m and m[1] in measured and int(m[3]) != measured[m[1]]:
            line = line.replace(f" | {m[3]} | ", f" | {measured[m[1]]} | ", 1)
        fixed.append(line)
    return fixed


def main(argv):
    docs = Path("docs"); check = "--check" in argv
    if "--docs" in argv:
        docs = Path(argv[argv.index("--docs") + 1])
    p = docs / "case-index.md"
    if not p.exists():
        print(f"no {p}; nothing to refresh", file=sys.stderr); return 0
    runs, excluded = read_run_log(docs)
    new, rep = refresh(p.read_text(), runs, excluded, read_datasets(docs), read_syncs(docs))
    if not check:
        p.write_text(new)
    print(f"{'would write' if check else 'wrote'} {p}: {len(rep['updated'])} row(s) refreshed, "
          f"{len(rep['added'])} added")
    for rid in rep["added"]:
        print(f"  added  {rid}  <- write its variation ({NEW_FLAG})")
    for rid in rep["unplaced"]:
        print(f"  NOT PLACED  {rid}: its label names no case in CASE_OF", file=sys.stderr)
    for sec, ph in rep["placeholders"]:
        if any(case_of(r) == sec for r in rep["added"]):
            print(f"  note   {sec} still has the placeholder row {ph} — superseded?")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
