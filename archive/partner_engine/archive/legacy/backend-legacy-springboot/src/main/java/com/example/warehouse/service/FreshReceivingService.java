package com.example.warehouse.service;

import com.example.warehouse.dto.FreshReceiveRequest;
import com.example.warehouse.entity.FreshBatch;
import com.example.warehouse.entity.Inventory;
import com.example.warehouse.entity.Product;
import com.example.warehouse.entity.Shelf;
import com.example.warehouse.mapper.FreshBatchMapper;
import com.example.warehouse.mapper.InventoryMapper;
import com.example.warehouse.mapper.ProductMapper;
import com.example.warehouse.mapper.ShelfMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Service
public class FreshReceivingService {
    private final ProductMapper productMapper;
    private final ShelfMapper shelfMapper;
    private final InventoryMapper inventoryMapper;
    private final FreshBatchMapper freshBatchMapper;
    private final ShelfLifeService shelfLifeService;
    private final WarningService warningService;
    private final WarehouseEventPublisher publisher;

    public FreshReceivingService(ProductMapper productMapper,
                                 ShelfMapper shelfMapper,
                                 InventoryMapper inventoryMapper,
                                 FreshBatchMapper freshBatchMapper,
                                 ShelfLifeService shelfLifeService,
                                 WarningService warningService,
                                 WarehouseEventPublisher publisher) {
        this.productMapper = productMapper;
        this.shelfMapper = shelfMapper;
        this.inventoryMapper = inventoryMapper;
        this.freshBatchMapper = freshBatchMapper;
        this.shelfLifeService = shelfLifeService;
        this.warningService = warningService;
        this.publisher = publisher;
    }

    public List<FreshBatch> listBatches() {
        return freshBatchMapper.findAllDetail();
    }

    public List<FreshBatch> listRiskBatches() {
        return freshBatchMapper.findRiskBatches();
    }

    @Transactional
    public Map<String, Object> confirmReceive(FreshReceiveRequest request) {
        validateRequest(request);
        Product product = productMapper.findById(request.getProductId());
        if (product == null) {
            throw new IllegalArgumentException("商品不存在：" + request.getProductId());
        }
        Shelf shelf = shelfMapper.findById(request.getShelfId());
        if (shelf == null) {
            throw new IllegalArgumentException("货架不存在：" + request.getShelfId());
        }
        if (shelf.getFree() < request.getQuantity()) {
            throw new IllegalStateException("货架剩余容量不足");
        }
        if (product.getStorageType() != null && shelf.getStorageType() != null
                && !Objects.equals(product.getStorageType(), shelf.getStorageType())) {
            throw new IllegalStateException("商品存储类型与货架冷链类型不匹配：商品=" + product.getStorageType() + "，货架=" + shelf.getStorageType());
        }

        ShelfLifeService.PredictionResult prediction = shelfLifeService.predict(
                product,
                defaultValue(request.getInitialQualityScore(), new BigDecimal("90")),
                defaultValue(request.getStorageTemperature(), shelf.getCurrentTemperature()),
                defaultValue(request.getStorageHumidity(), shelf.getCurrentHumidity()),
                BigDecimal.ZERO
        );

        FreshBatch batch = new FreshBatch();
        batch.setBatchCode(generateBatchCode());
        batch.setProductId(product.getId());
        batch.setShelfId(shelf.getId());
        batch.setSupplier(request.getSupplier());
        batch.setOriginPlace(request.getOriginPlace());
        batch.setReceiveTime(LocalDateTime.now());
        batch.setQuantityInitial(request.getQuantity());
        batch.setQuantityRemaining(request.getQuantity());
        batch.setPurchasePrice(request.getPurchasePrice());
        batch.setQualityGrade(request.getQualityGrade() == null ? "A" : request.getQualityGrade());
        batch.setInitialQualityScore(defaultValue(request.getInitialQualityScore(), new BigDecimal("90")));
        batch.setStorageTemperature(defaultValue(request.getStorageTemperature(), shelf.getCurrentTemperature()));
        batch.setStorageHumidity(defaultValue(request.getStorageHumidity(), shelf.getCurrentHumidity()));
        batch.setPredictedStorageDays(prediction.getPredictedStorageDays());
        batch.setRemainingDays(prediction.getRemainingDays());
        batch.setFreshnessScore(prediction.getFreshnessScore());
        batch.setStatus(prediction.getStatus());
        freshBatchMapper.insert(batch);

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
        publisher.publish("FRESH_RECEIVED");
        return Map.of("message", "生鲜收货成功，已生成批次并预测保鲜期", "batch", batch, "prediction", prediction);
    }

    private void validateRequest(FreshReceiveRequest request) {
        if (request.getProductId() == null) throw new IllegalArgumentException("productId 不能为空");
        if (request.getShelfId() == null) throw new IllegalArgumentException("shelfId 不能为空");
        if (request.getQuantity() == null || request.getQuantity() <= 0) throw new IllegalArgumentException("quantity 必须大于 0");
    }

    private BigDecimal defaultValue(BigDecimal value, BigDecimal fallback) {
        return value != null ? value : fallback;
    }

    private String generateBatchCode() {
        return "FB" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmssSSS"));
    }
}
