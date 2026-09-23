package org.avni.models;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * The `/v2` slice endpoints, as recorded in the generated entity table.
 *
 * `PAGING=slice` exists to measure one thing: Spring's `Page` runs a `count(*)` over the whole
 * matching set to populate `totalPages`, and `Slice` does not. The delta between two otherwise
 * identical runs is that count's cost.
 *
 * That only means anything if the table is right, and the table is the fragile part — the list of
 * sliced paths cannot be derived from `openchs-models`, because the client does not call them. It
 * is copied from the server, so it can drift from the server without anything noticing.
 */
class SlicePathTest {

    private static List<JsonNode> entities() throws Exception {
        try (InputStream in = SlicePathTest.class.getClassLoader()
                .getResourceAsStream("avni-entities.json")) {
            assertNotNull(in, "avni-entities.json should be on the classpath");
            JsonNode root = new ObjectMapper().readTree(in);
            List<JsonNode> out = new ArrayList<>();
            root.get("entities").forEach(out::add);
            return out;
        }
    }

    private static String text(JsonNode n, String field) {
        JsonNode v = n.get(field);
        return v == null || v.isNull() ? null : v.asText();
    }

    @Test
    @DisplayName("a slice path is always its paged path plus /v2")
    void slicePathDerivesFromThePagedPath() throws Exception {
        // If these ever diverge, a slice run would be hitting a different endpoint than the page
        // run it is being compared against, and the delta would mean nothing.
        for (JsonNode e : entities()) {
            String slice = text(e, "slicePath");
            if (slice != null) {
                assertEquals(text(e, "path") + "/v2", slice,
                    "slicePath for " + text(e, "entityName") + " should be its path plus /v2");
            }
        }
    }

    @Test
    @DisplayName("the transactional entities that matter all have one")
    void theHeavyEntitiesAreSliceable() throws Exception {
        // These are the tables the count(*) is expensive on - program_encounter alone is 11.4 GB
        // with GIN indexes. A slice run that silently fell back on these would measure nothing.
        List<String> mustHave = List.of("Individual", "ProgramEnrolment", "ProgramEncounter",
            "Encounter", "GroupSubject", "IndividualRelationship");
        for (String name : mustHave) {
            JsonNode e = entities().stream()
                .filter(n -> name.equals(text(n, "entityName")))
                .findFirst().orElseThrow(() -> new AssertionError("no entity named " + name));
            assertNotNull(text(e, "slicePath"), name + " should have a slice endpoint");
        }
    }

    @Test
    @DisplayName("only pulled entities carry one, and the count is what the banner reports")
    void sliceCoverageIsWhatWeClaim() throws Exception {
        long sliced = entities().stream()
            .filter(e -> e.get("pullRequired").asBoolean() && text(e, "slicePath") != null)
            .count();
        // The banner tells the operator how many of the pulled entities fall back to paging.
        // If this number moves, that sentence is wrong and so is the comparison it describes.
        assertEquals(22, sliced,
            "expected 22 pulled entities with a slice endpoint - if the server gained or lost one, "
                + "update SLICED_PATHS in tools/entity-metadata/generate.js and this number");
    }

    @Test
    @DisplayName("entities without a slice endpoint say so with null, not an empty string")
    void absentSlicePathsAreNull() throws Exception {
        for (JsonNode e : entities()) {
            JsonNode v = e.get("slicePath");
            assertNotNull(v, "every entity should carry the field, even when null");
            assertFalse(v.isTextual() && v.asText().isEmpty(),
                text(e, "entityName") + " has an empty slicePath; it should be null");
        }
    }
}
