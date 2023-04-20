package org.avni;

import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;
import static java.lang.System.out;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import io.gatling.javaapi.core.*;
import io.gatling.javaapi.http.*;
import org.avni.models.AvniEntity;
import org.avni.models.SyncDetail;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.*;


public class AvniSyncSimulation extends Simulation {
    private static final String baseUrl = System.getProperty("BASE_URL", "https://perf.avniproject.org");
    private static final Integer users = Integer.getInteger("USER_COUNT", csv("users.csv").recordsCount());
    private static final Integer rampPeriod = Integer.getInteger("RAMP_PERIOD", csv("users.csv").recordsCount() * 3);
    private static final Integer pageSize = Integer.getInteger("PAGE_SIZE", 100);
    private static final Integer maxPauseToSimulateRealmStorage = Integer.getInteger("MAX_REALM_STORAGE_PAUSE", 2);
    private static final String now = System.getProperty("NOW", java.time.Instant.now().toString());
    private static final Boolean reportByEntityTypeUuid = Boolean.getBoolean("REPORT_BY_ENTITY_TYPE_UUID");

    FeederBuilder<String> feeder = csv("users.csv").random();
    static ObjectMapper om = new ObjectMapper();

//    public static final List<Map<String, Object>> allSyncableEntities = jsonFile("AvniEntities.json").readRecords();

    HttpProtocolBuilder httpProtocol = http.baseUrl(baseUrl).acceptHeader("application/json").contentTypeHeader("application/json").acceptEncodingHeader("gzip").header("USER-NAME", "#{userName}").header("AUTH-TOKEN", "#{token}").connectionHeader("Keep-Alive").userAgentHeader("okhttp/5.0.0-alpha.11");
    ChainBuilder syncChainBuilder =
//        exec(
//        http("resetSyncs")
//            .get("/resetSyncs?lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T10:25:58.819Z&size=100&page=0")
//
//        )
//        .pause(1)
//    .

        exec(http("Getting SyncDetails").post("/v2/syncDetails").body(RawFileBody("EmptyBody.json"))
            .check(jsonPath("$.syncDetails")
                .transform(listElements -> {
                    try {
                        return om.readValue(listElements, new TypeReference<List<SyncDetail>>() {
                        });
                    } catch (JsonProcessingException e) {
                        out.println("Exception" + e);
                        throw new RuntimeException(e);
                    }
                }).saveAs("syncDetails")
            ))
            .exec(sync());
    ScenarioBuilder syncScenario = scenario("Sync").feed(feeder).exec(syncChainBuilder);

    {
        setUp(syncScenario.injectOpen(rampUsers(users).during(rampPeriod))).protocols(httpProtocol)
//            .assertions(forAll().failedRequests().percent().lte(1.0));
        ;
    }

    private static ChainBuilder sync() {
        return foreach(Arrays.asList(
            new AvniEntity("Extension", "/extensions?", "reference"),
            new AvniEntity("Privilege", "/privilege/search/lastModified?", "reference"),
            new AvniEntity("Groups", "/groups/search/lastModified?", "reference"),
            new AvniEntity("GroupPrivileges", "/groupPrivilege/search/lastModified?", "reference"),
            new AvniEntity("MyGroups", "/myGroups/search/lastModified?", "reference"),
            new AvniEntity("Concept", "/concept/search/lastModified?", "reference"),
            new AvniEntity("ConceptAnswer", "/conceptAnswer/search/lastModified?", "reference"),
            new AvniEntity("SubjectType", "/operationalSubjectType/search/lastModified?", "reference"),
            new AvniEntity("GroupRole", "/groupRole/search/lastModified?", "reference"),
            new AvniEntity("Gender", "/gender/search/lastModified?", "reference"),
            new AvniEntity("ProgramOutcome", "/programOutcome/search/lastModified?", "reference"),
            new AvniEntity("Program", "/operationalProgram/search/lastModified?", "reference"),
            new AvniEntity("EncounterType", "/operationalEncounterType/search/lastModified?", "reference"),
            new AvniEntity("TaskType", "/taskType/search/lastModified?", "reference"),
            new AvniEntity("TaskStatus", "/taskStatus/search/lastModified?", "reference"),
            new AvniEntity("AddressLevel", "/addressLevel/search/lastModified?", "reference"),
            new AvniEntity("LocationMapping", "/locationMapping/search/lastModified?", "reference"),
            new AvniEntity("Translation", "/translation/search/lastModified?", "reference"),
            new AvniEntity("PlatformTranslation", "/platformTranslation/search/lastModified?", "reference"),
            new AvniEntity("OrganisationConfig", "/organisationConfig/search/lastModified?", "reference"),
            new AvniEntity("IdentifierSource", "/identifierSource/search/lastModified?", "reference"),
            new AvniEntity("Documentation", "/documentation/search/lastModified?", "reference"),
            new AvniEntity("DocumentationItem", "/documentationItem/search/lastModified?", "reference"),
            new AvniEntity("Form", "/form/search/lastModified?", "reference"),
            new AvniEntity("FormElementGroup", "/formElementGroup/search/lastModified?", "reference"),
            new AvniEntity("FormElement", "/formElement/search/lastModified?", "reference"),
            new AvniEntity("FormMapping", "/formMapping/search/lastModified?", "reference"),
            new AvniEntity("ProgramConfig", "/programConfig/search/lastModified?", "reference"),
            new AvniEntity("IndividualRelation", "/individualRelation/search/lastModified?", "reference"),
            new AvniEntity("IndividualRelationGenderMapping", "/individualRelationGenderMapping/search/lastModified?", "reference"),
            new AvniEntity("IndividualRelationshipType", "/individualRelationshipType/search/lastModified?", "reference"),
            new AvniEntity("RuleDependency", "/ruleDependency/search/lastModified?", "reference"),
            new AvniEntity("Rule", "/rule/search/lastModified?", "reference"),
            new AvniEntity("ChecklistDetail", "/checklistDetail/search/lastModified?", "reference"),
            new AvniEntity("ChecklistItemDetail", "/checklistItemDetail/search/lastModified?", "reference"),
            new AvniEntity("Video", "/video/search/lastModified?", "reference"),
            new AvniEntity("LocationHierarchy", "/locationHierarchy/search/lastModified?", "reference"),
            new AvniEntity("MenuItem", "/menuItem/search/lastModified?", "reference"),
            new AvniEntity("StandardReportCardType", "/standardReportCardType/search/lastModified?", "reference"),
            new AvniEntity("ReportCard", "/card/search/lastModified?", "reference"),
            new AvniEntity("Dashboard", "/dashboard/search/lastModified?", "reference"),
            new AvniEntity("DashboardSection", "/dashboardSection/search/lastModified?", "reference"),
            new AvniEntity("DashboardSectionCardMapping", "/dashboardSectionCardMapping/search/lastModified?", "reference"),
            new AvniEntity("ApprovalStatus", "/approvalStatus/search/lastModified?", "reference"),
            new AvniEntity("GroupDashboard", "/groupDashboard/search/lastModified?", "reference"),

            new AvniEntity("UserInfo", "/me/v3?", "tx"),
            new AvniEntity("Individual", "/individual/search/lastModified/v2?subjectTypeUuid=", "tx"),
            new AvniEntity("ProgramEnrolment", "/programEnrolment/v2?programUuid=", "tx"),
            new AvniEntity("ProgramEncounter", "/programEncounter/v2?programEncounterTypeUuid=", "tx"),
            new AvniEntity("IdentifierAssignment", "/identifierAssignment/v2?", "tx"),
            new AvniEntity("Encounter", "/encounter/v2?encounterTypeUuid=", "tx"),
            new AvniEntity("Checklist", "/txNewChecklistEntity/v2?checklistDetailUuid=", "tx"),
            new AvniEntity("ChecklistItem", "/txNewChecklistItemEntity/v2?checklistDetailUuid=", "tx"),
            new AvniEntity("IndividualRelationship", "/individualRelationship/v2?subjectTypeUuid=", "tx"),
            new AvniEntity("EntityApprovalStatus", "/entityApprovalStatus/v2?", "tx"),
            new AvniEntity("CommentThread", "/commentThread/v2?", "tx"),
            new AvniEntity("Comment", "/comment/v2?", "tx"),
            new AvniEntity("GroupSubject", "/groupSubject/v2?", "tx"),
//            new AvniEntity("News", "/news/v2?", "tx"), //commented as this connects to prod s3 which fails
            new AvniEntity("SubjectProgramEligibility", "/subjectProgramEligibility/v2?", "tx"),
            new AvniEntity("TaskUnAssigment", "/taskUnAssigments/v2?", "tx"),
            new AvniEntity("Task", "/task/v2?", "tx"),
            new AvniEntity("UserSubjectAssignment", "/userSubjectAssignment/v2?", "tx"),
            new AvniEntity("SubjectMigration", "/subjectMigrations/v2?subjectTypeUuid=", "tx")
        ), "entity").on(
            foreach(session -> session.getList("syncDetails"), "syncDetail").on(
//                    doIfEqualsOrElse("#{syncDetail.entityName}", "#{entity.entityName}")
                doIfEquals("#{syncDetail.entityName}", "#{entity.entityName}")
                    .then(
                        exec(getAndPaginate("#{entity.entityName}", "#{entity.resourcePath}", "#{syncDetail.entityTypeUuid}"))
                    )
//                    .orElse(exec(print("no match for #{entity.entityName}")))
            ));
    }

    private static ChainBuilder getAndPaginate(String entityName, String endpoint, String entityTypeUuid) {
        String endpointWithParam = String.format("%s%s&", endpoint, entityTypeUuid);
        String reportItemString = reportByEntityTypeUuid && entityTypeUuid != null
            ? String.format("Getting %s pages for entityTypeUuid %s", entityName, entityTypeUuid)
            : String.format("Getting %s pages", entityName);
        return exec(session -> session.set("allPagesNotFetched", true))
            .asLongAs("#{allPagesNotFetched}", "index")
            .on(
                exec(http(reportItemString)
                        .get(String.format("%slastModifiedDateTime=#{lastModifiedDateTime}&now=%s&size=%d&page=#{index}", endpointWithParam, now, pageSize))
                        .check(status().is(200))
//                    .asJson()
                        .checkIf((response, session) -> response.body().string().contains("totalPages")).then(
                            jmesPath("page.totalPages").ofInt()
                                .transformWithSession((totalPages, session) -> totalPages > session.getInt("index") + 1)
                                .saveAs("allPagesNotFetched"))
                        .checkIf((response, session) -> response.body().string().contains("hasNext")).then(
                            jmesPath("slice.hasNext").ofBoolean()
                                .transformWithSession((hasNext, session) -> hasNext)
                                .saveAs("allPagesNotFetched"))

                )
                    .pause(0, maxPauseToSimulateRealmStorage) //to simulate the time between requests while client stores the data in realm
//                        .exec(session -> { // for debugging
//                            System.out.println("allPagesNotFetched::" + session.getString("allPagesNotFetched"));
//                            System.out.println("name:" + entityName);
//                            return session;
//                        })
            );

    }
}
