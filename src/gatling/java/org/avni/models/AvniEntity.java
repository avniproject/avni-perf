package org.avni.models;

public class AvniEntity {
    public String entityName;
    public String resourcePath;
    public String type;

    public AvniEntity() {
    }

    public AvniEntity(String entityName, String resourcePath, String type) {
        this.entityName = entityName;
        this.resourcePath = resourcePath;
        this.type = type;
    }
}
