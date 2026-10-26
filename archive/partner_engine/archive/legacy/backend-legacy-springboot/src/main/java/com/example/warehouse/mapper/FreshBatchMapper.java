package com.example.warehouse.mapper;

import com.example.warehouse.entity.FreshBatch;
import org.apache.ibatis.annotations.*;

import java.util.List;

public interface FreshBatchMapper {

    @Select("""
        select
          b.*,
          p.product_name as productName,
          p.product_code as productCode,
          s.code as shelfCode
        from fresh_batch b
        join products p on p.id = b.product_id
        left join shelf s on s.id = b.shelf_id
        order by b.remaining_days asc, b.receive_time desc
    """)
    List<FreshBatch> findAllDetail();

    @Select("""
        select
          b.*,
          p.product_name as productName,
          p.product_code as productCode,
          s.code as shelfCode
        from fresh_batch b
        join products p on p.id = b.product_id
        left join shelf s on s.id = b.shelf_id
        where b.status in ('EXPIRING', 'EXPIRED', 'TEMP_ABNORMAL')
        order by b.remaining_days asc
    """)
    List<FreshBatch> findRiskBatches();

    @Select("select * from fresh_batch where id = #{id}")
    FreshBatch findById(@Param("id") Long id);

    @Insert("""
        insert into fresh_batch(
          batch_code, product_id, shelf_id, supplier, origin_place,
          receive_time, quantity_initial, quantity_remaining, purchase_price,
          quality_grade, initial_quality_score, storage_temperature, storage_humidity,
          predicted_storage_days, remaining_days, freshness_score, status
        )
        values(
          #{batchCode}, #{productId}, #{shelfId}, #{supplier}, #{originPlace},
          #{receiveTime}, #{quantityInitial}, #{quantityRemaining}, #{purchasePrice},
          #{qualityGrade}, #{initialQualityScore}, #{storageTemperature}, #{storageHumidity},
          #{predictedStorageDays}, #{remainingDays}, #{freshnessScore}, #{status}
        )
    """)
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(FreshBatch batch);
}
