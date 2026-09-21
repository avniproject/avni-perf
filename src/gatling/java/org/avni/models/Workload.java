package org.avni.models;

import java.util.Map;

/**
 * One population of devices, and what a sync costs for them.
 *
 * E7 is why this exists. Case 7 runs the customer's tenants and production's other organisations
 * against the same server at the same time, and they are not the same workload: the customer
 * pushes twenty encounters a sync and queues a photograph for half of them, while a production
 * co-tenant pushes nine records across a third of its syncs and almost never touches media. A
 * single global setting could describe one or the other, not both at once, which is precisely the
 * scenario the hosting decision turns on.
 *
 * It also fixes a reporting problem that would otherwise invalidate the result. Every request is
 * named with this prefix, so the customer's percentiles stay separable from the co-tenants'. Case
 * 7 asks what the customer's sync experience is *while* the platform is busy - pooling both
 * populations into one distribution answers a question nobody asked, and would flatter or damn the
 * result depending only on the mix.
 */
public class Workload {
    /** Prefixes every request name, so the report separates the two populations. */
    public final String name;
    /** The user file this population is fed from. */
    public final String feederFile;
    /** Per-entity push volumes - see PushProfiles. */
    public final Map<String, PushVolume> volumes;
    /** Media files each encounter queues, which differs sharply between the two. */
    public final double mediaPerEncounter;

    public Workload(String name, String feederFile, Map<String, PushVolume> volumes,
                    double mediaPerEncounter) {
        this.name = name;
        this.feederFile = feederFile;
        this.volumes = volumes;
        this.mediaPerEncounter = mediaPerEncounter;
    }

    /** Request name for this population. Empty prefix when only one workload is running. */
    public String request(String label) {
        return name.isEmpty() ? label : name + " · " + label;
    }

    public double recordsPerSync() {
        return volumes.values().stream().mapToDouble(PushVolume::perSync).sum();
    }

    /** Encounter-bearing records per sync, which is what media volume scales with. */
    public double encountersPerSync() {
        double n = 0;
        for (Map.Entry<String, PushVolume> e : volumes.entrySet()) {
            if (e.getKey().equals("ProgramEncounter") || e.getKey().equals("Encounter")) {
                n += e.getValue().perSync();
            }
        }
        return n;
    }
}
