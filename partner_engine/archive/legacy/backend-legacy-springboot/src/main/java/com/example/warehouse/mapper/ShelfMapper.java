package com.example.warehouse.mapper;

import com.example.warehouse.entity.Shelf;
import org.apache.ibatis.annotations.*;

import java.math.BigDecimal;
import java.util.List;

public interface ShelfMapper {

    @Select("select * from shelf order by id")
    List<Shelf> findAll();

    @Select("select * from shelf where id = #{id}")
    Shelf findById(@Param("id") Long id);

    @Select("""
        select *
        from shelf
        where coalesce(capacity, 0) - coalesce(used, 0) >= #{quantity}
        order by id
    """)
    List<Shelf> findAvailable(@Param("quantity") Integer quantity);


    @Update("update shelf set used = used + #{quantity} where id = #{id}")
    int addUsed(@Param("id") Long id, @Param("quantity") Integer quantity);

    @Update("update shelf set used = greatest(used - #{quantity}, 0) where id = #{id}")
    int reduceUsed(@Param("id") Long id, @Param("quantity") Integer quantity);

    @Update("update shelf set status = #{status} where id = #{id}")
    int updateStatus(@Param("id") Long id, @Param("status") String status);

    @Update("""
        update shelf
        set current_temperature = #{temperature},
            current_humidity = #{humidity}
        where id = #{shelfId}
    """)
    int updateEnvironment(@Param("shelfId") Long shelfId,
                          @Param("temperature") BigDecimal temperature,
                          @Param("humidity") BigDecimal humidity);
}
