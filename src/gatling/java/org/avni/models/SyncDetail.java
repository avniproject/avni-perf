package org.avni.models;

public class SyncDetail {
    public String uuid;
    public String entityName;
    public String loadedSince;
    public String entityTypeUuid;
    public boolean approvalStatusType;
    public boolean encounterOrEnrolmentType;

    public SyncDetail(String uuid, String entityName, String loadedSince, String entityTypeUuid, boolean approvalStatusType, boolean encounterOrEnrolmentType) {
        this.uuid = uuid;
        this.entityName = entityName;
        this.loadedSince = loadedSince;
        this.entityTypeUuid = entityTypeUuid;
        this.approvalStatusType = approvalStatusType;
        this.encounterOrEnrolmentType = encounterOrEnrolmentType;
    }

    public SyncDetail() {

    }

}
