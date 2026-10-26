package com.example.warehouse.mapper;

import com.example.warehouse.entity.Inventory;
import org.apache.ibatis.annotations.*;

import java.util.List;

public interface InventoryMapper {

    @Select("""
        select
          i.*,
          p.product_name as productName,
          p.product_code as sku,
          p.category as category,
          s.code as shelfCode
        from inventory i
        join products p on p.id = i.product_id
        left join shelf s on s.id = i.shelf_id
        order by i.update_time desc
    """)
    List<Inventory> findAllDetail();

    @Select("""
        select
          i.*,
          p.product_name as productName,
          p.product_code as sku,
          p.category as category,
          s.code as shelfCode
        from inventory i
        join products p on p.id = i.product_id
        left join shelf s on s.id = i.shelf_id
        where i.product_id = #{productId}
        order by i.update_time desc
    """)
    List<Inventory> findByProductId(@Param("productId") Long productId);

    @Select("""
        select
          i.*,
          p.product_name as productName,
          p.product_code as sku,
          p.category as category,
          s.code as shelfCode
        from inventory i
        join products p on p.id = i.product_id
        left join shelf s on s.id = i.shelf_id
        where i.shelf_id = #{shelfId}
        order by i.layer_no
    """)
    List<Inventory> findByShelfId(@Param("shelfId") Long shelfId);

    @Select("select coalesce(sum(quantity), 0) from inventory")
    Integer totalStock();

    @Select("select coalesce(sum(quantity), 0) from inventory where product_id = #{productId}")
    Integer totalByProduct(@Param("productId") Long productId);

    @Select("""
        select *
        from inventory
        where product_id = #{productId}
          and shelf_id = #{shelfId}
          and layer_no = #{layerNo}
        limit 1
    """)
    Inventory findOne(@Param("productId") Long productId,
                      @Param("shelfId") Long shelfId,
                      @Param("layerNo") Integer layerNo);

    @Insert("""
        insert into inventory(product_id, shelf_id, layer_no, quantity)
        values(#{productId}, #{shelfId}, #{layerNo}, #{quantity})
    """)
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(Inventory inventory);

    @Update("update inventory set quantity = quantity + #{delta} where id = #{id}")
    int addQuantity(@Param("id") Long id, @Param("delta") Integer delta);

    @Update("update inventory set quantity = greatest(quantity - #{delta}, 0) where id = #{id}")
    int reduceQuantity(@Param("id") Long id, @Param("delta") Integer delta);
}
