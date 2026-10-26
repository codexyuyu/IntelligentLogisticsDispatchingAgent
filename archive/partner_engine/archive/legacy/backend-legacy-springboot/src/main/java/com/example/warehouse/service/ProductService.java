package com.example.warehouse.service;

import com.example.warehouse.entity.Product;
import com.example.warehouse.mapper.ProductMapper;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ProductService {

    private final ProductMapper productMapper;

    public ProductService(ProductMapper productMapper) {
        this.productMapper = productMapper;
    }

    public List<Product> findAll() {
        return productMapper.findAll();
    }

    public Product findById(Long id) {
        return productMapper.findById(id);
    }
}
