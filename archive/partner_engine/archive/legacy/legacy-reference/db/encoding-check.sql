create database if not exists smart_warehouse default character set utf8mb4 collate utf8mb4_unicode_ci;
alter database smart_warehouse character set utf8mb4 collate utf8mb4_unicode_ci;
use smart_warehouse;
set names utf8mb4 collate utf8mb4_unicode_ci;

-- 用途：检查前端显示乱码是否来自数据库连接或数据库中已经写入的中文数据。
-- 执行方式：先执行 db/init.sql，再执行本文件。重点看 character_set_client / connection / results 是否为 utf8mb4。
show variables like 'character_set%';
show variables like 'collation%';

select 'warehouse' as data_source, warehouse_id as row_id, warehouse_name as chinese_text, hex(warehouse_name) as utf8_hex
from warehouse
order by warehouse_id;

select 'shelf' as data_source, id as row_id, category as chinese_text, hex(category) as utf8_hex
from shelf
order by id;

select 'product' as data_source, id as row_id, name as chinese_text, hex(name) as utf8_hex
from product
order by id;

select 'warning_record' as data_source, id as row_id, message as chinese_text, hex(message) as utf8_hex
from warning_record
order by id;
