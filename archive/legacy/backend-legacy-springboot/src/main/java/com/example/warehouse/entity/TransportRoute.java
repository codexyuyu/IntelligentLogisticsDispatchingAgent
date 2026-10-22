package com.example.warehouse.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class TransportRoute {
    private Long id;
    private String routeCode;
    private String startNode;
    private String endNode;
    private BigDecimal distanceKm;
    private Integer estimatedMinutes;
    private String roadStatus;
    private BigDecimal roadFactor;
    private BigDecimal tollCost;
    private Boolean refrigeratedRequired;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getRouteCode() { return routeCode; }
    public void setRouteCode(String routeCode) { this.routeCode = routeCode; }
    public String getStartNode() { return startNode; }
    public void setStartNode(String startNode) { this.startNode = startNode; }
    public String getEndNode() { return endNode; }
    public void setEndNode(String endNode) { this.endNode = endNode; }
    public BigDecimal getDistanceKm() { return distanceKm; }
    public void setDistanceKm(BigDecimal distanceKm) { this.distanceKm = distanceKm; }
    public Integer getEstimatedMinutes() { return estimatedMinutes; }
    public void setEstimatedMinutes(Integer estimatedMinutes) { this.estimatedMinutes = estimatedMinutes; }
    public String getRoadStatus() { return roadStatus; }
    public void setRoadStatus(String roadStatus) { this.roadStatus = roadStatus; }
    public BigDecimal getRoadFactor() { return roadFactor; }
    public void setRoadFactor(BigDecimal roadFactor) { this.roadFactor = roadFactor; }
    public BigDecimal getTollCost() { return tollCost; }
    public void setTollCost(BigDecimal tollCost) { this.tollCost = tollCost; }
    public Boolean getRefrigeratedRequired() { return refrigeratedRequired; }
    public void setRefrigeratedRequired(Boolean refrigeratedRequired) { this.refrigeratedRequired = refrigeratedRequired; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
