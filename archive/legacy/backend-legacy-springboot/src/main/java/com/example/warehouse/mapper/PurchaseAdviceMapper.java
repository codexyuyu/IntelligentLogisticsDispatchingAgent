package com.example.warehouse.mapper;

import com.example.warehouse.entity.PurchaseAdvice;
import org.apache.ibatis.annotations.*;

import java.util.List;

public interface PurchaseAdviceMapper {

    @Select("select * from purchase_advice order by created_at desc")
    List<PurchaseAdvice> findLatest();

    @Delete("delete from purchase_advice")
    int clearAll();

    @Insert("""
        insert into purchase_advice(
          product_id, product_name, current_inventory, safety_stock,
          avg_market_price, price_change_rate, price_trend,
          advice_type, suggested_quantity, reason
        )
        values(
          #{productId}, #{productName}, #{currentInventory}, #{safetyStock},
          #{avgMarketPrice}, #{priceChangeRate}, #{priceTrend},
          #{adviceType}, #{suggestedQuantity}, #{reason}
        )
    """)
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(PurchaseAdvice advice);
}
