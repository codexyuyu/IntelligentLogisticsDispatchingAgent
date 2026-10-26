package com.example.warehouse.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class PurchaseAdvice {
    private Long id;
    private Long productId;
    private String productName;
    private Integer currentInventory;
    private Integer safetyStock;
    private BigDecimal avgMarketPrice;
    private BigDecimal priceChangeRate;
    private String priceTrend;
    private String adviceType;
    private Integer suggestedQuantity;
    private String reason;
    private LocalDateTime createdAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getProductId() { return productId; }
    public void setProductId(Long productId) { this.productId = productId; }
    public String getProductName() { return productName; }
    public void setProductName(String productName) { this.productName = productName; }
    public Integer getCurrentInventory() { return currentInventory; }
    public void setCurrentInventory(Integer currentInventory) { this.currentInventory = currentInventory; }
    public Integer getSafetyStock() { return safetyStock; }
    public void setSafetyStock(Integer safetyStock) { this.safetyStock = safetyStock; }
    public BigDecimal getAvgMarketPrice() { return avgMarketPrice; }
    public void setAvgMarketPrice(BigDecimal avgMarketPrice) { this.avgMarketPrice = avgMarketPrice; }
    public BigDecimal getPriceChangeRate() { return priceChangeRate; }
    public void setPriceChangeRate(BigDecimal priceChangeRate) { this.priceChangeRate = priceChangeRate; }
    public String getPriceTrend() { return priceTrend; }
    public void setPriceTrend(String priceTrend) { this.priceTrend = priceTrend; }
    public String getAdviceType() { return adviceType; }
    public void setAdviceType(String adviceType) { this.adviceType = adviceType; }
    public Integer getSuggestedQuantity() { return suggestedQuantity; }
    public void setSuggestedQuantity(Integer suggestedQuantity) { this.suggestedQuantity = suggestedQuantity; }
    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
