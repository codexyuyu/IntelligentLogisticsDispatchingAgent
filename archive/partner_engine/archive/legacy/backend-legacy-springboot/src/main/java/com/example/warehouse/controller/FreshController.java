package com.example.warehouse.controller;

import com.example.warehouse.dto.FreshReceiveRequest;
import com.example.warehouse.entity.FreshBatch;
import com.example.warehouse.service.FreshReceivingService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/fresh")
public class FreshController {
    private final FreshReceivingService freshReceivingService;

    public FreshController(FreshReceivingService freshReceivingService) {
        this.freshReceivingService = freshReceivingService;
    }

    @PostMapping("/receive/confirm")
    public Map<String, Object> confirmReceive(@RequestBody FreshReceiveRequest request) {
        return freshReceivingService.confirmReceive(request);
    }

    @GetMapping("/batches")
    public List<FreshBatch> batches() {
        return freshReceivingService.listBatches();
    }

    @GetMapping("/batches/risk")
    public List<FreshBatch> riskBatches() {
        return freshReceivingService.listRiskBatches();
    }
}
