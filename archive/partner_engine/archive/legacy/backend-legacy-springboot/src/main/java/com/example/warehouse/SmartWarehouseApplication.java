package com.example.warehouse;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.example.warehouse.mapper")
public class SmartWarehouseApplication {
    public static void main(String[] args) {
        SpringApplication.run(SmartWarehouseApplication.class, args);
    }
}
