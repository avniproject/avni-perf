# Pending edits to the injector's dataset provenance

**This file exists because `dataset-provenance.md` is single-copy on an ephemeral instance.** It
lives only at `/opt/avni-perf/context/dataset-provenance.md` on the injector
(`i-041afc7c6e0761195`) — nothing in `avni-perf` or `avni-infra` references or stages it, and
`env-teardown.sh` advises destroying the instance beyond a week, which would take the record with
it. Both items below were agreed on 8 Oct 2026 and need the environment up.

**Delete this file once both are done.**

## 1. Append the case 11 run 1 residue

Measured 8 Oct 2026 after the run, before the environment was stopped. Verified two ways — a
`created_date_time` filter and a delta against the 1,506,900 / 5,396,156 baseline — which agreed to
the row. Text to append:

> ## 2026-10-08 — case 11 run 1 pushed into the dataset
>
> Run `2026-10-08T14-05-56Z-case11-run1-d484f18` ran with `PUSH=on`. It added **43,257 rows —
> 3,146 individual, 40,111 encounter** — 25.72 rows per sync across 1,682 completed syncs. No
> program rows: the dataset has none to push.
>
> Counts moved 1,506,900 → 1,510,046 (individual) and 5,396,156 → 5,436,267 (encounter), +0.627%
> overall. By organisation: 10 → 14,286, 11 → 14,740, orgs 12–19 ~1,700–1,900 each — proportional
> to tenant size.
>
> The rows carry `created_date_time` 2026-10-08 14:07–15:52 UTC. Generated data runs
> 2021-01-01…2025-12-21, so the ten-month gap makes the boundary exact. **Generated rows are not
> all dated 2020-01-01** — that assumption was wrong and cost a 275 KB query result to discover.
>
> The D7 device syncs of 2026-10-07 left no rows.
>
> **This dataset is no longer pristine for incremental runs.** The pushed rows are the newest in
> the database by ten months, so they fall inside the window every incremental sync targets by
> `lastSyncTime`. Reload before any incremental-mode run meant to compare against run 1.

## 2. Move the file into `avni-perf/docs/`

**Fetch the live file first — do not reconstruct it.** The on-disk copy is the source of truth and
holds content not recorded anywhere else (the no-provenance-split decision, the five gates, the
~5% index growth). Then commit it as `docs/dataset-provenance.md` and add staging so the injector
copy derives from the repo.

One open question to settle with the file and the role in view: the natural home is the
`avni_injector` role beside `run-scenario.sh.j2`, but this file is *data about the dataset* that is
appended to over time, not rendered config — **a template would be overwritten on every provision
and would destroy the history**. A one-way upload from the repo, or keeping the repo authoritative
and copying up on demand, both avoid that.
