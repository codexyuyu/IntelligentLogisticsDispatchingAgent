package com.example.warehouse.dto;

import java.math.BigDecimal;

public class FreshReceiveRequest {
    private Long productId;
    private Integer quantity;
    private Long shelfId;
    private String supplier;
    private String originPlace;
    private BigDecimal purchasePrice;
    private String qualityGrade;
    private BigDecimal initialQualityScore;
    private BigDecimal storageTemperature;
    private BigDecimal storageHumidity;

    public Long getProductId() { return productId; }
    public void setProductId(Long productId) { this.productId = productId; }
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }
    public Long getShelfId() { return shelfId; }
    public void setShelfId(Long shelfId) { this.shelfId = shelfId; }
    public String getSupplier() { return supplier; }
    public void setSupplier(String supplier) { this.supplier = supplier; }
    public String getOriginPlace() { return originPlace; }
    public void setOriginPlace(String originPlace) { this.originPlace = originPlace; }
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
}
