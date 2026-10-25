package com.example.warehouse.entity;

import java.math.BigDecimal;

public class Shelf {
    private Long id;
    private Long warehouseId;
    private String code;
    private String category;
    private Integer x;
    private Integer y;
    private Integer layers;
    private Integer capacity;
    private Integer used;
    private String status;
    private String storageType;
    private BigDecimal currentTemperature;
    private BigDecimal currentHumidity;

    public Integer getFree() {
        if (capacity == null || used == null) {
            return 0;
        }
        return capacity - used;
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getWarehouseId() { return warehouseId; }
    public void setWarehouseId(Long warehouseId) { this.warehouseId = warehouseId; }
    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }
    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }
    public Integer getX() { return x == null ? 0 : x; }
    public void setX(Integer x) { this.x = x; }
    public Integer getY() { return y == null ? 0 : y; }
    public void setY(Integer y) { this.y = y; }
    public Integer getLayers() { return layers == null ? 1 : layers; }
    public void setLayers(Integer layers) { this.layers = layers; }
    public Integer getCapacity() { return capacity; }
    public void setCapacity(Integer capacity) { this.capacity = capacity; }
    public Integer getUsed() { return used; }
    public void setUsed(Integer used) { this.used = used; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getStorageType() { return storageType; }
    public void setStorageType(String storageType) { this.storageType = storageType; }
    public BigDecimal getCurrentTemperature() { return currentTemperature; }
    public void setCurrentTemperature(BigDecimal currentTemperature) { this.currentTemperature = currentTemperature; }
    public BigDecimal getCurrentHumidity() { return currentHumidity; }
    public void setCurrentHumidity(BigDecimal currentHumidity) { this.currentHumidity = currentHumidity; }
}
