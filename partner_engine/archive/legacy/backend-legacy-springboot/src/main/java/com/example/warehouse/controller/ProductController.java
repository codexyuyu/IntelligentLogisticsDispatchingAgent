package com.example.warehouse.controller;

import com.example.warehouse.entity.Product;
import com.example.warehouse.mapper.ProductMapper;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
public class ProductController {

    private final ProductMapper productMapper;

    public ProductController(ProductMapper productMapper) {
        this.productMapper = productMapper;
    }

    @GetMapping("/api/products")
    public List<Product> list() {
        return productMapper.findAll();
    }
}
