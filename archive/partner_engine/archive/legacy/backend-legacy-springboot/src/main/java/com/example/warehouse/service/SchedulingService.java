package com.example.warehouse.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class SchedulingService {
    private final JdbcTemplate jdbc;
    private final RestClient restClient;
    private final DateTimeFormatter formatter = DateTimeFormatter.ISO_LOCAL_DATE_TIME;
    private final AtomicLong scheduleIdGenerator = new AtomicLong(1);
    private final Map<Long, Map<String, Object>> schedules = new ConcurrentHashMap<>();

    public SchedulingService(JdbcTemplate jdbc,
                             @Value("${app.algorithm.base-url:http://localhost:8000}") String baseUrl) {
        this.jdbc = jdbc;
        this.restClient = RestClient.builder().baseUrl(baseUrl).build();
    }

    /**
     * Reads the existing smart_warehouse tables. No scheduling tables are required.
     */
    public List<Map<String, Object>> listBatches() {
        return jdbc.queryForList("""
            SELECT
                b.id AS id,
                b.batch_code AS batchCode,
                p.product_name AS product,
                COALESCE(b.quality_grade, 'A') AS grade,
                b.quantity_remaining AS quantity,
                b.receive_time AS expectedInbound,
                COALESCE(p.min_temperature, 0) AS minTemperature,
                COALESCE(p.max_temperature, 25) AS maxTemperature,
                COALESCE(p.base_shelf_life_days, 7) AS maxStorageDays,
                COALESCE(b.remaining_days, p.base_shelf_life_days, 7) AS remainingShelfDays,
                CASE WHEN p.perishable = 1 THEN true ELSE false END AS preCoolingRequired,
                b.status AS status
            FROM fresh_batch b
            JOIN products p ON p.id = b.product_id
            WHERE b.quantity_remaining > 0
              AND COALESCE(b.status, 'NORMAL') <> 'EXPIRED'
            ORDER BY b.receive_time
            """);
    }

    public List<Map<String, Object>> listOrders() {
        return jdbc.queryForList("""
            SELECT
                o.id AS id,
                CONCAT('ORD-', LPAD(o.id, 4, '0')) AS orderCode,
                CONCAT('客户-', o.id) AS customer,
                p.product_name AS product,
                o.quantity AS quantity,
                'A' AS grade,
                DATE_ADD(COALESCE(o.created_at, NOW()), INTERVAL 2 DAY) AS latestDelivery,
                1 AS minShelfLifeDays,
                o.status AS status
            FROM outbound_order o
            JOIN products p ON p.id = o.product_id
            WHERE COALESCE(o.status, 'CREATED') IN ('CREATED', 'PENDING')
            ORDER BY o.created_at, o.id
            """);
    }

    public List<Map<String, Object>> listColdRooms() {
        return jdbc.queryForList("""
            SELECT
                s.id AS id,
                s.code AS roomCode,
                COALESCE(w.name, '智能仓库 Demo') AS warehouseName,
                COALESCE(s.capacity, 0) AS capacity,
                COALESCE(s.used, 0) AS usedCapacity,
                CASE WHEN s.storage_type = 'FROZEN' THEN -22
                     WHEN s.storage_type = 'CHILLED' THEN 0
                     ELSE 10 END AS minTemperature,
                CASE WHEN s.storage_type = 'FROZEN' THEN -18
                     WHEN s.storage_type = 'CHILLED' THEN 4
                     ELSE 30 END AS maxTemperature,
                COALESCE(s.category, '通用') AS supportedProducts,
                false AS preCoolingSupported,
                2 AS cleaningHours,
                1 AS switchHours,
                CASE WHEN COALESCE(s.status, 'NORMAL') = 'NORMAL' THEN 'NORMAL'
                     ELSE s.status END AS deviceStatus,
                1.5 AS costPerTonHour,
                s.storage_type AS storageType,
                s.current_temperature AS currentTemperature,
                s.current_humidity AS currentHumidity
            FROM shelf s
            LEFT JOIN warehouse w ON w.id = s.warehouse_id
            WHERE s.storage_type IN ('CHILLED', 'FROZEN')
            ORDER BY s.id
            """);
    }

    /** Vehicles are currently demo resources and deliberately not persisted in MySQL. */
    public List<Map<String, Object>> listVehicles() {
        return List.of(
            vehicle(1, "V01", "冷藏车", 1000, 18, 0, 8, 2.50),
            vehicle(2, "V02", "冷藏车", 800, 15, 0, 6, 2.30),
            vehicle(3, "V03", "冷藏车", 500, 10, 2, 8, 2.00)
        );
    }

    /** Routes are currently demo resources and deliberately not persisted in MySQL. */
    public List<Map<String, Object>> listRoutes() {
        return List.of(
            route(1, "R001", "智能仓库 Demo", "县城生鲜超市", 18.5, 35, "NORMAL", 1.0, 0.0),
            route(2, "R002", "智能仓库 Demo", "区域批发市场", 35.0, 60, "NORMAL", 1.0, 8.0),
            route(3, "R003", "智能仓库 Demo", "社区电商配送中心", 15.0, 30, "NORMAL", 1.0, 0.0),
            route(4, "R004", "智能仓库 Demo", "乡镇配送点", 26.0, 50, "CONGESTED", 1.35, 5.0)
        );
    }

    public Map<String, Object> solve(Map<String, Object> options) {
        long begin = System.currentTimeMillis();
        Map<String, Object> safeOptions = options == null ? Map.of() : options;

        // FastAPI is the single scheduling data adapter + algorithm boundary.
        // Only user options are sent; FastAPI reads smart_warehouse directly.
        Map<String, Object> result = callAlgorithm("/api/schedule/solve", safeOptions);
        result.put("solveMs", System.currentTimeMillis() - begin);
        result.putIfAbsent("status", "DRAFT");

        long id = scheduleIdGenerator.getAndIncrement();
        result.put("id", id);
        result.put("status", "DRAFT");
        normalizeAssignments(result);
        schedules.put(id, deepCopyMap(result));
        return result;
    }

    /**
     * Because the user's MySQL schema intentionally remains unchanged, confirmation is
     * an in-memory action in this phase. No schedule tables are written to MySQL.
     */
    public Map<String, Object> confirm(Long scheduleId) {
        Map<String, Object> schedule = schedules.get(scheduleId);
        if (schedule == null) {
            throw new NoSuchElementException("找不到当前进程中的调度方案 " + scheduleId);
        }
        schedule.put("status", "CONFIRMED");
        return deepCopyMap(schedule);
    }

    public Map<String, Object> getSchedule(Long id) {
        Map<String, Object> schedule = schedules.get(id);
        if (schedule == null) {
            throw new NoSuchElementException("找不到当前进程中的调度方案 " + id);
        }
        return deepCopyMap(schedule);
    }

    private void normalizeAssignments(Map<String, Object> result) {
        Object raw = result.get("assignments");
        if (!(raw instanceof List<?> list)) return;

        List<Map<String, Object>> batches = safeList(result.get("batches"));
        List<Map<String, Object>> rooms = safeList(result.get("coldRooms"));
        List<Map<String, Object>> orders = safeList(result.get("orders"));
        List<Map<String, Object>> vehicles = safeList(result.get("vehicles"));
        List<Map<String, Object>> routes = safeList(result.get("routes"));

        // FastAPI normally returns camelCase assignment fields. The Vue page already
        // understands the original snake_case response, so expose both names here.
        for (Object item : list) {
            if (!(item instanceof Map<?, ?> rawMap)) continue;
            @SuppressWarnings("unchecked") Map<String, Object> a = (Map<String, Object>) rawMap;
            longValue(a, "batchId").ifPresent(v -> {
                a.putIfAbsent("batch_id", v);
                findById(batches, v).ifPresent(x -> a.putIfAbsent("batch_code", first(x, "batchCode", "batch_code")));
                findById(batches, v).ifPresent(x -> a.putIfAbsent("product", x.get("product")));
            });
            longValue(a, "coldRoomId").ifPresent(v -> {
                a.putIfAbsent("cold_room_id", v);
                findById(rooms, v).ifPresent(x -> a.putIfAbsent("room_code", first(x, "roomCode", "room_code")));
            });
            longValue(a, "orderId").ifPresent(v -> {
                a.putIfAbsent("order_id", v);
                findById(orders, v).ifPresent(x -> a.putIfAbsent("order_code", first(x, "orderCode", "order_code")));
            });
            longValue(a, "vehicleId").ifPresent(v -> {
                a.putIfAbsent("vehicle_id", v);
                findById(vehicles, v).ifPresent(x -> a.putIfAbsent("vehicle_code", first(x, "vehicleCode", "vehicle_code")));
            });
            longValue(a, "routeId").ifPresent(v -> {
                a.putIfAbsent("route_id", v);
                findById(routes, v).ifPresent(x -> a.putIfAbsent("route_code", first(x, "routeCode", "route_code")));
            });
            copyAlias(a, "plannedInbound", "planned_inbound");
            copyAlias(a, "plannedOutbound", "planned_outbound");
            copyAlias(a, "allocatedQuantity", "allocated_quantity");
            copyAlias(a, "storageCost", "storage_cost");
            copyAlias(a, "transportCost", "transport_cost");
            copyAlias(a, "qualityRisk", "quality_risk");
        }
    }

    private Map<String, Object> callAlgorithm(String path, Map<String, Object> payload) {
        try {
            Map<?, ?> raw = restClient.post().uri(path).body(payload).retrieve().body(Map.class);
            if (raw == null) throw new IllegalStateException("算法服务返回为空");
            Map<String, Object> result = new LinkedHashMap<>();
            raw.forEach((k, v) -> result.put(String.valueOf(k), v));
            return result;
        } catch (Exception ex) {
            throw new IllegalStateException("调度算法服务不可用，请先启动 FastAPI（默认 http://localhost:8000）", ex);
        }
    }

    private Map<String, Object> vehicle(int id, String code, String type, int capacity, int volume,
                                        int minTemp, int maxTemp, double costPerKm) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id); m.put("vehicleCode", code); m.put("vehicleType", type);
        m.put("capacity", capacity); m.put("volume", volume); m.put("refrigerated", true);
        m.put("minTemperature", minTemp); m.put("maxTemperature", maxTemp);
        m.put("currentLocation", "智能仓库 Demo"); m.put("availableFrom", LocalDateTime.now().format(formatter));
        m.put("status", "AVAILABLE"); m.put("costPerKm", costPerKm);
        return m;
    }

    private Map<String, Object> route(int id, String code, String start, String end,
                                      double distanceKm, int minutes, String status,
                                      double factor, double toll) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id); m.put("routeCode", code); m.put("startNode", start); m.put("endNode", end);
        m.put("distanceKm", distanceKm); m.put("estimatedMinutes", minutes); m.put("roadStatus", status);
        m.put("roadFactor", factor); m.put("tollCost", toll); m.put("refrigeratedRequired", true);
        m.put("status", "AVAILABLE");
        return m;
    }

    private List<Map<String, Object>> safeList(Object value) {
        if (!(value instanceof List<?> list)) return List.of();
        List<Map<String, Object>> out = new ArrayList<>();
        for (Object item : list) if (item instanceof Map<?, ?> m) {
            Map<String, Object> copy = new LinkedHashMap<>();
            m.forEach((k, v) -> copy.put(String.valueOf(k), v));
            out.add(copy);
        }
        return out;
    }

    private Optional<Long> longValue(Map<String, Object> map, String key) {
        Object value = map.get(key);
        if (value == null) return Optional.empty();
        if (value instanceof Number n) return Optional.of(n.longValue());
        try { return Optional.of(Long.parseLong(String.valueOf(value))); }
        catch (NumberFormatException ex) { return Optional.empty(); }
    }

    private Optional<Map<String, Object>> findById(List<Map<String, Object>> rows, long id) {
        return rows.stream().filter(x -> {
            Object v = x.get("id");
            try { return v instanceof Number n ? n.longValue() == id : Long.parseLong(String.valueOf(v)) == id; }
            catch (Exception ex) { return false; }
        }).findFirst();
    }

    private Object first(Map<String, Object> map, String... keys) {
        for (String k : keys) if (map.containsKey(k)) return map.get(k);
        return null;
    }

    private void copyAlias(Map<String, Object> map, String source, String target) {
        if (map.containsKey(source) && !map.containsKey(target)) map.put(target, map.get(source));
        if (map.containsKey(target) && !map.containsKey(source)) map.put(source, map.get(target));
    }

    private Map<String, Object> deepCopyMap(Map<String, Object> source) {
        Map<String, Object> copy = new LinkedHashMap<>();
        source.forEach((k, v) -> {
            if (v instanceof List<?> list) {
                List<Object> lc = new ArrayList<>();
                for (Object item : list) {
                    if (item instanceof Map<?, ?> m) {
                        Map<String, Object> mc = new LinkedHashMap<>();
                        m.forEach((mk, mv) -> mc.put(String.valueOf(mk), mv));
                        lc.add(mc);
                    } else lc.add(item);
                }
                copy.put(k, lc);
            } else copy.put(k, v);
        });
        return copy;
    }
}
