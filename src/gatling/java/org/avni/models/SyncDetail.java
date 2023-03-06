package org.avni.models;

public class SyncDetail {
    public String uuid;
    public String entityName;
    public String loadedSince;
    public String entityTypeUuid;

    public SyncDetail(String uuid, String entityName, String loadedSince, String entityTypeUuid) {
        this.uuid = uuid;
        this.entityName = entityName;
        this.loadedSince = loadedSince;
        this.entityTypeUuid = entityTypeUuid;
    }

    public SyncDetail() {

    }

}
