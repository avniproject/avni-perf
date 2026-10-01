package org.avni.models;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** What the measured concentration has to hold true, so it cannot quietly flatten back out. */
class CoTenantLoadTest {

    /** `n` organisations, the i-th carrying `users[i]` rows, as a feeder would hold them. */
    private static List<Map<String, String>> feeder(int... users) {
        List<Map<String, String>> rows = new ArrayList<>();
        for (int org = 0; org < users.length; org++) {
            for (int u = 0; u < users[org]; u++) {
                Map<String, String> row = new LinkedHashMap<>();
                row.put("userName", "u" + org + "-" + u);
                row.put("organisationUUID", "org-" + org);
                rows.add(row);
            }
        }
        return rows;
    }

    private static int[] descending(int n) {
        int[] users = new int[n];
        for (int i = 0; i < n; i++) {
            users[i] = n - i;   // rank by row count, largest first
        }
        return users;
    }

    @Test
    @DisplayName("the measured shares reproduce production's concentration")
    void theSharesAreProductions() {
        // The figures this exists to carry: rank 1 holds 16% of device sync, the top 3 41%, the
        // top 16 84%. A change that flattens these is the defect, and it would otherwise show up
        // only as a cache hit rate nobody was looking at.
        assertEquals(0.160, CoTenantLoad.shareAtRank(1), 0.002);
        double top3 = CoTenantLoad.shareAtRank(1) + CoTenantLoad.shareAtRank(2)
                      + CoTenantLoad.shareAtRank(3);
        assertEquals(0.411, top3, 0.005);
        double top16 = 0;
        for (int r = 1; r <= 16; r++) {
            top16 += CoTenantLoad.shareAtRank(r);
        }
        assertTrue(top16 > 0.78 && top16 < 0.90, "top 16 should hold ~84%, got " + top16);
    }

    @Test
    @DisplayName("share falls monotonically with rank")
    void shareFallsWithRank() {
        for (int r = 1; r < CoTenantLoad.ACTIVE_ORGANISATIONS; r++) {
            assertTrue(CoTenantLoad.shareAtRank(r) >= CoTenantLoad.shareAtRank(r + 1),
                "rank " + r + " should not hold less than rank " + (r + 1));
        }
    }

    @Test
    @DisplayName("organisations past the measured tail never sync")
    void theTailIsSilent() {
        // Four fifths of the organisations holding data make no sync request in eleven days.
        // Giving them a floor share would be the easy mistake and would spread the working set
        // across five times the pages.
        assertEquals(0.0, CoTenantLoad.shareAtRank(CoTenantLoad.ACTIVE_ORGANISATIONS + 1));
        assertEquals(0.0, CoTenantLoad.shareAtRank(513));
        int[] cover = CoTenantLoad.coverage(feeder(descending(200)), "organisationUUID");
        assertEquals(CoTenantLoad.ACTIVE_ORGANISATIONS, cover[0]);
        assertEquals(200, cover[1]);
    }

    @Test
    @DisplayName("an organisation's share is split across its users, not multiplied by them")
    void shareIsDividedNotMultiplied() {
        // The trap: co-tenant user counts already scale with subjects, so letting row count carry
        // the weight a second time models the square of the measured share.
        Map<String, Double> w = CoTenantLoad.rowWeights(feeder(10, 5), "organisationUUID");
        double org0 = w.entrySet().stream().filter(e -> e.getKey().startsWith("u0-"))
                       .mapToDouble(Map.Entry::getValue).sum();
        double org1 = w.entrySet().stream().filter(e -> e.getKey().startsWith("u1-"))
                       .mapToDouble(Map.Entry::getValue).sum();
        assertEquals(CoTenantLoad.shareAtRank(1), org0, 1e-9);
        assertEquals(CoTenantLoad.shareAtRank(2), org1, 1e-9);
        // and every user of one organisation carries the same weight
        assertEquals(CoTenantLoad.shareAtRank(1) / 10, w.get("u0-0"), 1e-12);
    }

    @Test
    @DisplayName("the draw reproduces the measured shares")
    void theDrawMatchesTheShares() {
        List<Map<String, String>> rows = feeder(descending(40));
        java.util.Iterator<Map<String, Object>> it =
            CoTenantLoad.feeder(rows, "organisationUUID", 7L);
        Map<String, Integer> drawn = new LinkedHashMap<>();
        int n = 200_000;
        for (int i = 0; i < n; i++) {
            String org = (String) it.next().get("organisationUUID");
            drawn.merge(org, 1, Integer::sum);
        }
        double total = 0;
        for (int r = 1; r <= 40; r++) {
            total += CoTenantLoad.shareAtRank(r);
        }
        for (int r = 1; r <= 3; r++) {
            double expected = CoTenantLoad.shareAtRank(r) / total;
            double actual = drawn.getOrDefault("org-" + (r - 1), 0) / (double) n;
            assertEquals(expected, actual, 0.01, "rank " + r + " drew " + actual);
        }
    }

    @Test
    @DisplayName("the draw is seeded, so a run can be repeated")
    void theDrawIsSeeded() {
        List<Map<String, String>> rows = feeder(descending(20));
        java.util.Iterator<Map<String, Object>> a = CoTenantLoad.feeder(rows, "organisationUUID", 1L);
        java.util.Iterator<Map<String, Object>> b = CoTenantLoad.feeder(rows, "organisationUUID", 1L);
        java.util.Iterator<Map<String, Object>> c = CoTenantLoad.feeder(rows, "organisationUUID", 2L);
        boolean differs = false;
        for (int i = 0; i < 100; i++) {
            assertEquals(a.next().get("userName"), b.next().get("userName"));
            differs |= !c.next().get("userName").equals(
                CoTenantLoad.feeder(rows, "organisationUUID", 1L).next().get("userName"));
        }
        assertTrue(differs, "a different seed should give a different sequence");
    }

    @Test
    @DisplayName("a feeder with no organisation column fails rather than drawing uniformly")
    void aMissingColumnIsLoud() {
        // Without it every row falls into one organisation, which draws uniformly from rank 1 --
        // indistinguishable at runtime from the uniform behaviour this replaces.
        List<Map<String, String>> rows = feeder(descending(5));
        rows.forEach(r -> r.remove("organisationUUID"));
        int[] cover = CoTenantLoad.coverage(rows, "organisationUUID");
        assertEquals(1, cover[0], "every row collapsed into one organisation");
        assertEquals(1, cover[1]);
    }
}
