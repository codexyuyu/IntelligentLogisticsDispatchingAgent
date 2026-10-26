# R20 一级目录整理与交付记录（2026-10-16）

本次只整理磁盘目录和配套引用，**没有修改算法求解、独立校验、业务接口、冷链场景或冻结实验内容**。早期 README 和 docs/history/ 中的历史目录描述属于当时项目状态，不能当作当前路径。

## 一级目录（9 个）

```text
R20_COLD_CHAIN_REORGANIZED/
├── backend/               正式 FastAPI / OR-Tools / SimPy
├── frontend/              正式 React 前端
├── contracts/             API 与生成类型契约
├── data/                  可复现场景
├── benchmarks/            实验与已验收证据（未迁移）
├── scripts/               合同导出 / 自检 / 打包
├── docs/                  当前文档、历史日志与说明
├── infra/
│   ├── deploy/            原 deploy/
│   └── platform/          原 platform/
└── archive/
    ├── legacy/
    │   ├── algorithm-service/          原 algorithm-service/
    │   ├── backend-legacy-springboot/  原 backend-legacy-springboot/
    │   ├── frontend-legacy-vue3/      原 frontend-legacy-vue3/
    │   └── legacy-reference/          原 legacy-reference/
    ├── reference_demos/               原 reference_demos/
    └── releases/                      原 artifacts/
```

## 保留及清理原则

- `backend`、`frontend` 的源代码与配置、`contracts`、`data`、`benchmarks` 全部原样保留；R17、R18、R19 的 accepted 实验归档不移动、不重算、不改动。
- 旧版后端、旧版前端、早期算法服务、历史 SQL 与参考探针归档而不删除；旧版发行 ZIP 和对应 SHA256 保留在 `archive/releases`。
- 仅移除可再生成的 `frontend/node_modules`、`frontend/dist`、旧 Spring Boot `target`、Python `__pycache__` 和 `.pytest_cache`，未删除冻结证据。
- `OWNERSHIP.json`、`FILE_MAP.md`、打包脚本、当前 README 和当前开发交接指引已同步新路径。`docs/history` 内旧版记录为了证据溯源保留原措辞。
- `python scripts/package_demo.py` 生成轻量化源码包；完整交接需加 `--include-archive` 使已归档旧源码与旧版交付包也包含在内，包内有逐文件 SHA256 清单。

## 环境启动和验证

根目录：

```powershell
python -m pip install -r backend/requirements-lock.txt
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

前端另开终端：

```powershell
cd frontend
npm ci
npm run contracts:check
npm run test:evidence
npm run test:speed
npm run build
npm run dev
```

工程静态和后端测试在根目录：

```powershell
python scripts/export_contracts.py --check
python scripts/build_file_map.py --check
python scripts/check_project.py
python -m pytest -q backend/tests
```

`check_project.py` 的 application → adapters 边界问题在原工程中已有记录，本次目录整理不改动该历史业务实现；详见现行 `DEV_LOG.md`。本交付环境的实际验证结果另在本文件末尾追加，不以历史记录冒充本机实测。

## 本次交付环境验证结果

- 原包 CRC 完整，整理后一级目录数 **9**。
- 按原始 ZIP 逐文件 SHA256 核对，`contracts/`、`data/`、`benchmarks/`、正式前端源文件均 **未改变**；`backend/` 仅更新仓储迁移说明 `MIGRATION.md` 中的旧服务路径，调度/校验/仿真代码均未改变。
- `python scripts/export_contracts.py --check`：**PASS**；`python scripts/build_file_map.py --check`：**PASS**（310 个纳入清单的文件）；API 健康检查 HTTP **200**。
- 前端 `test:evidence`、`test:speed`：**PASS**；在提取的原包前端依赖上执行 TypeScript `tsc --noEmit`：**PASS**。
- 本交付为 Linux 验证环境；原 ZIP 带的前端依赖缺 Linux Rollup 原生可选包，故 Vite 完整构建**未能在本环境完成**；需要在用户 Windows 环境执行 `npm ci && npm run build`，不得把 TypeScript 检查当作完整构建通过。
- `python scripts/check_project.py`：只有与整理前同一批 **7 条既有 application→adapters 边界告警**，没有新产生的路径或 Markdown 链接错误。本次未修改这些业务耦合。
- `pytest`：当前环境未安装 `simpy`、`ortools`，且原有 `test_r19_reschedule_strategies.py` 收集时存在未导入 `Path` 的问题，无法宣称全量通过；排除两份无法收集的测试文件后，结果为 **71 passed、1 skipped、4 failed（4 项均缺 OR-Tools）**。这些限制不由目录移动引起，未修改业务测试来掩盖。

原包保留在交付压缩包之外以便用户回退；包内 `archive/releases/` 仍完整保留 R18、R19 的原历史发行 ZIP 及其校验文件。
