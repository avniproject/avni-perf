# Known harness issue: daily syncs download whole histories

**Found 10 Nov 2026. Not fixed.** Fix it before any new runs that quote absolute capacity or sync
times. Comparisons between existing runs are unaffected, because every run did the same thing.

## What happens

The simulation builds a daily sync's window in one place and ignores it in another.

- **The change check honours the window.** The `POST /v2/syncDetails` body carries a `loadedSince`
  per record type. Under `SYNC_MODE=realistic` it comes from `realisticLoadedSince`, drawn from
  production's measured gaps between syncs: minutes to about 8 days. The server uses it to report
  which record types have changed.
- **The downloads ignore it.** Every paged pull builds its URL from
  `session.getString("lastModifiedDateTime")` (`AvniSyncSimulation.java`, the pull URL builder;
  the `resetSync` pull does the same). That value is the user file's `lastModifiedDateTime`
  column, **`1900-01-01T00:00:00.000Z` for every user in every feeder**. `realistic` and
  `incremental` never overwrite it.

So whenever the server reports a record type as changed, the simulation downloads **all of that
type in the catchment, from 1900**:

- **Encounters, every sync.** `EncounterService.isScopeEntityChanged` always returns `true`, so
  encounters are always reported as changed, and the whole catchment's visit history is pulled.
- **Individuals, all or nothing.** They are pulled in full whenever the window finds any change,
  and skipped otherwise. This is the "all or nothing" `Individual` behaviour
  [`findings-case11-pair.md`](findings-case11-pair.md) observed and could not explain: 11,057
  records incremental against 14,186 for the whole catchment, the difference being exactly one
  full `Individual` pull.

**The app does not do this.** `ConventionalRestClient` builds each pull with
`lastModifiedDateTime: moment(loadedSince)`, where `loadedSince` is that record type's own sync
status, the same value it sent in the `syncDetails` body. A real daily sync downloads only what
changed since the phone last synced.

## Evidence

**A field worker's daily sync downloads the whole catchment.** In the ten-a-day datasets, a field
worker's catchment is one village shared by three workers:
- 3,000 beneficiaries;
- 5,400 visits (3 workers × 10 a day × 180 days);
- **8,400 records in all**.

Rows 25 and 26 measured **8,402 and 8,400** records per field-worker daily sync at the median.
Supervisors likewise pulled their whole catchment: 16,869 on the 5k dataset, 25,170 on the 10k.

## Which runs it affects

- **Affected:** every run with `SYNC_MODE=realistic` or `SYNC_MODE=incremental`. That is every
  scenario run since realistic windows were introduced, including all of rows 20–37.
- **Unaffected:** `SYNC_MODE=full`, where pulling from 1900 is intended. `csv` is consistent with
  itself, but every committed feeder carries 1900, so a `csv` run is a full sync too.

## What it does and does not change in the findings

**Still sound:**
- **Comparisons between runs**, all of which did the same work: the fixes' savings relative to
  their controls, scale-up and scale-out, one server against several, and where each tier binds.
- **Request-level findings:** per-request database overhead, `uploadUrl`'s twelve statements,
  the N+1 parent loads, the redundant UPDATEs, the cache bypass.
- **The worst case it models.** A server that copes when every daily sync downloads everything
  copes with real daily syncs.

**Overstated, or artefacts of this:**
- **Absolute capacity.** Every sync pulled a full history. Real daily syncs pull less, so the
  syncs-per-hour figures (row 31's ~25,000 on 16 + 16, row 34's database limit of ~48,000, row 36's
  50,000 with room to ~90,000) are cautious. How cautious is not known until a fixed run.
- **Records per sync, and the download part of a sync's time on the phone.** Upload time, which
  is most of a field worker's sync, is unaffected.
- **"An incremental sync pulls 69% of what a full one pulls"** ([case 2](findings-case2.md),
  [case 14](findings-case14.md), findings summary §4). It reflects the harness, not Avni.
- **"Records per sync track dataset depth one-for-one"** ([case 8](findings-case8.md)), for daily
  syncs. It holds for fresh syncs; a real daily sync's volume depends on recent activity, not
  depth.
- **Fix savings that scale with pull volume may be smaller in practice.** #1103's parent loads,
  for example, scale with the records pulled. Savings that are per request do not change.

## The fix

1. **Pull with the record type's own window.** In the pull URL builder, replace
   `session.getString("lastModifiedDateTime")` with `loadedSinceFor(session, entity.entityName)`,
   the value the same sync put in its `syncDetails` body. It is derived from user and record type,
   so the two always agree. Do the same for the `resetSync` pull. Under `csv` and `full`,
   `loadedSinceFor` already returns the feeder value and 1900, so those modes do not change.
2. **Give the window something to find.** On its own, step 1 makes daily syncs pull almost
   nothing. The generator dates every row's last edit relative to the dataset's `reference_date`
   (`pilot-day-180*`: 18 Sep 2026), spread by production's measured ages: a median of about two
   years, with only a thin recent tail. A window of minutes to 8 days back from a run in November
   finds almost none of it, only the run's own pushes. Choose one:
   - **Regenerate with `reference_date` at the planned run date.** Cleanest; costs a generation and
     a load. The 10k took 15 minutes to generate.
   - **Shift timestamps at load:** add `run date − reference_date` to every transactional row's
     `created_date_time` and `last_modified_date_time` after `reload.sql`. One pass, but a large
     UPDATE on tens of millions of rows. Reindex after.
   - **Pin `NOW` to the reference date.** No data change, but the run's own pushes then fall outside
     every window, so field workers no longer download each other's new visits.

   Regenerating is the recommendation: it keeps the measured age spread intact relative to the run.
3. **Record which behaviour a run used** in `run-metadata.json` (for example
   `sync.pullWindow: "per-entity"` against the old `"feeder"`), so old and new runs are never
   compared unknowingly.
4. **Re-measure one capacity point.** Repeat row 31's steady pair (16 + 16, release 18.3) or row 36's
   50,000 hour, and compare:
   - records per field-worker daily sync, now expected to be a small fraction of 8,400;
   - CPU seconds per sync;
   - the knee.

   The difference is how much the published capacity understates. Execution plan row 38.

## Before fixing, check

- **Push residue.** Each run's own pushes are newer than the generated data, so they land inside
  every window. With the fix, they become most of what a daily sync downloads. That is realistic,
  but it makes runs depend on how much residue earlier runs left, so the reset-before-every-run
  discipline matters more.
- **The 1% fresh syncs stay as they are.** `drawFullSync` sets `fullSync`, and `loadedSinceFor`
  returns 1900 for those syncs before anything else, so fresh syncs keep downloading everything.
