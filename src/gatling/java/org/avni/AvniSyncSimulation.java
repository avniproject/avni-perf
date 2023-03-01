package org.avni;

import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

import io.gatling.javaapi.core.*;
import io.gatling.javaapi.http.*;


public class AvniSyncSimulation extends Simulation {
    private static final String baseUrl = System.getProperty("BASE_URL", "http://localhost:8021");
    private static final Integer users = Integer.getInteger("USER_COUNT", csv("users.csv").recordsCount());
    private static final Integer rampPeriod = Integer.getInteger("RAMP_PERIOD", csv("users.csv").recordsCount() * 3);
    private static final Integer pageSize = Integer.getInteger("PAGE_SIZE", 100);

    FeederBuilder<String> feeder = csv("users.csv").random();

    HttpProtocolBuilder httpProtocol =
        http.baseUrl(baseUrl)
            .acceptHeader("application/json")
            .contentTypeHeader("application/json")
            .acceptEncodingHeader("gzip")
            .header("USER-NAME", "#{userName}")
            .header("AUTH-TOKEN", "#{token}")
            .connectionHeader("Keep-Alive")
            .userAgentHeader(
                "okhttp/5.0.0-alpha.11"
            );
    ChainBuilder refDataSync = exec(
        http("resetSyncs")
            .get("/resetSyncs?lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T10:25:58.819Z&size=100&page=0")

    )
        .pause(1)
        .exec(http("syncDetails")
            .post("/syncDetails")
            .body(RawFileBody("SyncDetailsBody.json"))
        )
        .exec(getAndPaginate("Privileges", "/privilege/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("Groups", "/groups/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("GroupPrivileges", "/groupPrivilege/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("Concept", "/concept/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("ConceptAnswer", "/conceptAnswer/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("OperationalSubjectType", "/operationalSubjectType/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("GroupRole", "/groupRole/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("Gender", "/gender/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("OperationalProgram", "/operationalProgram/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("OperationalEncounterType", "/operationalEncounterType/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("Locations", "/locations/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("LocationMapping", "/locationMapping/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("OrganisationConfig", "/organisationConfig/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("IdentifierSource", "/identifierSource/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("Form", "/form/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("FormElementGroup", "/formElementGroup/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("FormElement", "/formElement/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("FormMapping", "/formMapping/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("IndividualRelation", "/individualRelation/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("IndividualRelationGenderMapping", "/individualRelationGenderMapping/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("IndividualRelationshipType", "/individualRelationshipType/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("StandardReportCardType", "/standardReportCardType/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        .exec(getAndPaginate("ApprovalStatus", "/approvalStatus/search/lastModified?&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
        ;


    ChainBuilder txDataSync =
        exec(getAndPaginate("Me", "/v2/me?lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
            .exec(getAndPaginate("Individual", "/individual?subjectTypeUuid=acb42ed7-003c-4364-b131-b39827c33a58&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T14:37:59.686Z"))
            .exec(getAndPaginate("ProgramEnrolment", "/programEnrolment?programUuid=b940a8a0-9e18-45e1-8c8a-be18b2f80b2e&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T10:26:00.300Z"))
            .exec(getAndPaginate("ProgramEncounter", "/programEncounter?programEncounterTypeUuid=5bbc2389-6109-44ea-ac3f-883803ae830a&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T10:26:00.300Z"))
            .exec(getAndPaginate("IdentifierAssignment", "/identifierAssignment?lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T10:26:00.300Z"))
            .exec(getAndPaginate("Encounter", "/encounter?encounterTypeUuid=5ca9821c-56d6-4d58-8fa1-26f7415b9dcf&lastModifiedDateTime=#{lastModifiedDateTime}&now=2023-02-28T10:26:00.300Z"));

    ScenarioBuilder syncScenario = scenario("Sync").feed(feeder).exec(refDataSync, txDataSync);
//    ScenarioBuilder syncScenario = scenario("Sync").feed(feeder).exec(refDataSync);

    {
        setUp(
            syncScenario.injectOpen(rampUsers(users).during(rampPeriod))
        ).protocols(httpProtocol)
//            .assertions(forAll().failedRequests().percent().lte(1.0));
        ;
    }

    private static ChainBuilder getAndPaginate(String entityName, String endpoint) {
        return exec(session -> session.set("allPagesNotFetched", true))
            .asLongAs("#{allPagesNotFetched}", "index").on(
                exec(http(String.format("Getting %s pages", entityName))
                    .get(String.format("%s&size=%d&page=#{index}", endpoint, pageSize))
                    .check(status().is(200))
                    .asJson()
                    .check(
                        jmesPath("page.totalPages")
                            .ofInt()
                            .transformWithSession((totalPages, session) -> totalPages > session.getInt("index") + 1)
                            .saveAs("allPagesNotFetched")
                    )
                ).pause(1, 3)
            );
    }
}
