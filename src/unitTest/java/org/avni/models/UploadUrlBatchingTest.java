package org.avni.models;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class UploadUrlBatchingTest {

    @Test
    @DisplayName("blank and 0 are the per-file client, 1..50 the batched one")
    void parsesTheFlag() {
        assertEquals(0, UploadUrlBatching.parse(null));
        assertEquals(0, UploadUrlBatching.parse(""));
        assertEquals(0, UploadUrlBatching.parse("0"));
        assertEquals(1, UploadUrlBatching.parse("1"));
        assertEquals(50, UploadUrlBatching.parse(" 50 "));
    }

    @Test
    @DisplayName("past the server's cap, negative or not a number is refused, not run")
    void refusesWhatTheServerWouldReject() {
        IllegalArgumentException over = assertThrows(IllegalArgumentException.class,
            () -> UploadUrlBatching.parse("51"));
        assertTrue(over.getMessage().contains("server's cap"), over.getMessage());
        assertThrows(IllegalArgumentException.class, () -> UploadUrlBatching.parse("-1"));
        assertThrows(IllegalArgumentException.class, () -> UploadUrlBatching.parse("ten"));
    }

    @Test
    @DisplayName("files are grouped into full batches and a remainder, never more than the batch")
    void groupsFiles() {
        assertEquals(Arrays.asList(50, 50, 50, 10), UploadUrlBatching.groups(160, 50));
        assertEquals(Arrays.asList(8, 8, 8), UploadUrlBatching.groups(24, 8));
        assertEquals(List.of(3), UploadUrlBatching.groups(3, 50));
        assertTrue(UploadUrlBatching.groups(0, 50).isEmpty());
        assertTrue(UploadUrlBatching.groups(160, 0).isEmpty(), "batching off: no groups");
        assertEquals(160, UploadUrlBatching.groups(160, 7).stream().mapToInt(Integer::intValue).sum());
    }

    @Test
    @DisplayName("URL requests per sync: one per file unbatched, one per group batched")
    void countsRequests() {
        assertEquals(160, UploadUrlBatching.requests(160, 0));
        assertEquals(4, UploadUrlBatching.requests(160, 50));
        assertEquals(20, UploadUrlBatching.requests(160, 8));
        assertEquals(0, UploadUrlBatching.requests(0, 50));
    }
}
