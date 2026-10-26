# SQL 表结构修改说明

本次修改基于上一版 `smart-warehouse-twin-mvp-fixed-java21-db123456.zip`，重点按照用户提出的用户表、仓库表字段格式进行调整，同时保持原有数字孪生、库存、入库、出库、预警功能可继续运行。

## 1. 用户表 app_user

| 中文含义 | SQL 字段 | 约束/说明 |
|---|---|---|
| 用户 id | `user_id` | `bigint primary key auto_increment`，从 1 开始 |
| 用户名 | `username` | 只能使用英文字母和常见特殊字符，禁止数字、中文、空格；数据库有 `CHECK`，后端 DTO/Service 也做校验 |
| 用户密码 | `password_hash` | 不保存明文密码，保存 BCrypt 或兼容旧演示账号的 SHA-256 哈希；后端校验“首尾不能为空格、禁止中文” |
| 用户注册时间 | `user_registration_time` | `datetime not null default current_timestamp`，snake_case |
| 用户权限 | `user_permission` | `tinyint not null default 1`；0=仓库主管，1=仓库管理员，2=游客 |
| 用户权限修改时间 | `user_permission_modified_time` | `datetime null default null`，修改权限时再写入当前时间 |

初始化账号：

| 用户名 | 密码 | 权限 |
|---|---|---|
| `admin` | `admin123` | 0，仓库主管 |
| `demo` | `demo123` | 1，仓库管理员 |
| `guest` | 兼容预留账号 | 2，游客 |

## 2. 仓库表 warehouse

| 中文含义 | SQL 字段 | 约束/说明 |
|---|---|---|
| 仓库 id | `warehouse_id` | `bigint primary key auto_increment`，从 1 开始 |
| 仓库名 | `warehouse_name` | 格式：`仓库类型-仓库id`，例如 `上海青浦综合智能仓-1` |
| 仓库货柜数量 | `cabinet_count` | `int not null default 1`，必须大于等于 1 |
| 仓库货柜 id | `warehouse_cabinet_id` | 绑定到货柜表 `shelf.id`，用于指定该仓库的首个/主货柜 id |
| 仓库存储类型 | `warehouse_storage_type` | 只能是：`生鲜`、`小件商品`、`大件商品`、`电子产品`、`贵重物品` |
| 仓库创建时间 | `warehouse_created_time` | `datetime not null default current_timestamp`，snake_case |
| 仓库类型修改时间 | `warehouse_type_modified_time` | `datetime null default null`，仓库主管修改类型后写入当前时间 |

为保持原 3D 数字孪生可视化继续工作，仓库表保留了空间字段：`width`、`depth`、`start_x`、`start_y`、`exit_x`、`exit_y`。

## 3. 货柜表绑定说明

现有项目中的 `shelf` 表承担货柜/货架功能，因此没有另起一个重复的货柜表。绑定关系如下：

- `shelf.warehouse_id` 外键绑定 `warehouse.warehouse_id`。
- `warehouse.warehouse_cabinet_id` 外键绑定 `shelf.id`。
- 初始化数据中，仓库 `1` 的 `warehouse_cabinet_id = 1`，且 `shelf.id = 1` 的 `warehouse_id = 1`，保证 id 关系一致。

## 4. 后端同步修改

- `AppUser.java`：改为匹配 `user_id`、`user_permission`、`user_registration_time`、`user_permission_modified_time`。
- `UserMapper.java`：全部 SQL 改为新字段，新增按用户 id 查询与权限更新时间写入方法。
- `AuthService.java`：注册时默认新用户为仓库管理员 `user_permission=1`；登录/注册均校验用户名和密码规则。
- `Warehouse.java`：改为匹配 `warehouse_id`、`warehouse_name`、`cabinet_count`、`warehouse_cabinet_id`、`warehouse_storage_type`、`warehouse_created_time`、`warehouse_type_modified_time`。
- `WarehouseMapper.java`：全部 SQL 改为新字段，新增修改仓库存储类型方法。
- `WarehouseService.java`：新增“只有仓库主管可以修改仓库存储类型”的业务校验。
- `WarehouseController.java`：新增接口 `PATCH /api/warehouse/{warehouseId}/storage-type`。

## 5. 修改仓库存储类型接口

请求地址：

```http
PATCH /api/warehouse/1/storage-type
Content-Type: application/json
```

请求体：

```json
{
  "storageType": "贵重物品",
  "operatorUserId": 1
}
```

说明：

- `operatorUserId=1` 是默认主管 `admin`。
- 只有 `user_permission=0` 的用户可以修改。
- 修改成功后，系统会自动把 `warehouse_name` 改为 `上海外高桥贵重物品安防仓-1`，并把 `warehouse_type_modified_time` 写为当前时间。

## 6. 重置数据库注意事项

因为修改了表结构，若你本机之前已经启动过旧版 MySQL 数据卷，必须删除旧数据卷后重新初始化：

```bash
docker compose down -v
docker compose up -d
```

如果只执行 `docker compose up -d`，旧表结构不会自动变成新表结构。
