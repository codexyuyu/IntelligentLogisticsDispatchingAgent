-- 冷链协同调度 MVP 数据库增量脚本
use smart_warehouse;

create table if not exists schedule_batch (
  id bigint primary key auto_increment,
  batch_code varchar(50) not null unique,
  product varchar(50) not null,
  grade varchar(20) not null,
  quantity decimal(12,2) not null,
  expected_inbound datetime not null,
  min_temperature decimal(6,2) not null,
  max_temperature decimal(6,2) not null,
  max_storage_days int not null default 7,
  remaining_shelf_days decimal(8,2) not null default 7,
  pre_cooling_required bit not null default b'0',
  status varchar(20) not null default 'PENDING',
  created_at datetime not null default current_timestamp,
  updated_at datetime null default null on update current_timestamp
);

create table if not exists schedule_order (
  id bigint primary key auto_increment,
  order_code varchar(50) not null unique,
  customer varchar(100) not null,
  product varchar(50) not null,
  quantity decimal(12,2) not null,
  grade varchar(20) not null,
  latest_delivery datetime not null,
  min_shelf_life_days decimal(8,2) not null default 1,
  status varchar(20) not null default 'PENDING',
  created_at datetime not null default current_timestamp,
  updated_at datetime null default null on update current_timestamp
);

create table if not exists cold_room (
  id bigint primary key auto_increment,
  room_code varchar(30) not null unique,
  warehouse_name varchar(100) not null,
  capacity decimal(12,2) not null,
  used_capacity decimal(12,2) not null default 0,
  min_temperature decimal(6,2) not null,
  max_temperature decimal(6,2) not null,
  supported_products varchar(255) not null,
  pre_cooling_supported bit not null default b'0',
  cleaning_hours decimal(6,2) not null default 2,
  switch_hours decimal(6,2) not null default 1,
  device_status varchar(20) not null default 'NORMAL',
  cost_per_ton_hour decimal(10,2) not null default 1,
  created_at datetime not null default current_timestamp
);

create table if not exists cold_room_time_slot (
  id bigint primary key auto_increment,
  cold_room_id bigint not null,
  start_time datetime not null,
  end_time datetime not null,
  slot_type varchar(30) not null default 'AVAILABLE',
  batch_id bigint null,
  schedule_id bigint null,
  status varchar(20) not null default 'FREE',
  remark varchar(255) null,
  created_at datetime not null default current_timestamp,
  index idx_slot_room_time(cold_room_id,start_time,end_time),
  index idx_slot_status(status),
  foreign key (cold_room_id) references cold_room(id) on delete cascade on update cascade,
  foreign key (batch_id) references schedule_batch(id) on delete set null on update cascade
);

create table if not exists schedule_plan (
  id bigint primary key auto_increment,
  schedule_code varchar(50) not null unique,
  schedule_type varchar(20) not null default 'NORMAL',
  objective varchar(100) not null,
  planning_start datetime not null,
  planning_end datetime not null,
  status varchar(20) not null default 'DRAFT',
  utilization decimal(8,2) not null default 0,
  fulfillment decimal(8,2) not null default 0,
  on_time_inbound decimal(8,2) not null default 0,
  total_cost decimal(12,2) not null default 0,
  high_risk_count int not null default 0,
  changed_count int not null default 0,
  solve_ms bigint not null default 0,
  original_plan_id bigint null,
  created_at datetime not null default current_timestamp
);

create table if not exists schedule_assignment (
  id bigint primary key auto_increment,
  schedule_id bigint not null,
  batch_id bigint not null,
  cold_room_id bigint not null,
  order_id bigint null,
  vehicle_id bigint null,
  route_id bigint null,
  planned_inbound datetime not null,
  planned_outbound datetime not null,
  allocated_quantity decimal(12,2) not null,
  storage_cost decimal(12,2) not null default 0,
  transport_cost decimal(12,2) not null default 0,
  quality_risk varchar(20) not null default 'LOW',
  feasible bit not null default b'1',
  change_note varchar(500) null,
  foreign key (schedule_id) references schedule_plan(id),
  foreign key (batch_id) references schedule_batch(id),
  foreign key (cold_room_id) references cold_room(id),
  foreign key (order_id) references schedule_order(id)
);


create table if not exists vehicle (
  id bigint primary key auto_increment,
  vehicle_code varchar(50) not null unique,
  vehicle_type varchar(30) not null default '冷藏车',
  capacity decimal(12,2) not null,
  volume decimal(12,2) null,
  refrigerated bit not null default b'1',
  min_temperature decimal(6,2) null,
  max_temperature decimal(6,2) null,
  current_location varchar(100) null,
  available_from datetime null,
  status varchar(20) not null default 'AVAILABLE',
  cost_per_km decimal(10,2) not null default 2.50,
  created_at datetime not null default current_timestamp,
  updated_at datetime null default null on update current_timestamp
);

create table if not exists transport_route (
  id bigint primary key auto_increment,
  route_code varchar(50) not null unique,
  start_node varchar(100) not null,
  end_node varchar(100) not null,
  distance_km decimal(10,2) not null,
  estimated_minutes int not null,
  road_status varchar(20) not null default 'NORMAL',
  road_factor decimal(6,3) not null default 1.000,
  toll_cost decimal(10,2) not null default 0,
  refrigerated_required bit not null default b'0',
  status varchar(20) not null default 'AVAILABLE',
  created_at datetime not null default current_timestamp,
  updated_at datetime null default null on update current_timestamp
);

create table if not exists abnormal_event (
  id bigint primary key auto_increment,
  event_code varchar(50) not null unique,
  event_type varchar(30) not null,
  source_id varchar(50) not null,
  event_time datetime not null,
  impact_description varchar(500) not null,
  severity varchar(20) not null default 'MEDIUM',
  status varchar(20) not null default 'PENDING_RESCHEDULE',
  created_at datetime not null default current_timestamp
);


insert ignore into vehicle(vehicle_code,vehicle_type,capacity,volume,refrigerated,min_temperature,max_temperature,current_location,available_from,status,cost_per_km) values
('V01','冷藏车',1000,18,1,0,8,'县域产地集配中心',NOW(),'AVAILABLE',2.50),
('V02','冷藏车',800,15,1,0,6,'中心冷库A',NOW(),'AVAILABLE',2.30),
('V03','冷藏车',500,10,1,2,8,'乡镇冷库B',NOW(),'AVAILABLE',2.00);

insert ignore into transport_route(route_code,start_node,end_node,distance_km,estimated_minutes,road_status,road_factor,toll_cost,refrigerated_required,status) values
('R001','县域产地集配中心','中心冷库A',18.50,35,'NORMAL',1.000,0,1,'AVAILABLE'),
('R002','县域产地集配中心','乡镇冷库B',26.00,50,'NORMAL',1.000,5.00,1,'AVAILABLE'),
('R003','中心冷库A','县城生鲜超市',22.00,40,'NORMAL',1.000,0,1,'AVAILABLE'),
('R004','中心冷库A','区域批发市场',35.00,60,'CONGESTED',1.350,8.00,1,'AVAILABLE'),
('R005','乡镇冷库B','社区电商配送中心',15.00,30,'NORMAL',1.000,0,1,'AVAILABLE');

insert ignore into schedule_batch(id,batch_code,product,grade,quantity,expected_inbound,min_temperature,max_temperature,max_storage_days,remaining_shelf_days,pre_cooling_required,status) values
(1,'BAT-OR-001','脐橙','A',180,DATE_ADD(NOW(),INTERVAL 4 HOUR),2,6,14,12,1,'PENDING'),
(2,'BAT-GR-001','葡萄','A',80,DATE_ADD(NOW(),INTERVAL 28 HOUR),0,4,7,6,1,'PENDING');

insert ignore into schedule_order(id,order_code,customer,product,quantity,grade,latest_delivery,min_shelf_life_days,status) values
(1,'ORD-001','县城生鲜超市','脐橙',100,'A',DATE_ADD(NOW(),INTERVAL 4 DAY),5,'PENDING'),
(2,'ORD-002','区域批发市场','葡萄',60,'A',DATE_ADD(NOW(),INTERVAL 3 DAY),3,'PENDING'),
(3,'ORD-003','社区电商平台','脐橙',80,'B及以上',DATE_ADD(NOW(),INTERVAL 6 DAY),4,'PENDING');

insert ignore into cold_room(id,room_code,warehouse_name,capacity,used_capacity,min_temperature,max_temperature,supported_products,pre_cooling_supported,cleaning_hours,switch_hours,device_status,cost_per_ton_hour) values
(1,'CR-01','中心冷库A',300,120,2,6,'脐橙,柑橘类',1,2,1,'NORMAL',1.8),
(2,'CR-02','中心冷库A',220,80,0,4,'葡萄,浆果类',1,3,2,'NORMAL',2.2),
(3,'CR-03','乡镇冷库B',260,0,2,8,'脐橙,柑橘类,综合',0,2,2,'NORMAL',1.5),
(4,'CR-04','乡镇冷库B',180,120,0,5,'葡萄,综合',0,3,2,'MAINTENANCE',1.6);
