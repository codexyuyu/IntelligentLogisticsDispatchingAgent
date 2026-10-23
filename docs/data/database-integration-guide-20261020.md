# 数据库集成与 DTO 映射指南

**版本**: 1.0  
**日期**: 2026-10-20  
**适用阶段**: P03-P04  
**前置条件**: P02 领域模型已交付、G01 已签收

---

## 概述

本文档说明如何将 `data/preparation/competition-2026/` 数据包集成到正式 PostgreSQL 环境，并建立从 Synthetic Bundle → 领域模型 → 正式数据库的完整映射链路。

### 数据流向

```
Synthetic Bundle (JSON)
    ↓ [DTO 转换]
Preparation DTO
    ↓ [验证 + FK 完整性]
PostgreSQL competition_preparation schema
    ↓ [映射转换]
正式业务表 (logistics schema)
    ↓ [快照固定]
TestFixture + 版本化引用
```

---

## 第一部分：数据包概览

### 数据规模

| 场景 | 订单数 | 货物 | 仓库 | 车辆 | 司机 | 工人 | 工序 |
|-----|-------|------|------|------|------|------|------|
| T1  | 2     | 2    | 1    | 2    | 2    | 1    | —    |
| A8  | 8     | 8    | 2    | 4    | 4    | 2    | —    |
| B20 | 20    | 20   | 2    | 4    | 4    | 3    | 100  |
| **合计** | **30** | **30** | **2** | **4** | **4** | **3** | **100** |

### 关键特征

- **数据源**: Synthetic（非真实业务数据）
- **生成方法**: UUID5 + seed=42（可复现）
- **时间基准**: UTC epoch，整数单位（秒）
- **验证状态**: 18 项本地校验通过

### 生成文件清单

```
generated/
├── bundle.json                 # 主数据集 (完整实体 + 关系)
├── entities.csv                # 导入证据 (326 条记录)
├── entity_coverage.json        # 32 实体覆盖表
├── preview.sqlite3             # SQLite 预览库
├── postgres_staging.sql        # PostgreSQL 导入脚本
├── postgres_create_schema.sql  # Schema 创建
├── graph_nodes.csv             # 关系图节点
├── graph_edges.csv             # 关系图边
└── W1.json                     # W1 手算 Oracle
```

---

## 第二部分：DTO 映射规范

### 2.1 核心映射类

#### Bundle 实体 → DTO 转换

```python
# 位置: apps/packages/logistics_contracts/src/logistics_contracts/dtos/preparation.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

# ===== Enum 映射 =====

class PreparedCargoTypeEnum(str, Enum):
    """从 bundle.json 的 cargo.type 映射"""
    GENERAL = "GENERAL"           # 默认
    PERISHABLE_FROZEN = "FROZEN"  # 冷冻
    PERISHABLE_CHILLED = "CHILLED" # 冷鲜
    # 待批准: HAZMAT, FRAGILE, ...

class PreparedTemperatureZone(str, Enum):
    """仓库与车辆的温区"""
    AMBIENT = "AMBIENT"            # 常温
    CHILLED = "CHILLED"           # 0-4°C
    FROZEN = "FROZEN"             # -18°C 或以下

# ===== DTO 类定义 =====

@dataclass
class PreparedWarehouse:
    """仓库"""
    warehouse_id: str              # UUID
    name: str
    location_name: str
    zones: List['PreparedWarehouseZone']
    docks: List['PreparedDock']
    workers: List['PreparedWorker']
    equipment: List['PreparedEquipment']
    
@dataclass
class PreparedWarehouseZone:
    """温区 + 库位"""
    zone_id: str
    zone_type: PreparedTemperatureZone
    capacity_kg: int
    capacity_volume_m3: float
    locations: List['PreparedStorageLocation']

@dataclass
class PreparedStorageLocation:
    """库位"""
    location_id: str
    zone_id: str
    capacity_kg: int
    initial_stock: List['PreparedInventory']

@dataclass
class PreparedDock:
    """月台"""
    dock_id: str
    warehouse_id: str
    name: str

@dataclass
class PreparedVehicle:
    """车辆"""
    vehicle_id: str
    plate: str
    capacity_kg: int
    capacity_m3: float
    temperature_zones: List[PreparedTemperatureZone]
    driver_id: str

@dataclass
class PreparedOrder:
    """订单"""
    order_id: str
    cargo: 'PreparedCargo'
    source_warehouse_id: str
    destination_warehouse_id: str
    time_window_start: datetime
    time_window_end: datetime

@dataclass
class PreparedCargo:
    """货物"""
    cargo_id: str
    order_id: str
    weight_kg: int
    volume_m3: float
    cargo_type: PreparedCargoTypeEnum
    required_temperature: PreparedTemperatureZone

@dataclass
class PreparedInventory:
    """初始库存"""
    location_id: str
    cargo_type: PreparedCargoTypeEnum
    quantity_kg: int
    shelf_life_days: Optional[int]
    created_at: datetime

@dataclass
class PreparedWorker:
    """工人"""
    worker_id: str
    warehouse_id: str
    name: str
    skills: List[str]

@dataclass
class PreparedEquipment:
    """设备"""
    equipment_id: str
    warehouse_id: str
    kind: str  # "SHELF", "DOCK_LIFT", "CONVEYOR", etc.
    capacity: Optional[int]
    maintenance_windows: List[tuple]  # [(start, end), ...]

@dataclass
class PreparedBundle:
    """完整数据包"""
    scenario_name: str  # "T1", "A8", "B20"
    generated_at: datetime
    seed: int
    warehouses: List[PreparedWarehouse]
    vehicles: List[PreparedVehicle]
    orders: List[PreparedOrder]
    workers: List[PreparedWorker]
    equipment_catalog: List[PreparedEquipment]
```

### 2.2 转换函数

```python
# 位置: apps/backend/src/logistics_persistence/converters/preparation_converter.py

import json
from typing import Dict, Any
from logistics_contracts.dtos.preparation import (
    PreparedBundle, PreparedWarehouse, PreparedVehicle, PreparedOrder
)

class PreparationBundleConverter:
    """从 bundle.json → PreparedBundle DTO"""
    
    @staticmethod
    def from_json_file(path: str) -> PreparedBundle:
        """
        加载 bundle.json 并转换为 DTO
        
        Args:
            path: bundle.json 文件路径
            
        Returns:
            PreparedBundle 对象
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: JSON 结构不符合预期
            TypeError: 类型转换失败
        """
        with open(path, 'r', encoding='utf-8') as f:
            bundle_dict = json.load(f)
        
        return PreparationBundleConverter.from_dict(bundle_dict)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> PreparedBundle:
        """
        从字典转换为 PreparedBundle
        
        验证逻辑：
        1. 检查必需顶级字段
        2. 转换各实体集合
        3. 验证 FK 完整性
        4. 检查时间窗合理性
        """
        
        # 验证结构
        required_keys = {'scenario', 'generated_at', 'warehouses', 'vehicles', 'orders'}
        if not required_keys.issubset(data.keys()):
            missing = required_keys - data.keys()
            raise ValueError(f"Missing required keys: {missing}")
        
        # 转换实体
        warehouses = [
            PreparationBundleConverter._convert_warehouse(w)
            for w in data['warehouses']
        ]
        
        vehicles = [
            PreparationBundleConverter._convert_vehicle(v)
            for v in data['vehicles']
        ]
        
        orders = [
            PreparationBundleConverter._convert_order(o)
            for o in data['orders']
        ]
        
        # 验证 FK 完整性
        warehouse_ids = {w.warehouse_id for w in warehouses}
        vehicle_ids = {v.vehicle_id for v in vehicles}
        
        for order in orders:
            if order.source_warehouse_id not in warehouse_ids:
                raise ValueError(f"Invalid source warehouse: {order.source_warehouse_id}")
            if order.destination_warehouse_id not in warehouse_ids:
                raise ValueError(f"Invalid destination warehouse: {order.destination_warehouse_id}")
        
        return PreparedBundle(
            scenario_name=data['scenario'],
            generated_at=datetime.fromisoformat(data['generated_at']),
            seed=data.get('seed', 42),
            warehouses=warehouses,
            vehicles=vehicles,
            orders=orders,
            workers=data.get('workers', []),
            equipment_catalog=data.get('equipment', [])
        )
    
    @staticmethod
    def _convert_warehouse(data: Dict) -> PreparedWarehouse:
        """转换单个仓库"""
        # 实现细节...
        pass
    
    @staticmethod
    def _convert_vehicle(data: Dict) -> PreparedVehicle:
        """转换单个车辆"""
        # 实现细节...
        pass
    
    @staticmethod
    def _convert_order(data: Dict) -> PreparedOrder:
        """转换单个订单"""
        # 实现细节...
        pass
```

---

## 第三部分：PostgreSQL 导入流程

### 3.1 环境启动

```bash
# 1. 设置环境变量
export LOGISTICS_PREP_PASSWORD="your-secure-password-here"
export COMPOSE_FILE="deploy/data-preparation-2026/compose.yaml"

# 2. 启动 PostgreSQL 容器
docker compose up -d --wait postgres

# 3. 验证连接
docker compose exec postgres psql -U logistics_prep -d logistics_prep_test \
  -c "SELECT version();"
```

### 3.2 Schema 创建与数据导入

```bash
# 1. 复制 SQL 导入脚本到容器
docker compose cp \
  data/preparation/competition-2026/generated/postgres_staging.sql \
  postgres:/tmp/preparation.sql

# 2. 执行导入（带事务和错误处理）
docker compose exec -T postgres psql \
  -v ON_ERROR_STOP=1 \
  -U logistics_prep \
  -d logistics_prep_test \
  -f /tmp/preparation.sql

# 3. 验证导入计数
docker compose exec -T postgres psql -U logistics_prep -d logistics_prep_test << SQL
SELECT COUNT(*) as total_entities FROM competition_preparation.entities;
SELECT COUNT(*) as total_refs FROM competition_preparation.refs;
SELECT entity_type, COUNT(*) FROM competition_preparation.entities 
GROUP BY entity_type ORDER BY entity_type;
SQL

# 预期输出：
# total_entities | 326
# total_refs     | 979
```

### 3.3 数据完整性验证

```sql
-- 验证脚本：tests/sql/verify_preparation_import.sql

-- 1. 检查重复 UUID
SELECT entity_type, entity_id, COUNT(*) 
FROM competition_preparation.entities 
GROUP BY entity_type, entity_id 
HAVING COUNT(*) > 1;
-- 预期：无结果

-- 2. 检查孤立外键（Order 指向不存在的 Warehouse）
SELECT o.* FROM competition_preparation.entities o
WHERE o.entity_type = 'Order'
  AND NOT EXISTS (
    SELECT 1 FROM competition_preparation.entities w
    WHERE w.entity_type = 'Warehouse'
      AND w.entity_id = (o.data->>'source_warehouse_id')
  );
-- 预期：无结果

-- 3. 检查时间窗合理性
SELECT entity_id FROM competition_preparation.entities
WHERE entity_type = 'Order'
  AND (data->>'time_window_end')::timestamp 
    < (data->>'time_window_start')::timestamp;
-- 预期：无结果

-- 4. 统计场景覆盖
SELECT data->>'scenario' as scenario, COUNT(*) as count
FROM competition_preparation.entities
WHERE entity_type = 'Order'
GROUP BY data->>'scenario';
-- 预期：T1=2, A8=8, B20=20
```

---

## 第四部分：转换到正式 Schema

### 4.1 迁移规范

```python
# 位置: apps/backend/migrations/202610_00_import_preparation_data.py

from alembic import op
import sqlalchemy as sa
from datetime import datetime
from logistics_persistence.converters.preparation_converter import PreparationBundleConverter
from logistics_domain import (
    Warehouse, WarehouseZone, StorageLocation,
    Vehicle, Driver, Order, Cargo
)

def upgrade():
    """从 staging 导入到正式表"""
    
    # 步骤 1: 加载 Preparation DTO
    bundle = PreparationBundleConverter.from_json_file(
        'data/preparation/competition-2026/generated/bundle.json'
    )
    
    # 步骤 2: 在事务中导入
    connection = op.get_bind()
    
    with connection.begin():
        # 2.1 导入仓库
        for prep_warehouse in bundle.warehouses:
            warehouse = Warehouse(
                id=prep_warehouse.warehouse_id,
                name=prep_warehouse.name,
                location_name=prep_warehouse.location_name,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            connection.execute(
                sa.insert(Warehouse).values(**warehouse.dict())
            )
        
        # 2.2 导入温区与库位
        for prep_warehouse in bundle.warehouses:
            for prep_zone in prep_warehouse.zones:
                zone = WarehouseZone(
                    id=prep_zone.zone_id,
                    warehouse_id=prep_warehouse.warehouse_id,
                    temperature_type=prep_zone.zone_type.value,
                    capacity_kg=prep_zone.capacity_kg,
                    capacity_m3=prep_zone.capacity_volume_m3
                )
                connection.execute(
                    sa.insert(WarehouseZone).values(**zone.dict())
                )
                
                for prep_location in prep_zone.locations:
                    location = StorageLocation(
                        id=prep_location.location_id,
                        zone_id=prep_zone.zone_id,
                        capacity_kg=prep_location.capacity_kg,
                        initial_stock_json=prep_location.initial_stock
                    )
                    connection.execute(
                        sa.insert(StorageLocation).values(**location.dict())
                    )
        
        # 2.3 导入车辆与司机
        for prep_vehicle in bundle.vehicles:
            vehicle = Vehicle(
                id=prep_vehicle.vehicle_id,
                plate=prep_vehicle.plate,
                capacity_kg=prep_vehicle.capacity_kg,
                capacity_m3=prep_vehicle.capacity_m3,
                temperature_zones=[z.value for z in prep_vehicle.temperature_zones]
            )
            connection.execute(
                sa.insert(Vehicle).values(**vehicle.dict())
            )
        
        # 2.4 导入订单与货物
        for prep_order in bundle.orders:
            order = Order(
                id=prep_order.order_id,
                source_warehouse_id=prep_order.source_warehouse_id,
                destination_warehouse_id=prep_order.destination_warehouse_id,
                time_window_start=prep_order.time_window_start,
                time_window_end=prep_order.time_window_end
            )
            connection.execute(
                sa.insert(Order).values(**order.dict())
            )
            
            cargo = Cargo(
                id=prep_order.cargo.cargo_id,
                order_id=prep_order.order_id,
                weight_kg=prep_order.cargo.weight_kg,
                volume_m3=prep_order.cargo.volume_m3,
                cargo_type=prep_order.cargo.cargo_type.value,
                required_temperature=prep_order.cargo.required_temperature.value
            )
            connection.execute(
                sa.insert(Cargo).values(**cargo.dict())
            )

def downgrade():
    """回滚导入"""
    connection = op.get_bind()
    with connection.begin():
        # 按外键依赖反序删除
        op.execute("DELETE FROM cargo WHERE source = 'preparation'")
        op.execute("DELETE FROM orders WHERE source = 'preparation'")
        op.execute("DELETE FROM storage_locations WHERE source = 'preparation'")
        op.execute("DELETE FROM warehouse_zones WHERE source = 'preparation'")
        op.execute("DELETE FROM vehicles WHERE source = 'preparation'")
        op.execute("DELETE FROM warehouses WHERE source = 'preparation'")
```

### 4.2 快照固定

```python
# 位置: tests/fixtures/preparation_snapshot.py

import json
from pathlib import Path
from datetime import datetime

class PreparationSnapshot:
    """固定的准备数据快照，用于重复测试"""
    
    BUNDLE_PATH = Path('data/preparation/competition-2026/generated/bundle.json')
    SNAPSHOT_ID = 'prep-v1-20261014'
    SNAPSHOT_DATE = datetime(2026, 10, 14)
    
    # 验证哈希（防止意外变化）
    EXPECTED_HASHES = {
        'bundle.json': '194ed2e6a2a2463b7189ea240c44db6062f09a02ad6583a2066af40c1a68d889',
        'entities.csv': '10efdc45ddf38ab1168479c41e72cd303df800f0951b1466dfe7d001228d8a0a',
        'postgres_staging.sql': 'd830d600066e05ee0224547e1a4eda12364a1e662d1d73d6b884141783e40829',
    }
    
    # 固定计数（防止导入错误）
    EXPECTED_COUNTS = {
        'total_entities': 326,
        'total_refs': 979,
        'orders_t1': 2,
        'orders_a8': 8,
        'orders_b20': 20,
        'warehouses': 2,
        'vehicles': 4,
        'drivers': 4,
        'workers': 3,
    }
    
    @staticmethod
    def load_bundle() -> dict:
        """加载完整 bundle"""
        with open(PreparationSnapshot.BUNDLE_PATH) as f:
            return json.load(f)
    
    @staticmethod
    def verify_integrity() -> bool:
        """验证快照完整性"""
        import hashlib
        
        for filename, expected_hash in PreparationSnapshot.EXPECTED_HASHES.items():
            path = PreparationSnapshot.BUNDLE_PATH.parent / filename
            
            with open(path, 'rb') as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            
            if actual_hash != expected_hash:
                raise ValueError(
                    f"Hash mismatch for {filename}: "
                    f"expected {expected_hash}, got {actual_hash}"
                )
        
        return True
```

---

## 第五部分：测试与验证

### 5.1 单元测试

```python
# tests/test_preparation_converter.py

import pytest
from datetime import datetime
from logistics_contracts.dtos.preparation import (
    PreparedBundle, PreparedWarehouse
)
from logistics_persistence.converters.preparation_converter import PreparationBundleConverter

class TestPreparationConverter:
    
    @pytest.fixture
    def bundle_json(self):
        """加载测试数据"""
        return PreparationBundleConverter.from_json_file(
            'data/preparation/competition-2026/generated/bundle.json'
        )
    
    def test_load_bundle_structure(self, bundle_json):
        """测试 Bundle 结构完整性"""
        assert isinstance(bundle_json, PreparedBundle)
        assert bundle_json.scenario_name in ['T1', 'A8', 'B20']
        assert len(bundle_json.warehouses) > 0
        assert len(bundle_json.vehicles) > 0
        assert len(bundle_json.orders) > 0
    
    def test_warehouse_zone_completeness(self, bundle_json):
        """测试仓库温区完整性"""
        for warehouse in bundle_json.warehouses:
            assert len(warehouse.zones) > 0, f"Warehouse {warehouse.warehouse_id} has no zones"
            
            for zone in warehouse.zones:
                assert zone.zone_type.value in ['AMBIENT', 'CHILLED', 'FROZEN']
                assert zone.capacity_kg > 0
                assert zone.capacity_volume_m3 > 0
    
    def test_order_time_windows_valid(self, bundle_json):
        """测试订单时间窗有效性"""
        for order in bundle_json.orders:
            assert order.time_window_start < order.time_window_end, \
                f"Invalid time window for order {order.order_id}"
            assert order.time_window_start.tzinfo is not None, \
                "Time must be timezone-aware"
    
    def test_cargo_type_enum(self, bundle_json):
        """测试货物类型枚举"""
        for order in bundle_json.orders:
            assert order.cargo.cargo_type.value in [
                'GENERAL', 'FROZEN', 'CHILLED'
            ]
    
    def test_fk_integrity(self, bundle_json):
        """测试外键完整性"""
        warehouse_ids = {w.warehouse_id for w in bundle_json.warehouses}
        vehicle_ids = {v.vehicle_id for v in bundle_json.vehicles}
        
        for order in bundle_json.orders:
            assert order.source_warehouse_id in warehouse_ids
            assert order.destination_warehouse_id in warehouse_ids
    
    def test_idempotence(self, bundle_json):
        """测试转换幂等性"""
        bundle1 = PreparationBundleConverter.from_json_file(
            'data/preparation/competition-2026/generated/bundle.json'
        )
        bundle2 = PreparationBundleConverter.from_json_file(
            'data/preparation/competition-2026/generated/bundle.json'
        )
        
        assert bundle1 == bundle2
```

### 5.2 集成测试

```python
# tests/integration/test_preparation_import.py

import pytest
from sqlalchemy import create_engine, text
from logistics_persistence.converters.preparation_converter import PreparationBundleConverter
from logistics_persistence.repositories import WarehouseRepository

class TestPreparationImport:
    
    @pytest.fixture
    def test_db(self):
        """创建测试数据库"""
        engine = create_engine('postgresql://localhost/logistics_test')
        # 创建 schema
        # ... setup code ...
        yield engine
        # 清理
        # ... teardown code ...
    
    def test_import_all_scenarios(self, test_db):
        """测试三个场景的完整导入"""
        bundle = PreparationBundleConverter.from_json_file(
            'data/preparation/competition-2026/generated/bundle.json'
        )
        
        # 导入数据
        # ... import code ...
        
        # 验证计数
        with test_db.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM warehouses WHERE source = 'preparation'"
            ))
            assert result.scalar() == 2
            
            result = conn.execute(text(
                "SELECT COUNT(*) FROM orders WHERE source = 'preparation'"
            ))
            assert result.scalar() == 30
    
    def test_no_duplicate_on_reimport(self, test_db):
        """测试重复导入时无重复记录"""
        bundle = PreparationBundleConverter.from_json_file(
            'data/preparation/competition-2026/generated/bundle.json'
        )
        
        # 导入一次
        # ... first import ...
        
        count1 = self._count_orders(test_db)
        
        # 再导入一次（应该使用 UPSERT）
        # ... second import ...
        
        count2 = self._count_orders(test_db)
        
        assert count1 == count2, "Duplicate import added new records"
    
    @staticmethod
    def _count_orders(engine) -> int:
        with engine.connect() as conn:
            return conn.execute(
                text("SELECT COUNT(*) FROM orders WHERE source = 'preparation'")
            ).scalar()
```

---

## 第六部分：问题排查

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|--------|
| `FileNotFoundError: bundle.json` | 文件未生成或路径错误 | 运行 `python -B data/preparation/competition-2026/build.py` |
| `FOREIGN KEY violation` | FK 完整性检查失败 | 检查 warehouse_id/vehicle_id 是否存在 |
| `duplicate key value` | UUID 重复或 UPSERT 未配置 | 检查约束定义，使用 INSERT ... ON CONFLICT |
| 导入时间过长 | 批量导入未优化 | 使用 COPY 或批量 INSERT 代替逐行 INSERT |
| 内存溢出 | Bundle 过大 | 分批导入或增加 JVM/Python 堆栈大小 |

---

## 第七部分：验收清单

导入完成后按以下清单验证：

- [ ] bundle.json 文件哈希与 manifest.json 匹配
- [ ] 326 条实体完整导入
- [ ] 979 条关系完整导入
- [ ] 无重复 UUID 记录
- [ ] 所有 FK 完整性检查通过
- [ ] 时间窗合理性验证通过
- [ ] 三个场景（T1/A8/B20）的订单计数正确
- [ ] SQLite 查询与 PostgreSQL 查询结果一致
- [ ] 重复导入时记录计数不变（幂等性）
- [ ] 快照版本号已记录（用于后续追踪）
- [ ] 测试 Fixture 已生成（用于单元/集成测试）
- [ ] 性能基准已记录（导入耗时 < 5s for 326 records）

---

**参考文档**
- `docs/architecture/DOMAIN_CATALOG.md` - 完整领域模型
- `docs/architecture/DATA_CONTRACTS.md` - 数据协议
- `docs/plan/TEST_FIXTURES.md` - 测试数据规范
- `data/preparation/competition-2026/README.md` - 数据包说明
