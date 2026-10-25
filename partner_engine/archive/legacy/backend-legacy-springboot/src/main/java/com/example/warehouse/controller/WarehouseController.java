package com.example.warehouse.controller;

import com.example.warehouse.dto.WarehouseStorageTypeRequest;
import com.example.warehouse.service.WarehouseService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/warehouse")
public class WarehouseController {
    private final WarehouseService warehouseService;

    public WarehouseController(WarehouseService warehouseService) {
        this.warehouseService = warehouseService;
    }

    @GetMapping("/twin")
    public Map<String, Object> twin() {
        return warehouseService.getTwinData();
    }

    @PatchMapping("/{warehouseId}/storage-type")
    public Map<String, Object> updateStorageType(@PathVariable Long warehouseId,
                                                  @Valid @RequestBody WarehouseStorageTypeRequest request) {
        return Map.of("warehouse", warehouseService.updateStorageType(warehouseId, request.getStorageType(), request.getOperatorUserId()));
    }

    @GetMapping("/shelves/{shelfId}")
    public Map<String, Object> shelfDetail(@PathVariable Long shelfId) {
        return warehouseService.getShelfDetail(shelfId);
    }
}
