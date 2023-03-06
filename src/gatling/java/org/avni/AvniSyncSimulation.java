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
    private static final String baseUrl = System.getProperty("BASE_URL", "http://localhost:8021");
    private static final Integer users = Integer.getInteger("USER_COUNT", csv("users.csv").recordsCount());
//    private static final Integer users = Integer.getInteger("USER_COUNT", 1);
    private static final Integer rampPeriod = Integer.getInteger("RAMP_PERIOD", csv("users.csv").recordsCount() * 3);
//    private static final Integer rampPeriod = Integer.getInteger("RAMP_PERIOD", 1);
    private static final Integer pageSize = Integer.getInteger("PAGE_SIZE", 100);

    FeederBuilder<String> feeder = csv("users.csv").random();
    static ObjectMapper om = new ObjectMapper();

    public static final List<Map<String, Object>> allSyncableEntities = jsonFile("AvniEntities.json").readRecords();

    HttpProtocolBuilder httpProtocol = http.baseUrl(baseUrl).acceptHeader("application/json").contentTypeHeader("application/json").acceptEncodingHeader("gzip").header("USER-NAME", "#{userName}").header("AUTH-TOKEN", "#{token}").connectionHeader("Keep-Alive").userAgentHeader("okhttp/5.0.0-alpha.11");
    ChainBuilder refDataSync =
//        exec(
//        http("resetSyncs")
//            .get("/resetSyncs?lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T10:25:58.819Z&size=100&page=0")
//
//        )
//        .pause(1)
//    .

        exec(http("Getting SyncDetails").post("/syncDetails").body(RawFileBody("EmptyBody.json"))
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
    //    ScenarioBuilder syncScenario = scenario("Sync").feed(feeder).exec(refDataSync, txDataSync);
    ScenarioBuilder syncScenario = scenario("Sync").feed(feeder).exec(refDataSync);

    {
        setUp(syncScenario.injectOpen(rampUsers(users).during(rampPeriod))).protocols(httpProtocol)
//            .assertions(forAll().failedRequests().percent().lte(1.0));
        ;
    }

    private static ChainBuilder sync() {
        AvniEntity ae01 = new AvniEntity("Extension", "/extensions?", "reference");
        AvniEntity ae02 = new AvniEntity("Privilege", "/privilege/search/lastModified?", "reference");
        AvniEntity ae03 = new AvniEntity("Groups", "/groups/search/lastModified?", "reference");
        AvniEntity ae04 = new AvniEntity("GroupPrivileges", "/groupPrivilege/search/lastModified?", "reference");
        AvniEntity ae05 = new AvniEntity("MyGroups", "/myGroups/search/lastModified?", "reference");
        AvniEntity ae06 = new AvniEntity("Concept", "/concept/search/lastModified?", "reference");
        AvniEntity ae07 = new AvniEntity("ConceptAnswer", "/conceptAnswer/search/lastModified?", "reference");
        AvniEntity ae08 = new AvniEntity("SubjectType", "/operationalSubjectType/search/lastModified?", "reference");
        AvniEntity ae09 = new AvniEntity("GroupRole", "/groupRole/search/lastModified?", "reference");
        AvniEntity ae10 = new AvniEntity("Gender", "/gender/search/lastModified?", "reference");
        AvniEntity ae11 = new AvniEntity("ProgramOutcome", "/programOutcome/search/lastModified?", "reference");
        AvniEntity ae12 = new AvniEntity("Program", "/operationalProgram/search/lastModified?", "reference");
        AvniEntity ae13 = new AvniEntity("EncounterType", "/operationalEncounterType/search/lastModified?", "reference");
        AvniEntity ae14 = new AvniEntity("TaskType", "/taskType/search/lastModified?", "reference");
        AvniEntity ae15 = new AvniEntity("TaskStatus", "/taskStatus/search/lastModified?", "reference");
        AvniEntity ae16 = new AvniEntity("AddressLevel", "/addressLevel/search/lastModified?", "reference");
        AvniEntity ae17 = new AvniEntity("LocationMapping", "/locationMapping/search/lastModified?", "reference");
        AvniEntity ae18 = new AvniEntity("Translation", "/translation/search/lastModified?", "reference");
        AvniEntity ae19 = new AvniEntity("PlatformTranslation", "/platformTranslation/search/lastModified?", "reference");
        AvniEntity ae20 = new AvniEntity("OrganisationConfig", "/organisationConfig/search/lastModified?", "reference");
        AvniEntity ae21 = new AvniEntity("IdentifierSource", "/identifierSource/search/lastModified?", "reference");
        AvniEntity ae22 = new AvniEntity("Documentation", "/documentation/search/lastModified?", "reference");
        AvniEntity ae23 = new AvniEntity("DocumentationItem", "/documentationItem/search/lastModified?", "reference");
        AvniEntity ae24 = new AvniEntity("Form", "/form/search/lastModified?", "reference");
        AvniEntity ae25 = new AvniEntity("FormElementGroup", "/formElementGroup/search/lastModified?", "reference");
        AvniEntity ae26 = new AvniEntity("FormElement", "/formElement/search/lastModified?", "reference");
        AvniEntity ae27 = new AvniEntity("FormMapping", "/formMapping/search/lastModified?", "reference");
        AvniEntity ae28 = new AvniEntity("ProgramConfig", "/programConfig/search/lastModified?", "reference");
        AvniEntity ae29 = new AvniEntity("IndividualRelation", "/individualRelation/search/lastModified?", "reference");
        AvniEntity ae30 = new AvniEntity("IndividualRelationGenderMapping", "/individualRelationGenderMapping/search/lastModified?", "reference");
        AvniEntity ae31 = new AvniEntity("IndividualRelationshipType", "/individualRelationshipType/search/lastModified?", "reference");
        AvniEntity ae32 = new AvniEntity("RuleDependency", "/ruleDependency/search/lastModified?", "reference");
        AvniEntity ae33 = new AvniEntity("Rule", "/rule/search/lastModified?", "reference");
        AvniEntity ae34 = new AvniEntity("ChecklistDetail", "/checklistDetail/search/lastModified?", "reference");
        AvniEntity ae35 = new AvniEntity("ChecklistItemDetail", "/checklistItemDetail/search/lastModified?", "reference");
        AvniEntity ae36 = new AvniEntity("Video", "/video/search/lastModified?", "reference");
        AvniEntity ae37 = new AvniEntity("LocationHierarchy", "/locationHierarchy/search/lastModified?", "reference");
        AvniEntity ae38 = new AvniEntity("MenuItem", "/menuItem/search/lastModified?", "reference");
        AvniEntity ae39 = new AvniEntity("StandardReportCardType", "/standardReportCardType/search/lastModified?", "reference");
        AvniEntity ae40 = new AvniEntity("ReportCard", "/card/search/lastModified?", "reference");
        AvniEntity ae41 = new AvniEntity("Dashboard", "/dashboard/search/lastModified?", "reference");
        AvniEntity ae42 = new AvniEntity("DashboardSection", "/dashboardSection/search/lastModified?", "reference");
        AvniEntity ae43 = new AvniEntity("DashboardSectionCardMapping", "/dashboardSectionCardMapping/search/lastModified?", "reference");
        AvniEntity ae44 = new AvniEntity("ApprovalStatus", "/approvalStatus/search/lastModified?", "reference");
        AvniEntity ae45 = new AvniEntity("GroupDashboard", "/groupDashboard/search/lastModified?", "reference");
        AvniEntity ae46 = new AvniEntity("UserInfo", "/v2/me?", "tx");
        AvniEntity ae47 = new AvniEntity("Individual", "/individual/search/lastModified?subjectTypeUuid=", "tx");
        AvniEntity ae48 = new AvniEntity("ProgramEnrolment", "/programEnrolment?programUuid=", "tx");
        AvniEntity ae49 = new AvniEntity("ProgramEncounter", "/programEncounter?programEncounterTypeUuid=", "tx");
        AvniEntity ae50 = new AvniEntity("IdentifierAssignment", "/identifierAssignment?", "tx");
        AvniEntity ae51 = new AvniEntity("Encounter", "/encounter?encounterTypeUuid=", "tx");
        AvniEntity ae52 = new AvniEntity("Checklist", "/checklist?", "tx");
        AvniEntity ae53 = new AvniEntity("ChecklistItem", "/checklistItem?", "tx");
        AvniEntity ae54 = new AvniEntity("IndividualRelationship", "/individualRelationship?subjectTypeUuid=", "tx");
        AvniEntity ae55 = new AvniEntity("EntityApprovalStatus", "/entityApprovalStatus?", "tx");
        AvniEntity ae56 = new AvniEntity("CommentThread", "/commentThread?", "tx");
        AvniEntity ae57 = new AvniEntity("Comment", "/comment?", "tx");
        AvniEntity ae58 = new AvniEntity("GroupSubject", "/groupSubject?", "tx");
        AvniEntity ae59 = new AvniEntity("VideoTelemetric", "/videoTelemetric?", "tx");
        AvniEntity ae60 = new AvniEntity("News", "/news?", "tx");
        AvniEntity ae61 = new AvniEntity("SubjectProgramEligibility", "/subjectProgramEligibility?", "tx");
        AvniEntity ae62 = new AvniEntity("TaskUnAssigment", "/taskUnAssigments?", "tx");
        AvniEntity ae63 = new AvniEntity("Task", "/task?", "tx");
        AvniEntity ae64 = new AvniEntity("UserSubjectAssignment", "/userSubjectAssignment?", "tx");

        return foreach(Arrays.asList(
            ae01, ae02, ae03, ae04, ae05, ae06, ae07, ae08, ae09, ae10,
            ae11, ae12, ae13, ae14, ae15, ae16, ae17, ae18, ae19, ae20,
            ae21, ae22, ae23, ae24, ae25, ae26, ae27, ae28, ae29, ae30,
            ae31, ae32, ae33, ae34, ae35, ae36, ae37, ae38, ae39, ae40,
            ae41, ae42, ae43, ae44, ae45, ae46, ae47, ae48, ae49, ae50,
            ae51, ae52, ae53, ae54, ae55, ae56, ae57, ae58, ae59, ae60,
            ae61, ae62, ae63, ae64
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
        return exec(session -> session.set("allPagesNotFetched", true))
            .asLongAs("#{allPagesNotFetched}", "index")
            .on(
                exec(http(String.format("Getting %s pages", entityName))
                    .get(String.format("%slastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z&size=%d&page=#{index}", endpointWithParam, pageSize))
                    .check(status().is(200))
//                    .asJson()
                    .check(jmesPath("page.totalPages").ofInt()
                        .transformWithSession((totalPages, session) -> totalPages > session.getInt("index") + 1)
                        .saveAs("allPagesNotFetched")))
                    .pause(0, 2) //to simulate the time between requests while client stores the data in realm
            );
    }
}
