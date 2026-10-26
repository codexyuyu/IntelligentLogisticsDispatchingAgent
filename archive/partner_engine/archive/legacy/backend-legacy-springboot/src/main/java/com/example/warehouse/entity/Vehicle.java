package com.example.warehouse.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class Vehicle {
    private Long id;
    private String vehicleCode;
    private String vehicleType;
    private BigDecimal capacity;
    private BigDecimal volume;
    private Boolean refrigerated;
    private BigDecimal minTemperature;
    private BigDecimal maxTemperature;
    private String currentLocation;
    private LocalDateTime availableFrom;
    private String status;
    private BigDecimal costPerKm;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getVehicleCode() { return vehicleCode; }
    public void setVehicleCode(String vehicleCode) { this.vehicleCode = vehicleCode; }
    public String getVehicleType() { return vehicleType; }
    public void setVehicleType(String vehicleType) { this.vehicleType = vehicleType; }
    public BigDecimal getCapacity() { return capacity; }
    public void setCapacity(BigDecimal capacity) { this.capacity = capacity; }
    public BigDecimal getVolume() { return volume; }
    public void setVolume(BigDecimal volume) { this.volume = volume; }
    public Boolean getRefrigerated() { return refrigerated; }
    public void setRefrigerated(Boolean refrigerated) { this.refrigerated = refrigerated; }
    public BigDecimal getMinTemperature() { return minTemperature; }
    public void setMinTemperature(BigDecimal minTemperature) { this.minTemperature = minTemperature; }
    public BigDecimal getMaxTemperature() { return maxTemperature; }
    public void setMaxTemperature(BigDecimal maxTemperature) { this.maxTemperature = maxTemperature; }
    public String getCurrentLocation() { return currentLocation; }
    public void setCurrentLocation(String currentLocation) { this.currentLocation = currentLocation; }
    public LocalDateTime getAvailableFrom() { return availableFrom; }
    public void setAvailableFrom(LocalDateTime availableFrom) { this.availableFrom = availableFrom; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public BigDecimal getCostPerKm() { return costPerKm; }
    public void setCostPerKm(BigDecimal costPerKm) { this.costPerKm = costPerKm; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
