package org.avni.models;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * D8.8. The paging loop continues or stops on what this returns, and the storage pause - the
 * dominant term in a modelled sync - is scaled by the record count it reports.
 *
 * Both come from one parse into a PageInfo, which is the point: the flag and the count describe
 * the same page, and they travel together on the session so they stay with the user that fetched
 * it. A count that belonged to a different page would leave sync durations plausible and wrong.
 */
class PageParsingTest {

    private static final ObjectMapper OM = new ObjectMapper();

    private static String paged(int totalPages, int records) {
        StringBuilder items = new StringBuilder();
        for (int i = 0; i < records; i++) {
            items.append(i == 0 ? "" : ",").append("{\"uuid\":\"u").append(i).append("\"}");
        }
        return "{\"_embedded\":{\"individual\":[" + items + "]},"
            + "\"page\":{\"size\":1000,\"totalElements\":9,\"totalPages\":" + totalPages
            + ",\"number\":0}}";
    }

    private static String sliced(boolean hasNext, int records) {
        StringBuilder items = new StringBuilder();
        for (int i = 0; i < records; i++) {
            items.append(i == 0 ? "" : ",").append("{\"uuid\":\"u").append(i).append("\"}");
        }
        return "{\"_embedded\":{\"encounter\":[" + items + "]},"
            + "\"slice\":{\"hasNext\":" + hasNext + "}}";
    }

    @Test
    @DisplayName("a paged response continues while later pages remain")
    void totalPagesDrivesTheLoop() {
        assertTrue(PageInfo.parse(paged(3, 1000), 0).hasMore);
        assertTrue(PageInfo.parse(paged(3, 1000), 1).hasMore);
        // Index is zero-based: on the last page there is nothing after it.
        assertFalse(PageInfo.parse(paged(3, 1000), 2).hasMore,
            "page 2 of 3 is the last, so the loop has to stop");
        assertFalse(PageInfo.parse(paged(1, 4), 0).hasMore);
    }

    @Test
    @DisplayName("a sliced response follows hasNext instead")
    void sliceDrivesTheLoop() {
        assertTrue(PageInfo.parse(sliced(true, 50), 0).hasMore);
        assertFalse(PageInfo.parse(sliced(false, 50), 0).hasMore);
        // hasNext is authoritative for a slice, so the page index does not enter into it.
        assertTrue(PageInfo.parse(sliced(true, 50), 99).hasMore);
    }

    @Test
    @DisplayName("a response with neither stops rather than looping")
    void noPageMetadataStops() {
        // The D8.5 failure mode was a loop that never terminated. Anything unrecognised has to
        // fall closed.
        assertFalse(PageInfo.parse("{\"_embedded\":{\"x\":[]}}", 0).hasMore);
        assertFalse(PageInfo.parse("{}", 0).hasMore);
    }

    @Test
    @DisplayName("the record count is the page's own, and scales the storage pause")
    void recordCountComesFromTheEmbeddedArray() {
        assertEquals(1000, PageInfo.parse(paged(3, 1000), 0).recordCount);
        assertEquals(7, PageInfo.parse(paged(1, 7), 0).recordCount);
        assertEquals(0, PageInfo.parse(paged(1, 0), 0).recordCount);
        assertEquals(50, PageInfo.parse(sliced(false, 50), 0).recordCount);
    }

    @Test
    @DisplayName("a body with no _embedded counts nothing rather than throwing")
    void missingEmbeddedIsZero() throws Exception {
        assertEquals(0, PageInfo.countRecords(OM.readTree("{}")));
        assertEquals(0, PageInfo.countRecords(OM.readTree("{\"_embedded\":{}}")));
        assertEquals(0, PageInfo.countRecords(OM.readTree("{\"_embedded\":[]}")));
    }

    @Test
    @DisplayName("the flag and the count describe the same page")
    void oneParseYieldsBoth() {
        // They are read from one PageInfo precisely so they cannot disagree. If these ever come
        // from separate parses again, a page could be counted while a different one is followed.
        PageInfo last = PageInfo.parse(paged(2, 314), 1);
        assertFalse(last.hasMore);
        assertEquals(314, last.recordCount);
    }

    @Test
    @DisplayName("an unparseable body fails loudly rather than being treated as the end")
    void malformedBodyThrows() {
        // Returning "no more pages" here would turn a broken response into a silently short sync.
        assertThrows(RuntimeException.class, () -> PageInfo.parse("not json", 0));
    }
}
