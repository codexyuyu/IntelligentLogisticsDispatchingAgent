package com.example.warehouse.service;

import com.example.warehouse.dto.InboundRequest;
import com.example.warehouse.entity.InboundTask;
import com.example.warehouse.entity.Inventory;
import com.example.warehouse.entity.Product;
import com.example.warehouse.entity.Shelf;
import com.example.warehouse.entity.Warehouse;
import com.example.warehouse.mapper.InventoryMapper;
import com.example.warehouse.mapper.ProductMapper;
import com.example.warehouse.mapper.ShelfMapper;
import com.example.warehouse.mapper.TaskMapper;
import com.example.warehouse.mapper.WarehouseMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class InboundService {
    private final ProductMapper productMapper;
    private final ShelfMapper shelfMapper;
    private final WarehouseMapper warehouseMapper;
    private final InventoryMapper inventoryMapper;
    private final TaskMapper taskMapper;
    private final WarningService warningService;
    private final WarehouseEventPublisher publisher;

    public InboundService(ProductMapper productMapper, ShelfMapper shelfMapper, WarehouseMapper warehouseMapper,
                          InventoryMapper inventoryMapper, TaskMapper taskMapper, WarningService warningService,
                          WarehouseEventPublisher publisher) {
        this.productMapper = productMapper;
        this.shelfMapper = shelfMapper;
        this.warehouseMapper = warehouseMapper;
        this.inventoryMapper = inventoryMapper;
        this.taskMapper = taskMapper;
        this.warningService = warningService;
        this.publisher = publisher;
    }

    public Map<String, Object> recommend(InboundRequest request) {
        Product product = requireProduct(request.getProductId());
        Warehouse warehouse = warehouseMapper.findFirst();
        List<Shelf> candidates = shelfMapper.findAvailable(request.getQuantity());
        if (candidates.isEmpty()) {
            throw new IllegalStateException("没有容量足够的货架，请先释放货位或增加货架容量");
        }

        List<Map<String, Object>> scored = candidates.stream().map(shelf -> scoreShelf(product, shelf, warehouse, request.getQuantity()))
                .sorted((a, b) -> Double.compare((double) b.get("score"), (double) a.get("score")))
                .toList();
        Map<String, Object> best = scored.get(0);

        InboundTask task = new InboundTask();
        task.setProductId(product.getId());
        task.setQuantity(request.getQuantity());
        task.setRecommendedShelfId(((Number) best.get("shelfId")).longValue());
        task.setStatus("RECOMMENDED");
        task.setCreatedAt(LocalDateTime.now());
        taskMapper.insertInbound(task);

        return Map.of(
                "task", task,
                "product", product,
                "best", best,
                "candidates", scored,
                "explain", "评分 = 冷链类型匹配 + 品类匹配 + 剩余容量 + 当前温度 + 距离出库口。生鲜优先保证冷藏/冷冻条件正确。"
        );
    }

    private Map<String, Object> scoreShelf(Product product, Shelf shelf, Warehouse warehouse, Integer quantity) {
        int distance = Math.abs(shelf.getX() - warehouse.getExitX()) + Math.abs(shelf.getY() - warehouse.getExitY());
        boolean storageMatched = product.getStorageType() != null && product.getStorageType().equals(shelf.getStorageType());
        boolean categoryMatched = product.getCategory() != null && shelf.getCategory() != null && shelf.getCategory().contains(product.getCategory());
        boolean tempMatched = shelf.getCurrentTemperature() != null
                && product.getMinTemperature() != null
                && product.getMaxTemperature() != null
                && shelf.getCurrentTemperature().compareTo(product.getMinTemperature()) >= 0
                && shelf.getCurrentTemperature().compareTo(product.getMaxTemperature()) <= 0;

        double storageScore = storageMatched ? 40 : -30;
        double categoryScore = categoryMatched ? 25 : 8;
        double capacityScore = Math.min(25, shelf.getFree() * 25.0 / Math.max(quantity, 1));
        double distanceScore = Math.max(0, 15 - distance * 1.5);
        double tempScore = tempMatched ? 10 : -20;
        double total = storageScore + categoryScore + capacityScore + distanceScore + tempScore;

        Map<String, Object> map = new LinkedHashMap<>();
        map.put("shelfId", shelf.getId());
        map.put("shelfCode", shelf.getCode());
        map.put("category", shelf.getCategory());
        map.put("storageType", shelf.getStorageType());
        map.put("currentTemperature", shelf.getCurrentTemperature());
        map.put("currentHumidity", shelf.getCurrentHumidity());
        map.put("free", shelf.getFree());
        map.put("distanceToExit", distance);
        map.put("score", Math.round(total * 100) / 100.0);
        map.put("reason", "存储类型" + (storageMatched ? "匹配" : "不匹配")
                + "；品类" + (categoryMatched ? "匹配" : "不完全匹配")
                + "；剩余容量 " + shelf.getFree()
                + "；当前温度 " + shelf.getCurrentTemperature()
                + "；到出口曼哈顿距离 " + distance);
        return map;
    }

    @Transactional
    public Map<String, Object> confirm(InboundRequest request) {
        Product product = requireProduct(request.getProductId());
        Shelf shelf = shelfMapper.findById(request.getShelfId());
        if (shelf == null) throw new IllegalArgumentException("货架不存在：" + request.getShelfId());
        if (shelf.getFree() < request.getQuantity()) throw new IllegalStateException("该货架剩余容量不足");

        Inventory existed = inventoryMapper.findOne(product.getId(), shelf.getId(), 1);
        if (existed == null) {
            Inventory inventory = new Inventory();
            inventory.setProductId(product.getId());
            inventory.setShelfId(shelf.getId());
            inventory.setLayerNo(1);
            inventory.setQuantity(request.getQuantity());
            inventoryMapper.insert(inventory);
        } else {
            inventoryMapper.addQuantity(existed.getId(), request.getQuantity());
        }
        shelfMapper.addUsed(shelf.getId(), request.getQuantity());
        shelfMapper.updateStatus(shelf.getId(), "NORMAL");
        warningService.scanLowStockWarnings();
        publisher.publish("INBOUND_CONFIRMED");
        return Map.of("message", "入库成功，库存已更新", "shelf", shelf, "product", product, "quantity", request.getQuantity());
    }

    private Product requireProduct(Long productId) {
        Product product = productMapper.findById(productId);
        if (product == null) throw new IllegalArgumentException("商品不存在：" + productId);
        return product;
    }
}
