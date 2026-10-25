package com.example.warehouse.entity;

import java.time.LocalDateTime;

public class InboundTask {
    private Long id;
    private Long productId;
    private Integer quantity;
    private Long recommendedShelfId;
    private String status;
    private LocalDateTime createdAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getProductId() { return productId; }
    public void setProductId(Long productId) { this.productId = productId; }
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }
    public Long getRecommendedShelfId() { return recommendedShelfId; }
    public void setRecommendedShelfId(Long recommendedShelfId) { this.recommendedShelfId = recommendedShelfId; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
