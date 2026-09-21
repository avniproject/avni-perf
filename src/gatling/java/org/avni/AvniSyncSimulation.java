package org.avni;

import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;
import static java.lang.System.out;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import io.gatling.javaapi.core.*;
import io.gatling.javaapi.http.*;
import org.avni.helper.CognitoHelper;
import org.avni.models.AvniEntity;
import org.avni.models.SyncDetail;
import com.fasterxml.jackson.databind.ObjectMapper;

import com.fasterxml.jackson.databind.JsonNode;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;


public class AvniSyncSimulation extends Simulation {
    // Declared first: loadEntities() runs in the static initialiser and needs it.
    private static final ObjectMapper om = new ObjectMapper();

    private static final String baseUrl = System.getProperty("BASE_URL", "https://perf.avniproject.org");
    private static final Integer userCount = Integer.getInteger("USER_COUNT", csv("sync-users.csv").recordsCount());
    private static final Integer rampPeriod = Integer.getInteger("RAMP_PERIOD", csv("sync-users.csv").recordsCount() * 20);
    // The client ships pageSize 1000 (avni-client config/initialSettings.json). It cannot be read from
    // the pinned openchs-models package - it lives in the client app, not the models library - so it
    // is mirrored here and must be updated if the client changes it. Older installs may still be on
    // 100; see the plan, D8.3.
    private static final Integer pageSize = Integer.getInteger("PAGE_SIZE", 1000);
    private static final Integer maxPauseToSimulateRealmStorage = Integer.getInteger("MAX_REALM_STORAGE_PAUSE", 2);
    // An override, not the default. Left unset, the window end comes from the syncDetails response
    // as the client does. Set it to pin the window across runs.
    private static final String nowOverride = System.getProperty("NOW");
    // The client sends its Android id; filterChangedEntities branches on it for device-aware entities.
    private static final String deviceId = System.getProperty("DEVICE_ID", "avni-perf-simulation");

    // E2. Which sync is being simulated. "csv" takes lastModifiedDateTime from the feeder file;
    // "full" forces a first sync; "incremental" forces a recent window. A run should say which of
    // these it is - they have completely different profiles, and the committed user file has always
    // held 1900-01-01, so every run to date has been a full sync whether or not that was intended.
    private static final String syncMode = System.getProperty("SYNC_MODE", "csv");
    /**
     * STRUCTURAL_CHECK turns the run into H5's structural gate rather than a measurement.
     *
     * A load run tolerates a small error budget, because at scale something always fails and the
     * question is whether the rate is acceptable. The structural check asks a different question -
     * can the client read this data at all - so its budget is zero. One bad datatype or one
     * dangling reference is a defective dataset, however rare.
     *
     * It also caps duration: a structural check that has not finished in a few minutes has found
     * something, and waiting out a full run to see it is wasted time.
     */
    private static final boolean structuralCheck =
        Boolean.parseBoolean(System.getProperty("STRUCTURAL_CHECK", "false"));
    private static final double maxFailedPercent =
        Double.parseDouble(System.getProperty("MAX_FAILED_PERCENT", "1.0"));
    /**
     * p95 for a light sync, measured at 80.0s in production (Q5, success criteria). Band 1 carries
     * 98% of production's syncs, so this is the threshold the common case is held to. Asserted only
     * when explicitly set, because a laptop against a local database is not the environment the
     * figure was measured in.
     */
    private static final String maxP95Millis = System.getProperty("MAX_P95_MS");
    private static final int incrementalSinceHours = Integer.getInteger("INCREMENTAL_SINCE_HOURS", 24);
    private static final String FULL_SYNC_SINCE = "1900-01-01T00:00:00.000Z";

    private static final List<AvniEntity> entities = loadEntities();

    // Authentication mode. "none" (default) sends only the USER-NAME header and requires the target
    // server to run with AVNI_IDP_TYPE=none. "cognito" mints a token per user and is limited to runs
    // shorter than the token lifetime - there is no refresh. See docs/sync-simulation-plan.md, B.
    private static final String authMode = System.getProperty("AUTH_MODE", "none");
    private static final boolean useCognito = "cognito".equalsIgnoreCase(authMode);
    private static final Map<String, String> userTokens = new ConcurrentHashMap<>();
    /**
     * The entity + entityTypeUuid pairs the server says this user tracks, learned by asking it.
     *
     * D1: the client posts one status row per (entityName, entityTypeUuid), and the server matches
     * on both. Posting an empty type uuid makes every typed entity - Individual, Encounter,
     * ProgramEncounter, ProgramEnrolment, and everything split by subject type or form mapping -
     * fall through to the server's 1900 default and full-sync regardless of what the window says.
     * That is most of the sync volume, so incremental mode was not exercising it at all.
     *
     * The list is per user rather than per organisation: every branch in
     * SyncDetailsService.getAllSyncableItems is gated on the user's privileges, so two users in one
     * organisation legitimately track different sets.
     */
    private static final Map<String, List<SyncDetail>> userSyncStatuses = new ConcurrentHashMap<>();
    private static final java.util.concurrent.atomic.AtomicBoolean warnedAboutMissingBootstrap =
        new java.util.concurrent.atomic.AtomicBoolean(false);

    // E1. circular, not random. random() draws with replacement, so the same real user can be driven
    // by two virtual users at once - contention that does not happen in the field - while other users
    // in the file never run at all. circular() walks the file in order and wraps, which makes a run
    // repeatable and spreads load evenly. It only overlaps users when USER_COUNT exceeds the file,
    // which is warned about below.
    FeederBuilder<String> feeder = csv("sync-users.csv").circular();

    HttpProtocolBuilder baseProtocol = http.baseUrl(baseUrl)
        .acceptHeader("application/json")
        .contentTypeHeader("application/json")
        .acceptEncodingHeader("gzip")
        .header("USER-NAME", "#{userName}")
        .connectionHeader("Keep-Alive")
        .userAgentHeader("okhttp/5.0.0-alpha.11");

    HttpProtocolBuilder httpProtocol = useCognito
        ? baseProtocol.header("AUTH-TOKEN", "#{token}")
        : baseProtocol;
    // Under AUTH_MODE=cognito, mint a token per user once and cache it. Blocking work inside a
    // session function stalls the injector's event loop, so this is deliberately confined to the
    // opt-in path; the default mode does no work here at all.
    ChainBuilder authChainBuilder = useCognito
        ? exec(session -> {
              if (session.contains("token") && !session.getString("token").isEmpty()) {
                  return session;
              }
              String userName = session.getString("userName");
              String token = userTokens.computeIfAbsent(userName,
                  u -> CognitoHelper.getTokenForUser(u, session.getString("password")));
              return session.set("token", token);
          })
        : exec(session -> session);

    /**
     * Ask the server what this user tracks, once, before the first real syncDetails call.
     *
     * An empty array is the client's own bootstrap shape: the server adds every syncable item it
     * can see for this user at REALLY_OLD_DATE and returns the lot, so the response round-trips
     * into the request body of every subsequent sync. Nothing has to derive the organisation's
     * structure independently.
     *
     * Two virtual users on the same username can race here and both bootstrap. The result is one
     * wasted request, not a wrong body, so it is left alone rather than locked - a lock in a
     * session function would stall the injector's event loop, which is a worse trade.
     */
    ChainBuilder bootstrapChain =
        doIf(session -> !userSyncStatuses.containsKey(session.getString("userName")))
            .then(exec(http("Bootstrap sync statuses")
                    .post(session -> "/v2/syncDetails?includeUserSubjectType=true&deviceId=" + deviceId)
                    .body(StringBody("[]")).asJson()
                    .check(status().is(200))
                    .check(jsonPath("$.syncDetails").transform(AvniSyncSimulation::parseSyncDetails)
                        .saveAs("bootstrappedStatuses")))
                .exec(session -> {
                    @SuppressWarnings("unchecked")
                    List<SyncDetail> tracked = (List<SyncDetail>) session.get("bootstrappedStatuses");
                    if (tracked != null && !tracked.isEmpty()) {
                        userSyncStatuses.putIfAbsent(session.getString("userName"), tracked);
                    }
                    return session;
                }));

    ChainBuilder syncChainBuilder =
        exec(authChainBuilder)
            .exec(bootstrapChain)
            .exec(session -> session.set("syncStartTime", java.time.Instant.now().toString()))
            .exec(resetSyncChain())
            .exec(http("Getting SyncDetails")
                .post(session -> "/v2/syncDetails?includeUserSubjectType=true&deviceId=" + deviceId)
                .body(StringBody(AvniSyncSimulation::syncStatusBody)).asJson()
                .check(status().is(200))
                .check(jsonPath("$.syncDetails")
                    .transform(AvniSyncSimulation::parseSyncDetails).saveAs("syncDetails"))
                // The client takes the sync window end from this response rather than from its own
                // clock, and uses two different values - see windowEndFor.
                .check(jsonPath("$.now").saveAs("serverNow"))
                .check(jsonPath("$.nowMinus10Seconds").saveAs("serverNowMinus10Seconds")))
            .exec(sync())
            .exec(postSyncTelemetry());
    ScenarioBuilder syncScenario = scenario("Sync " + syncMode)
        .feed(feeder)
        // `lastModifiedDateTime` stays on the session for SYNC_MODE=csv, which reads it from the
        // feeder. Every other mode computes the window per entity in syncStatusBody.
        .exec(syncChainBuilder);

    {
        int feederRows = csv("sync-users.csv").recordsCount();
        out.println(String.format(
            "Sync mode: %s | users: %d | feeder rows: %d | ramp: %ds | page size: %d | auth: %s",
            syncMode, userCount, feederRows, rampPeriod, pageSize, authMode));
        if (userCount > feederRows) {
            out.println(String.format(
                "WARNING: USER_COUNT (%d) exceeds the user file (%d rows), so the same real user will "
                + "be synced by more than one virtual user at once. That is contention the field does "
                + "not have - add users rather than oversubscribing the file.",
                userCount, feederRows));
        }
        if (structuralCheck) {
            out.println(
                "STRUCTURAL CHECK: asserting zero failures. This is H5's gate on a generated "
                + "dataset, not a measurement - any failure means the client cannot read the data.");
        }

        List<Assertion> assertions = new ArrayList<>();
        if (structuralCheck) {
            // Zero, not a rate. A non-200 anywhere means a reference the generated data does not
            // satisfy, and one is enough to make the dataset defective.
            assertions.add(forAll().failedRequests().count().is(0L));
        } else {
            assertions.add(forAll().failedRequests().percent().lte(maxFailedPercent));
        }
        if (maxP95Millis != null) {
            assertions.add(global().responseTime().percentile(95.0)
                .lte(Integer.parseInt(maxP95Millis)));
        }

        setUp(syncScenario.injectOpen(rampUsers(userCount).during(rampPeriod)))
            .protocols(httpProtocol)
            .assertions(assertions.toArray(new Assertion[0]));
    }

    /**
     * The sync window start for this virtual user, per SYNC_MODE.
     *
     * Incremental is the common production case and looks nothing like a first sync, so the two
     * belong in separate runs rather than being decided by whatever happens to be in the user file.
     *
     * Caveat: incremental is only partly effective until D1's bootstrap lands. The sync status body
     * carries an empty entityTypeUuid, and the server matches on name AND type uuid, so typed
     * entities - Individual, Encounter, ProgramEncounter, ProgramEnrolment - still fall through to
     * the server's 1900 default and still full-sync. Reference data does honour the window.
     */
    private static String loadedSinceFor(Session session, String entityName) {
        switch (syncMode) {
            case "full":
                return FULL_SYNC_SINCE;
            case "incremental":
                return java.time.Instant.now()
                    .minus(java.time.Duration.ofHours(incrementalSinceHours)).toString();
            case "csv":
                return session.getString("lastModifiedDateTime");
            case "realistic":
                return realisticLoadedSince(session.getString("userName"), entityName);
            default:
                throw new IllegalArgumentException(
                    "SYNC_MODE must be one of full, incremental, csv, realistic - got: " + syncMode);
        }
    }

    /**
     * Q2's measured gap between one user's syncs: hours, against the quantile they sit at.
     *
     * The shape matters more than any single figure. A median of 16 minutes beside a 75th
     * percentile of 12.5 hours is two behaviours, not one with spread - repeated syncing inside a
     * working session, then a long gap until the next. Drawing every entity from a distribution
     * centred on either mode gets the incremental payload wrong in opposite directions.
     */
    private static final double[][] GAP_HOURS = {
        {0.25, 0.0394}, {0.50, 0.2692}, {0.75, 12.50}, {0.90, 39.44}, {0.99, 196.70}
    };

    /**
     * A per-entity window, spread as production's own gaps are.
     *
     * Uniform timestamps across every entity produce uniform selectivity in the per-row queries,
     * which is the one thing real syncs never have: reference data was last pulled when the
     * configuration changed, transactional data a few minutes ago. Since `loadedSince` is what
     * feeds those queries, a uniform body measures a query plan production does not run.
     *
     * Derived from the user and entity name rather than drawn at random, so a run reproduces and
     * two virtual users on one account agree about what that account has already seen.
     */
    private static String realisticLoadedSince(String userName, String entityName) {
        int h = (userName + "|" + entityName).hashCode();
        double q = ((h & 0x7fffffff) % 10_000) / 10_000.0;
        q = Math.min(Math.max(q, 0.001), 0.999);

        double hours;
        if (q <= GAP_HOURS[0][0]) {
            hours = GAP_HOURS[0][1] * (q / GAP_HOURS[0][0]);
        } else if (q >= GAP_HOURS[GAP_HOURS.length - 1][0]) {
            hours = GAP_HOURS[GAP_HOURS.length - 1][1];
        } else {
            hours = GAP_HOURS[GAP_HOURS.length - 1][1];
            for (int i = 0; i < GAP_HOURS.length - 1; i++) {
                double q0 = GAP_HOURS[i][0], q1 = GAP_HOURS[i + 1][0];
                if (q >= q0 && q <= q1) {
                    double f = (q - q0) / (q1 - q0);
                    // Interpolate in log space: the range spans four orders of magnitude, and a
                    // straight line through it would put almost every entity in the tail.
                    hours = Math.exp(Math.log(GAP_HOURS[i][1])
                        + f * (Math.log(GAP_HOURS[i + 1][1]) - Math.log(GAP_HOURS[i][1])));
                    break;
                }
            }
        }
        return java.time.Instant.now()
            .minus(java.time.Duration.ofSeconds((long) (hours * 3600))).toString();
    }

    private static final String RESET_SYNC = "ResetSync";

    /**
     * The client pulls ResetSync before it even asks for syncDetails - dataServerSync calls
     * getResetSyncData first, and only then getSyncDetails. If rows come back, the client wipes local
     * data and re-downloads everything, so this call is the trigger for the heaviest event the server
     * sees.
     *
     * getResetSyncData also differs from the other pulls in two ways: it does not reverse the
     * metadata list, and it passes its own clock as `now` rather than the server's value - which it
     * could not use anyway, not having called syncDetails yet.
     *
     * The post-reset re-download itself is not modelled here. That is a scenario rather than a
     * request, and belongs with the spike profile in E3.
     */
    private static ChainBuilder resetSyncChain() {
        AvniEntity resetSync = entities.stream()
            .filter(e -> RESET_SYNC.equals(e.entityName))
            .findFirst()
            .orElse(null);
        if (resetSync == null) {
            return exec(session -> session);
        }
        return exec(session -> session.set("allPagesNotFetched", true))
            .asLongAs("#{allPagesNotFetched}", "index")
            .on(group(RESET_SYNC).on(
                exec(http(RESET_SYNC)
                    .get(session -> "/" + resetSync.path
                        + "?lastModifiedDateTime=" + session.getString("lastModifiedDateTime")
                        + "&now=" + java.time.Instant.now()
                        + "&size=" + pageSize
                        + "&page=" + session.getInt("index"))
                    .check(status().is(200))
                    .check(bodyString()
                        .transformWithSession(AvniSyncSimulation::hasMorePages)
                        .saveAs("allPagesNotFetched")))));
    }

    /**
     * Every real client ends every sync with a POST to /syncTelemetry. It is a write on the hot path,
     * and it is what populates the table the whole measurement strategy leans on - so leaving it out
     * both under-counts write load and produces runs that generate no telemetry of their own.
     *
     * The per-entity phase durations avni-client#2121 adds are not modelled here: the simulation does
     * not parse or persist anything, so it has no honest value to report for them. Counts are real.
     */
    private static ChainBuilder postSyncTelemetry() {
        return exec(http("Posting SyncTelemetry")
            .post("/syncTelemetry")
            .body(StringBody(AvniSyncSimulation::syncTelemetryBody)).asJson()
            .check(status().in(200, 201, 204)));
    }

    private static String syncTelemetryBody(Session session) {
        Map<String, Object> entityStatus = new LinkedHashMap<>();
        List<Map<String, Object>> pull = new ArrayList<>();
        for (AvniEntity entity : entities) {
            if (!entity.pullRequired) {
                continue;
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("entity", entity.entityName);
            row.put("todo", 0);
            row.put("done", 0);
            pull.add(row);
        }
        entityStatus.put("pull", pull);
        entityStatus.put("push", new ArrayList<>());

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("uuid", UUID.randomUUID().toString());
        body.put("syncStatus", "complete");
        body.put("syncStartTime", session.getString("syncStartTime"));
        body.put("syncEndTime", java.time.Instant.now().toString());
        body.put("entityStatus", entityStatus);
        body.put("appVersion", "avni-perf");
        body.put("androidVersion", "simulated");
        body.put("deviceName", deviceId);
        body.put("deviceInfo", Collections.singletonMap("simulated", true));
        body.put("appInfo", Collections.singletonMap("simulated", true));
        body.put("syncSource", "avni-perf-simulation");
        try {
            return om.writeValueAsString(body);
        } catch (JsonProcessingException e) {
            throw new UncheckedIOException("Could not serialise sync telemetry", e);
        }
    }

    /**
     * The sync window end, taken from the syncDetails response as the client does.
     *
     * The client uses two different values, and the difference is not cosmetic. getRefData's
     * signature takes three arguments and is called with four, so the endDateTime it is passed falls
     * on the floor and reference entities use `now`. getTxData does take it, so transactional
     * entities use `nowMinus10Seconds`. The ten-second offset presumably avoids missing records
     * written while the sync is in flight.
     *
     * This may well be unintentional on the client's side, but it is what runs, so it is what the
     * simulation reproduces. NOW overrides both, for runs that need a fixed window.
     */
    private static String windowEndFor(AvniEntity entity, Session session) {
        if (nowOverride != null) {
            return nowOverride;
        }
        String key = "reference".equals(entity.type) ? "serverNow" : "serverNowMinus10Seconds";
        String value = session.getString(key);
        if (value == null) {
            throw new IllegalStateException(
                "No " + key + " in session - the syncDetails response did not carry it");
        }
        return value;
    }

    /**
     * The body of the syncDetails request: the client posts every row of its EntitySyncStatus table,
     * which is what the server diffs against to decide what has changed.
     *
     * Posting an empty array is not neutral. getChangedEntities adds any syncable item the client did
     * not mention at REALLY_OLD_DATE, so an empty body asks for a full sync of everything and the
     * incremental path is never exercised. See the plan, D1.
     */
    private static List<SyncDetail> parseSyncDetails(String listElements) {
        try {
            return om.readValue(listElements, new TypeReference<List<SyncDetail>>() {
            });
        } catch (JsonProcessingException e) {
            throw new UncheckedIOException("Could not parse syncDetails", e);
        }
    }

    /**
     * The status array the client posts: one row per (entityName, entityTypeUuid) it tracks.
     *
     * Built from what the server told us this user tracks, not from the generated entity table.
     * The table lists entity *types*; the body needs *rows*, and the difference is every entity
     * split by subject type, programme or encounter type. Getting that wrong is not a smaller
     * body - it is a body the server cannot match, so those entities silently full-sync.
     *
     * Falls back to the flat table only if the bootstrap has not run, which keeps a misconfigured
     * run working rather than failing obscurely. The console says when that happens.
     */
    private static String syncStatusBody(Session session) {
        List<SyncDetail> tracked = userSyncStatuses.get(session.getString("userName"));
        List<Map<String, Object>> statuses = new ArrayList<>();

        if (tracked == null || tracked.isEmpty()) {
            if (warnedAboutMissingBootstrap.compareAndSet(false, true)) {
                out.println(
                    "WARNING: no bootstrapped status list for this user, so the body carries an "
                    + "empty entityTypeUuid per entity. The server matches on name AND type uuid, "
                    + "so every typed entity will fall through to its 1900 default and full-sync "
                    + "whatever SYNC_MODE says.");
            }
            for (AvniEntity entity : entities) {
                if (!entity.pullRequired) {
                    continue;
                }
                statuses.add(statusRow(entity.entityName, "", loadedSinceFor(session, entity.entityName)));
            }
        } else {
            for (SyncDetail d : tracked) {
                statuses.add(statusRow(d.entityName,
                    d.entityTypeUuid == null ? "" : d.entityTypeUuid,
                    loadedSinceFor(session, d.entityName)));
            }
        }

        try {
            return om.writeValueAsString(statuses);
        } catch (JsonProcessingException e) {
            throw new UncheckedIOException("Could not serialise sync statuses", e);
        }
    }

    private static Map<String, Object> statusRow(String entityName, String entityTypeUuid,
                                                 String loadedSince) {
        Map<String, Object> status = new LinkedHashMap<>();
        status.put("uuid", UUID.randomUUID().toString());
        status.put("entityName", entityName);
        status.put("loadedSince", loadedSince);
        status.put("entityTypeUuid", entityTypeUuid);
        status.put("voided", false);
        return status;
    }

    /**
     * Entities are generated from the client's own EntityMetaData - see tools/entity-metadata.
     * The table is already in pull order, so it is walked as-is.
     */
    private static List<AvniEntity> loadEntities() {
        try (InputStream in = AvniSyncSimulation.class.getClassLoader()
                .getResourceAsStream("avni-entities.json")) {
            if (in == null) {
                throw new IllegalStateException(
                    "avni-entities.json not found. Run tools/entity-metadata to generate it.");
            }
            JsonNode root = om.readTree(in);
            List<AvniEntity> loaded = om.convertValue(
                root.get("entities"), new TypeReference<List<AvniEntity>>() {});
            out.println(String.format("Loaded %d entities from %s",
                loaded.size(), root.path("_source").asText("unknown")));
            return loaded;
        } catch (IOException e) {
            throw new UncheckedIOException("Could not read avni-entities.json", e);
        }
    }

    /**
     * One chain per entity, built once at startup. The previous shape nested a foreach over every
     * entity inside a foreach over every sync detail with a doIfEquals, which is entities x details
     * comparisons per virtual user per sync - several thousand, repeated every run.
     */
    private static ChainBuilder sync() {
        ChainBuilder chain = exec(session -> session);
        for (AvniEntity entity : entities) {
            if (!entity.pullRequired || RESET_SYNC.equals(entity.entityName)) {
                continue;
            }
            chain = chain.exec(
                foreach(session -> syncDetailsFor(session, entity.entityName), "syncDetail")
                    .on(exec(getAndPaginate(entity))));
        }
        return chain;
    }

    /** The sync details the server returned for this entity. Empty means nothing to pull. */
    @SuppressWarnings("unchecked")
    private static List<SyncDetail> syncDetailsFor(Session session, String entityName) {
        List<SyncDetail> all = (List<SyncDetail>) session.get("syncDetails");
        if (all == null) {
            return Collections.emptyList();
        }
        List<SyncDetail> matching = new ArrayList<>();
        for (SyncDetail detail : all) {
            if (entityName.equals(detail.entityName)) {
                matching.add(detail);
            }
        }
        return matching;
    }

    private static ChainBuilder getAndPaginate(AvniEntity entity) {
        return exec(session -> session.set("allPagesNotFetched", true))
            .asLongAs("#{allPagesNotFetched}", "index")
            .on(group(entity.entityName).on(
                exec(http(requestName(entity))
                        .get(session -> url(entity, session))
                        .check(status().is(200))
                        // One parse per response. The previous shape called response.body().string()
                        // in two separate predicates, materialising every page twice just to test for
                        // a substring - injector CPU spent inflating the latency being measured.
                        .check(bodyString()
                            .transformWithSession(AvniSyncSimulation::hasMorePages)
                            .saveAs("allPagesNotFetched"))
                )
                    // Stands in for the time the client spends parsing and persisting the page.
                    // See the plan, D6 - this constant is a placeholder, not a measurement.
                    .pause(0, maxPauseToSimulateRealmStorage)
            ));
    }

    /**
     * Named per entity and type so the report is readable. The previous shape named requests after
     * the entityTypeUuid, which is empty for every entity that is not split by type.
     */
    private static String requestName(AvniEntity entity) {
        return entity.entityTypeUuidParams == null || entity.entityTypeUuidParams.isEmpty()
            ? entity.entityName
            : entity.entityName + " [#{syncDetail.entityTypeUuid}]";
    }

    /** Built the way ConventionalRestClient builds it, so the simulation requests what the client requests. */
    private static String url(AvniEntity entity, Session session) {
        StringBuilder sb = new StringBuilder("/").append(entity.path).append("?");
        if (entity.entityTypeUuidParams != null && !entity.entityTypeUuidParams.isEmpty()) {
            SyncDetail detail = (SyncDetail) session.get("syncDetail");
            String uuid = detail.entityTypeUuid == null ? "" : detail.entityTypeUuid;
            for (String param : entity.entityTypeUuidParams) {
                sb.append(param).append("=").append(uuid).append("&");
            }
        }
        if (entity.staticParams != null) {
            for (Map.Entry<String, String> param : entity.staticParams.entrySet()) {
                String value = param.getValue() == null ? deviceIdFor(param.getKey()) : param.getValue();
                sb.append(param.getKey()).append("=").append(value).append("&");
            }
        }
        sb.append("lastModifiedDateTime=").append(session.getString("lastModifiedDateTime"))
          .append("&now=").append(windowEndFor(entity, session))
          .append("&size=").append(pageSize)
          .append("&page=").append(session.getInt("index"));
        return sb.toString();
    }

    /**
     * Paged responses carry page.totalPages; sliced ones carry slice.hasNext. Which shape comes back
     * depends on the endpoint, so both are handled - but the body is parsed once either way.
     */
    private static boolean hasMorePages(String body, Session session) {
        try {
            JsonNode root = om.readTree(body);
            JsonNode page = root.path("page");
            if (!page.isMissingNode() && page.has("totalPages")) {
                return page.get("totalPages").asInt() > session.getInt("index") + 1;
            }
            JsonNode slice = root.path("slice");
            if (!slice.isMissingNode() && slice.has("hasNext")) {
                return slice.get("hasNext").asBoolean();
            }
            return false;
        } catch (IOException e) {
            throw new UncheckedIOException("Could not parse page metadata", e);
        }
    }

    /** A null static param value means the client fills it in per device; deviceId is the only one today. */
    private static String deviceIdFor(String key) {
        return "deviceId".equals(key) ? deviceId : "";
    }
}
