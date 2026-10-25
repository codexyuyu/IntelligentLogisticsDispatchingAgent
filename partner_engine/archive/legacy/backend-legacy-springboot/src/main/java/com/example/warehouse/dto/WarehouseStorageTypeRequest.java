package com.example.warehouse.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public class WarehouseStorageTypeRequest {
    @NotBlank(message = "仓库存储类型不能为空")
    private String storageType;

    @NotNull(message = "操作用户ID不能为空")
    private Long operatorUserId;

    public String getStorageType() { return storageType; }
    public void setStorageType(String storageType) { this.storageType = storageType; }
    public Long getOperatorUserId() { return operatorUserId; }
    public void setOperatorUserId(Long operatorUserId) { this.operatorUserId = operatorUserId; }
}
