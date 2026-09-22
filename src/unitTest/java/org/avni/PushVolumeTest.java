package org.avni;

import org.avni.models.PushProfiles;
import org.avni.models.PushVolume;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * D8.9. These cover the three ways PushVolume used to accept bad input in silence, and the
 * distribution maths that a silent correction would distort.
 *
 * The push volume decides how many records each sync writes, so a mis-specified override does not
 * fail a run - it produces a plausible-looking run measuring the wrong workload. That is the
 * failure these are here to make loud.
 */
class PushVolumeTest {

    private static PushVolume q17ProgramEncounters() {
        return new PushVolume("ProgramEncounter", 0.2868, 3, 33, 323, 8.3);
    }

    @Test
    @DisplayName("the measured defaults produce no warnings")
    void realDefaultsAreSilent() {
        // The guard against these checks becoming noise. If Q17's own numbers trip a warning,
        // the warning is wrong, not the data.
        for (Map.Entry<String, PushVolume> e : PushProfiles.production().entrySet()) {
            assertTrue(e.getValue().warnings.isEmpty(),
                () -> "production profile " + e.getKey() + " warned: " + e.getValue().warnings);
        }
        for (boolean programModel : new boolean[]{true, false}) {
            for (Map.Entry<String, PushVolume> e : PushProfiles.customer(programModel).entrySet()) {
                assertTrue(e.getValue().warnings.isEmpty(),
                    () -> "customer profile " + e.getKey() + " warned: " + e.getValue().warnings);
            }
        }
    }

    @Test
    @DisplayName("probability outside 0..1 throws rather than silently pushing always or never")
    void probabilityIsValidated() {
        // Above 1 made every sync push, at or below 0 made none. Both are typos, not intents,
        // which is why these throw where the other two only warn.
        IllegalArgumentException high = assertThrows(IllegalArgumentException.class,
            () -> new PushVolume("Individual", 1.5, 1, 13, 174, 3.3));
        assertTrue(high.getMessage().contains("between 0 and 1"), high.getMessage());
        assertTrue(high.getMessage().contains("1.5"), high.getMessage());

        assertThrows(IllegalArgumentException.class,
            () -> new PushVolume("Individual", -0.1, 1, 13, 174, 3.3));
        assertDoesNotThrow(() -> new PushVolume("Individual", 0.0, 1, 13, 174, 3.3));
        assertDoesNotThrow(() -> new PushVolume("Individual", 1.0, 1, 13, 174, 3.3));
    }

    @Test
    @DisplayName("a transposed quantile is corrected, and says so")
    void clampingWarns() {
        PushVolume v = new PushVolume("ProgramEncounter", 0.5, 3, 2, 300, 8);
        assertEquals(3, v.p95, "p95 below p50 has to be raised for the quantiles to be usable");
        assertTrue(v.warnings.stream().anyMatch(w -> w.contains("p95") && w.contains("2")
                && w.contains("3")),
            () -> "expected a warning naming the given and used value, got " + v.warnings);
    }

    @Test
    @DisplayName("a mean the quantiles cannot reach warns in both directions")
    void unreachableMeanWarns() {
        // Above what the shape can produce: the fit converges at the fattest tail and averages low.
        PushVolume low = new PushVolume("ProgramEncounter", 0.28, 3, 33, 323, 500);
        assertTrue(low.warnings.stream().anyMatch(w -> w.contains("average low")),
            () -> "expected an undershoot warning, got " + low.warnings);

        // Below it: the tail pins at p95 and still averages high.
        PushVolume high = new PushVolume("ProgramEncounter", 0.28, 3, 33, 323, 2);
        assertTrue(high.warnings.stream().anyMatch(w -> w.contains("average high")),
            () -> "expected an overshoot warning, got " + high.warnings);
    }

    @Test
    @DisplayName("a consistent spec reproduces its own mean")
    void fittedTailReproducesTheMean() {
        // The reason the tail is fitted at all: without it the top 5% carries so much weight that
        // the modelled mean comes out two to three times the measured one.
        PushVolume v = q17ProgramEncounters();
        assertTrue(v.warnings.isEmpty(), () -> v.warnings.toString());

        double sum = 0;
        int draws = 200_000;
        for (int i = 0; i < draws; i++) {
            sum += v.quantile((i + 0.5) / draws);
        }
        double modelled = sum / draws;
        assertEquals(v.mean, modelled, v.mean * 0.05,
            "conditional mean should land within 5% of the measured one");
    }

    @Test
    @DisplayName("quantiles stay inside the stated bounds and are non-decreasing")
    void quantilesAreMonotonicAndBounded() {
        PushVolume v = q17ProgramEncounters();
        int previous = 0;
        for (int i = 0; i <= 1000; i++) {
            int q = v.quantile(i / 1000.0);
            assertTrue(q >= v.min, "quantile " + q + " below min " + v.min);
            assertTrue(q <= v.max, "quantile " + q + " above max " + v.max);
            assertTrue(q >= previous, "quantile went backwards at u=" + (i / 1000.0));
            previous = q;
        }
        assertEquals(v.p50, v.quantile(0.5), 1.0, "median should land on p50");
        assertEquals(v.p95, v.quantile(0.95), 1.0, "95th should land on p95");
    }

    @Test
    @DisplayName("probability nought never pushes, and perSync accounts for the syncs that do not")
    void probabilityGovernsWhetherAnythingIsPushed() {
        PushVolume never = new PushVolume("Encounter", 0.0, 1, 13, 479, 4.0);
        for (int i = 0; i < 1000; i++) {
            assertEquals(0, never.draw());
        }
        PushVolume v = q17ProgramEncounters();
        assertEquals(v.probability * v.mean, v.perSync(), 1e-9,
            "records per sync averages over the syncs that push nothing");
    }

    @Test
    @DisplayName("an override round-trips in both accepted forms, and a malformed one is rejected")
    void parseHandlesBothFormsAndRejectsTheRest() {
        PushVolume fallback = q17ProgramEncounters();

        PushVolume five = PushVolume.parse("ProgramEncounter", "0.5:8:20:150:24", fallback);
        assertEquals(0.5, five.probability, 1e-9);
        assertEquals(1, five.min, "the five-field form leaves the floor at one");
        assertEquals(8, five.p50);

        PushVolume six = PushVolume.parse("ProgramEncounter", "0.5:8:20:45:150:24", fallback);
        assertEquals(8, six.min, "the six-field form sets the floor");
        assertEquals(20, six.p50);

        assertSame(fallback, PushVolume.parse("ProgramEncounter", null, fallback));
        assertSame(fallback, PushVolume.parse("ProgramEncounter", "", fallback));
        assertThrows(IllegalArgumentException.class,
            () -> PushVolume.parse("ProgramEncounter", "0.5:8:20", fallback));
    }
}
