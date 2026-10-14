-- Does a read-only sync write rows?
--
--   psql "$DB" -f tools/read-only-sync-writes-check.sql          -- before the sync
--   <run one GET /encounter as a sync user>
--   psql "$DB" -f tools/read-only-sync-writes-check.sql          -- after
--
-- **The hypothesis.** `AbstractUserType.deepCopy` round-trips every jsonb value through Java
-- serialisation to build Hibernate's dirty-checking snapshot, and `isMutable()` is true so it runs
-- for every entity loaded. `equals` then compares the live map against that reconstructed copy. If
-- any value does not round-trip to an `equals`-equal instance, the entity looks dirty.
--
-- `DummyInterceptor` forces a flush at the end of every web request -- `genderRepository.findAll()`
-- inside `@Transactional`, by its own comment a hack "to ensure all dirty objects are flushed out".
-- A dirty Encounter at flush fires `@PreUpdate beforeUpdate()`, which calls `getIndividual()`: a
-- lazy load, one per dirty row. The 12a trace shows nine such selects spread through one request,
-- 11% of it, which nothing else explains.
--
-- **If a pull writes rows this stops being a CPU question.** It would mean every sync generates
-- WAL, bloats the table, and leaves work for autovacuum -- on the read path, for every device.
--
-- Read-only. n_tup_upd is cumulative since the last stats reset, so the figure matters only as a
-- difference across the two runs. Take it on an otherwise quiet server: anything else touching
-- these tables lands in the same counters.

SELECT relname                AS table_name,
       n_tup_upd              AS updates,
       n_tup_hot_upd          AS hot_updates,
       n_live_tup             AS live_rows,
       n_dead_tup             AS dead_rows,
       last_autovacuum,
       last_autoanalyze
FROM pg_stat_user_tables
WHERE relname IN ('encounter', 'individual', 'program_encounter', 'program_enrolment')
ORDER BY relname;

-- WAL is the second witness, and it cannot be explained away by stats timing: if the pull really
-- writes, this moves by more than the handful of bytes an idle server produces.
SELECT pg_current_wal_lsn() AS wal_position;
