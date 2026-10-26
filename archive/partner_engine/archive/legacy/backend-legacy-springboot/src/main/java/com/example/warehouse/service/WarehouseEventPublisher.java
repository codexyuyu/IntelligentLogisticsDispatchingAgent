package com.example.warehouse.service;

import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;

@Service
public class WarehouseEventPublisher {
    private final SimpMessagingTemplate template;

    public WarehouseEventPublisher(SimpMessagingTemplate template) {
        this.template = template;
    }

    public void publish(String eventType) {
        template.convertAndSend("/topic/warehouse", Map.of(
                "eventType", eventType,
                "time", LocalDateTime.now().toString()
        ));
    }
}
