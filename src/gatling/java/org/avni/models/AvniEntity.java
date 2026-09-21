package org.avni.models;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.util.List;
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

    /**
     * Query parameters carrying the sync detail's entityTypeUuid. The client sets privilegeParam and
     * apiQueryParamKey to the same value where both are declared, so this can hold more than one.
     * Empty when the entity is not split by type.
     */
    public List<String> entityTypeUuidParams;

    /**
     * Path the client POSTs this entity to, for tx entities. Null for reference entities, which are
     * never pushed.
     *
     * Not derivable from `path` above: postAllEntities drops the apiVersion segment and pluralises
     * the resource name at the call site, so UserInfo pulls from v2/me and pushes to me. Some of the
     * results look wrong - News posts to /newss - but that is what the client sends, and the
     * simulation's job is to send the same thing.
     */
    public String pushPath;

    /** Query params the client always sends for this entity. A null value means the simulation supplies it. */
    public Map<String, String> staticParams;

    /** The client's own relative weight for this entity. Not a measured cost - see the plan, D6.2. */
    public Integer syncWeight;

    /**
     * What a record of this entity costs the client to parse and persist, as a multiple of
     * BASE_MS_PER_RECORD. Assigned by tier in the generator, so a new entity arrives with a weight
     * rather than silently defaulting to one.
     *
     * Deliberately not syncWeight above. That is a progress-bar increment, is a per-entity total
     * rather than a per-record cost, and has never been checked against a clock.
     */
    public double storageWeight = 1.0;

    public boolean pullRequired = true;
    public boolean pushRequired = true;

    public AvniEntity() {
    }
}
