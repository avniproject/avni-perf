package org.avni.models;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Round-trip time as the run archive records it.
 *
 * The number matters because a sync is ~109 requests, so a round trip is paid 109 times: 25 ms is
 * 2.7 s on a 14.1 s median. Recording the injector's label said two runs came from different
 * places; this says by how much, which is what makes them comparable or not.
 */
class RttTest {

    private static final int REQUESTS = 109;

    @Test
    @DisplayName("the floor and the typical value are both kept, and can differ")
    void minAndMedianAreBothReported() {
        // They diverge on a congested or shared path, and that divergence is the point: the
        // minimum is the network, the median is what the run actually pays.
        Rtt r = new Rtt(List.of(30.0, 12.0, 14.0, 60.0, 13.0), 5);
        assertEquals(12.0, r.minMillis());
        assertEquals(14.0, r.medianMillis());
    }

    @Test
    @DisplayName("samples arrive in any order")
    void orderDoesNotMatter() {
        assertEquals(new Rtt(List.of(5.0, 1.0, 3.0), 3).medianMillis(),
                     new Rtt(List.of(1.0, 3.0, 5.0), 3).medianMillis());
    }

    @Test
    @DisplayName("an even number of samples averages the middle two")
    void evenSampleCount() {
        assertEquals(3.0, new Rtt(List.of(2.0, 4.0), 2).medianMillis());
    }

    @Test
    @DisplayName("a round trip is turned into what a sync pays for it")
    void syncOverheadMakesTheNumberLegible() {
        // 25 ms is "small" until multiplied by 109 - that is the whole reason this field exists.
        Rtt r = new Rtt(List.of(25.0), 1);
        assertEquals(2.725, r.syncOverheadSeconds(REQUESTS), 0.001);
        // And the difference between two positions is the difference between the two runs.
        Rtt near = new Rtt(List.of(1.0), 1);
        assertTrue(r.syncOverheadSeconds(REQUESTS) - near.syncOverheadSeconds(REQUESTS) > 2.5);
    }

    @Test
    @DisplayName("an unreachable target records why, not a zero")
    void unreachableIsNotZero() {
        // A zero would read as an infinitely fast network, which is the worst possible way to be
        // wrong about this particular number.
        Rtt r = new Rtt(List.of(), 5);
        assertFalse(r.measured());
        assertEquals(-1, r.minMillis());
        assertEquals(-1, r.syncOverheadSeconds(REQUESTS));
        String status = (String) r.asMetadata(REQUESTS).get("status");
        assertTrue(status.contains("unreachable") && status.contains("5"), status);
        assertFalse(r.asMetadata(REQUESTS).containsKey("minMillis"),
            "an unmeasured rtt must not report a number at all");
    }

    @Test
    @DisplayName("not attempting is distinguishable from failing to connect")
    void notAttemptedSaysSo() {
        assertEquals("not attempted", Rtt.UNMEASURED.asMetadata(REQUESTS).get("status"));
    }

    @Test
    @DisplayName("a measured rtt reports its numbers and how they were obtained")
    void metadataCarriesTheBasis() {
        var m = new Rtt(List.of(10.0, 20.0, 30.0), 3).asMetadata(REQUESTS);
        assertEquals(10.0, m.get("minMillis"));
        assertEquals(20.0, m.get("medianMillis"));
        assertEquals(3, m.get("samples"));
        assertEquals(2.18, m.get("estimatedSyncOverheadSeconds"));
        assertTrue(((String) m.get("basis")).contains("TCP connect"),
            "the archive should say what was measured, not just the value");
    }
}
