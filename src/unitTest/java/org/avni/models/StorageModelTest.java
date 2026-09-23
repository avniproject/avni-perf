package org.avni.models;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * The bounds on a page's modelled client cost, and the relationship between the two coefficients
 * that decides whether the ceiling ever has to bind.
 */
class StorageModelTest {

    private static final double MS_PER_PAGE = 174;
    private static final double MS_PER_RECORD = 0.60;
    private static final double MAX = 2000;

    private static long page(int records, double weight) {
        return StorageModel.pauseMillis(MS_PER_PAGE, records, weight, MS_PER_RECORD, MAX);
    }

    @Test
    @DisplayName("the per-page term is a floor, not a maximum")
    void perPageIsAFloor() {
        // The easy misreading. It is added to every page whatever its size.
        assertEquals(174L, page(0, 1.0));
        assertEquals(174L, page(0, 3.0));
        assertTrue(page(100, 1.0) > 174, "records must add on top of the fixed term");
    }

    @Test
    @DisplayName("the heaviest page a device can pull stays under the ceiling")
    void theDefaultsDoNotRelyOnTheCap() {
        // The cap is a guard, not the mechanism. If the defaults ever need clipping, the pause
        // stops tracking page size and D6's whole purpose is lost.
        long heaviest = page(1000, 3.0);
        assertTrue(heaviest < MAX,
            "heaviest page should land under the ceiling, not on it; got " + heaviest);
        assertEquals(1974L, heaviest);
    }

    @Test
    @DisplayName("a full page across the three tiers is seconds, not half a minute")
    void fullPagesAcrossTheTiers() {
        assertEquals(294L, page(1000, 0.2));
        assertEquals(774L, page(1000, 1.0));
        assertEquals(1974L, page(1000, 3.0));
    }

    @Test
    @DisplayName("the ceiling bounds a per-record cost that would otherwise run away")
    void theCeilingBinds() {
        // Q1's raw 9.19 modelled 27.7s for a heavy page - 27.7 ms to write one row, and twice a
        // whole median sync in a single page. That is what the cap exists to stop.
        assertEquals(2000L, StorageModel.pauseMillis(174, 1000, 3.0, 9.19, MAX));
        // And it binds far below a full page, which is why a cap is a poor primary mechanism:
        // above about 66 records the pause stops changing at all.
        assertEquals(2000L, StorageModel.pauseMillis(174, 100, 3.0, 9.19, MAX));
    }

    @Test
    @DisplayName("a negative pause is impossible")
    void negativesClampToZero() {
        // Reachable by netting the server's median response out of msPerPage, which the model's
        // own comments recommend, on a page that returned nothing.
        assertEquals(0L, StorageModel.clamp(-50, MAX));
        assertEquals(0L, StorageModel.pauseMillis(-200, 0, 1.0, MS_PER_RECORD, MAX));
    }

    @Test
    @DisplayName("the pause tracks page size, which is the whole point of the model")
    void pauseTracksRecordCount() {
        long previous = -1;
        for (int n = 0; n <= 1000; n += 50) {
            long p = page(n, 1.0);
            assertTrue(p >= previous, "pause must not fall as records rise");
            assertTrue(p < MAX, "no ordinary page should reach the ceiling at the defaults");
            previous = p;
        }
        assertTrue(page(1000, 1.0) > page(100, 1.0) * 2,
            "a tenfold page should cost materially more, not be flattened by the cap");
    }
}
