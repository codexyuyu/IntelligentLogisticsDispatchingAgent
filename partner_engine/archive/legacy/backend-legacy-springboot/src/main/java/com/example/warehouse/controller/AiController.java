package com.example.warehouse.controller;

import com.example.warehouse.dto.AiChatRequest;
import com.example.warehouse.service.AiAgentService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/ai")
public class AiController {
    private final AiAgentService aiAgentService;

    public AiController(AiAgentService aiAgentService) {
        this.aiAgentService = aiAgentService;
    }

    @PostMapping("/chat")
    public Map<String, Object> chat(@Valid @RequestBody AiChatRequest request) {
        return aiAgentService.chat(request.getQuestion());
    }
}
