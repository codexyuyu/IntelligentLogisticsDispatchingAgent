create database if not exists smart_warehouse default character set utf8mb4 collate utf8mb4_unicode_ci;
alter database smart_warehouse character set utf8mb4 collate utf8mb4_unicode_ci;
use smart_warehouse;
set names utf8mb4 collate utf8mb4_unicode_ci;

create table if not exists warehouse_maintenance (
    maintenance_id bigint primary key auto_increment,
    warehouse_id bigint not null,
    equipment_id bigint not null,
    equipment_name varchar(100) not null,
    equipment_maintenance_time datetime not null default current_timestamp,
    maintenance_staff_user_id bigint not null,
    equipment_maintenance_method varchar(800) not null,
    equipment_maintenance_result varchar(30) not null default 'COMPLETED',
    constraint fk_maintenance_warehouse foreign key (warehouse_id) references warehouse(warehouse_id),
    constraint fk_maintenance_staff foreign key (maintenance_staff_user_id) references app_user(user_id),
    constraint chk_maintenance_result check (equipment_maintenance_result in ('PLANNED', 'PROCESSING', 'COMPLETED', 'FAILED')),
    key idx_maintenance_warehouse(warehouse_id),
    key idx_maintenance_staff(maintenance_staff_user_id)
) auto_increment = 1;

set foreign_key_checks = 0;
truncate table replenishment_task;
truncate table warning_record;
truncate table outbound_order;
truncate table inbound_task;
truncate table warehouse_maintenance;
truncate table inventory;
truncate table product;
truncate table shelf;
truncate table warehouse;
-- 默认不清空 app_user，避免注册用户丢失。需要重置账号时再单独执行：truncate table app_user;
set foreign_key_checks = 1;

-- 由于 warehouse.warehouse_cabinet_id 与 shelf.id 双向绑定，重置演示数据时先临时关闭外键检查完成成组插入。
set foreign_key_checks = 0;

insert ignore into warehouse(warehouse_id, warehouse_name, cabinet_count, warehouse_cabinet_id, warehouse_storage_type, warehouse_created_time, warehouse_type_modified_time, width, depth, start_x, start_y, exit_x, exit_y) values
(1, '上海青浦综合智能仓-1', 12, 1, '小件商品', now(), null, 24, 14, 1, 1, 22, 1);

insert ignore into shelf(id, warehouse_id, code, category, x, y, layers, capacity, used, status) values
(1, 1, '冷链鲜食货架-F01', '生鲜', 8, 4, 4, 220, 70, 'WARNING'),
(2, 1, '冷链鲜食货架-F02', '生鲜', 8, 7, 4, 220, 30, 'NORMAL'),
(3, 1, '冷链鲜食货架-F03', '生鲜', 8, 10, 4, 220, 0, 'NORMAL'),
(4, 1, '日用百货货架-S01', '小件商品', 12, 4, 4, 260, 90, 'WARNING'),
(5, 1, '日用百货货架-S02', '小件商品', 12, 7, 4, 260, 45, 'NORMAL'),
(6, 1, '日用百货货架-S03', '小件商品', 12, 10, 4, 260, 0, 'NORMAL'),
(7, 1, '电子配件防静电柜-E01', '电子产品', 16, 4, 4, 140, 18, 'WARNING'),
(8, 1, '电子配件防静电柜-E02', '电子产品', 16, 7, 4, 140, 20, 'NORMAL'),
(9, 1, '电子配件防静电柜-E03', '电子产品', 16, 10, 4, 140, 0, 'NORMAL'),
(10, 1, '家电大件托盘区-L01', '大件商品', 20, 4, 4, 60, 12, 'NORMAL'),
(11, 1, '家电大件托盘区-L02', '大件商品', 20, 7, 4, 60, 20, 'NORMAL'),
(12, 1, '贵重物品加锁货柜-V01', '贵重物品', 20, 10, 4, 80, 18, 'NORMAL');

insert ignore into product(id, sku, name, category, safe_stock, turnover_score) values
(1, 'FRESH-MILK-950', '每日鲜语低温鲜牛奶950ml', '生鲜', 120, 96),
(2, 'SMALL-TISSUE-6P', '心相印茶语抽纸6包装', '小件商品', 160, 88),
(3, 'LARGE-WASHER-10KG', '海尔10公斤滚筒洗衣机', '大件商品', 30, 62),
(4, 'ELEC-EARBUDS-B6', '小米Redmi Buds 6耳机', '电子产品', 40, 82),
(5, 'VALUE-WATCH-S10', 'Apple Watch Series 10智能手表', '贵重物品', 15, 70);

insert ignore into inventory(product_id, shelf_id, layer_no, quantity) values
(1, 1, 1, 70),
(1, 2, 2, 30),
(2, 4, 1, 90),
(2, 5, 2, 45),
(3, 10, 1, 12),
(3, 11, 2, 20),
(4, 7, 1, 18),
(4, 8, 1, 20),
(5, 12, 1, 18);

insert ignore into warehouse_maintenance(maintenance_id, warehouse_id, equipment_id, equipment_name, equipment_maintenance_time, maintenance_staff_user_id, equipment_maintenance_method, equipment_maintenance_result) values
(1, 1, 1, '堆垛机-01', now() - interval 2 day, 2, '检查升降链条张紧度，补充润滑油，复位限位传感器。', 'COMPLETED'),
(2, 1, 2, '冷链温湿度传感器-F01', now() - interval 1 day, 2, '校准温度探头，确认 2-8℃ 报警阈值正常。', 'COMPLETED');

insert ignore into warning_record(id, type, product_id, shelf_id, message, status, suggestion, created_at) values
(1, 'LOW_STOCK', 1, 1, '每日鲜语低温鲜牛奶950ml 当前库存 100，低于安全库存 120。', 'OPEN', '建议补货 140 件，并优先放到冷链鲜食货架-F01 或冷链鲜食货架-F02。', now()),
(2, 'LOW_STOCK', 2, 4, '心相印茶语抽纸6包装 当前库存 135，低于安全库存 160。', 'OPEN', '建议补货 185 件，并优先放到日用百货货架-S01 或日用百货货架-S02。', now()),
(3, 'LOW_STOCK', 4, 7, '小米Redmi Buds 6耳机 当前库存 38，低于安全库存 40。', 'OPEN', '建议补货 42 件，并优先放到电子配件防静电柜-E01 或电子配件防静电柜-E02。', now());

set foreign_key_checks = 1;
