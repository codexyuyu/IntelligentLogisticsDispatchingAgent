package com.example.warehouse.mapper;

import com.example.warehouse.entity.InboundTask;
import com.example.warehouse.entity.OutboundOrder;
import com.example.warehouse.entity.ReplenishmentTask;
import org.apache.ibatis.annotations.*;

import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface TaskMapper {
    @Insert("insert into inbound_task(product_id, quantity, recommended_shelf_id, status, created_at) values(#{productId}, #{quantity}, #{recommendedShelfId}, #{status}, #{createdAt})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertInbound(InboundTask task);

    @Update("update inbound_task set status = #{status} where id = #{id}")
    int updateInboundStatus(@Param("id") Long id, @Param("status") String status);

    @Insert("insert into outbound_order(product_id, quantity, shelf_id, status, path_json, created_at) values(#{productId}, #{quantity}, #{shelfId}, #{status}, #{pathJson}, #{createdAt})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertOutbound(OutboundOrder order);

    @Select("select * from outbound_order where id = #{id}")
    OutboundOrder findOutbound(Long id);

    @Update("update outbound_order set status = #{status} where id = #{id}")
    int updateOutboundStatus(@Param("id") Long id, @Param("status") String status);

    @Select("select count(*) from inbound_task where date(created_at) = curdate()")
    Integer countTodayInbound();

    @Select("select count(*) from outbound_order where date(created_at) = curdate()")
    Integer countTodayOutbound();

    @Insert("insert into replenishment_task(warning_id, product_id, quantity, status, created_at) values(#{warningId}, #{productId}, #{quantity}, #{status}, #{createdAt})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertReplenishment(ReplenishmentTask task);

    @Select("select * from outbound_order order by created_at desc limit 10")
    List<OutboundOrder> latestOutbound();

    @Select("select now()")
    LocalDateTime dbNow();
}
