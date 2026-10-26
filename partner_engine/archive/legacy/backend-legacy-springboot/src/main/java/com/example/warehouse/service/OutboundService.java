package com.example.warehouse.service;

import com.example.warehouse.dto.OutboundRequest;
import com.example.warehouse.dto.Point;
import com.example.warehouse.entity.Inventory;
import com.example.warehouse.entity.OutboundOrder;
import com.example.warehouse.entity.Product;
import com.example.warehouse.entity.Shelf;
import com.example.warehouse.entity.Warehouse;
import com.example.warehouse.mapper.InventoryMapper;
import com.example.warehouse.mapper.ProductMapper;
import com.example.warehouse.mapper.ShelfMapper;
import com.example.warehouse.mapper.TaskMapper;
import com.example.warehouse.mapper.WarehouseMapper;
import com.example.warehouse.util.PathPlanner;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Service
public class OutboundService {
    private final ProductMapper productMapper;
    private final InventoryMapper inventoryMapper;
    private final ShelfMapper shelfMapper;
    private final WarehouseMapper warehouseMapper;
    private final TaskMapper taskMapper;
    private final WarningService warningService;
    private final WarehouseEventPublisher publisher;
    private final ObjectMapper objectMapper;

    public OutboundService(ProductMapper productMapper, InventoryMapper inventoryMapper, ShelfMapper shelfMapper,
                           WarehouseMapper warehouseMapper, TaskMapper taskMapper, WarningService warningService,
                           WarehouseEventPublisher publisher, ObjectMapper objectMapper) {
        this.productMapper = productMapper;
        this.inventoryMapper = inventoryMapper;
        this.shelfMapper = shelfMapper;
        this.warehouseMapper = warehouseMapper;
        this.taskMapper = taskMapper;
        this.warningService = warningService;
        this.publisher = publisher;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public Map<String, Object> createOrder(OutboundRequest request) {
        Product product = productMapper.findById(request.getProductId());
        if (product == null) throw new IllegalArgumentException("商品不存在：" + request.getProductId());
        List<Inventory> locations = inventoryMapper.findByProductId(product.getId());
        if (locations.isEmpty()) throw new IllegalStateException("该商品没有库存，无法出库");
        Inventory pick = locations.stream().filter(i -> i.getQuantity() >= request.getQuantity()).findFirst().orElse(locations.get(0));
        if (pick.getQuantity() < request.getQuantity()) throw new IllegalStateException("库存不足：当前最多可出库 " + pick.getQuantity());

        Shelf shelf = shelfMapper.findById(pick.getShelfId());
        Warehouse warehouse = warehouseMapper.findFirst();
        List<Point> path = PathPlanner.manhattanPath(
                new Point(warehouse.getStartX(), warehouse.getStartY()),
                new Point(shelf.getX(), shelf.getY()),
                new Point(warehouse.getExitX(), warehouse.getExitY())
        );

        OutboundOrder order = new OutboundOrder();
        order.setProductId(product.getId());
        order.setQuantity(request.getQuantity());
        order.setShelfId(shelf.getId());
        order.setStatus("CREATED");
        order.setCreatedAt(LocalDateTime.now());
        try {
            order.setPathJson(objectMapper.writeValueAsString(path));
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("路径转换失败", e);
        }
        taskMapper.insertOutbound(order);
        publisher.publish("OUTBOUND_CREATED");
        return Map.of(
                "order", order,
                "product", product,
                "shelf", shelf,
                "path", path,
                "explain", "路径使用简单曼哈顿路径：从起点先横向再纵向到货架，然后再到出库口。比赛演示足够清晰，后续可升级为 A* 算法避障。"
        );
    }

    @Transactional
    public Map<String, Object> finishOrder(Long orderId) {
        OutboundOrder order = taskMapper.findOutbound(orderId);
        if (order == null) throw new IllegalArgumentException("出库订单不存在：" + orderId);
        if ("FINISHED".equals(order.getStatus())) throw new IllegalStateException("该订单已经完成，不要重复扣库存");
        List<Inventory> locations = inventoryMapper.findByProductId(order.getProductId());
        Inventory target = locations.stream().filter(i -> i.getShelfId().equals(order.getShelfId())).findFirst()
                .orElseThrow(() -> new IllegalStateException("找不到订单对应货架库存"));
        if (target.getQuantity() < order.getQuantity()) throw new IllegalStateException("库存不足，无法完成出库");

        inventoryMapper.reduceQuantity(target.getId(), order.getQuantity());
        shelfMapper.reduceUsed(order.getShelfId(), order.getQuantity());
        taskMapper.updateOutboundStatus(orderId, "FINISHED");
        warningService.scanLowStockWarnings();
        publisher.publish("OUTBOUND_FINISHED");
        return Map.of("message", "出库完成，库存已扣减", "orderId", orderId);
    }
}
