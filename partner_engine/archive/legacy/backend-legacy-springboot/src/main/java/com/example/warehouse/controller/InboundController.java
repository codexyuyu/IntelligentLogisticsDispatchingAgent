package com.example.warehouse.controller;

import com.example.warehouse.dto.InboundRequest;
import com.example.warehouse.service.InboundService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/inbound")
public class InboundController {
    private final InboundService inboundService;

    public InboundController(InboundService inboundService) {
        this.inboundService = inboundService;
    }

    @PostMapping("/recommend")
    public Map<String, Object> recommend(@Valid @RequestBody InboundRequest request) {
        return inboundService.recommend(request);
    }

    @PostMapping("/confirm")
    public Map<String, Object> confirm(@Valid @RequestBody InboundRequest request) {
        return inboundService.confirm(request);
    }
}
