package org.avni.models;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.io.UncheckedIOException;

/**
 * What one page of a pull turned out to be: whether another follows, and how many records it held.
 *
 * **Both come from one parse, deliberately.** An earlier shape called `response.body().string()`
 * in two separate predicates and materialised every page twice, which is injector CPU spent
 * inflating the latency being measured. Keeping the flag and the count in one object is what
 * makes a single parse sufficient - and it also means the two cannot describe different pages.
 *
 * **It is carried on the Gatling session, not in a ThreadLocal.** It used to be the latter, which
 * is per-thread and therefore not per-user: Gatling multiplexes hundreds of virtual users onto a
 * handful of event-loop threads. That was correct only because the check and the pause that reads
 * it happen to run in one synchronous continuation, an internal detail rather than a contract.
 * The storage pause is the dominant term in a modelled sync and D6 exists so that it tracks *this
 * user's* page size, so it is not a value to leave resting on an implementation accident.
 *
 * Lives here rather than on the simulation so it can be tested without the simulation's static
 * initialisation, which loads the entity table and the user file.
 */
public final class PageInfo {
    private static final ObjectMapper OM = new ObjectMapper();

    /** The state a loop starts in: nothing fetched yet, so there is always a first page. */
    public static final PageInfo FIRST = new PageInfo(true, 0);

    public final boolean hasMore;
    public final int recordCount;

    public PageInfo(boolean hasMore, int recordCount) {
        this.hasMore = hasMore;
        this.recordCount = recordCount;
    }

    /**
     * Takes the page index rather than the session, so the logic is reachable from a test without
     * standing up a Gatling session for it.
     */
    public static PageInfo parse(String body, int pageIndex) {
        try {
            JsonNode root = OM.readTree(body);
            return new PageInfo(hasMorePages(root, pageIndex), countRecords(root));
        } catch (IOException e) {
            // Loud on purpose. Treating an unparseable body as "no more pages" would turn a broken
            // response into a silently short sync, which reads as a fast one.
            throw new UncheckedIOException("Could not parse page metadata", e);
        }
    }

    /**
     * The server pages two ways. `page.totalPages` is a count, compared against the zero-based
     * index; `slice.hasNext` is authoritative on its own. Anything else falls closed - the D8.5
     * failure was a loop that never terminated, so an unrecognised shape must stop rather than
     * continue.
     */
    static boolean hasMorePages(JsonNode root, int pageIndex) {
        JsonNode page = root.path("page");
        if (!page.isMissingNode() && page.has("totalPages")) {
            return page.get("totalPages").asInt() > pageIndex + 1;
        }
        JsonNode slice = root.path("slice");
        if (!slice.isMissingNode() && slice.has("hasNext")) {
            return slice.get("hasNext").asBoolean();
        }
        return false;
    }

    /** The first array under `_embedded`, which is where every pull puts its rows. */
    static int countRecords(JsonNode root) {
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
}
