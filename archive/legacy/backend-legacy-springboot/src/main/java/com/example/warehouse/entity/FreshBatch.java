package com.example.warehouse.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class FreshBatch {
    private Long id;
    private String batchCode;
    private Long productId;
    private Long shelfId;
    private String supplier;
    private String originPlace;
    private LocalDateTime receiveTime;
    private Integer quantityInitial;
    private Integer quantityRemaining;
    private BigDecimal purchasePrice;
    private String qualityGrade;
    private BigDecimal initialQualityScore;
    private BigDecimal storageTemperature;
    private BigDecimal storageHumidity;
    private BigDecimal predictedStorageDays;
    private BigDecimal remainingDays;
    private BigDecimal freshnessScore;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private String productName;
    private String productCode;
    private String shelfCode;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getBatchCode() { return batchCode; }
    public void setBatchCode(String batchCode) { this.batchCode = batchCode; }
    public Long getProductId() { return productId; }
    public void setProductId(Long productId) { this.productId = productId; }
    public Long getShelfId() { return shelfId; }
    public void setShelfId(Long shelfId) { this.shelfId = shelfId; }
    public String getSupplier() { return supplier; }
    public void setSupplier(String supplier) { this.supplier = supplier; }
    public String getOriginPlace() { return originPlace; }
    public void setOriginPlace(String originPlace) { this.originPlace = originPlace; }
    public LocalDateTime getReceiveTime() { return receiveTime; }
    public void setReceiveTime(LocalDateTime receiveTime) { this.receiveTime = receiveTime; }
    public Integer getQuantityInitial() { return quantityInitial; }
    public void setQuantityInitial(Integer quantityInitial) { this.quantityInitial = quantityInitial; }
    public Integer getQuantityRemaining() { return quantityRemaining; }
    public void setQuantityRemaining(Integer quantityRemaining) { this.quantityRemaining = quantityRemaining; }
    public BigDecimal getPurchasePrice() { return purchasePrice; }
    public void setPurchasePrice(BigDecimal purchasePrice) { this.purchasePrice = purchasePrice; }
    public String getQualityGrade() { return qualityGrade; }
    public void setQualityGrade(String qualityGrade) { this.qualityGrade = qualityGrade; }
    public BigDecimal getInitialQualityScore() { return initialQualityScore; }
    public void setInitialQualityScore(BigDecimal initialQualityScore) { this.initialQualityScore = initialQualityScore; }
    public BigDecimal getStorageTemperature() { return storageTemperature; }
    public void setStorageTemperature(BigDecimal storageTemperature) { this.storageTemperature = storageTemperature; }
    public BigDecimal getStorageHumidity() { return storageHumidity; }
    public void setStorageHumidity(BigDecimal storageHumidity) { this.storageHumidity = storageHumidity; }
    public BigDecimal getPredictedStorageDays() { return predictedStorageDays; }
    public void setPredictedStorageDays(BigDecimal predictedStorageDays) { this.predictedStorageDays = predictedStorageDays; }
    public BigDecimal getRemainingDays() { return remainingDays; }
    public void setRemainingDays(BigDecimal remainingDays) { this.remainingDays = remainingDays; }
    public BigDecimal getFreshnessScore() { return freshnessScore; }
    public void setFreshnessScore(BigDecimal freshnessScore) { this.freshnessScore = freshnessScore; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    public String getProductName() { return productName; }
    public void setProductName(String productName) { this.productName = productName; }
    public String getProductCode() { return productCode; }
    public void setProductCode(String productCode) { this.productCode = productCode; }
    public String getShelfCode() { return shelfCode; }
    public void setShelfCode(String shelfCode) { this.shelfCode = shelfCode; }
}
