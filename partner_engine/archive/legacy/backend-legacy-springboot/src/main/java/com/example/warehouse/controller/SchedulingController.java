package com.example.warehouse.controller;

import com.example.warehouse.service.SchedulingService;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/schedules")
public class SchedulingController {
    private final SchedulingService service;
    public SchedulingController(SchedulingService service) { this.service = service; }

    @GetMapping("/batches")
    public List<Map<String,Object>> batches() { return service.listBatches(); }

    @GetMapping("/orders")
    public List<Map<String,Object>> orders() { return service.listOrders(); }

    @GetMapping("/cold-rooms")
    public List<Map<String,Object>> coldRooms() { return service.listColdRooms(); }

    @GetMapping("/vehicles")
    public List<Map<String,Object>> vehicles() { return service.listVehicles(); }

    @GetMapping("/routes")
    public List<Map<String,Object>> routes() { return service.listRoutes(); }

    @PostMapping("/solve")
    public Map<String,Object> solve(@RequestBody(required=false) Map<String,Object> options) {
        return service.solve(options == null ? Map.of() : options);
    }

    @GetMapping("/{id}")
    public Map<String,Object> get(@PathVariable Long id) { return service.getSchedule(id); }

    @PostMapping("/{id}/confirm")
    public Map<String,Object> confirm(@PathVariable Long id) { return service.confirm(id); }
}
