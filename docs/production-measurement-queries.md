# Production measurement queries

Read-only aggregate queries against the Avni production database, supporting
[the sync simulation plan](sync-simulation-plan.md). The plan carries the *findings*; this document
carries the queries that produced them, the caveats on running them, and the defects corrected along
the way.

**Anonymised production data is not available to this project and a clone is not an option**, so the
generated dataset (plan section H) has to be sized from aggregate statistics instead. That is what
these queries are for. They return counts, percentiles and distributions only — no personal data, no
organisation names.

## Running them

> **Run against the read replica** unless a query says otherwise. Only **Q7c** must use the primary:
> `idx_scan` counters are per-instance, and the replica serves Metabase alone, so a zero there says
> nothing about whether sync traffic uses an index.

> **Filter on `sync_start_time`, not `sync_end_time`.** Only `sync_start_time`, `user_id` and
> `last_modified_date_time` are indexed. Filtering on `sync_end_time` forces a full scan — it is why
> the first Q3 did not finish in ten minutes, and why Q4 was the one query that returned promptly.

> **Bound the window with `<= now()`.** Diagnostic D1 found 63 rows carrying a future
> `sync_start_time`, the worst dated **2031**. Unbounded they inflate Q4's bucket count, can win Q3's
> latest-row-per-user selection outright, and stretch Q2's gap tail. They are 0.05% of the table, and
> they are why Q1's first run read as pure noise.

> **Exclude two `sync_source` values.** `'avni-perf-simulation'` is the simulation's own telemetry —
> since plan task D4 it posts like any client, and left in it would pollute the very distributions
> these queries establish, worsening every time the simulation runs. `'automatic-upload-only'` is the
> background upload job, which pushes without pulling and so never advances the pull window. Q6, Q7,
> Q9, Q10, Q12 and Q13 read application tables the simulation never writes to and need no filter.

> **Run as a superuser.** Under row-level security an organisation-scoped role sees only its own rows,
> and Q12 in particular returns one meaningless line instead of failing.

> **Results here are summarised.** This repository is public. The full result sets — per-organisation
> sizes, per-index scan counts, the complete hourly and weekly series — are recorded in the private
> `avni-product-ops` repository, at `context/production-database-state-2026-09.md`.

## Provenance

Three runs against production: **2026-09-03**, **2026-09-17**, and a third the same day applying the
corrections below. Windows are 30 days, except Q2 (90 days) and Q10 (6 months). Where runs disagree,
the later stands.

### Defects found, and what each cost

| # | Defect | Symptom | Effect on the result |
|---|---|---|---|
| 1 | Filtered on unindexed `sync_end_time` | Q3 ran >10 min, cancelled | No result at all |
| 2 | No `<= now()` bound | Q4 reported 38 hour-buckets in a 30-day window | **Q1 read as r²=0.00001** |
| 3 | Q4 grouped by hour-of-day, not calendar hour | Buckets summed 30 days each | Overstated peak load ~30× |
| 4 | Q3 counted one row per *sync* | Frequent syncers dominated | Skewed a per-user distribution |
| 5 | `sync_source` literal did not exist | Filter matched nothing, silently | ~2.7% unwanted rows retained |
| 6 | Q7 had no `schemaname` filter | Per-org ETL schemas returned too | Real rows buried in zero-count noise |
| 7 | Q7 read `n_live_tup` on a replica | All zeros beside multi-GB indexes | Row counts unavailable |
| 8 | Q9 used `?` against a `jsonb_path_ops` GIN | Sequential scan, never finished | No result at all |
| 9 | Q13 used a correlated `LATERAL` | 1.2M subqueries, cancelled | No result at all |

Two are worth carrying beyond this document. **A `distinct from` filter against a non-existent literal
fails silently and looks like a clean null result** — defect 5 survived two runs undetected.

**And least-squares regression has unbounded sensitivity to outliers.** Eighty bad rows out of 131,538
— 0.06% — held Q1's r² at 0.00001 and its intercept at 63 seconds. Removing them moved r² to 0.187 and
the intercept to 26.5 s while barely touching the slope. An r² near zero is a signal to inspect the
extremes before concluding anything about the relationship; the Q5 band analysis was the right
cross-check precisely because percentiles ignore outliers, and it gave ~10 ms/record from data the
regression read as noise.

---

**Q1 — `baseMsPerRecord` (D6.1).** `baseMsPerRecord` is a *marginal* cost, so ask for a slope rather
than a ratio.

Dividing total duration by records pulled conflates fixed and marginal cost at every volume: every
sync pays for `syncDetails`, an entity request per entity whether or not it returns anything, and the
telemetry post. That fixed cost is baked into the ratio, inflating it most for small syncs and
approaching the truth only for very large ones. No minimum-records threshold fixes that — it only
hides the worst cases.

```sql
with s as (
  select
    extract(epoch from (sync_end_time - sync_start_time)) * 1000 as duration_ms,
    (select coalesce(sum((e->>'done')::int), 0)
       from jsonb_array_elements(entity_status->'pull') e) as pulled
  from sync_telemetry
  where sync_source is distinct from 'avni-perf-simulation'
    and sync_status = 'complete'
    and sync_start_time > now() - interval '30 days'
    and sync_start_time <= now()
    and sync_end_time > sync_start_time
    and sync_end_time - sync_start_time < interval '2 hours'
    and sync_source is distinct from 'automatic-upload-only'
)
select count(*)                            as syncs,
       regr_slope(duration_ms, pulled)     as ms_per_record,      -- marginal: baseMsPerRecord
       regr_intercept(duration_ms, pulled) as fixed_overhead_ms,  -- per-sync cost at zero records
       regr_r2(duration_ms, pulled)        as fit
from s
where pulled > 0;
```

`regr_intercept` gives the per-sync fixed cost for free, which is worth having on its own. **Check
`fit` before using the slope** — a low r² means duration is not linear in record count, and a single
coefficient is then the wrong model, which is itself a finding.

**Result:** 108,374 syncs · **9.188 ms/record** · intercept 26,533 ms · r² 0.187. Q5's volume bands give 10.0 ms independently, so two methods agree. Interpreted in plan section **D6.1**, including why the first run read as r² = 0.00001.

> **Guard against device clock skew.** `sync_start_time` and `sync_end_time` come from the device, and
> Q4's corrected run returned up to 38 distinct hour-buckets for a 30-day window where 31 is the
> ceiling — so some rows fall outside the window entirely. Since duration is `end - start`, a skewed
> clock yields a negative or absurd duration that a regression cannot survive, and **that is a leading
> candidate for Q1's r² of 0.00001 and its 63-second intercept.** The bounds above drop those rows;
> diagnostic D1 reports how many there were.


> **Still a ceiling.** Duration measured on the client includes network and server time, so the slope
> is an upper bound on client-side parse-and-persist. See the caveat in D6.1 — do not use it as
> `baseMsPerRecord` unmodified.

**Q2 — `loadedSince` gap distribution (D1).** Drives the realistic-spread scenario.

**The exclusion literal in the first two runs was wrong, so no filtering happened.** `sync_source`
never takes the value `ONLY_UPLOAD_BACKGROUND_JOB` — diagnostic D2 shows the real vocabulary is
`manual` (93.7%), `automatic-upload-only` (2.7%), null (2.0%) and `automatic` (1.6%). That is why
adding the filter changed the result by precisely nothing, and it is a lesson worth generalising:
**a `distinct from` filter against a non-existent literal fails silently and looks like a null
result.** The figures below therefore still include upload-only syncs and need one more run with the
correct literal — though at 2.7% of rows the correction is unlikely to move the percentiles much.

> **Worth reconciling separately:** background sync is understood to have been disabled some time ago,
> yet `automatic-upload-only` and `automatic` together account for **4.3% of syncs in the last 30
> days**. Either some deployments have not picked up the change, or the disabling was narrower than
> assumed. It does not change the plan — 95% of traffic is manual either way — but it is a loose end.

**Result:** gap hours p25 0.039 · p50 0.269 · p75 12.50 · p90 39.44 · p99 196.70 — that is a
**median of 16 minutes** between syncs, with a p75 of 12.5 hours. Interpreted in plan section **D1**.

**Q3 — Per-user data volume (E5, G5, H3).** `totalCounts` is the local row count on each device —
effectively "rows in this user's catchment" — and it drives both catchment design and generated data
volume.

Two things the first version got wrong. It counted **one row per sync**, so a user who syncs five
hundred times contributed five hundred times to a distribution that is meant to be per user. And it
filtered on `sync_end_time`, which has no index — only `sync_start_time` and `user_id` do — so it
scanned the whole table and did not finish in ten minutes. Taking the latest row per user fixes the
skew and shrinks the percentile sort from every sync to one per user.

```sql
with latest as (
  select distinct on (user_id)
         user_id,
         entity_status -> 'totalCounts' as counts
  from sync_telemetry
  where sync_source is distinct from 'avni-perf-simulation'
    and sync_status = 'complete'
    and sync_start_time > now() - interval '30 days'
    and sync_start_time <= now()
    and entity_status ? 'totalCounts'
  order by user_id, sync_start_time desc
),
v as (
  select (counts ->> 'subjects')::numeric           as subjects,
         (counts ->> 'programEnrolments')::numeric  as enrolments,
         (counts ->> 'programEncounters')::numeric  as program_encounters,
         (counts ->> 'encounters')::numeric         as encounters
  from latest
)
select count(*) as users,
       percentile_cont(array[0.5, 0.9, 0.99]) within group (order by subjects)           as subjects_p50_p90_p99,
       percentile_cont(array[0.5, 0.9, 0.99]) within group (order by enrolments)         as enrolments_p50_p90_p99,
       percentile_cont(array[0.5, 0.9, 0.99]) within group (order by program_encounters) as prog_encounters_p50_p90_p99,
       percentile_cont(array[0.5, 0.9, 0.99]) within group (order by encounters)         as encounters_p50_p90_p99
from v;
```

**Result**, 2,828 users — subjects p50/p90/p99 464 / 5,685 / 42,519; enrolments 100 / 1,653 / 15,254;
program encounters 89 / 11,762 / 153,126; encounters 62 / 3,167 / 53,670. **A device holds ~715 rows at
p50 and ~264,569 at p99.** Interpreted in plan section **H3**.

If it is still slow, narrow the window to 7 days — a device's `totalCounts` is its current state, so a
shorter window costs only coverage of users who have not synced recently.

**Q4 — Peak-hour concurrency (E5, Success criteria).** Sync arrivals by local hour.

**Bucket per calendar hour first, then aggregate across days.** Grouping straight by hour-of-day sums
every occurrence of that hour in the window — over 30 days the 16:00 row returns thirty hours' worth
of syncs, and its `count(distinct user_id)` counts everyone who synced at 16:00 on *any* day, not
users present together. Both read as a single busy hour and overstate it roughly thirty-fold. The
first run of this query was misread exactly that way. Bucketing by `date_trunc('hour', ...)` keeps one
row per real hour, so `max` is a genuine busiest hour and the weekday/weekend split stays visible
instead of being averaged away.

```sql
with per_hour as (
  select date_trunc('hour', sync_start_time at time zone 'Asia/Kolkata') as hour_bucket,
         count(*)                as syncs,
         count(distinct user_id) as users
  from sync_telemetry
  where sync_source is distinct from 'avni-perf-simulation'
    and sync_start_time > now() - interval '30 days'
    and sync_start_time <= now()
  group by 1
)
select extract(hour from hour_bucket)                                   as hour_ist,
       count(*)                                                         as hours_observed,
       round(avg(syncs))                                                as avg_syncs,
       round(percentile_cont(0.95) within group (order by syncs))        as p95_syncs,
       max(syncs)                                                       as peak_syncs,
       round(avg(users))                                                as avg_users,
       max(users)                                                       as peak_users
from per_hour
group by 1
order by 1;
```

Arrival rate is `peak_syncs / 3600`. Design the *Load* profile against `p95_syncs` and the *Stress*
profile against `peak_syncs` — the maximum over 30 days is one real hour that genuinely happened, but
it is a single observation and a poor thing to size steady-state load against.

**Result:** busiest hour ever recorded **792 syncs at 12:00 IST across 267 distinct users**; the busiest hour on average is 16:00 at 378. Activity holds above 200 an hour from 09:00 to 21:00 — a working-day plateau, not a start-of-day rush. Interpreted in plan section **E5**.

**Q5 — Sync duration by volume band (F7, Success criteria).** The distribution the calibration gate
compares against.

```sql
with s as (
  select extract(epoch from (sync_end_time - sync_start_time)) * 1000 as duration_ms,
         (select coalesce(sum((e->>'done')::int), 0)
            from jsonb_array_elements(entity_status->'pull') e) as pulled
  from sync_telemetry
  where sync_source is distinct from 'avni-perf-simulation'
    and sync_status = 'complete'
    and sync_source is distinct from 'automatic-upload-only'
    and sync_start_time > now() - interval '30 days'
    and sync_start_time <= now()
    and sync_end_time > sync_start_time
    and sync_end_time - sync_start_time < interval '2 hours'
)
select width_bucket(pulled, 0, 50000, 10) as volume_band,
       count(*) as syncs,
       percentile_cont(0.5)  within group (order by duration_ms) as p50_ms,
       percentile_cont(0.95) within group (order by duration_ms) as p95_ms
from s
group by 1
order by 1;
```

**Result:** 108,688 syncs. **Band 1 holds 106,444 — 97.9% — at p50 14.1 s and p95 80.0 s**, which is the success criteria's threshold for the common case. The tail runs to p50 1,076 s at band 10. Interpreted in the **Success criteria** table and **D6.1**.

**Q6 — Observation shape (H3, H5).** The numbers that determine whether generated data behaves like
production. Repeat per entity table.

```sql
select percentile_cont(0.5)  within group (order by k) as p50_obs_keys,
       percentile_cont(0.95) within group (order by k) as p95_obs_keys,
       avg(sz)::int                                    as avg_obs_bytes
from (
  select (select count(*) from jsonb_object_keys(observations)) as k,
         pg_column_size(observations)                           as sz
  from program_encounter tablesample system (1)
  where observations is not null
) t;

-- distinct concept cardinality across observations
select count(distinct key) as distinct_concepts
from (
  select jsonb_object_keys(observations) as key
  from program_encounter tablesample system (1)
) t;
```

**Result:** `program_encounter` p50 12 keys / p95 34 / 878 bytes; `individual` 7 / 29 / 742; `encounter` 4 / 22 / 526; `program_enrolment` 2 / 20 / 360. **5,623 distinct concepts** appear as observation keys — across all 986 organisations, not one. Interpreted in plan section **H3**.

**Q7 — Row counts and index sizes (H5).** The single most informative comparison against generated
data — a GIN index an order of magnitude smaller than production's means the cardinality is wrong.

**Restrict to `public`.** `pg_stat_user_tables` spans every schema, and each organisation's ETL
schema holds its own same-named copies — `individual` alone comes back once per org, mostly with zero
or partial counts, burying the transactional row among thousands. The first run of this query returned
exactly that. The ETL copies are a separate question (G4), not part of the H5 comparison.

```sql
-- 7a. Row counts and sizes. Safe on a replica: reltuples is a catalog
--     column and replicates, unlike pg_stat_user_tables.n_live_tup.
select c.relname,
       c.reltuples::bigint                    as est_rows,
       pg_size_pretty(pg_table_size(c.oid))   as table_size,
       pg_size_pretty(pg_indexes_size(c.oid)) as indexes_size
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in ('individual', 'program_enrolment', 'program_encounter', 'encounter')
order by c.reltuples desc;

-- 7b. Index sizes. Sizes are physical, so these are correct anywhere.
select relname, indexrelname,
       pg_size_pretty(pg_relation_size(indexrelid)) as index_size
from pg_stat_user_indexes
where schemaname = 'public'
  and relname in ('individual', 'program_enrolment', 'program_encounter')
order by pg_relation_size(indexrelid) desc;

-- 7c. *** RUN THIS ONE ON THE PRIMARY ***
--     idx_scan is per-instance and resets on restart. On a replica it
--     counts only that replica's workload -- Metabase, not sync -- so a
--     zero there says nothing about whether sync uses the index.
--     Check how long the counters have been accumulating before reading them.
select (select pg_postmaster_start_time()) as counting_since,
       relname, indexrelname,
       pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
       idx_scan, idx_tup_read, idx_tup_fetch
from pg_stat_user_indexes
where schemaname = 'public'
  and relname in ('individual', 'program_enrolment', 'program_encounter', 'encounter')
order by idx_scan asc, pg_relation_size(indexrelid) desc;
```

> **`n_live_tup` returned zero for every table, and diagnostic D3 explains why: the query ran on a
> physical replica** (`pg_is_in_recovery()` = true, up since 2026-06-03). Autovacuum and analyze never
> run on a standby, so its stats collector has nothing to report. Use `pg_class.reltuples` instead —
> it is a catalog column, so it replicates correctly.
>
> The four sync-path tables hold roughly **13.6 GB of rows against 19.4 GB of indexes** — a 1.43×
> ratio overall, and as high as 3.7× on one table. Per-table counts and sizes are recorded in
> `avni-product-ops`.
>
> **`idx_scan` from a replica must be discarded.** It counts only that instance's own workload, and the
> replica serves Metabase alone — no sync traffic reaches it. Zero scans there is evidence about
> Metabase, not about sync. Query 7c above answers the question on the primary.

**Result**, 66 indexes over 69 days: **six of the seven GIN observation indexes were never scanned**
(~794 MB), while the seventh took over 1.5 million scans on the same column type in the same window.
Counting every index scanned fewer than a thousand times, **about 4.08 GB — 21% of index bulk — earns
almost nothing**. Several hot indexes are poorly selective, the worst reading tens of thousands of rows
per lookup. Interpreted in plan section **G4**; per-index detail is in `avni-product-ops`.

> Sixty-nine days misses quarterly reporting paths, and unique constraints enforce correctness
> regardless of scan count — both excluded from the 4.08 GB figure.

**Q8 — How many entities actually change per sync (D1.1).** The benefit side of the `syncDetails`
trade. `entity_status->'pull'` carries an entry per entity with `todo`/`done` counts; entries with
`todo > 0` are the entities `syncDetails` flagged as changed and the client then fetched.

```sql
with s as (
  select
    jsonb_array_length(entity_status->'pull') as entities_tracked,
    (select count(*) from jsonb_array_elements(entity_status->'pull') e
       where coalesce((e->>'todo')::int, 0) > 0) as entities_changed
  from sync_telemetry
  where sync_source is distinct from 'avni-perf-simulation'
    and sync_status = 'complete'
    and sync_source is distinct from 'automatic-upload-only'
    and entity_status ? 'pull'
    and sync_start_time > now() - interval '30 days'
)
select count(*) as syncs,
       percentile_cont(array[0.5, 0.9]) within group (order by entities_tracked) as tracked_p50_p90,
       percentile_cont(array[0.5, 0.9]) within group (order by entities_changed) as changed_p50_p90,
       avg(entities_changed::numeric / nullif(entities_tracked, 0)) as avg_fraction_changed
from s;
```

Read it as: **`avg_fraction_changed` near 0 means `syncDetails` is earning its cost many times over;
near 1 means it is mostly ceremony.** Validate the `todo`/`done` semantics against a sample row before
trusting the numbers — the client pre-populates the array from entity metadata, so entries exist for
entities that were never fetched.

**Result:** 112,349 syncs. The client posts **79 tracked entities and 4 come back changed at p50**, 7 at p90 — an average changed fraction of 6.1%. Interpreted in plan section **D1.1**, which argues the endpoint is still a good trade.

**Q9 — Media uploads per sync (D5.1).** Each media file costs a `GET /media/uploadUrl/{fileName}`
call on the sync path, so the rate sets how much server load media contributes. `sync_telemetry` does
not record media counts, but media observations are keyed by concepts whose `data_type` is a media
type, so the creation rate is derivable.

> **The GIN indexes cannot help this query, and that is why the first version never finished.**
> `V1_03__AddGinIndexForObservations.sql` builds `GIN (observations jsonb_path_ops)`. The
> `jsonb_path_ops` opclass supports only `@>`, `@?` and `@@` — **not `?`, `?|` or `?&`**, which are
> `jsonb_ops`-only. So `observations ? mc.uuid` gets no index assistance at any size, and running it
> as a correlated `EXISTS` per row turns into a sequential scan of `program_encounter` — a table
> carrying 11.4 GB of indexes — with a JSONB probe on every row.
>
> Worth carrying beyond this query: **any server-side code filtering observations by key presence has
> the same problem.** That is a candidate choke point in its own right, not just a query-writing
> nuisance.

Sample instead of scanning. A rate needs a representative fraction, not a census, and intersecting
each row's own keys against the media-concept set is bounded by keys-per-row — Q6 measured that at 12
at p50, 34 at p95 — rather than by the size of the concept table.

```sql
with media_concepts as (
  select array_agg(uuid) as uuids
  from concept
  where data_type in ('Image', 'ImageV2', 'Video', 'Audio', 'File')
    and is_voided = false
),
sampled as (
  select pe.observations
  from program_encounter pe tablesample system (1)
  where pe.last_modified_date_time > now() - interval '30 days'
)
select count(*)                                     as sampled_rows,
       count(*) filter (where observations ?| mc.uuids) as media_bearing_rows,
       round(100.0 * count(*) filter (where observations ?| mc.uuids)
             / nullif(count(*), 0), 2)              as pct_media_bearing
from sampled, media_concepts mc;
```

**Result:** 59 of 2,759 sampled rows carry a media observation — **2.14%**, or roughly 147,000 of
6.86 M program encounters. Interpreted in plan section **D5.1**.

Check `(select cardinality(uuids) from media_concepts)` first — if the organisation set defines no
media concepts, the answer is zero and D5.1 needs no further work. Raise the sample rate if
`sampled_rows` comes back too small to trust, and repeat per entity table. Validate `?|` against a
sample row before trusting it: media observations may hold a URL string or an array depending on
whether the concept is multi-select.

**Q10 — Reset sync frequency (D9).** A reset forces affected users into a full re-download, so it is
potentially the highest-load event in the system. `reset_sync` records every one.

```sql
SELECT date_trunc('week', created_date_time) AS week,
       count(*)                              AS resets,
       count(DISTINCT organisation_id)       AS orgs_affected,
       count(DISTINCT user_id)               AS users_affected,
       count(*) FILTER (WHERE subject_type_id IS NULL) AS org_wide_resets
FROM reset_sync
WHERE is_voided = false
  AND created_date_time > now() - interval '6 months'
GROUP BY 1 ORDER BY 1;
```

Read it as: frequent resets affecting many users at once justify modelling the post-reset stampede
(D9); rare, narrow ones do not. `users_affected` against `orgs_affected` says whether a reset is
typically one user or a whole organisation — which is the difference between a non-event and a herd.

**Result**, 27 weeks: a normal week is **~194 resets, 89% org-wide**, 1.8 per affected user. One week
(2026-04-06) recorded **25,141 resets — 130× normal**, essentially all org-wide, across 14 organisations
but only 156 users: about 161 resets per user. Interpreted in plan section **D9**.

**Q11 — Fleet page size split (D8.3).** *Not yet answerable* — `pageSize` is not recorded in
`app_info`. Rides the same client release as D7's per-entity durations. Until then the production
split between page size 100 and 1000 is unknown and both must be tested.

---

**Q12 — Organisation size and skew (Success criteria, I2, I3, H3, G5).** The plan requires tenant size
skew in four places and had no query for it. It also supplies the one remaining measurable row in the
Success criteria table — the concurrent-user target is "largest org size plus expected growth", and
nothing so far has measured largest org size.

Organisation identity is deliberately not selected. Rank and row counts are what the dataset
generator and the multi-tenancy scenarios need; the name is not, and leaving it out keeps pasted
output free of tenant identity.

```sql
with org_users as (
  select organisation_id, count(*) as users
  from users where is_voided = false group by 1
),
org_subjects as (
  select organisation_id, count(*) as subjects
  from individual where is_voided = false group by 1
)
select row_number() over (order by coalesce(s.subjects, 0) desc) as rank,
       o.id                                        as org_id,
       o.parent_organisation_id is not null        as is_child_org,
       coalesce(u.users, 0)                        as users,
       coalesce(s.subjects, 0)                     as subjects
from organisation o
left join org_users    u on u.organisation_id = o.id
left join org_subjects s on s.organisation_id = o.id
order by 1;
```

`individual` carries 2.7 GB of indexes and this scans it once — heavy but bounded. Adding
`program_encounter` the same way scans 11.4 GB and is worth a separate off-peak run rather than
bolting onto this one. **Run as a superuser**: under RLS an org-scoped role sees only its own rows,
and the query silently returns one meaningful line.

**Result:** **986 organisations.** The largest holds 21% of all subjects, the top 10 hold 63%, the top 50 over 90%, and **473 — 48% — hold none at all**. The largest by users ranks 71st by subjects, so the two axes are independent. Interpreted in plan section **H3**.

**Q13 — Address hierarchy shape (H3, G5).** H3 lists it as driving "the scope-resolution queries
behind catchment filtering", and it too had no query. `address_level.lineage` is an `ltree`, so depth
is exact rather than inferred.

```sql
-- depth distribution
select nlevel(lineage) as depth, count(*) as locations
from address_level
where is_voided = false
group by 1 order by 1;

-- hierarchy shape, per organisation
-- A cross-organisation version of this returns nothing usable: address_level_type
-- is per-org, so grouping by (level, name) merges ~986 independent hierarchies and
-- the same name lands at a different depth in each. Group by organisation first,
-- then describe the distribution across organisations.
--
-- address_level_type.level is a double each org sets for itself -- observed values
-- include 0.1, 2.6, 25 and 100 -- so it cannot order anything. nlevel(lineage) is
-- the only real depth.
with loc as (
  select organisation_id, id, parent_id, nlevel(lineage) as depth
  from address_level
  where is_voided = false
),
child_counts as (
  select parent_id, count(*) as n
  from loc
  where parent_id is not null
  group by parent_id
),
per_org as (
  select l.organisation_id,
         max(l.depth)                                          as depth,
         count(*)                                              as locations,
         round(avg(c.n) filter (where c.n is not null), 1)      as avg_branching,
         max(c.n)                                              as max_branching
  from loc l
  left join child_counts c on c.parent_id = l.id
  group by 1
)
select depth,
       count(*)                                                        as orgs,
       percentile_cont(0.5) within group (order by locations)::bigint   as median_locations,
       max(locations)                                                   as max_locations,
       round(avg(avg_branching), 1)                                     as avg_branching,
       max(max_branching)                                               as max_branching
from per_org
group by 1
order by 1;

-- which organisations own the chains deeper than 8 levels
select organisation_id,
       max(nlevel(lineage)) as max_depth,
       count(*)             as locations
from address_level
where is_voided = false
  and nlevel(lineage) > 8
group by 1
order by 2 desc;
```

A generator that gets total location count right but depth or branching wrong produces catchments
that resolve in a different number of index lookups than production's — which is precisely the cost
this drives.

**Result**, 812 organisations that hold any location:

| Depth | Orgs | Median locations | Max | Avg branching |
|---|---|---|---|---|
| 1 | 231 | 1 | 357 | — |
| 2 | 98 | 4 | 167 | 4.8 |
| 3 | 215 | 3 | 6,259 | 5.3 |
| 4 | 136 | 20 | **500,039** | 9.4 |
| 5 | 101 | 120 | 20,419 | 3.3 |
| 6 | 25 | 155 | 2,251 | 2.4 |
| 7 | 4 | 1,326 | 1,697 | 4.0 |
| 8 | 1 | 2,593 | 2,593 | 1.8 |
| 26 | 1 | 20,240 | 20,240 | 1.0 |

**The depth-26 anomaly is one organisation.** The second query returns a single row: 13,734 locations
below depth 8, all in one org. That is exactly 763 × 18, matching the 763-per-depth pattern, and it is
68% of that organisation's 20,240 locations. Interpreted in plan section **H3**.

> **Two things the first cross-organisation run exposed.** `address_level_type.level` is org-defined
> and unusable for ordering. And the type names carry a lot of test data — `dummy`, `test`, `xyz`, an
> empty-string name holding 19,075 locations, and several types named as voided. A generator copying
> production's shape should copy the working hierarchies, not the debris.

**Q14 — Temporal spread of `last_modified_date_time` (H3, D1).** Section H3 warns
that getting this wrong invalidates every incremental scenario — rows sharing one timestamp make
incremental sync return either everything or nothing — and no query covered it, so the generator
currently carries a placeholder flagged as unmeasured.

Two things are needed: how old rows are, and how often a row is edited after it was created. The
second matters because an edit moves a row back into every subsequent incremental window, which is
what makes an incremental sync non-empty at all.

```sql
with sampled as (
  select 'individual'        as tbl, created_date_time, last_modified_date_time
  from individual tablesample system (1) where is_voided = false
  union all
  select 'program_enrolment', created_date_time, last_modified_date_time
  from program_enrolment tablesample system (1) where is_voided = false
  union all
  select 'program_encounter', created_date_time, last_modified_date_time
  from program_encounter tablesample system (1) where is_voided = false
  union all
  select 'encounter', created_date_time, last_modified_date_time
  from encounter tablesample system (1) where is_voided = false
)
select tbl,
       count(*) as sampled_rows,
       percentile_cont(array[0.5, 0.9, 0.99]) within group (
         order by extract(epoch from (now() - last_modified_date_time)) / 86400
       ) as age_days_p50_p90_p99,
       round(100.0 * count(*) filter (
         where last_modified_date_time > created_date_time + interval '1 hour'
       ) / nullif(count(*), 0), 2) as pct_edited_after_creation,
       percentile_cont(0.5) within group (
         order by extract(epoch from (last_modified_date_time - created_date_time)) / 86400
       ) filter (where last_modified_date_time > created_date_time + interval '1 hour')
       as median_days_to_first_edit
from sampled
group by tbl
order by tbl;
```

The one-hour threshold separates a genuine later edit from the write that created the row, since
both timestamps are set on insert and can differ by milliseconds.

**Result:**

| Table | Sampled | Age p50 | p90 | p99 | Edited after creation | Median days to first edit |
|---|---|---|---|---|---|---|
| `encounter` | 32,969 | 821 d | 1,663 | 2,664 | 40.1% | 383 |
| `individual` | 25,751 | 788 d | 1,791 | 2,991 | 36.7% | 595 |
| `program_encounter` | 66,844 | 698 d | 1,897 | 2,869 | **74.8%** | **32** |
| `program_enrolment` | 7,459 | 444 d | 2,076 | 2,724 | 61.0% | 274 |

**Production data is old.** A median row was last touched nearly two years ago, and the 99th
percentile reaches eight years. Interpreted in plan section **H3**.

**Program encounters behave unlike everything else: three quarters are edited, and the median edit
lands 32 days after creation** — against 383 to 595 days for encounters and subjects. That is the
scheduled-visit pattern. A program encounter is created when a visit is scheduled and filled in when
the visit happens, so creation and completion are two writes weeks apart. A generator that writes
each row once produces neither the edit volume nor the timestamp spread, and **that is the difference
between an incremental sync returning a realistic trickle and returning nothing**.

**Q15 — Is the per-device volume two populations? (E0, H3, G5).** Q3 found per-device
row counts running from ~715 at the median to ~264,569 at the 99th percentile. The customer's
deployment has two user roles — field workers holding one catchment, supervisors holding the union of
many — which would produce exactly that spread without anyone being an outlier.

It matters because the generator currently samples one distribution for every user. If the population
is bimodal, that produces a continuum of catchment sizes where production has two clusters, and the
supervisor case — the expensive one — is then under-represented at exactly the volumes that matter.

Catchment size is the available proxy for role, since `sync_telemetry` records no role.

```sql
with device as (
  select distinct on (user_id)
         user_id,
         ((entity_status -> 'totalCounts' ->> 'subjects')::numeric
          + coalesce((entity_status -> 'totalCounts' ->> 'programEncounters')::numeric, 0)) as rows_held
  from sync_telemetry
  where sync_source is distinct from 'avni-perf-simulation'
    and sync_status = 'complete'
    and sync_start_time > now() - interval '30 days'
    and sync_start_time <= now()
    and entity_status ? 'totalCounts'
  order by user_id, sync_start_time desc
),
scoped as (
  select d.user_id, d.rows_held, count(v.addresslevel_id) as locations_in_catchment
  from device d
  join users u on u.id = d.user_id
  left join virtual_catchment_address_mapping_table v on v.catchment_id = u.catchment_id
  group by d.user_id, d.rows_held
)
select width_bucket(locations_in_catchment, 0, 200, 10) as catchment_band,
       count(*)                                          as users,
       min(locations_in_catchment)                       as min_locations,
       max(locations_in_catchment)                       as max_locations,
       percentile_cont(array[0.5, 0.9]) within group (order by rows_held) as rows_held_p50_p90
from scoped
group by 1
order by 1;
```

**Result**, 2,829 users:

| Locations in catchment | Users | Share | Rows p50 | Rows p90 |
|---|---|---|---|---|
| 0–19 | 2,081 | **73.6%** | 615 | 10,423 |
| 20–39 | 181 | 6.4% | 2,898 | 45,679 |
| 40–59 | 67 | 2.4% | 4,398 | 57,411 |
| 60–79 | 46 | 1.6% | 13,069 | 73,930 |
| 80–99 | 47 | 1.7% | 7,733 | 87,780 |
| 100–115 | 22 | 0.8% | 12,055 | 25,553 |
| 121–139 | 18 | 0.6% | 308 | 29,536 |
| 140–157 | 16 | 0.6% | **21** | 1,463 |
| 161–174 | 18 | 0.6% | 10,405 | 43,484 |
| 186–199 | 10 | 0.4% | 4,412 | 256,559 |
| 209–495,952 | 323 | **11.4%** | 3,926 | 124,188 |

**Catchment size is bimodal.** Three quarters of users hold 19 locations or fewer, 11% hold 209 or
more, and only 15% sit anywhere between. Two populations, as E0 predicted.

**But catchment size barely predicts how much data a user holds.** The 140–157 band has a median of
**21 rows** — thirty times *less* than the smallest-catchment band, despite holding eight times the
locations. The 121–139 band is similar at 308. A wide catchment in a sparsely populated organisation
still holds almost nothing, so catchment size and organisation data density vary independently.

**The consequence for the generator is concrete**: assigning catchments by size alone will not
reproduce the volume distribution. Catchment breadth and per-location data density have to be
separate parameters, and the second one is what Q3's spread is actually made of.

**One user's catchment spans 495,952 locations** — 41% of every location on the platform (Q13's
1,204,209). Those users exist today and sync today, which is worth knowing before treating any
generated catchment as an extreme.

**Counting the effective catchment, not the declared one.** `catchment_address_mapping` holds the
locations an administrator picked; `virtual_catchment_address_mapping_table` is a view that expands
those down the location lineage to every descendant, and that expanded set is what determines how
much data a user actually holds. Counting the declared rows instead would make a supervisor whose
catchment is one high-level location look smaller than a field worker with five villages listed.

Being a view over a function, it is the expensive half of this query. If it will not finish, fall
back to `catchment_address_mapping` and read the result as a lower bound on the split rather than a
measurement of it.
