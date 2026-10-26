package com.example.warehouse.controller;

import com.example.warehouse.entity.PurchaseAdvice;
import com.example.warehouse.mapper.PurchaseAdviceMapper;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/purchase-advice")
public class PurchaseAdviceController {
    private final PurchaseAdviceMapper purchaseAdviceMapper;

    public PurchaseAdviceController(PurchaseAdviceMapper purchaseAdviceMapper) {
        this.purchaseAdviceMapper = purchaseAdviceMapper;
    }

    @GetMapping
    public List<PurchaseAdvice> list() {
        return purchaseAdviceMapper.findLatest();
    }
}
