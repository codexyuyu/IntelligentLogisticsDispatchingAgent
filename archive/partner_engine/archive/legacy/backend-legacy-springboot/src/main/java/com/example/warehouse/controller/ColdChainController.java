package com.example.warehouse.controller;

import com.example.warehouse.mapper.FreshBatchMapper;
import com.example.warehouse.mapper.WarningMapper;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/cold-chain")
public class ColdChainController {
    private final FreshBatchMapper freshBatchMapper;
    private final WarningMapper warningMapper;

    public ColdChainController(FreshBatchMapper freshBatchMapper, WarningMapper warningMapper) {
        this.freshBatchMapper = freshBatchMapper;
        this.warningMapper = warningMapper;
    }

    @GetMapping("/overview")
    public Map<String, Object> overview() {
        List<Map<String, Object>> tasks = List.of(
                task("CT20260730001", "草莓", "粤A·C3281", "运输中", 68, 4.8, 82, "华南生鲜基地", "1号冷库"),
                task("CT20260730002", "低温鲜牛奶", "粤A·L9066", "待收货", 100, 3.2, 76, "每日鲜语供应商", "2号冷库"),
                task("CT20260730003", "三文鱼", "粤B·F5188", "温度异常", 44, 8.6, 88, "海产供应中心", "1号冷库")
        );

        List<Map<String, Object>> sensorLogs = new ArrayList<>();
        sensorLogs.add(sensor("CT20260730001", "10:00", 4.1, 81, "113.2644, 23.1291", "正常"));
        sensorLogs.add(sensor("CT20260730001", "10:10", 4.5, 82, "113.2712, 23.1355", "正常"));
        sensorLogs.add(sensor("CT20260730001", "10:20", 4.8, 82, "113.2798, 23.1413", "正常"));
        sensorLogs.add(sensor("CT20260730003", "10:00", 5.6, 86, "113.3310, 23.1170", "正常"));
        sensorLogs.add(sensor("CT20260730003", "10:10", 7.4, 87, "113.3256, 23.1202", "预警"));
        sensorLogs.add(sensor("CT20260730003", "10:20", 8.6, 88, "113.3188, 23.1235", "高风险"));

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("generatedAt", LocalDateTime.now());
        result.put("runningTasks", 2);
        result.put("pendingReceiving", 1);
        result.put("temperatureWarnings", Math.max(1, warningMapper.countOpen()));
        result.put("riskBatchCount", freshBatchMapper.findRiskBatches().size());
        result.put("tasks", tasks);
        result.put("sensorLogs", sensorLogs);
        result.put("note", "当前运输数据为演示接口，后续接入运输任务、GPS 与温湿度传感器数据库表。" );
        return result;
    }

    private Map<String, Object> task(String taskCode,
                                     String productName,
                                     String vehicleNo,
                                     String status,
                                     int progress,
                                     double temperature,
                                     int humidity,
                                     String origin,
                                     String destination) {
        Map<String, Object> value = new LinkedHashMap<>();
        value.put("taskCode", taskCode);
        value.put("productName", productName);
        value.put("vehicleNo", vehicleNo);
        value.put("status", status);
        value.put("progress", progress);
        value.put("temperature", temperature);
        value.put("humidity", humidity);
        value.put("origin", origin);
        value.put("destination", destination);
        return value;
    }

    private Map<String, Object> sensor(String taskCode,
                                       String collectTime,
                                       double temperature,
                                       int humidity,
                                       String location,
                                       String status) {
        Map<String, Object> value = new LinkedHashMap<>();
        value.put("taskCode", taskCode);
        value.put("collectTime", collectTime);
        value.put("temperature", temperature);
        value.put("humidity", humidity);
        value.put("location", location);
        value.put("status", status);
        return value;
    }
}
