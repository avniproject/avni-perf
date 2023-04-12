package org.avni.models;

public class SyncDetail {
    public String uuid;
    public String entityName;
    public String loadedSince;
    public String entityTypeUuid;
    public boolean approvalStatusType;

    public SyncDetail(String uuid, String entityName, String loadedSince, String entityTypeUuid, boolean approvalStatusType) {
        this.uuid = uuid;
        this.entityName = entityName;
        this.loadedSince = loadedSince;
        this.entityTypeUuid = entityTypeUuid;
        this.approvalStatusType = approvalStatusType;
    }

    public SyncDetail() {

    }

}
