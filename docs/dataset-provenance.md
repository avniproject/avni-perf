<!--
THIS FILE IS THE SOURCE OF TRUTH. It used to live only at
/opt/avni-perf/context/dataset-provenance.md on the injector, which env-teardown.sh
advises destroying beyond a week -- one destroy from losing the record. Moved here
9 Oct 2026.

Append here first, then copy up; do not edit the injector copy in place:

  ssh <injector> 'cat > /opt/avni-perf/context/dataset-provenance.md' < docs/dataset-provenance.md

Verify with sha256sum on both sides. The avni_injector role deliberately does NOT
template this file: it is appended to over time, and a template would overwrite the
history on every provision.
-->

# Dataset provenance — reloaded 8 Oct 2026

`pilot-day-180`, ten tenants in organisations 10–19, **all from one generation**.

| organisations | tenants | generated | loaded | id base |
|---|---|---|---|---|
| 10 | state-1 | 7 Oct, after the `id_base` fix | 7 Oct | 201,000,001 |
| 11–19 | state-2, ngo-1..8 | 7 Oct, same generation | **8 Oct 16:56** | 204,600,001 – 211,324,801 |

Archive: `datasets/pilot-day-180.tar.gz`, which now matches every tenant in the
database. The pre-fix archive is kept as
`datasets/pilot-day-180-pre-idbase-20261006.tar.gz`.

**This supersedes the split recorded here on 7 Oct.** Between 7 and 8 October
org 10 came from the regenerated dataset while orgs 11–19 still held the
generation that preceded the `id_base` fix — their ids ran from 3,600,001 rather
than 204,600,001. Row counts and catchment shape were identical either way, but
`case5-users-pilot.csv` names regenerated usernames, so 1,121 of its 1,682 users
did not exist and case 5 could not run. The nine were torn down and reloaded on
8 Oct; **there is no longer a provenance split.**

## Verified before the first run on this data

* teardown committed 4,594,056 rows deleted from nine organisations, 16:26 IST
* nine tenants reloaded, every one reporting `load OK (psql exit 0)`, by 16:56
* `VACUUM (ANALYZE)` on the eight affected tables; `n_dead_tup` 0 on all of them
* `syncDetails` 200 for users in orgs 10, 11 and 12 — the two that previously 401'd
* structural check PASS: every request 200, every paged entity terminated

```
orgs 10, 11    501,000 individuals   1,799,926 encounters   562 users
orgs 12-19      63,000 each            223,188 each          71 each
total        1,506,900 individuals   5,396,156 encounters
```

## The indexes are ~5% larger than when cases 2, 3, 4 and 14 were measured

Same rows, bigger indexes — the delete-and-reinsert cycle left B-tree bloat that
`VACUUM` does not reclaim, since it frees heap space for reuse but does not
shrink an index without a `REINDEX`:

```
encounter    2,687,426,560 -> 2,817,875,968 bytes   (+130 MB, +4.9%)
individual     847,044,608 ->   886,792,192 bytes   (+40 MB,  +4.7%)
```

Small, and in the direction of pessimism rather than flattery, but it means a
run on this dataset is not bit-for-bit comparable with one from before 8 Oct
16:56. Worth knowing before a 5% difference is read as a finding.

## Still true of this dataset

**Program data is absent.** `program_enrolment` and `program_encounter` are 0
rows database-wide, where the recipe specifies `enrolment_rate: 0.22` and
`program_encounter_share: 0.59`. Every sync measured here is therefore smaller
than a real one — recorded in findings-case2, findings-case3, findings-case4 and
findings-case14.

**Storage cost is engine-dependent and the figures are SQLite-shaped.** D7
measured a real device on 8 Oct: 2.22–2.53 ms/record on SQLite against
10.18–11.37 on Realm, where `baseMsPerRecord` is 2.78. Durations quoted from
runs on this dataset hold for a SQLite fleet and understate Realm by roughly
three times. See findings-d7.md.

## 2026-10-08 — case 11 run 1 pushed into this dataset

Run `2026-10-08T14-05-56Z-case11-run1-d484f18` ran with `PUSH=on`. It added
**43,257 rows — 3,146 individual, 40,111 encounter** — 25.72 rows per sync
across 1,682 completed syncs. No program rows: the dataset has none to push.

Counts moved 1,506,900 → 1,510,046 (individual) and 5,396,156 → 5,436,267
(encounter), **+0.627%**. By organisation: 10 → 14,286, 11 → 14,740, orgs 12–19
~1,700–1,900 each — proportional to tenant size.

Measured, not estimated, and before the environment was stopped: a
`created_date_time` filter and a delta against the 1,506,900 / 5,396,156
baseline agreed to the row. The rows carry `created_date_time` 2026-10-08
14:07–15:52 UTC; generated data runs 2021-01-01…2025-12-21, so the ten-month
gap makes the boundary exact. **Generated rows are not all dated 2020-01-01** —
that assumption was wrong, and the query written on it returned the whole
dataset rather than the residue.

The D7 device syncs of 2026-10-07 left no rows.

**That made the dataset unfit for a further incremental run.** The pushed rows
were the newest in the database by ten months, so they fell inside the window
every `SYNC_MODE=realistic` sync targets by `lastSyncTime`, compressed into
1h45 — a shape the modelled distribution does not contain. Hence the reload
below rather than running the case 11 pair on top of them.
