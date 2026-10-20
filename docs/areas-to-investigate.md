# Areas to investigate: where the server's database calls go

**19 October 2026.** The run-level findings are in
[`findings-summary.md`](findings-summary.md) and its siblings. This is the code-level work they
point at — none of it needs an environment.

[`findings-case9-12a.md`](findings-case9-12a.md) measured `DummyInterceptor` at 5.57% of every
request and found that **97% of that cost was the transaction wrapper, not the `gender` query it
runs**. That was an instance of a pattern rather than a one-off, and this is the search for the
others: **work the server does on every request that nothing downstream needs.**

All eight below are of that shape. None is an algorithmic improvement; each removes work.

**Items 1 to 5 and 8 are measured. Items 6 and 7 are read from the code**, and item 6 carries an
open question — it is listed because if it is real it is larger than
almost everything else here, and because one profiler run settles it.

## How these were measured, and how to re-derive them

Two sources, chosen for different properties:

* **`Transaction.databaseCallCount`** is a **census** — every transaction records its own count, so
  shares are exact. Read from `2026-10-19T07-14-41Z-case4-span20-c2a0e76`: healthy, 175 syncs,
  4,416 requests, **zero failures**, so no figure is inflated by queueing.
* **`SqlTrace`** gives statement text and per-call time, but New Relic captures **slow statements
  above a threshold, aggregated** — so its *counts are samples*, not totals. Read its ranking and
  its milliseconds-per-call; never quote its counts as a census.

* **`Metric` timeslices** give the segment tree — `apm.service.overview.web` for the Java/JDBC
  split, and `newrelic.timeslice.value` faceted by `metricTimesliceName` for per-class segments.
  Effectively a coarse profile, and the only route to where application time goes without
  async-profiler.

The first two come from the backup, so they need no account
([`newrelic.md`](newrelic.md)):

```
make newrelic_query RUN=case4-span20                      # the per-endpoint table below
make newrelic_query RUN=case11-run1 EVENT_TYPE=SqlTrace   # statement cost
```

> **The timeslice tree is the one thing the backup does not hold.** `metricTimesliceName` is a
> dimension NRQL resolves at query time; `SELECT * FROM Metric` does not return it, so the export
> keeps only four golden metrics for the app. The segment figures below were taken live and
> **cannot be re-derived from the files** — which matters because `Metric` is the long-retention
> store and this tree is its most valuable content. Worth adding a faceted-aggregate mode to
> `newrelic-export.py`.

The two sources agree where they overlap: the local `Transaction` census gives 802,981 ms over
4,416 transactions with 123,654 database calls, against the live timeslice's 802,783 ms and
123,636 — **0.02% apart**, which is what licenses mixing them below.

## The budget

**4,416 requests, 123,654 database calls, 707 calls per sync.**

| endpoint | requests | db calls | share | calls/request |
|---|---|---|---|---|
| `encounter (GET)` | 2,676 | 73,249 | 59% | 27.4 |
| **`v2/syncDetails (POST)`** | **350** | **39,745** | **32%** | **113.6** |
| `ping (GET)` | 980 | 2,940 | 2.4% | 3.0 |
| `resetSyncs (GET)` | 175 | 2,448 | 2.0% | 14.0 |
| `syncTelemetry (POST)` | 175 | 2,302 | 1.9% | 13.2 |

**`encounter` earns its 27.4 calls** — it returns a thousand records. Everything else on this list
returns almost nothing and is charged like a query.

## Where request time goes, which re-ranks everything below

**Added 20 October 2026.** The table above counts *database calls*. That is the wrong denominator
when the constraint is application CPU, and correcting it reorders the list.

From `apm.service.overview.web` over the same window — **4,416 transactions, 802,981 ms**:

| | ms | share of request time |
|---|---|---|
| **Java** | 657,642 | **81.9%** |
| JDBC | 137,036 | 17.1% |
| Web external | 8,104 | 1.0% |

**So a fix that removes a third of all database calls removes about 5% of request time, not a
third.** `syncDetails` owns 32% of database calls but only **2.7%** of request time.

The timeslice tree gives the segments, and one of them dominates everything else that is removable:

| segment | ms | share | calls | ms/call |
|---|---|---|---|---|
| `DispatcherServlet/doDispatch` | 740,292 | 92.2% | 4,049 | 182.83 |
| `EncounterController/getEncountersBy...` | 540,435 | **67.3%** | 2,675 | 202.03 |
| `Spring/HandlerInterceptor` (all) | 105,619 | 13.2% | 87,785 | 1.20 |
| **`DummyInterceptor/postHandle`** | **101,039** | **12.6%** | 8,066 | 12.53 |
| `SyncController/getSyncDetailsWithScopeAwareEAS` | 41,659 | 5.2% | 350 | 119.03 |
| `AuthenticationFilter/doFilter` | 19,268 | 2.4% | 492 | 39.16 |

**`DummyInterceptor` is 12.6% of all request time and 96% of all interceptor time.** The 5.57%
in [`findings-case9-12a.md`](findings-case9-12a.md) came from a **saturated** trace, where
queueing inflated every other segment and diluted a fixed cost's share. **12.6% is the figure for a
healthy server**, and it makes this the largest single removable item in the document — ahead of
every database fix combined.

> **Two segments are not usable.** `Java/other` aggregates 372,372 calls including background
> threads and is not request time. `AuthenticationFilter/doFilter` reports 492 calls against 4,416
> transactions, so its 2.4% is a sample rather than a total — the 5.62% from the saturated trace
> remains the better figure for it.

### Two bounds this puts on the serialization work

Neither response serialization nor gzip appears as its own segment, but the gaps bound them:

* **Response serialization ≤ 11.7% of request time.** `doDispatch` is 92.2% and the controller
  inside it is 67.3%; the 24.9% between them holds interceptors (13.2%) plus Jackson, HATEOAS
  assembly and view resolution.
* **Gzip plus the whole filter chain ≤ 7.8%.** That is what falls outside `doDispatch`, and
  `AuthenticationFilter` is part of it.

Both are ceilings, not measurements. The gzip bound is what rules item 8 out.

---

## 1. `syncDetails` is 32% of all database calls

113.6 calls per invocation, **twice per sync**, to tell the client which entities changed.

> **Partly tracked.** avniproject/avni-server#1057 (`count(*)` → `exists`) and #1060
> suspect 2 (`filterChangedEntities`) cover parts of this endpoint. **1a, 1b and 1c below are on
> neither.** Fix them in one pass — and note that the 113.6 calls split across all of these
> mechanisms in a proportion nobody has measured.

### 1a. Lazy associations dereferenced inside five loops

`SyncDetailsService.getAllSyncableItems` opens with ~6 bulk repository reads, which is correct, and
then walks each result:

```java
generalEncounters.forEach(formMapping -> {
    if (!groupPrivileges.hasPrivilege(..., formMapping.getSubjectType(), null,
                                           formMapping.getEncounterType(), null)) { ... }
```

`FormMapping.subjectType`, `.program` and `.encounterType` are all
`@ManyToOne(fetch = FetchType.LAZY)` (`FormMapping.java:25-35`), and so is
`OperationalSubjectType.subjectType` — **five collections, not four**:

| collection | associations touched |
|---|---|
| `subjectTypeRepository.findAll()` → `map(OperationalSubjectType::getSubjectType)` | `subjectType` |
| `getAllGeneralEncounterFormMappings()` | `subjectType`, `encounterType` |
| `getAllProgramEncounterFormMappings()` | `subjectType`, `program`, `encounterType` |
| `getAllProgramEnrolmentFormMappings()` | `subjectType`, `program` |
| `getAllRegistrationFormMappings()` | `subjectType` |

**The privilege check is not the only dereference.** `getEncounterTypeUuid()` and `getProgramUuid()`
are convenience accessors doing `this.getProgram().getUuid()`, so the `addToSyncableItems(...)`
lines load proxies too.

**Fix: `@EntityGraph`, not `JOIN FETCH`.** All four form-mapping finders are Spring Data *derived*
queries — `findAllByProgramNullAndEncounterTypeNotNullAndIsVoidedFalseAndFormFormTypeAndImplVersion`
and siblings — so there is no query text to add a fetch join to:

```java
@EntityGraph(attributePaths = {"subjectType", "program", "encounterType"})
List<FormMapping> findByEncounterTypeNotNullAndProgramNotNullAndIsVoidedFalseAnd...(...);
```

`OperationalSubjectTypeRepository` needs a dedicated annotated method rather than an annotation on
inherited `findAll()`.

> **If these are rewritten as `@Query` instead, `join fetch` is an INNER join.** `program` is null
> by definition for general-encounter and registration mappings, so an inner fetch **silently drops
> exactly those rows** and `syncDetails` stops reporting some entity types as syncable — a sync
> that quietly pulls less. It must be `left join fetch`. `@EntityGraph` avoids this: Hibernate
> applies it as a left outer join. All three associations are to-one, so there is no
> cartesian-product risk.

**Size it honestly.** The persistence context caches by identity within the session, so the second
reference to the same `SubjectType` is a hit, not a query. **The select count is bounded by the
number of *distinct* associated entities, not by row count** — with 12 subject types and 36
encounter types in the archetype bundle, roughly 50–60 selects, not 118 × 3.

### 1b. `isCommentEnabled()` is called inside the subject-type loop

```java
subjectTypes.forEach(subjectType -> {
    ...
    if (organisationConfigService.isCommentEnabled()) {      // <- inside the loop
```

It resolves to `organisationConfigRepository.findByOrganisationId(...)`
(`OrganisationConfigService:330-337`). That is a **derived query, not `findById`**, so the
first-level cache does not short-circuit it and it reaches the database on every iteration. The
organisation cannot change within a request, so the call is loop-invariant.

**Measured: 6,885 `organisation_config/select` calls** across 350 `syncDetails` invocations in
`case4-span20` — about 20 per call, against 12 subject types plus other callers.

**Fix: hoist it above the loop.** One line, independent of 1a, and it needs no review beyond
reading it.

### 1c. The change check repeats catchment resolution per syncable item

**Corrected 20 Oct 2026.** An earlier draft of this document said the `count(*)` → `exists` fix
(avniproject/avni-server#1057) would pay best on `Encounter`, as the entity with the most rows and
the most changes. **That is wrong, and the code says so plainly:**

```java
// EncounterService:174
public boolean isScopeEntityChanged(DateTime lastModifiedDateTime, String encounterTypeUuid) {
    return true;
}
```

**Four services already answer unconditionally and issue no query at all** — `EncounterService`,
`ProgramEncounterService`, `ProgramEnrolmentService` and `ScopedEntityApprovalStatusService`. The
three heaviest transactional entities are **already exempt**, so the counting cost never touched
them.

**What the remaining services do, per syncable item**, is three steps, not one:

| | step | repeated for |
|---|---|---|
| 1 | `subjectTypeRepository.findByUuid(...)` | every item naming the same subject type |
| 2 | `getAllRegistrationAddressIdsBySubjectType(catchment, subjectType)` | the same `(catchment, subjectType)` pair, every time |
| 3 | `count(spec) > 0`, with those address ids as an `IN` list | — |

Step 2 is the one to look at. `AddressLevelService:44-54` resolves a custom registration setting,
then address-level types, then the catchment-address projection — **with no cache** — and
`ScopeAwareService` caps the result at `MAX_SUPPORTED_LOCATIONS_IN_CATCHMENT = 65535`. A supervisor
with a wide catchment therefore resolves a large id list **and then passes it into the count as an
`IN` clause**, once per item, for `Individual`, `SubjectMigration`, `SubjectProgramEligibility`,
`Comment`, `CommentThread`, `IndividualRelationship` and `GroupSubject` alike.

**So the expensive part may not be the count the card names.** `#1057` replaces step 3; steps 1 and
2 survive it, and step 2 scales with catchment width — which is exactly what
[Block A′](findings-span20.md) varied.

### What `#1057` does and does not cover

**It changes step 3 only.** Its tech approach names `getChangedEntities` (`:383-392`) and
`filterChangedEntities` (`:432-460`) as entry points and `SyncableRepository.isEntityChanged` as
"the shape to change", then enumerates 23 implementations in four groups — 13 spec-built to convert
to `exists()`, 6 native SQL to rewrite as `select exists(select 1 …)`, 4 needing nothing. Every one
is the final query. The card mentions none of `AddressLevelService`,
`getAllRegistrationAddressIdsBySubjectType`, `findByUuid`, `getAllSyncableItems` or any caching.

**Structurally it cannot reach them.** The only callers of `isEntityChanged` are the three
`ScopeAwareService` default methods (`:24`, `:29`, `:34`), and steps 1 and 2 run in the
implementations *before* that call. So 1a, 1b and 1c all survive it.

**The two fixes are complementary, not competing.** `#1057` makes step 3 cheap **when the answer is
yes**; memoising steps 1 and 2 removes work that happens **whatever the answer**, and that scales
with catchment width. The card is explicit that routine sync gains least from it — *"stopping at
the first match gains nothing when there is no match, because the database still has to read every
candidate to prove there is none"* — which is the regime these runs measure.

> **Four of its 13 group-1 conversions look dead on this path.** `EncounterRepository`,
> `ProgramEncounterRepository`, `ProgramEnrolmentRepository` and `EntityApprovalStatusRepository`
> are all listed, but their services return `true` unconditionally, so `isEntityChanged` is never
> reached from `syncDetails` for them. Harmless to convert; it buys nothing here. **Worth
> confirming they have no caller outside this path** before treating the work as wasted — and
> worth knowing if the card's estimate assumed otherwise.

**Fix: memoise steps 1 and 2 for the duration of the request.** Both are pure functions of
`(catchment, subjectType)`, which cannot change mid request.

> **And the precedent for going further already exists.** If `Individual` is as certainly changed
> as `Encounter` was judged to be, it can join the four that return `true` — removing its check
> entirely rather than optimising it. That is a product judgement about staleness, not a
> performance one, and **avniproject/avni-server#1060 names the measurement**: Q9 against
> production, giving the distribution of entities actually changed per sync, with no load test
> needed.

### And then it is cacheable

The result depends only on the organisation and the user's privileges — nothing about the sync —
so once 1a and 1b are gone it can be cached per `(organisation, user)` rather than recomputed twice
per sync.

**Effort: hours. 1b is one line.**

## 2. The role-switching tax — 10.7% of every database call

`SetOrganisationJdbcInterceptor` charges **three round trips per connection borrow and return**:

```java
reset():   statement.execute("set role \"" + dbUser + "\";");            // on borrow
           statement.execute("set application_name to \"" + dbUser + "\";");
invoke():  statement.execute("RESET ROLE");                              // on close
```

13,248 of 123,654 calls in the run, before a single application query. In `SqlTrace`, **`RESET
ROLE` is the largest consumer of total database time in the entire capture** — more than any
select.

**This is the mechanism behind the `DummyInterceptor` finding generalised.** That interceptor was
expensive because it forced an extra borrow, and a borrow costs three round trips. Every borrow
does.

> **Tracked as avniproject/avni-server#1060 suspect 1**, where it was a hypothesis. This is its
> measurement.

**A second cost sits in the same class.** `invoke` builds a TRACE log line for nearly every proxied
connection method, and its argument is `connection.getMetaData().getConnection().hashCode()`.
**Parameterised logging defers formatting, not argument evaluation**, so `getMetaData()` runs on
every `prepareStatement`, `createStatement`, `commit` and `setAutoCommit` — at any log level. Fold
it into the same change.

**Fixes, cheapest first:**

1. **One statement instead of two on borrow.** PostgreSQL accepts
   `set role "x"; set application_name to "x";` in a single `execute()`. Removes a third of the
   tax. One line.
2. **Or drop `set application_name` altogether.** It labels `pg_stat_activity` and nothing else;
   row-level security depends on `set role` alone. Confirm no dashboard or runbook reads it first.
3. **`RESET ROLE` on close is belt-and-braces** against the early returns in `reset()` — null user
   context, super-admin, absent organisation — where a pooled connection could otherwise keep a
   previous role. Make the borrow path always set or reset explicitly and it can go. **Do this one
   last**: it is the only item here that trades a safety property for a round trip.

## 3. `DummyInterceptor` is 12.6% of request time, and it also runs on `/ping`

> **No card.** It is not among avniproject/avni-server#1060's seven suspects, which were drawn
> from reading the code before any measurement existed.

**The largest single removable cost in this document** — more than every database fix here
combined, and **96% of all interceptor time**. The 5.57% quoted in
[`findings-case9-12a.md`](findings-case9-12a.md) came from a saturated trace, where queueing
inflated everything around it; **12.6% is what it costs on a healthy server**.

> **That 12.6% is a share of sync load, not of production.** Every run behind it serves sync and
> nothing else: no admin or reporting requests, no concurrent ETL, `PUSH=off` on most of them.
> Production's avni-server also carries the web app, the API and bulk imports — `importZipJob`
> alone left 173 transaction traces outside every run window here, up to 189.2 s each — and its
> database is shared with avni-etl and Metabase (avni-server#1060 suspect 5).
>
> **Two consequences, and they pull opposite ways.** The interceptor fires on **every** web request,
> so against production's wider request mix the absolute waste is larger than these runs show. But
> the **share** does not transfer: heavier work per request — deeper pages, colder cache, larger
> organisations, which is the regime
> [avni-product#1904](https://github.com/avniproject/avni-product/issues/1904) measured — dilutes a
> fixed per-request cost. And CPU freed on the application tier does not become headroom
> one-for-one while other workloads contend for the same database.
>
> **So treat 12.6% as the reason to act, not as the saving to promise.**

It is also registered unscoped:

```java
public void addInterceptors(InterceptorRegistry registry) {
    registry.addInterceptor(dummyInterceptor);        // SyncConfiguration:111 — no path patterns
}
```

So the flush hack runs on **health checks**. `ping` reports exactly 3.0 database calls — the borrow
floor from item 2 — for an endpoint that reads nothing, and 17.6 ms of application time for one
that should have none. 2,940 calls in this four-hour run; in production the load balancer probes
forever.

**Two fixes, and they are not the same size.**

1. **Scope it** — `.addPathPatterns(...)` restricted to the sync and API paths. One line, changes
   nothing about the flush behaviour the hack exists for, removes it from `/ping` immediately.
   **Do this now**; it is strictly cheaper than removal and does not wait on anything.
2. **Remove it** — worth 12.6%, but it is a lost-update guard and
   [item 6](#6-java-serialization-on-the-read-path--unconfirmed-and-the-largest-if-it-holds)
   explains what it guards against. `tools/read-only-sync-writes-check.sql` on a quiet server
   decides whether it guards anything real: if a `PUSH=off` sync moves neither `n_tup_upd` nor the
   WAL LSN, the dirtiness was spurious.

## 4. Paged endpoints run a COUNT per page, and the Slice versions already exist

`SqlTrace` ranks COUNT as the **slowest statement class measured**: 180 executions at **1,376
ms/call**, with `count(individual)` the worst single statement at **1,543 ms/call**.

It is pagination, and both shapes are already in the codebase:

```java
@RequestMapping("/encounter")      → CollectionModel<EntityModel<Encounter>>   // Page  → COUNT
@RequestMapping("/encounter/v2")   → SlicedResources<EntityModel<Encounter>>   // Slice → none
```

New Relic records the transaction as **`encounter (GET)`**, so the counting variant is what runs,
and `EntityMetaData.js` confirms why: the `encounter` and `individual` entries carry **no
`apiVersion`**, while `userInfo` carries `apiVersion: "v2"`. The client already has the mechanism
and these entities do not use it. A supervisor at span 20 pulls 75,446 records at 1,000 a page —
roughly **75 COUNTs over millions of rows per sync** ([Block A′](findings-span20.md)).

> **Tracked as avniproject/avni-client#2096**, open — rated "the largest remaining win, no server
> work" on [avni-product#1904](https://github.com/avniproject/avni-product/issues/1904), which
> measured a cold `COUNT` on ChecklistItem page 0 at **24.4 s against 2.5 s** via `/v2`.
>
> **The progress bar is not a blocker**, though `SyncService.js:560` does read `totalElements`:
> #2096 settled it on 14 Oct 2026 — the bar has been relative since 2019, so the total is
> unchanged either way. **Nothing to decide; it needs shipping.**

## 5. INFO logging on the sync path

> **Tracked as avniproject/avni-server#1060 suspect 7.**

`DbRoleRepository` logs at **INFO on every role switch**:

```java
logger.info("Setting role back to user: " + organisation.getDbUser());
```

It reaches the sync path through `LocationSyncRepository` and `LocationMappingSyncRepository`, both
`SyncableRepository` implementations. `SyncController.getSyncDetailsWithScopeAwareEAS` adds two
timing lines per call.

Not every request — but the precedent is measured: `AuthenticationFilter`'s own code is **5.62% of
every request**, and F2 attributed it to its two INFO lines ([9/12a](findings-case9-12a.md)).

**Fix.** Demote to DEBUG.

---

## 6. Java serialization on the read path — *unconfirmed, and the largest if it holds*

```java
public boolean isMutable() { return true; }

public T deepCopy(final Object value) {
    ObjectOutputStream oos = new ObjectOutputStream(bos);   // full Java serialization
    oos.writeObject(value);
    return (T) new ObjectInputStream(bais).readObject();
}
```

> **No card.**

`AbstractUserType` backs every `ObservationCollection` column — confirmed: `AbstractEncounter:39` carries `@Type(ObservationCollectionUserType.class)`, and that type extends `AbstractJsonbUserType`, which extends `AbstractUserType`. `isMutable() = true` tells Hibernate
to take a **deep-copied snapshot of every observation column it loads**, to dirty-check later by
`equals()`. `disassemble()`, `assemble()` and `replace()` route through `deepCopy` as well.

If that runs on pulls, it is **Java serialization per record** on an endpoint that returns 1,000
records a page — far more expensive than the Jackson response serialization usually discussed, and
sitting exactly where the constraint is: the application tier at 99% CPU with the database at a
fifth of capacity.

> **Whether it runs on pulls is not established.** The sync endpoints are
> `@Transactional(readOnly = true)`. If that propagates to Hibernate loading entities read-only,
> snapshots are skipped and `deepCopy` never fires on the read path. If it only sets flush mode to
> `MANUAL` — which is the behaviour we know it has, and the behaviour that makes
> `DummyInterceptor` necessary — the snapshots are still taken. **This is the one item here that
> must be measured before it is believed**: async-profiler against `encounter (GET)` at an
> unsaturated load shows `ObjectOutputStream` immediately, or shows it absent.

**It is also the explanation for `DummyInterceptor`.** `spring.jpa.open-in-view` is not set, so
Spring Boot's default of `true` applies: one Session spans the whole request, outside any
transaction, where entities can be dirty with nothing to flush them. The interceptor forces a
transaction so a flush happens. Both halves — OSIV on by default, and a serialization-based
`deepCopy` in a mutable `UserType` — are well-documented anti-patterns rather than anything
peculiar to this codebase.

**Fixes, in descending order of how much they remove:**

1. **Hibernate 6 native JSON.** Boot 3.3.5 ships Hibernate 6.5, so `@JdbcTypeCode(SqlTypes.JSON)`
   replaces `AbstractUserType` outright — Jackson binding instead of Java serialization, and
   correct mutability semantics for free. Deletes a hand-rolled class rather than tuning it.
2. **`spring.jpa.open-in-view=false`.** Removes the condition `DummyInterceptor` exists for. **Risk
   is real**: responses serialize JPA entities through HATEOAS, so anything lazily loaded during
   serialization begins throwing `LazyInitializationException`. Needs a test pass — and items 1
   and 4 above push the same way by making fetches explicit.
3. **If the `UserType` stays, stop serializing.** `new ObservationCollection((Map) value)` is a copy
   orders of magnitude cheaper. Or `isMutable() = false`, which skips the copy entirely — that
   needs the **four** in-place `getObservations().putAll(...)` sites changed to replace the
   collection instead. All four are on the write path, applying decisions during save, so the
   change is bounded.

**Do not delete `DummyInterceptor` on this reasoning alone.** Run
`tools/read-only-sync-writes-check.sql` first: if a `PUSH=off` sync moves `n_tup_upd` or the WAL
LSN, something genuinely mutates entities on a read path and that must be found before the guard
comes out. If it moves neither, the dirtiness was spurious and the guard was protecting nothing.

## 7. Jackson: Blackbird, and a version split to fix regardless

> **No card.**

`AvniSpringConfiguration:184` declares `@Bean @Primary ObjectMapper` returning
`ObjectMapperSingleton.getObjectMapper()`, so HTTP responses do flow through that single mapper and
a module registered there takes effect.

**Registering `jackson-module-blackbird` is hours of work and worth roughly 1–2% of request time**,
not the 10–20% usually quoted for it. Two reasons to discount:

* That 10–20% is of *serialization time*, and serialization is at most 11.7% of a request here.
* Blackbird optimises **bean accessors** via `LambdaMetafactory`. `ObservationCollection extends
  HashMap<String, Object>`, and map serialization goes through `MapSerializer` untouched. Encounter
  observations are p50 **4 keys** against 12 entity fields, so most of the payload is still
  bean-shaped and some benefit lands — but not all of it.

**The version split is worth fixing on its own.** `avni-server-data/build.gradle:30-34` pins
`jackson-databind`, `-core` and `-annotations` to **2.15.4**, overriding Boot 3.3.5's BOM at
**2.17.2**. A Blackbird dependency added without a version resolves from the BOM at 2.17.2 against
databind 2.15.4, and Jackson requires matched minors across modules. Pin Blackbird to 2.15.4 or
align everything — do not let it float. `./gradlew :avni-server-api:dependencies | grep
jackson-databind` shows what actually resolves today.

## 8. Gzip runs on the JVM, and there is nowhere to move it to

> **No card — and, as of 20 Oct 2026, no fix.** Recorded so it is not proposed again.

`server.compression.enabled=true` in `application.properties`, so Tomcat compresses every response
over 2 KB on the thread that is the constraint. The obvious remedy is to push it to the edge. **The
edge cannot take it:**

* **TLS terminates at the ALB** — `provision/tofu/modules/avni-env/loadbalancer.tf:63-68`, an
  HTTPS listener with `certificate_arn`. **An ALB does not compress responses**; it passes them
  through.
* **There is no proxy tier behind it.** `configure/loadtest_avni_servers.yml:21` says so outright
  — *"avni-server on 8021 directly with no nginx in front"* — and `nginx_appserver` is commented
  out in `configure/site.yml:36`.

So moving gzip is not a configuration change. It is either **CloudFront in front of the ALB**, which
puts a CDN in front of an API for one reason, or **re-enabling an nginx tier** on every app server,
which is a component to deploy, run and patch. The `nginx` role exists, so the second is cheaper
than building from nothing — but neither is a config edit.

**Against a ceiling of ≤ 7.8% shared with the whole filter chain — low single digits — that trade
does not pay.** Leave it on the JVM.

**What does help is making the payload smaller.** Compression cost scales with bytes in, so
anything that shrinks a sync response reduces it without moving it: item 7, and any trimming of
what the sync returns. That is the lever here, not relocation.

## Ranked

**Ordered by share of request time**, which is the denominator that matters while application CPU
is the constraint — not share of database calls.

| | fix | effort | share of request time |
|---|---|---|---|
| **3** | **remove or path-scope `DummyInterceptor`** | one line to scope; more to remove | **12.6%** |
| 6 | native JSON mapping / stop serializing in `deepCopy` | days | **unconfirmed** — profile first |
| 1 | `@EntityGraph` on five `syncDetails` finders; hoist `isCommentEnabled()` | hours; 1b is one line | 2.7% (32% of database calls) |
| 4 | ship avni-client#2096 (`/v2` Slice) | specified, not built | slowest statement class |
| 2 | one-statement role set; drop `application_name` | one line | ~1.8% |
| 7 | Blackbird + fix the Jackson version split | hours | ~1–2% |
| 5 | demote INFO logs | one line | 5.62% precedent, sample uncertain |

**Item 3 is now the headline.** Path-scoping it is one line and removes it from `/ping` today;
removing it outright needs the flush question settled first, and that is what
`tools/read-only-sync-writes-check.sql` is for.

**Item 8 is not in the table**: there is no proxy tier to move gzip to, so it has no fix to rank.

**Item 6 is the one that could beat it**, and it is not measured yet — one async-profiler run
against `encounter (GET)` settles it.

> **Validated against `avni-client`, 20 Oct 2026.** A ninth item — dropping Spring HATEOAS wrapping
> on the sync endpoints — was removed: `SubjectMigrationService.js:68` reads `_links`, so the
> envelope is consumed. The same pass found that `totalElements` is consumed too, which is what
> turned item 4 from a switch into a design choice. **Check the client before proposing to change
> what the server returns.**

## What this does not claim

**It does not promise a faster sync.** Database time is about 15% of a request and `serverMs` is
6–7% of a sync, so none of this moves what a device waits for
([summary](findings-summary.md), §3). **These raise the saturation ceiling**, which is where cases
[12](findings-case12.md) and [13](findings-case13.md) showed the system actually fails — case 13
lost 38% of its throughput to 47% more load.

**It is not a profile.** Shares here are of *database calls*, not CPU. The application tier is the
constraint and most of its time is not database time, so a change that removes 10% of calls does
not remove 10% of the request. [`findings-case9-12a.md`](findings-case9-12a.md) recommends
async-profiler against `encounter (GET)` at an unsaturated load for that, and it remains the right
next measurement — the rest are what can be acted on without it.

**Items 1a and 6 need a correctness review, not just a benchmark.** A fetch join changes what a
query returns when associations are null — `left`, not inner — and changing a `UserType`'s
mutability changes when Hibernate detects a write. Items 1b, 2, 3 and 5 are behaviour-preserving by
inspection, and item 4 is specified on avni-client#2096.
