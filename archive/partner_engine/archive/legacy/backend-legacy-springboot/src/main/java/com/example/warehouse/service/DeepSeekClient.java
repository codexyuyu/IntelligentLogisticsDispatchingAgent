package com.example.warehouse.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

@Service
public class DeepSeekClient {
    private final boolean enabled;
    private final String apiKey;
    private final String model;
    private final RestClient restClient;

    public DeepSeekClient(
            @Value("${app.deepseek.enabled}") boolean enabled,
            @Value("${app.deepseek.api-key}") String apiKey,
            @Value("${app.deepseek.base-url}") String baseUrl,
            @Value("${app.deepseek.model}") String model) {
        this.enabled = enabled;
        this.apiKey = apiKey;
        this.model = model;
        this.restClient = RestClient.builder().baseUrl(baseUrl).build();
    }

    @SuppressWarnings("unchecked")
    public String chat(String systemPrompt, String userQuestion) {
        if (!enabled || apiKey == null || apiKey.isBlank()) {
            return null;
        }
        try {
            Map<String, Object> body = Map.of(
                    "model", model,
                    "messages", List.of(
                            Map.of("role", "system", "content", systemPrompt),
                            Map.of("role", "user", "content", userQuestion)
                    ),
                    "temperature", 0.2
            );
            Map<String, Object> response = restClient.post()
                    .uri("/chat/completions")
                    .contentType(MediaType.APPLICATION_JSON)
                    .header("Authorization", "Bearer " + apiKey)
                    .body(body)
                    .retrieve()
                    .body(Map.class);
            if (response == null) return null;
            List<Map<String, Object>> choices = (List<Map<String, Object>>) response.get("choices");
            if (choices == null || choices.isEmpty()) return null;
            Map<String, Object> message = (Map<String, Object>) choices.get(0).get("message");
            return message == null ? null : String.valueOf(message.get("content"));
        } catch (Exception ex) {
            return "DeepSeek API 调用失败，已自动切换到本地规则版。失败原因：" + ex.getMessage();
        }
    }
}
