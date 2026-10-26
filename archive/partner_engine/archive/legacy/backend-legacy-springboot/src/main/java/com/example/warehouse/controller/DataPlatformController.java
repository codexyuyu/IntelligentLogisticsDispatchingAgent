package com.example.warehouse.controller;

import com.example.warehouse.mapper.FreshBatchMapper;
import com.example.warehouse.mapper.InventoryMapper;
import com.example.warehouse.mapper.ProductMapper;
import com.example.warehouse.mapper.WarningMapper;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/data-platform")
public class DataPlatformController {
    private final ProductMapper productMapper;
    private final InventoryMapper inventoryMapper;
    private final FreshBatchMapper freshBatchMapper;
    private final WarningMapper warningMapper;

    public DataPlatformController(ProductMapper productMapper,
                                  InventoryMapper inventoryMapper,
                                  FreshBatchMapper freshBatchMapper,
                                  WarningMapper warningMapper) {
        this.productMapper = productMapper;
        this.inventoryMapper = inventoryMapper;
        this.freshBatchMapper = freshBatchMapper;
        this.warningMapper = warningMapper;
    }

    @GetMapping("/overview")
    public Map<String, Object> overview() {
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("productCount", productMapper.findAll().size());
        metrics.put("totalStock", inventoryMapper.totalStock());
        metrics.put("freshBatchCount", freshBatchMapper.findAllDetail().size());
        metrics.put("riskBatchCount", freshBatchMapper.findRiskBatches().size());
        metrics.put("openWarningCount", warningMapper.countOpen());
        metrics.put("todayCollectedRecords", 12860);

        List<Map<String, Object>> sources = List.of(
                source("采购与价格数据", "业务接口 / 定时采集", "每日", "正常"),
                source("库存与出入库数据", "Spring Boot 业务事件", "实时", "正常"),
                source("运输 GPS 与温湿度", "HTTP / MQTT 预留接口", "30秒", "演示"),
                source("仓储温湿度", "冷链传感器日志", "1分钟", "正常"),
                source("收货与品质数据", "收货验收业务", "实时", "正常"),
                source("预警与处理记录", "预警中心", "实时", "正常")
        );

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("generatedAt", LocalDateTime.now());
        result.put("metrics", metrics);
        result.put("sources", sources);
        result.put("dates", List.of("7/24", "7/25", "7/26", "7/27", "7/28", "7/29", "7/30"));
        result.put("consumptionTrend", List.of(118, 126, 121, 142, 155, 149, 163));
        result.put("collectionTrend", List.of(8200, 9100, 9850, 10320, 11260, 11980, 12860));
        result.put("temperatureTrend", List.of(4.2, 4.6, 5.1, 4.8, 6.3, 5.4, 4.7));
        result.put("riskDistribution", List.of(
                Map.of("name", "正常批次", "value", Math.max(1, freshBatchMapper.findAllDetail().size() - freshBatchMapper.findRiskBatches().size())),
                Map.of("name", "临期风险", "value", Math.max(1, freshBatchMapper.findRiskBatches().size())),
                Map.of("name", "温度异常", "value", 2),
                Map.of("name", "库存不足", "value", Math.max(1, warningMapper.countOpenLowStock()))
        ));
        result.put("note", "大数据平台负责采集、清洗、存储和统计，为 AI 预测与 Agent 工具调用提供数据基础。" );
        return result;
    }

    private Map<String, Object> source(String name, String method, String frequency, String status) {
        Map<String, Object> value = new LinkedHashMap<>();
        value.put("name", name);
        value.put("method", method);
        value.put("frequency", frequency);
        value.put("status", status);
        return value;
    }
}
