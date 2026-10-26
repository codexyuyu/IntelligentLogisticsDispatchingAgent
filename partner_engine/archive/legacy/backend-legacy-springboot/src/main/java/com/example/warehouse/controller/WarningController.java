package com.example.warehouse.controller;

import com.example.warehouse.entity.WarningRecord;
import com.example.warehouse.service.WarningService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/warnings")
public class WarningController {
    private final WarningService warningService;

    public WarningController(WarningService warningService) {
        this.warningService = warningService;
    }

    @GetMapping
    public List<WarningRecord> list() {
        return warningService.listWarnings();
    }

    @PostMapping("/scan")
    public Map<String, Object> scan() {
        warningService.scanLowStockWarnings();
        return Map.of("message", "预警扫描完成");
    }

    @PostMapping("/{id}/confirm")
    public Map<String, Object> confirm(@PathVariable Long id) {
        return warningService.confirmWarning(id);
    }
}
