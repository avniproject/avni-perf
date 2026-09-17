package org.avni.models;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.util.Map;

/**
 * One syncable entity, generated from the client's own EntityMetaData.
 * See tools/entity-metadata - do not hand-edit the generated table.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AvniEntity {
    public String entityName;
    public String type;

    /** Path relative to the server root, exactly as the client builds it. No leading slash. */
    public String path;

    /** Query parameter carrying the sync detail's entityTypeUuid, or null if this entity is not split by type. */
    public String entityTypeUuidParam;

    /** Query params the client always sends for this entity. A null value means the simulation supplies it. */
    public Map<String, String> staticParams;

    /** The client's own relative weight for this entity. Not a measured cost - see the plan, D6.2. */
    public Integer syncWeight;

    public boolean pullRequired = true;
    public boolean pushRequired = true;

    public AvniEntity() {
    }
}
