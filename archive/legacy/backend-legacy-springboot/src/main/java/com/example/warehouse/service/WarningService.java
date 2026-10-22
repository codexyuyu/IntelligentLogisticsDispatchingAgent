package com.example.warehouse.service;

import com.example.warehouse.entity.FreshBatch;
import com.example.warehouse.entity.Inventory;
import com.example.warehouse.entity.Product;
import com.example.warehouse.entity.ReplenishmentTask;
import com.example.warehouse.entity.WarningRecord;
import com.example.warehouse.mapper.FreshBatchMapper;
import com.example.warehouse.mapper.InventoryMapper;
import com.example.warehouse.mapper.ProductMapper;
import com.example.warehouse.mapper.ShelfMapper;
import com.example.warehouse.mapper.TaskMapper;
import com.example.warehouse.mapper.WarningMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Service
public class WarningService {
    private final ProductMapper productMapper;
    private final InventoryMapper inventoryMapper;
    private final WarningMapper warningMapper;
    private final TaskMapper taskMapper;
    private final ShelfMapper shelfMapper;
    private final FreshBatchMapper freshBatchMapper;
    private final WarehouseEventPublisher publisher;

    public WarningService(ProductMapper productMapper,
                          InventoryMapper inventoryMapper,
                          WarningMapper warningMapper,
                          TaskMapper taskMapper,
                          ShelfMapper shelfMapper,
                          FreshBatchMapper freshBatchMapper,
                          WarehouseEventPublisher publisher) {
        this.productMapper = productMapper;
        this.inventoryMapper = inventoryMapper;
        this.warningMapper = warningMapper;
        this.taskMapper = taskMapper;
        this.shelfMapper = shelfMapper;
        this.freshBatchMapper = freshBatchMapper;
        this.publisher = publisher;
    }

    public List<WarningRecord> listWarnings() {
        return warningMapper.findAll();
    }

    @Transactional
    public void scanLowStockWarnings() {
        scanLowStockOnly();
        scanFreshBatchWarnings();
        publisher.publish("WARNING_SCANNED");
    }

    private void scanLowStockOnly() {
        for (Product product : productMapper.findAll()) {
            int total = safeInt(inventoryMapper.totalByProduct(product.getId()));
            int safetyStock = safeInt(product.getSafetyStock());
            if (safetyStock <= 0) {
                continue;
            }
            Integer exists = warningMapper.countOpenByTypeAndProduct("LOW_STOCK", product.getId());
            if (total < safetyStock && safeInt(exists) == 0) {
                List<Inventory> locations = inventoryMapper.findByProductId(product.getId());
                Long shelfId = locations.isEmpty() ? null : locations.get(0).getShelfId();
                WarningRecord record = new WarningRecord();
                record.setType("LOW_STOCK");
                record.setProductId(product.getId());
                record.setShelfId(shelfId);
                record.setMessage(product.getProductName() + " 当前库存 " + total + "，低于安全库存 " + safetyStock);
                record.setSuggestion("建议补货 " + Math.max(safetyStock * 2 - total, safetyStock) + product.getUnit() + "，并优先放到匹配的冷链区域。管理员确认后生成补货任务。");
                record.setStatus("OPEN");
                record.setCreatedAt(LocalDateTime.now());
                warningMapper.insert(record);
                if (shelfId != null) {
                    shelfMapper.updateStatus(shelfId, "WARNING");
                }
            }
        }
    }

    private void scanFreshBatchWarnings() {
        for (FreshBatch batch : freshBatchMapper.findAllDetail()) {
            if (batch.getRemainingDays() != null && batch.getRemainingDays().compareTo(BigDecimal.ZERO) <= 0) {
                createFreshWarning("EXPIRED", batch);
            } else if (batch.getRemainingDays() != null && batch.getRemainingDays().compareTo(new BigDecimal("1.5")) <= 0) {
                createFreshWarning("EXPIRING_SOON", batch);
            }
            if ("TEMP_ABNORMAL".equals(batch.getStatus())) {
                createFreshWarning("TEMP_ABNORMAL", batch);
            }
        }
    }

    private void createFreshWarning(String type, FreshBatch batch) {
        Integer exists = warningMapper.countOpenByTypeAndProduct(type, batch.getProductId());
        if (safeInt(exists) > 0) {
            return;
        }
        WarningRecord record = new WarningRecord();
        record.setType(type);
        record.setProductId(batch.getProductId());
        record.setShelfId(batch.getShelfId());
        record.setStatus("OPEN");
        record.setCreatedAt(LocalDateTime.now());
        String productName = batch.getProductName() == null ? "生鲜批次" : batch.getProductName();
        if ("EXPIRED".equals(type)) {
            record.setMessage(productName + " 批次 " + batch.getBatchCode() + " 已过期");
            record.setSuggestion("建议立即下架，并进行人工质量复核。");
        } else if ("EXPIRING_SOON".equals(type)) {
            record.setMessage(productName + " 批次 " + batch.getBatchCode() + " 即将临期，剩余约 " + batch.getRemainingDays() + " 天");
            record.setSuggestion("建议优先出库、降价促销或人工复核。");
        } else if ("TEMP_ABNORMAL".equals(type)) {
            record.setMessage(productName + " 批次 " + batch.getBatchCode() + " 冷链温度异常");
            record.setSuggestion("建议检查冷链设备，并复核该批次品质。");
        }
        warningMapper.insert(record);
        if (batch.getShelfId() != null) {
            shelfMapper.updateStatus(batch.getShelfId(), "WARNING");
        }
    }

    @Transactional
    public Map<String, Object> confirmWarning(Long id) {
        WarningRecord record = warningMapper.findById(id);
        if (record == null) {
            throw new IllegalArgumentException("预警不存在：" + id);
        }
        warningMapper.updateStatus(id, "CONFIRMED");

        if (!"LOW_STOCK".equals(record.getType())) {
            publisher.publish("WARNING_CONFIRMED");
            return Map.of("message", "已确认生鲜质量风险预警，不生成补货任务", "warning", record);
        }

        Product product = productMapper.findById(record.getProductId());
        if (product == null) {
            throw new IllegalArgumentException("预警关联商品不存在：" + record.getProductId());
        }
        int current = safeInt(inventoryMapper.totalByProduct(record.getProductId()));
        int safetyStock = safeInt(product.getSafetyStock());
        int quantity = Math.max(safetyStock * 2 - current, safetyStock);

        ReplenishmentTask task = new ReplenishmentTask();
        task.setWarningId(id);
        task.setProductId(record.getProductId());
        task.setQuantity(quantity);
        task.setStatus("CREATED");
        task.setCreatedAt(LocalDateTime.now());
        taskMapper.insertReplenishment(task);
        publisher.publish("WARNING_CONFIRMED");
        return Map.of("message", "已生成补货任务", "task", task);
    }

    private int safeInt(Integer value) {
        return value == null ? 0 : value;
    }
}
