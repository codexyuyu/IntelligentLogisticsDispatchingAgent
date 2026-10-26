package com.example.warehouse.mapper;

import com.example.warehouse.entity.Warehouse;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

@Mapper
public interface WarehouseMapper {
    String WAREHOUSE_COLUMNS = "id, name as warehouseName, 0 as cabinetCount, null as warehouseCabinetId, " +
            "'生鲜' as warehouseStorageType, null as warehouseCreatedTime, null as warehouseTypeModifiedTime, " +
            "width, depth, start_x as startX, start_y as startY, exit_x as exitX, exit_y as exitY";

    @Select("select " + WAREHOUSE_COLUMNS + " from warehouse where id = #{id}")
    Warehouse findById(Long id);

    @Select("select " + WAREHOUSE_COLUMNS + " from warehouse order by id asc limit 1")
    Warehouse findFirst();

    @Update("update warehouse set name = #{storageType} where id = #{warehouseId}")
    int updateStorageType(@Param("warehouseId") Long warehouseId, @Param("storageType") String storageType);
}
