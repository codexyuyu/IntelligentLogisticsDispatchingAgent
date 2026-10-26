package com.example.warehouse.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class Product {
    private Long id;
    private String productCode;
    private String productName;
    private String category;
    private String unit;
    private Integer safetyStock;
    private LocalDateTime createTime;

    private String storageType;
    private BigDecimal minTemperature;
    private BigDecimal maxTemperature;
    private BigDecimal minHumidity;
    private BigDecimal maxHumidity;
    private Integer baseShelfLifeDays;
    private Integer perishable;

    public Long getId() {
        return id;
    }

    public String getProductCode() {
        return productCode;
    }

    public String getProductName() {
        return productName;
    }

    public String getCategory() {
        return category;
    }

    public String getUnit() {
        return unit;
    }

    public Integer getSafetyStock() {
        return safetyStock;
    }

    public LocalDateTime getCreateTime() {
        return createTime;
    }

    public String getStorageType() {
        return storageType;
    }

    public BigDecimal getMinTemperature() {
        return minTemperature;
    }

    public BigDecimal getMaxTemperature() {
        return maxTemperature;
    }

    public BigDecimal getMinHumidity() {
        return minHumidity;
    }

    public BigDecimal getMaxHumidity() {
        return maxHumidity;
    }

    public Integer getBaseShelfLifeDays() {
        return baseShelfLifeDays;
    }

    public Integer getPerishable() {
        return perishable;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public void setProductCode(String productCode) {
        this.productCode = productCode;
    }

    public void setProductName(String productName) {
        this.productName = productName;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public void setUnit(String unit) {
        this.unit = unit;
    }

    public void setSafetyStock(Integer safetyStock) {
        this.safetyStock = safetyStock;
    }

    public void setCreateTime(LocalDateTime createTime) {
        this.createTime = createTime;
    }

    public void setStorageType(String storageType) {
        this.storageType = storageType;
    }

    public void setMinTemperature(BigDecimal minTemperature) {
        this.minTemperature = minTemperature;
    }

    public void setMaxTemperature(BigDecimal maxTemperature) {
        this.maxTemperature = maxTemperature;
    }

    public void setMinHumidity(BigDecimal minHumidity) {
        this.minHumidity = minHumidity;
    }

    public void setMaxHumidity(BigDecimal maxHumidity) {
        this.maxHumidity = maxHumidity;
    }

    public void setBaseShelfLifeDays(Integer baseShelfLifeDays) {
        this.baseShelfLifeDays = baseShelfLifeDays;
    }

    public void setPerishable(Integer perishable) {
        this.perishable = perishable;
    }

    // 兼容旧代码，暂时保留
    public String getSku() {
        return productCode;
    }

    public String getName() {
        return productName;
    }

    public Integer getSafeStock() {
        return safetyStock;
    }

    public Integer getTurnoverScore() {
        return 80;
    }
}
