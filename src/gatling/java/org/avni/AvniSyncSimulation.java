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

    private static final List<AvniEntity> entities = loadEntities();

    // Authentication mode. "none" (default) sends only the USER-NAME header and requires the target
    // server to run with AVNI_IDP_TYPE=none. "cognito" mints a token per user and is limited to runs
    // shorter than the token lifetime - there is no refresh. See docs/sync-simulation-plan.md, B.
    private static final String authMode = System.getProperty("AUTH_MODE", "none");
    private static final boolean useCognito = "cognito".equalsIgnoreCase(authMode);
    private static final Map<String, String> userTokens = new ConcurrentHashMap<>();

    FeederBuilder<String> feeder = csv("sync-users.csv").random();

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

    ChainBuilder syncChainBuilder =
        exec(authChainBuilder)
            .exec(http("Getting SyncDetails")
                .post(session -> "/v2/syncDetails?includeUserSubjectType=true&deviceId=" + deviceId)
                .body(StringBody(AvniSyncSimulation::syncStatusBody)).asJson()
                .check(status().is(200))
                .check(jsonPath("$.syncDetails")
                    .transform(listElements -> {
                        try {
                            return om.readValue(listElements, new TypeReference<List<SyncDetail>>() {
                            });
                        } catch (JsonProcessingException e) {
                            throw new UncheckedIOException("Could not parse syncDetails", e);
                        }
                    }).saveAs("syncDetails"))
                // The client takes the sync window end from this response rather than from its own
                // clock, and uses two different values - see windowEndFor.
                .check(jsonPath("$.now").saveAs("serverNow"))
                .check(jsonPath("$.nowMinus10Seconds").saveAs("serverNowMinus10Seconds")))
            .exec(sync());
    ScenarioBuilder syncScenario = scenario("Sync").feed(feeder).exec(syncChainBuilder);

    {
        setUp(syncScenario.injectOpen(rampUsers(userCount).during(rampPeriod))).protocols(httpProtocol)
//            .assertions(forAll().failedRequests().percent().lte(1.0));
        ;
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
    private static String syncStatusBody(Session session) {
        List<Map<String, Object>> statuses = new ArrayList<>();
        String loadedSince = session.getString("lastModifiedDateTime");
        for (AvniEntity entity : entities) {
            if (!entity.pullRequired) {
                continue;
            }
            Map<String, Object> status = new LinkedHashMap<>();
            status.put("uuid", UUID.randomUUID().toString());
            status.put("entityName", entity.entityName);
            status.put("loadedSince", loadedSince);
            status.put("entityTypeUuid", "");
            status.put("voided", false);
            statuses.add(status);
        }
        try {
            return om.writeValueAsString(statuses);
        } catch (JsonProcessingException e) {
            throw new UncheckedIOException("Could not serialise sync statuses", e);
        }
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
            if (!entity.pullRequired) {
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
        return entity.entityTypeUuidParam == null
            ? entity.entityName
            : entity.entityName + " [#{syncDetail.entityTypeUuid}]";
    }

    /** Built the way ConventionalRestClient builds it, so the simulation requests what the client requests. */
    private static String url(AvniEntity entity, Session session) {
        StringBuilder sb = new StringBuilder("/").append(entity.path).append("?");
        if (entity.entityTypeUuidParam != null) {
            SyncDetail detail = (SyncDetail) session.get("syncDetail");
            sb.append(entity.entityTypeUuidParam).append("=")
              .append(detail.entityTypeUuid == null ? "" : detail.entityTypeUuid).append("&");
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
