package com.example.warehouse.controller;

import com.example.warehouse.dto.OutboundRequest;
import com.example.warehouse.service.OutboundService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/outbound")
public class OutboundController {
    private final OutboundService outboundService;

    public OutboundController(OutboundService outboundService) {
        this.outboundService = outboundService;
    }

    @PostMapping("/orders")
    public Map<String, Object> createOrder(@Valid @RequestBody OutboundRequest request) {
        return outboundService.createOrder(request);
    }

    @PostMapping("/orders/{orderId}/finish")
    public Map<String, Object> finish(@PathVariable Long orderId) {
        return outboundService.finishOrder(orderId);
    }
}
