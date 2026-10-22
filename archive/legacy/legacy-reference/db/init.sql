create database if not exists smart_warehouse default character set utf8mb4 collate utf8mb4_unicode_ci;
alter database smart_warehouse character set utf8mb4 collate utf8mb4_unicode_ci;
use smart_warehouse;
set names utf8mb4 collate utf8mb4_unicode_ci;

-- 说明：
-- 1. 本项目使用 MySQL 8，字段采用 snake_case；所有“修改时间”字段默认 null。
-- 2. 用户密码不明文入库，数据库保存 password_hash，前后端负责校验“首尾不能为空格、禁止中文”。
-- 3. 用户权限：0=仓库主管，1=仓库管理员，2=游客。
-- 4. 仓库存储类型：生鲜、小件商品、大件商品、电子产品、贵重物品。
-- 5. shelf.code 在 MVP 中作为“货架/货柜展示名称”使用，已改成贴近真实仓储场景的名称。

create table if not exists app_user (
    user_id bigint primary key auto_increment,
    username varchar(32) not null unique,
    password_hash varchar(120) not null,
    user_permission tinyint not null default 1,
    user_registration_time datetime not null default current_timestamp,
    user_permission_modified_time datetime null default null,
    constraint chk_app_user_username_ascii check (username regexp '^[A-Za-z!@#$%^&*._\\-+=]+$'),
    constraint chk_app_user_password_hash_not_blank check (trim(password_hash) <> ''),
    constraint chk_app_user_permission check (user_permission in (0, 1, 2))
) auto_increment = 1;

create table if not exists warehouse (
    warehouse_id bigint primary key auto_increment,
    warehouse_name varchar(100) not null unique,
    cabinet_count int not null default 1,
    warehouse_cabinet_id bigint not null,
    warehouse_storage_type varchar(20) not null,
    warehouse_created_time datetime not null default current_timestamp,
    warehouse_type_modified_time datetime null default null,
    width int not null,
    depth int not null,
    start_x int not null,
    start_y int not null,
    exit_x int not null,
    exit_y int not null,
    constraint chk_warehouse_cabinet_count check (cabinet_count >= 1),
    constraint chk_warehouse_storage_type check (warehouse_storage_type in ('生鲜', '小件商品', '大件商品', '电子产品', '贵重物品'))
) auto_increment = 1;

create table if not exists shelf (
    id bigint primary key auto_increment,
    warehouse_id bigint not null,
    code varchar(50) not null,
    category varchar(50) not null,
    x int not null,
    y int not null,
    layers int not null,
    capacity int not null,
    used int not null default 0,
    status varchar(20) not null default 'NORMAL',
    constraint fk_shelf_warehouse foreign key (warehouse_id) references warehouse(warehouse_id),
    constraint chk_shelf_layers check (layers >= 1),
    constraint chk_shelf_capacity check (capacity >= 1),
    constraint chk_shelf_used check (used >= 0 and used <= capacity)
) auto_increment = 1;

create table if not exists product (
    id bigint primary key auto_increment,
    sku varchar(50) not null,
    name varchar(100) not null,
    category varchar(50) not null,
    safe_stock int not null,
    turnover_score int not null,
    unique key uk_product_sku(sku),
    constraint chk_product_safe_stock check (safe_stock >= 0),
    constraint chk_product_turnover_score check (turnover_score between 0 and 100)
) auto_increment = 1;

create table if not exists inventory (
    id bigint primary key auto_increment,
    product_id bigint not null,
    shelf_id bigint not null,
    layer_no int not null,
    quantity int not null,
    unique key uk_product_shelf_layer(product_id, shelf_id, layer_no),
    constraint fk_inventory_product foreign key (product_id) references product(id),
    constraint fk_inventory_shelf foreign key (shelf_id) references shelf(id),
    constraint chk_inventory_layer_no check (layer_no >= 1),
    constraint chk_inventory_quantity check (quantity >= 0)
) auto_increment = 1;

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

create table if not exists inbound_task (
    id bigint primary key auto_increment,
    product_id bigint not null,
    quantity int not null,
    recommended_shelf_id bigint,
    status varchar(30) not null,
    created_at datetime not null default current_timestamp,
    constraint chk_inbound_quantity check (quantity > 0)
) auto_increment = 1;

create table if not exists outbound_order (
    id bigint primary key auto_increment,
    product_id bigint not null,
    quantity int not null,
    shelf_id bigint not null,
    status varchar(30) not null,
    path_json text,
    created_at datetime not null default current_timestamp,
    constraint chk_outbound_quantity check (quantity > 0)
) auto_increment = 1;

create table if not exists warning_record (
    id bigint primary key auto_increment,
    type varchar(30) not null,
    product_id bigint,
    shelf_id bigint,
    message varchar(500) not null,
    status varchar(30) not null,
    suggestion varchar(800),
    created_at datetime not null default current_timestamp
) auto_increment = 1;

create table if not exists replenishment_task (
    id bigint primary key auto_increment,
    warning_id bigint not null,
    product_id bigint not null,
    quantity int not null,
    status varchar(30) not null,
    created_at datetime not null default current_timestamp,
    constraint chk_replenishment_quantity check (quantity > 0)
) auto_increment = 1;


-- 为 warehouse.warehouse_cabinet_id 增加到 shelf.id 的外键，保证仓库表中的“仓库货柜id”能和货柜表真实绑定。
delimiter //
create procedure add_warehouse_cabinet_fk_if_missing()
begin
    if not exists (
        select 1
        from information_schema.table_constraints
        where constraint_schema = database()
          and table_name = 'warehouse'
          and constraint_name = 'fk_warehouse_cabinet'
    ) then
        alter table warehouse
            add constraint fk_warehouse_cabinet foreign key (warehouse_cabinet_id) references shelf(id);
    end if;
end//
delimiter ;
call add_warehouse_cabinet_fk_if_missing();
drop procedure add_warehouse_cabinet_fk_if_missing;

-- 初始化脚本必须幂等：Docker 首次创建数据库时会执行本文件。
-- 不要在 init.sql 中 truncate 业务表，避免误删已经产生的演示/注册数据。
-- 如确实需要重置演示数据，请手动执行 db/reset-demo.sql。

set foreign_key_checks = 0;

insert ignore into app_user(user_id, username, password_hash, user_permission, user_registration_time, user_permission_modified_time) values
(1, 'admin', 'c9mEVb+k1pkV5qzils25qxbi8o+IDHvjKLXkauflCLI=', 0, now(), null),
(2, 'demo', 'E0Yu/RJp+pny/KOcE74GCiiGWIFiAbbEDw+2+P34VUQ=', 1, now(), null),
(3, 'guest', 'N1YoO0OomORO1HKLjN44qRgTfqZyovGuPiUWEfnQTPU=', 2, now(), null);

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
