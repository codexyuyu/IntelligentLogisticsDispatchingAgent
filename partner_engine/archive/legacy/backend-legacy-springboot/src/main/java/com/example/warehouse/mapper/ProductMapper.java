package com.example.warehouse.mapper;

import com.example.warehouse.entity.Product;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

public interface ProductMapper {

    @Select("""
        select
          id,
          product_code as productCode,
          product_name as productName,
          category,
          unit,
          safety_stock as safetyStock,
          create_time as createTime,
          storage_type as storageType,
          min_temperature as minTemperature,
          max_temperature as maxTemperature,
          min_humidity as minHumidity,
          max_humidity as maxHumidity,
          base_shelf_life_days as baseShelfLifeDays,
          perishable
        from products
        order by id
    """)
    List<Product> findAll();

    @Select("""
        select
          id,
          product_code as productCode,
          product_name as productName,
          category,
          unit,
          safety_stock as safetyStock,
          create_time as createTime,
          storage_type as storageType,
          min_temperature as minTemperature,
          max_temperature as maxTemperature,
          min_humidity as minHumidity,
          max_humidity as maxHumidity,
          base_shelf_life_days as baseShelfLifeDays,
          perishable
        from products
        where id = #{id}
    """)
    Product findById(@Param("id") Long id);

    @Select("""
        select
          id,
          product_code as productCode,
          product_name as productName,
          category,
          unit,
          safety_stock as safetyStock,
          create_time as createTime,
          storage_type as storageType,
          min_temperature as minTemperature,
          max_temperature as maxTemperature,
          min_humidity as minHumidity,
          max_humidity as maxHumidity,
          base_shelf_life_days as baseShelfLifeDays,
          perishable
        from products
        where product_name like concat('%', #{keyword}, '%')
           or product_code like concat('%', #{keyword}, '%')
        order by id
    """)
    List<Product> search(@Param("keyword") String keyword);
}
