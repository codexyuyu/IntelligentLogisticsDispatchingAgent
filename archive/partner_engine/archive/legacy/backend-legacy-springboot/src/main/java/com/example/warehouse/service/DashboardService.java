package com.example.warehouse.service;

import com.example.warehouse.mapper.InventoryMapper;
import com.example.warehouse.mapper.TaskMapper;
import com.example.warehouse.mapper.WarningMapper;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Service
public class DashboardService {
    private final InventoryMapper inventoryMapper;
    private final WarningMapper warningMapper;
    private final TaskMapper taskMapper;
    private final StringRedisTemplate redisTemplate;

    public DashboardService(InventoryMapper inventoryMapper, WarningMapper warningMapper, TaskMapper taskMapper, StringRedisTemplate redisTemplate) {
        this.inventoryMapper = inventoryMapper;
        this.warningMapper = warningMapper;
        this.taskMapper = taskMapper;
        this.redisTemplate = redisTemplate;
    }

    public Map<String, Object> metrics() {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("totalStock", inventoryMapper.totalStock());
        data.put("lowStockWarnings", warningMapper.countOpenLowStock());
        data.put("todayInbound", taskMapper.countTodayInbound());
        data.put("todayOutbound", taskMapper.countTodayOutbound());
        data.put("openWarnings", warningMapper.countOpen());
        try {
            redisTemplate.opsForValue().set("dashboard:lastRefresh", String.valueOf(System.currentTimeMillis()), 30, TimeUnit.SECONDS);
            data.put("redis", "CONNECTED");
        } catch (Exception ex) {
            data.put("redis", "NOT_CONNECTED_BUT_SYSTEM_CAN_RUN");
        }
        return data;
    }
}
