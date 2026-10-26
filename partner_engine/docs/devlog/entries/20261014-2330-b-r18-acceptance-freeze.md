# 2026-10-14 23:30 / B / R18 收尾验收：证据冻结与缺陷修复

- 角色 / 日期 / 基线：成员 B，2026-10-14 晚；基线包 `D:\1aaaqianduan\R18_B06_MULTI_SCENE_EVIDENCE`（收尾前 `PACKAGE_MANIFEST.json` SHA256 `1cf482c976e230c5f47f5731decafb623f3f80ed07b9ae86763e7e6ca1b1e489`），R17 已验收证据 `benchmarks/b03/r17_accepted/r17_accepted_original.json` SHA256 `8341100ea488632843866762de7482cf630d9650826146f166016fd8f64e22cd`，源场景 SHA256 `592ece17d7f190cad52cc53b594a2da060586255e16dafa039121866773be2df`。
- 任务 / 状态：交接文档《第 5 节 第一步 · R18 收尾验收》——**已完成**（P0-1～P0-4、P1-5～P1-8、P2-13 完成；P1-9 与 P2-10～P2-12 保留，见“未完成”）。
- 授权范围：用户本轮明确授权两项越界改动——重生成并登记 `frontend/src/client/generated.ts`（SHARED 生成产物）、把 `backend/app/application/handle_event.py` 的函数内 import 提到模块顶部（AC 文件）。**未授权**：B-06 证据页新增 R18 面板（CODEX_FRONTEND）、把 `backend/tools/`、`benchmarks/b03/` 登记为 B 所有（OWNERSHIP.json 未改）。

## 完成及修改文件

新增：

- `backend/tools/r18_acceptance_freeze.py`：把一次 R18 运行冻结成稳定归档；逐字节复制证据，用同一独立审计逐单重算，与运行 `summary.json` 不一致就中止写入。
- `benchmarks/b03/r18_accepted/`：14 个归档文件（`manifest.json`、`summary.json/csv/md`、`scenarios/*.json`×5、`raw/*_paired.json`×5）+ `r18_accepted_manifest.json`（逐文件 SHA256）+ `r18_multiscene_audit.json`（独立复算 + R17 交叉核对）+ `README.md`。
- `.gitignore`（P2-13）；本日志。

修改：

- `backend/tools/r18_evidence_audit.py`、`r18_multiscene_ablation.py`、`r17_joint_ablation.py`：`write_text` 显式 `newline='\n'`（P1-5，消除 Windows LF→CRLF 造成的哈希漂移）。
- `scripts/project_files.py`：打包排除 `r18_runs/**` 与 `*.err`（P1-7）；`benchmarks/b03/r18_accepted/**` 仍随包交付。
- `backend/app/application/handle_event.py`：`hashlib`/`json`/`SolveMetadata` 提到模块顶部（P1-8，已授权，不改逻辑）。
- `backend/requirements.txt`：补 `simpy>=4.1.1,<5`（P0-1）。`backend/requirements-lock.txt`：补 `ortools==9.15.6755`、`simpy==4.1.2`、`absl-py`、`immutabledict`、`numpy`、`pandas`、`protobuf`、`python-dateutil`、`six`、`tzdata`（P0-2）。
- `README.md`：第 3、5 行版本号由 R17 改为 R18 并指向 R18 指南（P0-3）。
- `docs/R18_B06_MULTISCENE_GUIDE.md`、`docs/R18_VERIFICATION_LOG.md`：不改写历史正文，顶部加“2026-10-14 晚实测补记”指向，文末追加实测结果章节（P0-4）。
- `benchmarks/b03/r17_accepted/r17_arithmetic_audit.json`：还原为交付包原始字节，SHA256 `f70edfc76841b6d9edf8a87eaa9894cec677c3d235978c7d129ad81e12d81ff8`、1061 字节（上一轮重跑产生的 `060fd844…` 作废）。
- `frontend/src/client/generated.ts`：用锁定工具链重生成，结果与重生成前**逐字节相同**（`70a82f17565a372eefe2f9afa80ffd365dc8dd517482486871fde80935f49334`，49536 字节，纯 LF），`npm run contracts:check` 通过（P1-6）。
- `scripts/package_demo.py`：新增 `--top-level`（默认仍为 `demo`，对既有用法无影响），并在打包后校验“ZIP 第一层只有一个顶层文件夹”（交付纪律第 6 条）；本版用它打出唯一顶层 `R18_B06_MULTI_SCENE_EVIDENCE/`。
- `FILE_MAP.md`：按实际文件重建（235 个源文件，`--check` 通过）。`DEV_LOG.md`：追加增量条目。根目录 `PACKAGE_MANIFEST.json`：替换为新 ZIP 内的清单（`1cf482c9…` → `40bf8e4b…`），使工作区与交付包一致；旧清单里 `generated.ts` 的 `8a3477e2…` 已由新清单的 `70a82f17…` 取代。

删除（临时文件）：`backend/r18_official_run.log`、`backend/r18_official_run.err`、`frontend/build_r18.log`。

## 契约与输入输出

- 契约版本前后：**无变化**（`contracts/VERSION`、`contracts/openapi.json` SHA256 `99d0ff358ffa6918ec8c89768561c661e768569d34de5e766b0156c7b66da6da` 均未改动，`scripts/export_contracts.py --check` 输出 `Contracts match source`）；无变更提案。
- 输入输出/单位/状态/URL：**无变化**；未新增或修改任何 HTTP 路由、数据库结构、求解模型或预算参数。
- 证据口径：冻结归档保持运行当时的 CRLF 字节原样（哈希以实际字节为准）；换行缺陷修复只影响**今后**的运行输出。归档为合成场景等预算成对证据，不含显著性检验。

## 验证命令与原始结果

- `cd backend; python -m pytest -q tests` → **62 passed, 25 warnings in 3.20s**，exit 0。
- `python -m compileall -q backend/app backend/tools` → exit 0。
- `python scripts/export_contracts.py --check` → `Contracts match source`，exit 0。
- `python scripts/check_project.py` → exit 1，仅 7 条既有 `application cannot import adapters` 告警：`coordinator.py`×3、`handle_event.py`×1、`http_services.py`×3（P1-9，未处理）。
- `cd frontend; npm run contracts:check` → `Frontend contract types match OpenAPI`，exit 0。
- `npm run test:evidence` → `R15 frontend core evidence tests: PASS`，exit 0；`npm run test:speed` → `R16 speed tests: PASS`，exit 0。
- `npm run build` → exit 0，`✓ built in 2.06s`；`dist/assets/index-CsXBf6wO.css 30.39 kB`、`index-DGRU4xyB.js 914.87 kB`（存在 >500 kB 分块提示，非失败）。
- 冻结：`cd backend; python -m tools.r18_acceptance_freeze --run-dir ../benchmarks/b03/r18_runs/run_20261014_212550_205783` → `Frozen 14 files (487201 bytes)`；5 组全部 `complete_validated_pair`＋`equal_distance`；复算 derived 与运行 summary 完全一致（有效对 5、改善/持平/变差 5/0/0、平均 40.13%）；R17 交叉核对 `s20_seed66` = **match**。
- 归档复核：复制后逐文件 SHA256 再校验，全部一致。
- 交付包：`artifacts/R18_B06_MULTI_SCENE_EVIDENCE_20261014.zip`；236 个条目 = 235 个源文件 + 包内 `PACKAGE_MANIFEST.json`；第一层仅 `R18_B06_MULTI_SCENE_EVIDENCE/`；已确认不含 `r18_runs`、`node_modules`、`frontend/dist`、`__pycache__`、`*.err`。**权威大小与 SHA256 记录在包外的同名 `.sha256` 文件**（本日志本身随包交付，不能写死包含自己的压缩包哈希）。

## 未完成 / 已知限制 / 阻塞

1. P1-9：`check_project.py` 的 `application→adapters` 告警未消除（涉及公共组合根，需与 AC 协调，不在临赛期大重构）。
2. P2-10：R18 五组结果**未上网页**（`frontend/` 属 CODEX_FRONTEND，本轮未获授权）。
3. P2-11：场景扰动维度仍偏弱（分层抽样 + service_duration ±30s + release_at +0/60/120/180s）；**不得事后修改已用协议**，应作为 R19 的协议 1.1 新增维度。
4. P2-12：汇总缺“深协同代价”维度（轮次、CP-SAT/Routing 各自耗时、无改善占比）与“距离不同但全服务”计数；只可在新协议中新增，不回改已冻结的 R18 汇总。
5. 治理不一致（未授权修改）：`OWNERSHIP.json` 未列 `backend/tools/`、`benchmarks/b03/`，按最长前缀规则这些 B-06 产物当前解析为 `AC`；建议用户确认后再同步 OWNERSHIP.json。
6. 环境限制：本机沙箱只允许写入工作区**根目录**，子目录写入被拒；已验证的应对方式是仅在确需子目录写入的命令上单次放宽。该限制与项目代码无关。
7. `r17_joint_ablation.py` 修复后重跑会产出 LF，而归档的 R17/R18 证据是 CRLF；两者内容等价、哈希不同，归档哈希一律以实际字节为准。

## 交给谁 / 下一步

- 交给用户（成员 B）：按新 ZIP 的 `docs/R18_B06_MULTISCENE_GUIDE.md` 与 `README.md` 验证；R17/R18 正式证据**不再重跑**。
- 下一步：R19 = B-04「不重调度 / 全量重调度 / 局部重调度」三策略同事件集对照（SimPy 确定性回放、等预算、失败留痕），前置为与 AC 协调 P1-9。
