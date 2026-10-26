package com.example.warehouse.mapper;

import com.example.warehouse.entity.WarningRecord;
import org.apache.ibatis.annotations.*;
import org.apache.ibatis.annotations.Select;
import java.util.List;

public interface WarningMapper {

    @Select("""
    select count(*)
    from warning_record
    where status = 'OPEN'
      and type = 'LOW_STOCK'
""")
    Integer countOpenLowStock();
    @Select("""
        select
          w.*,
          p.product_name as productName,
          s.code as shelfCode
        from warning_record w
        left join products p on p.id = w.product_id
        left join shelf s on s.id = w.shelf_id
        order by w.created_at desc
    """)
    List<WarningRecord> findAll();

    @Select("""
        select
          w.*,
          p.product_name as productName,
          s.code as shelfCode
        from warning_record w
        left join products p on p.id = w.product_id
        left join shelf s on s.id = w.shelf_id
        where w.status = 'OPEN'
        order by w.created_at desc
    """)
    List<WarningRecord> findOpen();

    @Select("select count(*) from warning_record where status = 'OPEN'")
    Integer countOpen();

    @Select("""
        select count(*)
        from warning_record
        where status = 'OPEN'
          and type = #{type}
          and product_id = #{productId}
    """)
    Integer countOpenByTypeAndProduct(@Param("type") String type,
                                      @Param("productId") Long productId);

    @Select("select * from warning_record where id = #{id}")
    WarningRecord findById(@Param("id") Long id);

    @Insert("""
        insert into warning_record(type, product_id, shelf_id, message, suggestion, status, created_at)
        values(#{type}, #{productId}, #{shelfId}, #{message}, #{suggestion}, #{status}, #{createdAt})
    """)
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(WarningRecord record);

    @Update("update warning_record set status = #{status} where id = #{id}")
    int updateStatus(@Param("id") Long id, @Param("status") String status);
}
