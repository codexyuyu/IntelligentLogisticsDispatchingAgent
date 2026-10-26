package com.example.warehouse.service;

import com.example.warehouse.dto.Point;
import com.example.warehouse.entity.Inventory;
import com.example.warehouse.entity.Shelf;
import com.example.warehouse.entity.Warehouse;
import com.example.warehouse.entity.AppUser;
import com.example.warehouse.mapper.InventoryMapper;
import com.example.warehouse.mapper.ShelfMapper;
import com.example.warehouse.mapper.WarehouseMapper;
import com.example.warehouse.mapper.UserMapper;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class WarehouseService {
    private static final Set<String> ALLOWED_STORAGE_TYPES = Set.of("生鲜", "小件商品", "大件商品", "电子产品", "贵重物品");

    private final WarehouseMapper warehouseMapper;
    private final ShelfMapper shelfMapper;
    private final InventoryMapper inventoryMapper;
    private final UserMapper userMapper;

    public WarehouseService(WarehouseMapper warehouseMapper, ShelfMapper shelfMapper, InventoryMapper inventoryMapper, UserMapper userMapper) {
        this.warehouseMapper = warehouseMapper;
        this.shelfMapper = shelfMapper;
        this.inventoryMapper = inventoryMapper;
        this.userMapper = userMapper;
    }

    public Map<String, Object> getTwinData() {
        Warehouse warehouse = warehouseMapper.findFirst();
        List<Shelf> shelves = shelfMapper.findAll();
        List<Inventory> inventories = inventoryMapper.findAllDetail();
        Map<Long, List<Inventory>> inventoryByShelf = inventories.stream()
                .collect(Collectors.groupingBy(Inventory::getShelfId));

        List<Map<String, Object>> shelfViews = new ArrayList<>();
        for (Shelf shelf : shelves) {
            List<Inventory> shelfInventory = inventoryByShelf.getOrDefault(shelf.getId(), List.of());
            Map<Integer, List<Inventory>> byLayer = shelfInventory.stream()
                    .collect(Collectors.groupingBy(Inventory::getLayerNo));
            List<Map<String, Object>> layers = new ArrayList<>();
            for (int i = 1; i <= shelf.getLayers(); i++) {
                layers.add(Map.of(
                        "layerNo", i,
                        "items", byLayer.getOrDefault(i, List.of())
                ));
            }
            Map<String, Object> view = new LinkedHashMap<>();
            view.put("id", shelf.getId());
            view.put("code", shelf.getCode());
            view.put("category", shelf.getCategory());
            view.put("x", shelf.getX());
            view.put("y", shelf.getY());
            view.put("layers", layers);
            view.put("layerCount", shelf.getLayers());
            view.put("capacity", shelf.getCapacity());
            view.put("used", shelf.getUsed());
            view.put("free", shelf.getFree());
            view.put("status", shelf.getStatus());
            view.put("inventory", shelfInventory);
            shelfViews.add(view);
        }
        List<Map<String, Object>> zones = List.of(
                Map.of("code", "PICKING", "name", "分拣区", "x", 0, "y", 0, "width", 6, "depth", warehouse.getDepth(), "status", "EMPTY"),
                Map.of("code", "STORAGE", "name", "存储区", "x", 6, "y", 0, "width", warehouse.getWidth() - 6, "depth", warehouse.getDepth(), "status", "RUNNING")
        );

        return Map.of(
                "warehouse", warehouse,
                "zones", zones,
                "shelves", shelfViews,
                "forkliftPatrolPath", buildForkliftPatrolPath(warehouse, shelves)
        );
    }

    private List<Point> buildForkliftPatrolPath(Warehouse warehouse, List<Shelf> shelves) {
        List<Point> path = new ArrayList<>();
        addIfNew(path, warehouse.getStartX(), warehouse.getStartY());
        moveTo(path, 6, warehouse.getStartY());
        shelves.stream()
                .sorted(Comparator.comparing(Shelf::getX).thenComparing(Shelf::getY))
                .forEach(shelf -> {
                    int aisleX = Math.max(6, shelf.getX() - 1);
                    moveTo(path, aisleX, shelf.getY());
                    moveTo(path, shelf.getX(), shelf.getY());
                    moveTo(path, aisleX, shelf.getY());
                });
        moveTo(path, warehouse.getExitX(), warehouse.getStartY());
        moveTo(path, warehouse.getExitX(), warehouse.getExitY());
        return path;
    }

    private void moveTo(List<Point> path, int x, int y) {
        Point last = path.get(path.size() - 1);
        addIfNew(path, x, last.getY());
        addIfNew(path, x, y);
    }

    private void addIfNew(List<Point> path, int x, int y) {
        if (path.isEmpty() || path.get(path.size() - 1).getX() != x || path.get(path.size() - 1).getY() != y) {
            path.add(new Point(x, y));
        }
    }

    public Warehouse updateStorageType(Long warehouseId, String storageType, Long operatorUserId) {
        String normalizedStorageType = storageType == null ? "" : storageType.trim();
        if (!ALLOWED_STORAGE_TYPES.contains(normalizedStorageType)) {
            throw new IllegalArgumentException("仓库存储类型只能是：生鲜、小件商品、大件商品、电子产品、贵重物品");
        }
        AppUser operator = userMapper.findById(operatorUserId);
        if (operator == null) {
            throw new IllegalArgumentException("操作用户不存在：" + operatorUserId);
        }
        if (operator.getUserPermission() == null || operator.getUserPermission() != 0) {
            throw new IllegalStateException("只有仓库主管可以修改仓库存储类型");
        }
        Warehouse warehouse = warehouseMapper.findById(warehouseId);
        if (warehouse == null) {
            throw new IllegalArgumentException("仓库不存在：" + warehouseId);
        }
        warehouseMapper.updateStorageType(warehouseId, normalizedStorageType);
        return warehouseMapper.findById(warehouseId);
    }

    public Map<String, Object> getShelfDetail(Long shelfId) {
        Shelf shelf = shelfMapper.findById(shelfId);
        if (shelf == null) {
            throw new IllegalArgumentException("货架不存在：" + shelfId);
        }
        return Map.of("shelf", shelf, "inventory", inventoryMapper.findByShelfId(shelfId));
    }
}
