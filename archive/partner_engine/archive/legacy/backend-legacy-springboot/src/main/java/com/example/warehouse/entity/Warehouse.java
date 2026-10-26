package com.example.warehouse.entity;

import java.time.LocalDateTime;

public class Warehouse {
    private Long id;
    private String warehouseName;
    private Integer cabinetCount;
    private Long warehouseCabinetId;
    private String warehouseStorageType;
    private LocalDateTime warehouseCreatedTime;
    private LocalDateTime warehouseTypeModifiedTime;
    private Integer width;
    private Integer depth;
    private Integer startX;
    private Integer startY;
    private Integer exitX;
    private Integer exitY;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Long getWarehouseId() { return id; }
    public void setWarehouseId(Long warehouseId) { this.id = warehouseId; }

    public String getName() { return warehouseName; }
    public String getWarehouseName() { return warehouseName; }
    public void setWarehouseName(String warehouseName) { this.warehouseName = warehouseName; }

    public Integer getCabinetCount() { return cabinetCount; }
    public void setCabinetCount(Integer cabinetCount) { this.cabinetCount = cabinetCount; }
    public Long getWarehouseCabinetId() { return warehouseCabinetId; }
    public void setWarehouseCabinetId(Long warehouseCabinetId) { this.warehouseCabinetId = warehouseCabinetId; }
    public String getWarehouseStorageType() { return warehouseStorageType; }
    public void setWarehouseStorageType(String warehouseStorageType) { this.warehouseStorageType = warehouseStorageType; }
    public LocalDateTime getWarehouseCreatedTime() { return warehouseCreatedTime; }
    public void setWarehouseCreatedTime(LocalDateTime warehouseCreatedTime) { this.warehouseCreatedTime = warehouseCreatedTime; }
    public LocalDateTime getWarehouseTypeModifiedTime() { return warehouseTypeModifiedTime; }
    public void setWarehouseTypeModifiedTime(LocalDateTime warehouseTypeModifiedTime) { this.warehouseTypeModifiedTime = warehouseTypeModifiedTime; }

    public Integer getWidth() { return width; }
    public void setWidth(Integer width) { this.width = width; }
    public Integer getDepth() { return depth; }
    public void setDepth(Integer depth) { this.depth = depth; }
    public Integer getStartX() { return startX; }
    public void setStartX(Integer startX) { this.startX = startX; }
    public Integer getStartY() { return startY; }
    public void setStartY(Integer startY) { this.startY = startY; }
    public Integer getExitX() { return exitX; }
    public void setExitX(Integer exitX) { this.exitX = exitX; }
    public Integer getExitY() { return exitY; }
    public void setExitY(Integer exitY) { this.exitY = exitY; }
}
