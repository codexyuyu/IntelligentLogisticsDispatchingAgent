# 2026-10-15 05:30 / B / 交接整理：去重、归档历史文档、修复未打包指南

- 角色 / 日期：成员 B，2026-10-15 凌晨。
- 任务 / 状态：用户要求"把多余清出去，让文件夹更清晰方便交接"，并选定执行 **B（删重复运行目录）+ D（历史 md 归入 docs/history/）+ E（修复被引用但没打包的指南）** 三项；A（可重建垃圾）、C（旧交付 ZIP）、F（Spring Boot 编译产物）经确认**不执行**。

## 删除前的证据核对（先证后删）

对三份冻结归档与其来源运行目录逐文件比对 SHA256：

| 归档 | 核对文件数 | 不一致/缺失 |
|---|---|---|
| `b03/r18_accepted` ← `r18_runs/run_20261014_212550_205783` | 14 | **0** |
| `b04/r19_accepted` ← `r19_runs/run_20261014_235140_246501` | 16 | **0** |
| `b04/r19_accepted_v2` ← `r19_runs/run_20261015_004322_357508` | 16 | **0** |

唯一未被归档覆盖的文件是 R18 dry-run 的 `run_20261014_212531_930726/manifest.json`；与归档 manifest 逐行比较后确认**只差 `status` 字段**（`not_started` vs `complete_validated_pair`，各 5 行），协议、源场景哈希、预算、场景设计与 SHA256、模式顺序、scope 全部相同 → 判定冗余后一并清理。

## 执行内容

**移动（不删除）**
- 13 个零引用历史文档 → `docs/history/`：`CURRENT_BASELINE.md`、`MIGRATION_STATUS.md`、`MERGED_ARCHITECTURE.md`、`B_ALGORITHM_DEMO_GUIDE.md`、`B01/B02×2/B03/B04/B05/B06×2`、`R16_RELEASE_NOTES.md`。
- 4 个现行指南 → `docs/`：`R15_EXPERIMENT_EVIDENCE_GUIDE.md`、`R16_FAST_BENCHMARK_GUIDE.md`、`R17_B03_DEEP_JOINT_OPTIMIZATION_GUIDE.md`、`WINDOWS_SETUP.md`。

**删除（已核对为逐字节重复）**
- `benchmarks/b03/r18_runs/`（20 文件 / 0.67 MB）
- `benchmarks/b04/r19_runs/`（32 文件 / 9.99 MB）

**链接与说明同步**
- 修复 6 处因移动而断掉的引用（`README.md` 的 R17 指南链接；`docs/history/` 内 5 处指向 R15/R16/R17/WINDOWS_SETUP 的引用改用 `../`）。修完复扫全仓库，所有引用均指向存在的路径。
- 3 份归档 README 中"原始运行目录保留在…"的过时说明改为"清理时已删除，本归档为逐字节副本，来源目录名保存在 `source_run`"。（归档 README 不在逐文件哈希清单内，改动不影响归档完整性声明。）
- `docs/R18_B06_MULTISCENE_GUIDE.md`、`docs/R18_VERIFICATION_LOG.md`、`docs/R19_B04_RESCHEDULE_GUIDE.md` 中指向被删运行目录的 3 处补充了同义说明。
- 历史增量日志与 `DEV_LOG.md` 的既有条目**未改写**，本条目为准。

**新增说明文件**
- `benchmarks/README.md`：讲清"`*_accepted/` 是证据、`*_runs/` 只是过程输出"，列出四份归档的校验方式、运行目录清理的依据与重跑命令。
- `docs/history/README.md`：说明这些是被取代的历史记录、为什么保留、以及移入 `docs/` 的现行指南。

## 顺带修好的一个真问题（E 的实质）

`R15/R16/R17` 指南与 `WINDOWS_SETUP.md` 此前位于仓库根目录，但 `scripts/project_files.py` 的根文件白名单（`ROOT_FILES`）不含它们 —— **历次交付 ZIP 里这几个链接是断的**。移入 `docs/` 后（`docs/` 在 `ROOT_DIRS` 中），它们已进入源文件列表，随包交付。核对：三个文件名与 `docs/history/*` 均 `IN`，源文件数 289 → **308**。

## 验证命令与原始结果

- `python scripts/build_file_map.py` → 308 个源文件；`--check` 通过（exit 0）。
- `python scripts/export_contracts.py --check` → `Contracts match source`（exit 0；本轮未动契约）。
- `python scripts/check_project.py` → 仍是既有 7 条 `application cannot import adapters`，**未新增**。
- `python -m pytest -q tests` → **97 passed**（22.36 s）。
- 目录体积：162.27 MB / 7420 文件 → **151.61 MB / 7368 文件**；根目录文件数 25 → **9**。

## 未执行（用户明确不选，保持原样）

- `frontend/node_modules`（134.93 MB）、`frontend/dist`、`__pycache__`/`.pytest_cache`、空目录。
- 旧交付 ZIP（`R18_...20261014.zip`、`R19_...20261015.zip`）与 `artifacts/*.sha256`。
- `backend-legacy-springboot/target/**` 的 Maven 编译产物。
- 根 `PACKAGE_MANIFEST.json`：目前仍是 R20 之前那次 v2 包的清单，**已相对当前工作区过时**（未在用户选择范围内，故未动；若后续再打包会被覆盖）。

## 注意

- 删除 `*_runs` 后，若要复现"归档＝原始运行输出"的比对，需按 `benchmarks/README.md` 的命令重跑；归档自身的逐文件 SHA256 清单与复算审计足以独立校验其内容。
- 本轮为纯整理，**未改动任何业务代码、契约或证据内容**。
