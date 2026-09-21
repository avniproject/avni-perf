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
import org.avni.models.PushSeed;
import org.avni.models.SyncDetail;
import com.fasterxml.jackson.databind.ObjectMapper;

import com.fasterxml.jackson.databind.JsonNode;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.BiFunction;


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
    /**
     * A page costs a fixed amount plus a per-record amount. Both terms come from production.
     *
     * Anchoring the intercept at band 1's p50 - a sync that pulls almost nothing still costs
     * 14.1s - makes the marginal term fall out consistently across bands 2 to 9 at 8.8 to 9.2
     * ms/record, against free-intercept fits that gave -92s, +26.6s and +47.4s. All three are
     * impossible inside a 14.1s median sync, which is how we know they were the wrong model.
     *
     * Both are calibration starting points, not measurements. F7 fits them by matching a simulated
     * sync's duration against production's own: 14.1s + 8.85 ms x records.
     */
    private static final double baseMsPerRecord =
        Double.parseDouble(System.getProperty("BASE_MS_PER_RECORD", "9.19"));
    /**
     * What a page costs before its first record: the client's transaction open and commit, its
     * batched index maintenance, and the round trip.
     *
     * **This is the term that shapes load, and D6.2 originally dismissed it as negligible.** A
     * production sync is 81 requests over 14.1s, so 174 ms a page - and for the 98% of syncs that
     * pull few records it is essentially the whole cost. At 50 records the per-record term is 3%
     * of the sync.
     *
     * It is also why a real device issues one request every 174 ms. On a LAN the round trip
     * vanishes, so without this the simulation issues requests about four times faster per user
     * than any device does, and manufactures contention rather than measuring it.
     *
     * Net out the server's own response time, which the simulation really incurs: pass
     * 174 minus the server's median response, not 174.
     */
    private static final double msPerPage =
        Double.parseDouble(System.getProperty("MS_PER_PAGE", "174"));
    /**
     * `weighted` applies the per-entity model. `zero` removes client cost entirely, for runs that
     * are trying to saturate the server rather than reproduce a device.
     *
     * The old uniform pause is gone rather than kept as a third mode. No existing run results need
     * preserving, and an unexercised config path rots the same way the hand-maintained entity table
     * did.
     */
    private static final String storageModel = System.getProperty("STORAGE_MODEL", "weighted");
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
    /**
     * The customer's decision: 0.05%. At 81 requests a sync that permits roughly one sync in
     * twenty-five losing a single request, so a run that breaches it has a fault rather than noise
     * - which is the point of setting it this tight.
     */
    private static final double maxFailedPercent =
        Double.parseDouble(System.getProperty("MAX_FAILED_PERCENT", "0.05"));
    /**
     * p95 for a light sync, measured at 80.0s in production (Q5, success criteria). Band 1 carries
     * 98% of production's syncs, so this is the threshold the common case is held to. Asserted only
     * when explicitly set, because a laptop against a local database is not the environment the
     * figure was measured in.
     */
    private static final String maxP95Millis = System.getProperty("MAX_P95_MS");
    /*
     * D3 - the push path.
     *
     * Off by default, and that default is a deliberate trade rather than caution. Push writes rows:
     * once it is on, a run changes the database it measured, so the next run is not the same
     * experiment and the dataset's H5 verdict no longer describes what is in the tables. Leaving it
     * off keeps every existing run repeatable.
     *
     * The cost of the default is that a green result from a run without PUSH=on says nothing about
     * write contention, lock waits or index maintenance - which is most of what the write path
     * costs. The startup banner says so in as many words, because the failure mode here is someone
     * reading a read-only run as the realistic case.
     */
    private static final boolean pushEnabled = enabled(System.getProperty("PUSH", "false"));

    /** "on" as well as "true", because the banner and the docs both say PUSH=on. */
    private static boolean enabled(String value) {
        return "true".equalsIgnoreCase(value) || "on".equalsIgnoreCase(value)
            || "yes".equalsIgnoreCase(value);
    }

    /*
     * Records queued per sync, per entity. Provisional: derived from the customer's stated 20
     * encounters per field worker per day against a daily sync, not measured. Q17 replaces them
     * with production's own `sync_telemetry.entity_status->'push'` distribution.
     *
     * These are absolute per-sync counts, not a rate. A real queue is proportional to the time
     * since the last sync, so a run at a different interval than INCREMENTAL_SINCE_HOURS=24 needs
     * them re-derived rather than reused.
     */
    private static final int pushIndividuals = Integer.getInteger("PUSH_INDIVIDUALS", 1);
    private static final int pushEnrolments = Integer.getInteger("PUSH_ENROLMENTS", 1);
    private static final int pushProgramEncounters = Integer.getInteger("PUSH_PROGRAM_ENCOUNTERS", 20);
    private static final int pushEncounters = Integer.getInteger("PUSH_ENCOUNTERS", 2);

    /**
     * Observations per pushed record, as a count of harvested rows to concatenate. One means the
     * pushed row carries the same observation set as a real one; higher inflates the jsonb and the
     * GIN maintenance with it, which is the knob F-series stress runs need.
     */
    private static final int pushObservationMultiple = Integer.getInteger("PUSH_OBSERVATION_MULTIPLE", 1);

    /**
     * D5.1 - media files an encounter queues, which is the media half of a sync.
     *
     * A per-deployment property, not a platform average. Production-wide, 2.14% of
     * program_encounter rows carry a media observation - but that spans 986 organisations, most of
     * which capture no images at all, and it is the wrong base rate for a screening programme. Read
     * the deployment's own bundle instead: `make survey_bundle` reports files per filled form.
     *
     * The default is the customer bundle's figure averaged over its twelve encounter types, with
     * the screening encounter at 16 files: two mandatory image elements, each inside a repeatable
     * question group filled once per lesion photographed.
     *
     * **It is a floor, and the encounter mix is what moves it.** 1.42 assumes every encounter type
     * is equally frequent. In a screening programme the screening encounter is not one of twelve,
     * it is most of them, and the figure runs to 16:
     *
     *   uniform, 1 of 12   1.42 per encounter    31 files per sync    125s at 1 Mbps
     *   a quarter          4.08                  90                   359s
     *   half               8.08                 178                   711s
     *   all of them       16.00                 352                  1408s
     *
     * Set it from the deployment, not from this default: `make survey_bundle` reports files per
     * form, and the mix is a question for whoever knows the programme.
     */
    private static final double mediaPerEncounter =
        Double.parseDouble(System.getProperty("PUSH_MEDIA_PER_ENCOUNTER", "1.42"));

    /**
     * D5.2 - whether the simulation spends the time a media upload really takes.
     *
     * `pause` (default) models the transfer as elapsed time; `none` charges nothing for it.
     *
     * The bytes are never actually transferred, and the reason is fidelity rather than economy.
     * S3 serves those objects directly, so a PUT from the injector measures the injector's own
     * network - a fat in-region pipe that uploads 500 KB in tens of milliseconds where a field
     * device on rural 3G takes seconds. Transferring would reproduce neither the server's load nor
     * the device's timing. A modelled pause reproduces the timing, which is the part that matters,
     * and can be varied across bandwidths the way a real transfer cannot.
     *
     * What this does NOT cover: whether the presigned URL works end to end. That is a wiring
     * check against a real bucket, not a load question, and it belongs in a smoke test.
     */
    private static final String mediaModel = System.getProperty("MEDIA_MODEL", "pause");

    /**
     * Upload size per file. The client captures at 1280x960, quality 1 (MediaV2FormElement), which
     * is a full-quality 1.2 MP JPEG - a few hundred KB and up. Audio and video are larger.
     */
    private static final int mediaFileKb = Integer.getInteger("MEDIA_FILE_KB", 500);

    /**
     * Device upload bandwidth, in KB/s. 125 KB/s is about 1 Mbps: optimistic for rural 3G,
     * pessimistic for a town on 4G. It is the single biggest lever on how long a media-bearing
     * sync takes, so vary it rather than trusting the default.
     */
    private static final int mediaUploadKbps = Integer.getInteger("MEDIA_UPLOAD_KBPS", 125);

    /** How many rows to harvest per entity when seeding a device. Enough to vary, cheap to fetch. */
    private static final int pushSeedSize = Integer.getInteger("PUSH_SEED_SIZE", 20);

    /**
     * Hosts this simulation will not push to. Pushing invents subjects and encounters that look
     * like field data and cannot be told apart from it afterwards by anything but the UUID prefix,
     * so the guard is a deny list rather than a warning.
     */
    private static final List<String> PROTECTED_HOSTS =
        Arrays.asList("app.avniproject.org", "prod.avniproject.org");
    private static final boolean pushTargetAllowed =
        Boolean.getBoolean("PUSH_ALLOW_UNSAFE_TARGET") || PROTECTED_HOSTS.stream().noneMatch(baseUrl::contains);

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

    /**
     * What each user's device holds, harvested once - see PushSeed. Keyed by user rather than by
     * virtual user because the same real user may be fed to several, and the inventory is a
     * property of the account's catchment, not of the injector.
     */
    private static final Map<String, PushSeed> userPushSeeds = new ConcurrentHashMap<>();

    /**
     * Devices that could not be fully seeded, by what they were missing.
     *
     * Counted rather than warned about one at a time, and reported in after(). A run where most
     * users have no enrolments to hang encounters off pushes a fraction of the configured volume
     * and still finishes green, so the count is the difference between a valid result and one that
     * measured nothing - it belongs beside the report, not buried in the startup scroll.
     */
    private static final Map<String, AtomicInteger> unseedable = new ConcurrentHashMap<>();
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
            .exec(seedChain())
            .exec(session -> session.set("syncStartTime", java.time.Instant.now().toString()))
            // The client uploads before it asks what changed: dataServerSync runs pushData, then
            // the reset-sync check, then getSyncDetails. Pushing after the pull would measure a
            // different thing - the server's clock for the pull window is read after the upload
            // precisely so a device does not re-download what it just sent.
            .exec(pushChain())
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

        if ("weighted".equals(storageModel)) {
            out.println(String.format(
                "Storage model: weighted | %.0f ms/page + %.2f ms/record | a full page costs "
                + "%.1fs light, %.1fs medium, %.1fs heavy",
                msPerPage, baseMsPerRecord,
                (msPerPage + pageSize * 0.2 * baseMsPerRecord) / 1000.0,
                (msPerPage + pageSize * 1.0 * baseMsPerRecord) / 1000.0,
                (msPerPage + pageSize * 3.0 * baseMsPerRecord) / 1000.0));
            out.println(
                "  Both terms are calibration starting points, not measurements. MS_PER_PAGE "
                + "should be 174 minus the server's own median response, since the simulation "
                + "really incurs that. F7 fits them against production's 14.1s + 8.85ms x records.");
        } else {
            out.println("Storage model: zero - no client-side pause. Server saturation only; "
                + "throughput here is not a rate any real fleet produces.");
        }
        if (userCount > feederRows) {
            out.println(String.format(
                "WARNING: USER_COUNT (%d) exceeds the user file (%d rows), so the same real user will "
                + "be synced by more than one virtual user at once. That is contention the field does "
                + "not have - add users rather than oversubscribing the file.",
                userCount, feederRows));
        }
        if (!pushEnabled) {
            out.println(
                "Push: OFF - this run exercises the download path only. Write contention, lock "
                + "waits and index maintenance cannot appear in the result, so a green run here is "
                + "not evidence the write path holds. PUSH=on to include it (D3).");
        } else if (!pushTargetAllowed) {
            throw new IllegalStateException(
                "PUSH=on against " + baseUrl + ", which is on the protected host list. Pushing "
                + "creates subjects and encounters indistinguishable from field data. Point at a "
                + "performance environment, or set PUSH_ALLOW_UNSAFE_TARGET=true if this really is "
                + "intended.");
        } else {
            int perSync = pushIndividuals + pushEnrolments + pushProgramEncounters + pushEncounters;
            double mediaFiles = (pushProgramEncounters + pushEncounters) * mediaPerEncounter;
            out.println(String.format(
                "Push: ON | %d records per sync (%d individual, %d enrolment, %d programEncounter, "
                + "%d encounter)",
                perSync, pushIndividuals, pushEnrolments, pushProgramEncounters, pushEncounters));
            out.println(String.format(
                "  The client has no bulk endpoint: that is %d sequential POSTs per sync, each "
                + "through the full filter chain and its own transaction. Volumes are derived from "
                + "20 encounters per worker per day, not measured - Q17 replaces them.", perSync));
            if (mediaPerEncounter > 0) {
                long transferMs = mediaTransfer().toMillis();
                out.println(String.format(
                    "Media: %.0f files per sync at %.2f per encounter | %d KB each = %.0f MB at "
                    + "%d KB/s = %.0fs of transfer, ahead of the first pushed record",
                    mediaFiles, mediaPerEncounter, mediaFileKb,
                    mediaFiles * mediaFileKb / 1024.0, mediaUploadKbps,
                    mediaFiles * transferMs / 1000.0));
                out.println(
                    "  PUSH_MEDIA_PER_ENCOUNTER assumes an encounter mix. The default is a "
                    + "uniform one; where the image-heavy encounter type is the common one the "
                    + "figure is up to 11x higher. Set it from the deployment's own bundle.");
                if (!"pause".equals(mediaModel)) {
                    out.println(
                        "  MEDIA_MODEL=" + mediaModel + " - transfer time is NOT charged. The data "
                        + "push then starts sooner than any real device could manage it, and sync "
                        + "duration is understated by the figure above.");
                } else {
                    out.println(
                        "  Bytes are not transferred: S3 serves them directly, so a PUT from here "
                        + "would measure the injector's own bandwidth rather than a field link. "
                        + "The time is charged, the request is not.");
                }
                out.println(String.format(
                    "  That makes a sync take roughly %.0fs longer than its server work alone. "
                    + "Those are syncs in progress, not requests in flight - during the transfer "
                    + "the device asks avni-server for nothing.",
                    mediaFiles * transferMs / 1000.0));
            }
            out.println(
                "  This run WRITES. The database it measures is not the database the next run "
                + "measures, and the dataset's H5 verdict no longer describes what is in the tables.");
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
     * What the report cannot say for itself: how much of the configured push volume actually ran.
     *
     * A device with nothing to reference pushes nothing and fails no request, so a run against a
     * dataset without enrolments finishes green having exercised almost none of the write path.
     * The counts below are the qualifier on the result.
     */
    @Override
    public void after() {
        if (!pushEnabled) {
            return;
        }
        int seeded = userPushSeeds.size();
        int incomplete = unseedable.values().stream()
            .mapToInt(AtomicInteger::get).sum();
        out.println(String.format("Push seeding: %d devices, %d fully seeded, %d partial",
            seeded, seeded - incomplete, incomplete));
        if (incomplete > 0) {
            unseedable.forEach((missing, count) -> out.println(String.format(
                "  %d missing %s", count.get(), missing)));
            out.println(
                "  Those entities were skipped, so the run pushed less than the configured volume. "
                + "Treat the write-path result as a floor, not a measurement.");
        }
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
        entityStatus.put("push", pushStatus(session));

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
     * What this sync pushed, in the shape the client reports it.
     *
     * todo equals done because the simulation only counts requests it made: a real client records
     * todo from the queue before pushing and done as each POST returns, so a divergence there means
     * records failed to upload. Reporting them equal is honest about what this measures, and it
     * keeps Q17 - which reads these very rows to derive the volumes above - free of simulated
     * failures it would misread as field behaviour.
     */
    private static List<Map<String, Object>> pushStatus(Session session) {
        List<Map<String, Object>> push = new ArrayList<>();
        if (!pushEnabled) {
            return push;
        }
        for (AvniEntity entity : entities) {
            PushEntity pushEntity = PUSHABLE.get(entity.entityName);
            if (pushEntity == null || !entity.pushRequired) {
                continue;
            }
            int count = pushCount(session, pushEntity);
            if (count == 0) {
                continue;
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("entity", entity.entityName);
            row.put("todo", count);
            row.put("done", count);
            push.add(row);
        }
        return push;
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

    /**
     * How many records the page carried, from the HAL `_embedded` collection.
     *
     * The resource name under `_embedded` varies per entity, and there is only ever one, so the
     * first array found is it. A page with no `_embedded` is an empty page, not an error.
     */
    private static int countRecords(JsonNode root) {
        JsonNode embedded = root.path("_embedded");
        if (embedded.isMissingNode() || !embedded.isObject()) {
            return 0;
        }
        for (JsonNode child : embedded) {
            if (child.isArray()) {
                return child.size();
            }
        }
        return 0;
    }

    /**
     * Carries the record count from the body check to the pause that follows it, within one
     * virtual user's turn on the thread. A ThreadLocal because Gatling runs a session's steps on
     * one thread at a time and the check completes before the pause is evaluated.
     */
    private static final ThreadLocal<Integer> lastPageRecordCount = ThreadLocal.withInitial(() -> 0);

    /**
     * What this page costs the client, per D6.2: a fixed term plus a per-record term.
     *
     * Writing a page is one transaction, so the incremental cost of record N sits well below the
     * first record's. Modelling it as records x rate alone charges a 10-record page a tenth of a
     * 100-record page, when in reality they cost nearly the same.
     */
    private static java.time.Duration storagePause(AvniEntity entity) {
        if (!"weighted".equals(storageModel)) {
            return java.time.Duration.ZERO;
        }
        long millis = Math.round(
            msPerPage + lastPageRecordCount.get() * entity.storageWeight * baseMsPerRecord);
        return java.time.Duration.ofMillis(Math.max(0L, millis));
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
                    // The time the client spends parsing and persisting this page: its record
                    // count times the entity's tier times baseMsPerRecord (D6.2). A page of
                    // observation-bearing rows costs fifteen times a page of lookup rows, which one
                    // uniform constant could not express.
                    .pause(session -> storagePause(entity))
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
    /**
     * Whether another page follows, and — as a side effect on the session — how many records this
     * page carried.
     *
     * Both come out of one parse. Reading the body twice is what A4 removed: injector CPU spent
     * inflating the latency being measured.
     */
    private static boolean hasMorePages(String body, Session session) {
        try {
            JsonNode root = om.readTree(body);
            lastPageRecordCount.set(countRecords(root));
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


    // ---------------------------------------------------------------------------------------
    // D3 - the push path
    //
    // Two things about it are worth knowing before reading the code, because both shape the load
    // and neither is visible from the server side.
    //
    // 1. There is no bulk endpoint. ConventionalRestClient.chainPostEntities builds one POST per
    //    record, and ChainedRequests.fire() reduces the queue over a single promise chain - so a
    //    device with twenty queued encounters makes twenty sequential round trips, each through the
    //    full authentication filter, the organisation interceptor and its own @Transactional
    //    handler. Push cost scales with record count in requests, not just in bytes.
    //
    // 2. Entities go in a fixed order, parents first: EntityMetaData.model() reversed, which is the
    //    order the generated table is already in. Individual before ProgramEnrolment before
    //    ProgramEncounter. Iterating the table rather than a list of our own keeps that true if the
    //    client's order changes.
    // ---------------------------------------------------------------------------------------

    /** One pushable entity: how many records per sync, and how to build one. */
    private static final class PushEntity {
        final String entityName;
        final int perSync;
        final BiFunction<Session, PushSeed, String> body;
        /** Whether this device holds what the body needs. */
        final java.util.function.Predicate<PushSeed> ready;

        PushEntity(String entityName, int perSync, java.util.function.Predicate<PushSeed> ready,
                   BiFunction<Session, PushSeed, String> body) {
            this.entityName = entityName;
            this.perSync = perSync;
            this.ready = ready;
            this.body = body;
        }
    }

    private static final Map<String, PushEntity> PUSHABLE = pushable();

    private static Map<String, PushEntity> pushable() {
        Map<String, PushEntity> m = new LinkedHashMap<>();
        m.put("Individual", new PushEntity("Individual", pushIndividuals,
            PushSeed::canPushIndividual, AvniSyncSimulation::individualBody));
        m.put("ProgramEnrolment", new PushEntity("ProgramEnrolment", pushEnrolments,
            PushSeed::canPushEnrolment, AvniSyncSimulation::enrolmentBody));
        m.put("ProgramEncounter", new PushEntity("ProgramEncounter", pushProgramEncounters,
            PushSeed::canPushProgramEncounter, AvniSyncSimulation::programEncounterBody));
        m.put("Encounter", new PushEntity("Encounter", pushEncounters,
            PushSeed::canPushEncounter, AvniSyncSimulation::encounterBody));
        return m;
    }

    /**
     * The push phase: every configured entity, in the client's own order, one request per record.
     *
     * Records are skipped rather than faked when the device has nothing to reference. A pushed
     * ProgramEncounter with an invented programEnrolmentUUID is rejected in the handler before it
     * reaches a table, so counting it as load would measure the validation path and report a write
     * that never happened.
     */
    private static ChainBuilder pushChain() {
        if (!pushEnabled) {
            return exec(session -> session);
        }
        // Media first: sync() runs mediaSync to completion before dataServerSync, so every
        // presigned-URL call lands ahead of the first record. Ordering matters because the two
        // hit the same filter chain and pool - interleaving them would spread a burst the real
        // client delivers up front.
        ChainBuilder chain = mediaUploadChain();
        for (AvniEntity entity : entities) {
            PushEntity pushEntity = PUSHABLE.get(entity.entityName);
            if (pushEntity == null || !entity.pushRequired || pushEntity.perSync <= 0) {
                continue;
            }
            String path = entity.pushPath;
            chain = chain.exec(
                doIf(session -> pushCount(session, pushEntity) > 0)
                    .then(group("Push " + entity.entityName).on(
                        repeat(session -> pushCount(session, pushEntity), "pushIndex")
                            .on(exec(http("Push " + entity.entityName)
                                .post("/" + path)
                                .body(StringBody(session ->
                                    pushEntity.body.apply(session, seedFor(session))))
                                .asJson()
                                .check(status().in(200, 201, 204)))))));
        }
        return chain;
    }

    /**
     * How many records of this entity this virtual user pushes this sync.
     *
     * Zero when the device could not be seeded, which is a real outcome rather than an error: a
     * user whose catchment holds no enrolments has nothing to hang a program encounter off, and the
     * field equivalent of that user does not push one either.
     */
    private static int pushCount(Session session, PushEntity pushEntity) {
        PushSeed seed = seedFor(session);
        if (seed == null || !pushEntity.ready.test(seed)) {
            return 0;
        }
        return Math.round(pushEntity.perSync * pushScale(session));
    }

    /**
     * Per-user push volume, from an optional `pushScale` column in the user file.
     *
     * Volume is not uniform across roles and the difference runs the opposite way to sync volume: a
     * supervisor pulls a wide catchment but creates few records, while a field worker pulls a
     * narrow one and creates twenty encounters a day. Without this, case 3 would push a field
     * worker's queue from a supervisor's account and overstate the write load by the same factor it
     * understates the read.
     */
    private static float pushScale(Session session) {
        String scale = session.getString("pushScale");
        if (scale == null || scale.isEmpty()) {
            return 1.0f;
        }
        return Float.parseFloat(scale);
    }

    private static PushSeed seedFor(Session session) {
        return userPushSeeds.get(session.getString("userName"));
    }

    /**
     * D5.1 - one presigned-URL request per media file queued, ahead of the data push.
     *
     * Modelled as a rate against encounter volume rather than as a queue of its own, because that
     * is what the measurement supports: 2.14% of program_encounter rows carry a media observation.
     * The fractional part is played out per sync rather than rounded, so a device pushing twenty
     * encounters makes a media call on roughly two syncs in five instead of never.
     */
    private static ChainBuilder mediaUploadChain() {
        if (mediaPerEncounter <= 0) {
            return exec(session -> session);
        }
        return exec(session -> session.set("mediaCalls", mediaCallCount(session)))
            .doIf(session -> session.getInt("mediaCalls") > 0)
            .then(group("Push Media").on(
                repeat(session -> session.getInt("mediaCalls"), "mediaIndex")
                    .on(exec(http("Media uploadUrl")
                            .get(session -> "/media/uploadUrl/" + UUID.randomUUID() + ".jpg")
                            // A device with no media privilege gets a 4xx here and carries on; the
                            // request still costs the server the filter chain, which is the point.
                            .check(status().in(200, 201)))
                        // The PUT to S3 that follows each signed URL. Not issued - see mediaModel
                        // - but the device spends the time, and spending it here is what keeps the
                        // data push from arriving earlier than any real client could send it.
                        .pause(mediaTransfer()))));
    }

    /**
     * How long one file takes to reach S3 at the configured bandwidth.
     *
     * Serial, because PARALLEL_UPLOAD_COUNT is 1 in MediaQueueService: the chunking around it
     * suggests otherwise, but each chunk holds one item, so files go up one at a time. And the
     * whole queue drains before dataServerSync starts, so this time lands entirely ahead of the
     * first pushed record.
     */
    private static java.time.Duration mediaTransfer() {
        if (!"pause".equals(mediaModel) || mediaUploadKbps <= 0) {
            return java.time.Duration.ZERO;
        }
        return java.time.Duration.ofMillis(Math.round(1000.0 * mediaFileKb / mediaUploadKbps));
    }

    private static int mediaCallCount(Session session) {
        PushSeed seed = seedFor(session);
        if (seed == null) {
            return 0;
        }
        double encounters = (pushProgramEncounters + pushEncounters) * pushScale(session);
        double expected = encounters * mediaPerEncounter;
        int whole = (int) expected;
        return ThreadLocalRandom.current().nextDouble() < (expected - whole) ? whole + 1 : whole;
    }

    // --- payload builders -------------------------------------------------------------------
    //
    // Shapes come from the client's own toResource getters (openchs-models), not from the server's
    // request contracts. The two differ: the server accepts fields the client never sends, and
    // sending them would measure a path no device exercises.

    private static String individualBody(Session session, PushSeed seed) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("uuid", UUID.randomUUID().toString());
        body.put("voided", false);
        body.put("firstName", "Perf");
        body.put("lastName", Long.toHexString(ThreadLocalRandom.current().nextLong() >>> 32));
        body.put("dateOfBirth", "1990-01-01");
        body.put("dateOfBirthVerified", false);
        body.put("registrationDate", java.time.LocalDate.now().toString());
        body.put("subjectTypeUUID", seed.subjectTypeUuid);
        body.put("addressLevelUUID", seed.addressLevelUuid);
        body.put("genderUUID", seed.genderUuid);
        return withObservations(body, "observations", seed.individualObservations);
    }

    private static String enrolmentBody(Session session, PushSeed seed) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("uuid", UUID.randomUUID().toString());
        body.put("voided", false);
        body.put("programUUID", seed.programUuid);
        body.put("individualUUID", pick(seed.individualUuids));
        body.put("enrolmentDateTime", java.time.OffsetDateTime.now().toString());
        body.put("programExitDateTime", null);
        body.put("programExitObservations", Collections.emptyList());
        return withObservations(body, "observations", seed.individualObservations);
    }

    private static String programEncounterBody(Session session, PushSeed seed) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("uuid", UUID.randomUUID().toString());
        body.put("voided", false);
        body.put("encounterTypeUUID", seed.programEncounterTypeUuid);
        body.put("programEnrolmentUUID", pick(seed.enrolmentUuids));
        body.put("encounterDateTime", encounterDateTime());
        body.put("name", "Perf encounter");
        body.put("cancelObservations", Collections.emptyList());
        return withObservations(body, "observations", seed.programEncounterObservations);
    }

    private static String encounterBody(Session session, PushSeed seed) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("uuid", UUID.randomUUID().toString());
        body.put("voided", false);
        body.put("encounterTypeUUID", seed.encounterTypeUuid);
        body.put("individualUUID", pick(seed.individualUuids));
        body.put("encounterDateTime", encounterDateTime());
        body.put("name", "Perf encounter");
        body.put("cancelObservations", Collections.emptyList());
        return withObservations(body, "observations", seed.encounterObservations);
    }

    /**
     * An encounter date inside the last day and never in the future.
     *
     * Encounter.validate rejects a future encounterDateTime, and one before the subject's
     * registrationDate. Real devices queue records made during the working day, so a few hours back
     * is both valid and representative.
     */
    private static String encounterDateTime() {
        return java.time.OffsetDateTime.now()
            .minusMinutes(ThreadLocalRandom.current().nextInt(1, 12 * 60)).toString();
    }

    /**
     * Serialise the body with a harvested observation array spliced in as raw JSON.
     *
     * Spliced rather than parsed and re-serialised: the values came off the wire as JSON and go
     * back as JSON, and re-modelling them through a Map would lose the numeric and date shapes that
     * decide how much work the jsonb column and its GIN index do on insert.
     */
    private static String withObservations(Map<String, Object> body, String field,
                                           List<String> harvested) {
        String observations = observationArray(harvested);
        try {
            String json = om.writeValueAsString(body);
            return json.substring(0, json.length() - 1)
                + ",\"" + field + "\":" + observations + "}";
        } catch (JsonProcessingException e) {
            throw new UncheckedIOException("Could not serialise push body", e);
        }
    }

    /** One harvested observation set, or several concatenated when PUSH_OBSERVATION_MULTIPLE > 1. */
    private static String observationArray(List<String> harvested) {
        if (harvested == null || harvested.isEmpty()) {
            return "[]";
        }
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < Math.max(1, pushObservationMultiple); i++) {
            String one = pick(harvested);
            String inner = one.substring(1, one.length() - 1).trim();
            if (inner.isEmpty()) {
                continue;
            }
            if (sb.length() > 1) {
                sb.append(",");
            }
            sb.append(inner);
        }
        return sb.append("]").toString();
    }

    private static String pick(List<String> values) {
        return values.get(ThreadLocalRandom.current().nextInt(values.size()));
    }


    /**
     * Harvest what this device holds, once, so it has something real to create records against.
     *
     * Four page-0 reads over a full window, named apart from the sync requests so they do not
     * enter the measured distribution. They are simulation setup, not a call any client makes.
     *
     * Why harvest rather than configure: the alternative is a list of UUIDs produced alongside the
     * dataset, which couples the simulation to the generator and goes stale the moment anyone runs
     * against a restored dump or a hand-built org. Reading them off the deployment keeps the push
     * path working wherever the data came from, and guarantees the references are ones this user
     * can actually see - a subject outside the catchment would be rejected by the same access check
     * a real device would hit.
     */
    private static ChainBuilder seedChain() {
        if (!pushEnabled) {
            return exec(session -> session);
        }
        return doIf(session -> !userPushSeeds.containsKey(session.getString("userName")))
            .then(exec(seedRequest("Individual"))
                .exec(seedRequest("ProgramEnrolment"))
                .exec(seedRequest("ProgramEncounter"))
                .exec(seedRequest("Encounter"))
                .exec(AvniSyncSimulation::assembleSeed));
    }

    private static ChainBuilder seedRequest(String entityName) {
        AvniEntity entity = entityByName(entityName);
        if (entity == null) {
            return exec(session -> session);
        }
        return exec(http("Seed: " + entityName)
            .get(session -> seedUrl(entity, session))
            .check(status().is(200))
            // A device whose catchment holds none of this entity still gets a 200 with an empty
            // page; the seed assembly turns that into "pushes nothing of this kind".
            .check(bodyString().saveAs("seed" + entityName)));
    }

    /**
     * A full-window page-0 read for one entity, with the entityTypeUuid the bootstrap pass found.
     *
     * The window end is this injector's clock rather than the server's, which the pull path is
     * careful to use instead. That is correct here: the seed read is not modelling a client call,
     * and taking it from the server would mean ordering the harvest after syncDetails, which is
     * after the push it exists to feed.
     */
    private static String seedUrl(AvniEntity entity, Session session) {
        StringBuilder sb = new StringBuilder("/").append(entity.path).append("?");
        if (entity.entityTypeUuidParams != null && !entity.entityTypeUuidParams.isEmpty()) {
            String uuid = firstEntityTypeUuid(session, entity.entityName);
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
        return sb.append("lastModifiedDateTime=").append(FULL_SYNC_SINCE)
            .append("&now=").append(java.time.Instant.now().toString())
            .append("&size=").append(pushSeedSize)
            .append("&page=0").toString();
    }

    /** The first entityTypeUuid the server tracks for this entity, from the bootstrap pass. */
    private static String firstEntityTypeUuid(Session session, String entityName) {
        List<SyncDetail> tracked = userSyncStatuses.get(session.getString("userName"));
        if (tracked == null) {
            return "";
        }
        for (SyncDetail detail : tracked) {
            if (entityName.equals(detail.entityName) && detail.entityTypeUuid != null
                    && !detail.entityTypeUuid.isEmpty()) {
                return detail.entityTypeUuid;
            }
        }
        return "";
    }

    private static AvniEntity entityByName(String entityName) {
        for (AvniEntity entity : entities) {
            if (entityName.equals(entity.entityName)) {
                return entity;
            }
        }
        return null;
    }

    private static Session assembleSeed(Session session) {
        String userName = session.getString("userName");
        if (userPushSeeds.containsKey(userName)) {
            return session;
        }
        List<JsonNode> individuals = harvested(session, "seedIndividual");
        List<JsonNode> enrolments = harvested(session, "seedProgramEnrolment");
        List<JsonNode> programEncounters = harvested(session, "seedProgramEncounter");
        List<JsonNode> encounters = harvested(session, "seedEncounter");

        PushSeed seed = new PushSeed(
            uuidsOf(individuals),
            uuidsOf(enrolments),
            firstLink(individuals, "subjectTypeUUID"),
            firstLink(individuals, "genderUUID"),
            firstLink(individuals, "addressUUID"),
            firstLink(enrolments, "programUUID"),
            firstLink(programEncounters, "encounterTypeUUID"),
            firstLink(encounters, "encounterTypeUUID"),
            observationsOf(individuals),
            observationsOf(programEncounters),
            observationsOf(encounters));

        String missing = seed.missing();
        if (!missing.equals("nothing")) {
            unseedable.computeIfAbsent(missing, k -> new AtomicInteger())
                .incrementAndGet();
        }
        userPushSeeds.put(userName, seed);
        return session;
    }

    /** The records in a saved seed response, or empty if the request never ran or returned none. */
    private static List<JsonNode> harvested(Session session, String key) {
        String body = session.getString(key);
        if (body == null || body.isEmpty()) {
            return Collections.emptyList();
        }
        try {
            JsonNode embedded = om.readTree(body).path("_embedded");
            for (JsonNode child : embedded) {
                if (child.isArray()) {
                    List<JsonNode> rows = new ArrayList<>();
                    child.forEach(rows::add);
                    return rows;
                }
            }
        } catch (IOException e) {
            throw new UncheckedIOException("Could not parse seed response for " + key, e);
        }
        return Collections.emptyList();
    }

    private static List<String> uuidsOf(List<JsonNode> rows) {
        List<String> uuids = new ArrayList<>();
        for (JsonNode row : rows) {
            String uuid = row.path("uuid").asText(null);
            if (uuid != null && !uuid.isEmpty()) {
                uuids.add(uuid);
            }
        }
        return uuids;
    }

    /**
     * A referenced UUID off the HAL links.
     *
     * The resource processors put them there rather than in the body - Link.of(uuid, "programUUID")
     * renders as _links.programUUID.href - so this is where a pulled record says what it belongs to.
     */
    private static String firstLink(List<JsonNode> rows, String rel) {
        for (JsonNode row : rows) {
            String href = row.path("_links").path(rel).path("href").asText(null);
            if (href != null && !href.isEmpty()) {
                return href;
            }
        }
        return null;
    }

    /**
     * Observation sets from pulled rows, converted from the wire's map form to the push form.
     *
     * A pulled record carries observations as an ObservationCollection - a {conceptUuid: value}
     * map. A pushed one carries [{conceptUUID, value}]. The client converts between them in
     * Observation.fromResource/toResource; the simulation does the same conversion once, here,
     * rather than per request.
     */
    private static List<String> observationsOf(List<JsonNode> rows) {
        List<String> converted = new ArrayList<>();
        for (JsonNode row : rows) {
            JsonNode observations = row.path("observations");
            if (!observations.isObject() || observations.isEmpty()) {
                continue;
            }
            List<Map<String, Object>> asList = new ArrayList<>();
            observations.properties().forEach(field -> {
                Map<String, Object> observation = new LinkedHashMap<>();
                observation.put("conceptUUID", field.getKey());
                observation.put("value", om.convertValue(field.getValue(), Object.class));
                asList.add(observation);
            });
            try {
                converted.add(om.writeValueAsString(asList));
            } catch (JsonProcessingException e) {
                throw new UncheckedIOException("Could not serialise harvested observations", e);
            }
        }
        return converted;
    }

    /** A null static param value means the client fills it in per device; deviceId is the only one today. */
    private static String deviceIdFor(String key) {
        return "deviceId".equals(key) ? deviceId : "";
    }
}
