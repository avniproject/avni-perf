# `DummyInterceptor`: 12.6% of request time, for a guard that never fires and could not work

**The largest single removable cost measured on this server**, and the one that took the most work
to characterise. Split out of [`areas-to-investigate.md`](areas-to-investigate.md) item 3 on 20
October 2026 because the evidence outgrew the summary.

> **Raised 21 Oct 2026 as avniproject/avni-server#1097**, with the timezone defect of measurement 2
> as avniproject/avni-server#1098. This document is the evidence behind both.

```java
/**
 * Hack. Ensure a transactional data query is made at the end of a web request so that all dirty
 * objects are flushed out. Somehow, changing flush mode does not seem to fix the problem, so
 * manually doing a query here.
 */
@Transactional
public void postHandle(...) { genderRepository.findAll(); }
```

## What it costs

| | ms | share of request time |
|---|---|---|
| **`DummyInterceptor/postHandle`** | **101,039** | **12.6%** |
| `Spring/HandlerInterceptor`, all of them | 105,619 | 13.2% |

From the `Metric` timeslice tree over `case4-span20` — healthy, unsaturated, 4,416 transactions.
**It is 96% of all interceptor time.** The 5.57% quoted in
[`findings-case9-12a.md`](findings-case9-12a.md) came from a *saturated* trace, where queueing
inflated every other segment and diluted a fixed cost's share.

**And 97% of that is the transaction wrapper, not the query.** The `gender` select is 66 ms of a
2.52 s segment; the rest is `@Transactional` borrowing a pooled connection, which costs three
round trips ([`areas-to-investigate.md`](areas-to-investigate.md) item 2).

It is also registered unscoped, so it runs on health checks:

```java
public void addInterceptors(InterceptorRegistry registry) {
    registry.addInterceptor(dummyInterceptor);        // SyncConfiguration:111 — no path patterns
}
```

`GET /ping` reports exactly 3.0 database calls — the connection-borrow floor — and 17.6 ms of
application time, for an endpoint that reads nothing. 2,940 calls in one four-hour run; in
production the load balancer probes forever.

> **That 12.6% is a share of sync load, not of production.** Every run behind it serves sync and
> nothing else. Production also carries the web app, the API and bulk imports, and shares its
> database with avni-etl and Metabase. The interceptor fires on **every** web request, so the
> absolute waste against a wider mix is larger than these runs show; but the **share** does not
> transfer, because heavier work per request dilutes a fixed cost. **Treat 12.6% as the reason to
> act, not the saving to promise.**

## Why it exists, and why that reason expired

```
Sep 2019   d2a4b5543  #23  | Run a dummy database get after a transaction
                            so that everything gets flushed properly
Mar 2026   9e1b91a0a  #966 | Make GET endpoints readonly, Replace Jakarta
                            @Transactional with Spring @Transactional
```

**The hack predates the change that obsoletes it by six and a half years.** `#966` matters twice
over: Jakarta's `@Transactional` has no `readOnly` attribute, so before that commit the flag could
not have worked even if someone had written it.

It guards against a real mechanism. `spring.jpa.open-in-view` is not set, so Spring Boot's default
of `true` applies: one Hibernate Session spans the whole request, including the parts outside any
transaction. An entity modified there is dirty with nothing to flush it, and
`@Transactional(readOnly = true)` sets flush mode `MANUAL`, so the read paths will not flush
either. `postHandle` runs a query inside a plain `@Transactional`, and Hibernate flushes before
executing it.

The comment's puzzlement — *"changing flush mode does not seem to fix the problem"* — follows from
the same mechanism. Flush mode governs *when* a flush happens **within** a transaction. If the
entity was modified outside one, there is no transaction to flush into.

## Measurement 1: no snapshot is taken on a read

A counter in `AbstractUserType.deepCopy`, loading one `Encounter` through
`EncounterRepository.findByUuid` inside a `TransactionTemplate`, against the local `openchs_test`
database:

```
readOnly = true   ->  0 deepCopy calls
readOnly = false  ->  2 deepCopy calls
```

`readOnly = true` propagates into Hibernate loading entities **read-only**, so no dirty-check
snapshot is taken. With no snapshot Hibernate cannot detect a change, and with flush mode `MANUAL`
it would not write one. **On a pull there is nothing for the guard to flush**, and every sync
endpoint is `@Transactional(readOnly = true)` (`EncounterController:248`).

## Measurement 2: on a UTC server it is never dirty

A counter on `session.isDirty()` at the top of `postHandle`, across the whole test suite — 1,051
tests — run twice with only the JVM default zone changed:

| JVM zone | invocations | dirty |
|---|---|---|
| `Asia/Kolkata` | 186 | **18** — all `POST /encounters`, `/programEnrolments`, `/programEncounters` |
| **`Etc/UTC`** — what production runs (`timedatectl`) | 186 | **0** |

No GET dirtied the session in either run, which is measurement 1 arriving from the other
direction.

> **Corrected 26 Oct 2026: the second row does not describe production.** The load tests and the
> production JVM say otherwise. Production runs with `user.timezone=Etc/UTC` (`jcmd …
> VM.system_properties`), and under Joda 2.10.10 that default zone has the ID `Etc/UTC`, which
> `equals()` treats as a different chronology from Jackson's `UTC`:
>
> | JVM default zone | Joda default ID | Jackson `DateTime` `equals` converter `DateTime` |
> |---|---|---|
> | `UTC` | `UTC` | **true** |
> | **`Etc/UTC`** — production, and the load-test server | `Etc/UTC` | **false** |
> | `GMT` / `Etc/GMT` | `Etc/GMT` | false |
> | `Asia/Kolkata` | `Asia/Kolkata` | false |
>
> **Re-run 26 Oct 2026 to settle it**, against the local `openchs_test`, with the zone pinned
> in the Gradle test task (`systemProperty 'user.timezone'`) rather than inherited, and the counter
> recording Joda's default with each result:
>
> | test JVM `user.timezone` | Joda default | invocations | dirty |
> |---|---|---|---|
> | `UTC` | `UTC` | 182 | **0** |
> | **`Etc/UTC`** | `Etc/UTC` | 182 | **18** — 10 `POST /encounters`, 6 `/programEnrolments`, 2 `/programEncounters` |
>
> The same 18 POSTs the `Asia/Kolkata` row shows. The zero above came from a JVM whose default was
> `UTC`, not `Etc/UTC`, and only that spelling avoids the defect. In both runs 2 invocations ran
> with Joda's default at `+05:30`: `SubjectApiControllerIntegrationTest` calls
> `DateTimeZone.setDefault` in its setup and never restores it, so whole-suite counts depend on test
> order. On the servers, entities with a Joda `DateTime` are permanently dirty,
> and the load tests measure the consequence directly. **UPDATEs per INSERT on `sync_telemetry`,
> which every sync writes:**
>
> | run | `DummyInterceptor` | UPDATE / INSERT |
> |---|---|---|
> | case 12 control (15 Oct), row 19 at 2 and 4 vCPU, row 26 | registered (twice) | **3.00** in all four |
> | rows 21 and 22 | removed | **1.00** in both |
>
> The push runs show the same 3.00 on `encounter`, `program_encounter` and `program_enrolment`, and
> 0 on `individual`, which has no Joda `DateTime`. **One UPDATE is the controller's commit
> rewriting the still-dirty entity, and two are the interceptor's two `@Transactional` commits.**
> Production pays all three on every such write, and each fires `audit_table_trigger`. At row 26's
> 10,000 users that is ~314,000 redundant full-row UPDATEs an hour.

### The 18 were a timezone bug, not the guard working

`JodaDateTimeConverter.convertToEntityAttribute` returns `new DateTime(data.getTime())` — the **JVM
default zone** — while Jackson's `JodaModule` deserializes client timestamps as **UTC**. Joda's
`equals()` compares instant *and* chronology, so the same moment compares unequal and the entity is
**permanently dirty**. Flushing cannot settle it: the reloaded state takes the database
representation again.

```
from client         : 2018-02-21T17:10:30.000Z        (Jackson -> UTC)
from database       : 2018-02-21T22:40:30.000+05:30   (converter -> default zone)
equals()            : false   <- what Hibernate's dirty check uses
isEqual() (instant) : true
with UTC pinned     : true    <- the fix
```

Where it fires, it **writes**: Hibernate statistics showed `entityUpdates` **delta = 1 on every
POST** — one redundant UPDATE per write, of a row whose values never changed. In UTC that
disappears entirely.

**Fix the converter regardless** — avniproject/avni-server#1098:
`new DateTime(data.getTime(), DateTimeZone.UTC)`. One line. ~~Not a production performance fix —
production is already UTC~~ — **it is a production performance fix** (corrected 26 Oct, above):
production's `Etc/UTC` default zone triggers the defect, so it removes one redundant UPDATE and audit
row per write there, and the interceptor's removal (#1097) takes away the other two. It also stops
developer machines in IST behaving differently from servers. **It also explains the 2019
origin**: a developer in IST would see entities permanently dirty and reasonably conclude flushing
was broken.

## Measurement 3: disabling it breaks nothing, and that proves little

| | tests | failures | errors |
|---|---|---|---|
| baseline | 1,051 | 0 | 0 |
| interceptor disabled in both registrations | 1,051 | 0 | 0 |

**Read that result against its coverage, which is thin.** The full suite produced 186 `postHandle`
invocations across **21 distinct URIs, out of 346 handler methods — about 6%**:

```
DELETE /forms            POST /concepts/bulk      POST /individuals
GET /ping                POST /encounterTypes     POST /programEncounters
GET /individual/search   POST /encounters         POST /programEnrolments
GET /programEnrolment    POST /formMappings       POST /programs        ...
```

**Every covered write is `@Transactional`**, so it flushes at its own commit and the guard has no
role there by construction. The suite exercises **none** of the handlers where it could matter.

> **A load test would not improve this.** It exercises `/encounter`, `/individual`,
> `/v2/syncDetails`, `/resetSyncs`, `/syncTelemetry`, `/encounters` and `/ping` — all
> `@Transactional`. Thousands of invocations, zero dirty, and the question still unanswered. More
> samples of the wrong paths.

## Measurement 4: no code path relies on the flush

The guard can only matter where a handler mutates a managed entity and depends on dirty-check
flushing at request end. **That is a property of the code, not of test coverage**, which is why it
carries the argument:

```
346  handler methods under web/**
278    @Transactional                      -> flush at their own commit
 68    without
 37      mutating (POST/PUT/DELETE)        <- the only candidates
 31        call a non-transactional service method
  0          mutate a managed entity without saving
```

Every mutating service method either persists explicitly — `VideoService`, `RuleService`,
`StorageManagementConfigService`, `OrganisationConfigService.deleteExportSettings` — or touches no
entity. The one method flagged as relying on a flush, `ObservationService.createObservations`, sets
a field on an `ObservationRequest` **DTO**, not an entity. The same is true of the three handlers
that set without saving: `ConfigurationController.getConfig` sets a response DTO, and
`UserController.createUser`/`updateUser` call `userService.updateUser(...)`, which persists.

**None of the 37 is a sync endpoint.** They are admin, config, metabase, user, video and rule
paths.

> **Limits of this analysis, stated so nobody over-reads it.** It is regex and brace matching, not
> a parser, so lambdas and inherited methods can slip through. It follows **one** service level,
> not services calling services. Class-level `@Transactional` detection is approximate. And it
> shows that no *current* path needs the guard — not that none ever did.

## Measurement 5: it would not work even if it did fire

Measurements 1 to 4 show the guard never has anything to flush. **This one asks whether it would
flush it if it did.**

A test-only endpoint with no `@Transactional` that loads an `Encounter`, sets `legacyId` and
returns without saving — exactly the scenario the comment describes:

| | persisted? |
|---|---|
| interceptor **enabled** | **no** |
| interceptor **disabled** | **no** |
| entity loaded via Spring Data | no |
| entity loaded straight off the `EntityManager` | no |

**Every precondition held.** Inside `postHandle`: `txActive=true`, the transaction was
`DummyInterceptor.postHandle`'s own, `flushMode=AUTO`, the entity was **not** read-only, and
`session.isDirty()` was **true**. The guard was in precisely the situation it exists for and
changed nothing.

### Why: Hibernate's auto-flush is query-space scoped

```
postHandle:        txActive=true  dirty=true  flushMode=AUTO
after findAll():   updates 0 -> 0, dirty=true
```

`FlushMode.AUTO` flushes before a query **only when the query's tables intersect the pending
changes**. `genderRepository.findAll()` queries `gender`; the dirty entity is an `encounter`. No
intersection, **no flush** — and the dirty entity the hack exists to rescue is exactly the kind it
skips.

**The hack queries an arbitrary unrelated table, which guarantees it can never flush anything.** It
would work only if the dirty entity happened to be a `Gender`.

> **Two limits.** The commit path is less clear-cut than the query path: `updates` stayed at 0 and
> the value never reached the database, but why the transaction commit *also* failed to write it
> was not isolated, and OSIV participation semantics are fiddly. And this is one entity type on one
> path — "cannot flush a dirty `Encounter`" is measured; "cannot flush anything" follows from how
> query-space flushing works, which is reasoning rather than measurement.

**If a guard of this shape is wanted at all, it should call `session.flush()`** — not query an
unrelated table. That is the version that would do what the comment claims.

## What to do, in order

1. **Fix `JodaDateTimeConverter`** — pin UTC. One line, independent of everything else, and it ends
   the IST/UTC divergence between developer machines and servers.
2. **Path-scope the interceptor** — `.addPathPatterns(...)` to the sync and API paths. One line,
   changes nothing about the flush behaviour it exists for, and removes it from `/ping` and from
   the traffic where measurement 1 proves it cannot fire. **Safe on the evidence above; do this
   without waiting for anything.**
3. **Disable it entirely on prerelease**, with the `isDirty()` counter left in place, and let
   normal admin use run against it. **This is the only thing that exercises the at-risk 37 with
   real usage** — they are admin-console paths, so the environment that reaches them has humans in
   it, not a load generator. **Measurement 5 lowers the stakes here considerably**: there is no
   demonstrated behaviour to lose.
4. **Then remove it**, and re-measure. The 12.6% is a share of request time, not a prediction of
   throughput gain; this campaign has already published one figure that did not survive its
   context.

**`tools/read-only-sync-writes-check.sql` remains worth running** on a quiet server as independent
confirmation from outside the JVM: if a `PUSH=off` sync moves neither `n_tup_upd` nor the WAL LSN,
nothing was being flushed.

## Still not settled

* **Whether any non-web entry point depends on it.** The interceptor only runs on web requests, so
  batch and scheduled work is out of its scope by construction — but that has not been verified.
* **A second service level** in measurement 4.
* **What the 2019 bug actually was — and what, if anything, fixed it.** The timezone explanation
  fits the symptom and is the likeliest, but the commit references nothing beyond its message.
  **Measurement 5 makes this sharper rather than academic**: whatever was observed in 2019, this
  code cannot have fixed it. Either the problem went away for another reason, or it is still
  there and has been masked by every write path calling `save()` explicitly.

## Reproducing any of this

The instrumentation is four to twenty lines in each case and was reverted after each run; the
patches and test files are not in this repository. Measurements 1 and 2 need the local
`openchs_test` database and `AbstractControllerIntegrationTest`; 3 and 4 need no database at all.

> **One trap in measurement 1, which fails towards a false positive.** Spring applies
> `readOnly = true` only when it **starts** a transaction. `@DataJpaTest` in this codebase is
> itself `@Transactional`, so a service call with default `REQUIRED` propagation joins the
> harness's read-write transaction and the flag is silently ignored. Use a `TransactionTemplate`
> with `setReadOnly`, or go through the controller.
