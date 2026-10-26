-- 运输调度增量升级：已创建 schedule_assignment 的数据库直接执行本脚本
USE smart_warehouse;

SET @db := DATABASE();

SET @sql1 := (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE schedule_assignment ADD COLUMN vehicle_id BIGINT NULL COMMENT ''运输车辆ID'' AFTER order_id',
    'SELECT 1')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=@db AND TABLE_NAME='schedule_assignment' AND COLUMN_NAME='vehicle_id'
);
PREPARE stmt FROM @sql1; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql2 := (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE schedule_assignment ADD COLUMN route_id BIGINT NULL COMMENT ''运输路线ID'' AFTER vehicle_id',
    'SELECT 1')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=@db AND TABLE_NAME='schedule_assignment' AND COLUMN_NAME='route_id'
);
PREPARE stmt FROM @sql2; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql3 := (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE schedule_assignment ADD COLUMN transport_cost DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT ''运输成本'' AFTER storage_cost',
    'SELECT 1')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=@db AND TABLE_NAME='schedule_assignment' AND COLUMN_NAME='transport_cost'
);
PREPARE stmt FROM @sql3; EXECUTE stmt; DEALLOCATE PREPARE stmt;


CREATE TABLE IF NOT EXISTS cold_room_time_slot (
  id BIGINT NOT NULL AUTO_INCREMENT,
  cold_room_id BIGINT NOT NULL,
  start_time DATETIME NOT NULL,
  end_time DATETIME NOT NULL,
  slot_type VARCHAR(30) NOT NULL DEFAULT 'AVAILABLE',
  batch_id BIGINT NULL,
  schedule_id BIGINT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'FREE',
  remark VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_slot_room_time (cold_room_id,start_time,end_time),
  KEY idx_slot_status (status),
  CONSTRAINT fk_slot_room FOREIGN KEY (cold_room_id) REFERENCES cold_room(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_slot_batch FOREIGN KEY (batch_id) REFERENCES schedule_batch(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS vehicle (
  id BIGINT NOT NULL AUTO_INCREMENT,
  vehicle_code VARCHAR(50) NOT NULL UNIQUE,
  vehicle_type VARCHAR(30) NOT NULL DEFAULT '冷藏车',
  capacity DECIMAL(12,2) NOT NULL,
  volume DECIMAL(12,2) NULL,
  refrigerated BIT NOT NULL DEFAULT b'1',
  min_temperature DECIMAL(6,2) NULL,
  max_temperature DECIMAL(6,2) NULL,
  current_location VARCHAR(100) NULL,
  available_from DATETIME NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE',
  cost_per_km DECIMAL(10,2) NOT NULL DEFAULT 2.50,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS transport_route (
  id BIGINT NOT NULL AUTO_INCREMENT,
  route_code VARCHAR(50) NOT NULL UNIQUE,
  start_node VARCHAR(100) NOT NULL,
  end_node VARCHAR(100) NOT NULL,
  distance_km DECIMAL(10,2) NOT NULL,
  estimated_minutes INT NOT NULL,
  road_status VARCHAR(20) NOT NULL DEFAULT 'NORMAL',
  road_factor DECIMAL(6,3) NOT NULL DEFAULT 1.000,
  toll_cost DECIMAL(10,2) NOT NULL DEFAULT 0,
  refrigerated_required BIT NOT NULL DEFAULT b'0',
  status VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO vehicle(vehicle_code,vehicle_type,capacity,volume,refrigerated,min_temperature,max_temperature,current_location,available_from,status,cost_per_km) VALUES
('V01','冷藏车',1000,18,1,0,8,'县域产地集配中心',NOW(),'AVAILABLE',2.50),
('V02','冷藏车',800,15,1,0,6,'中心冷库A',NOW(),'AVAILABLE',2.30),
('V03','冷藏车',500,10,1,2,8,'乡镇冷库B',NOW(),'AVAILABLE',2.00);

INSERT IGNORE INTO transport_route(route_code,start_node,end_node,distance_km,estimated_minutes,road_status,road_factor,toll_cost,refrigerated_required,status) VALUES
('R001','县域产地集配中心','中心冷库A',18.50,35,'NORMAL',1.000,0,1,'AVAILABLE'),
('R002','县域产地集配中心','乡镇冷库B',26.00,50,'NORMAL',1.000,5.00,1,'AVAILABLE'),
('R003','中心冷库A','县城生鲜超市',22.00,40,'NORMAL',1.000,0,1,'AVAILABLE'),
('R004','中心冷库A','区域批发市场',35.00,60,'CONGESTED',1.350,8.00,1,'AVAILABLE'),
('R005','乡镇冷库B','社区电商配送中心',15.00,30,'NORMAL',1.000,0,1,'AVAILABLE');

SELECT 'vehicle' AS table_name, COUNT(*) AS record_count FROM vehicle
UNION ALL
SELECT 'transport_route', COUNT(*) FROM transport_route
UNION ALL
SELECT 'schedule_assignment', COUNT(*) FROM schedule_assignment;
