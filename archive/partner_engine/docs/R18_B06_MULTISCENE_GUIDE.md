# R18 / B-06 多场景同预算成对实验：成员 B 交付说明

> **2026-10-14 晚实测补记**：R18 五组已在 Windows 机真实跑完（5/5 有效、等距离、描述性平均改善 40.13%），并冻结为 `benchmarks/b03/r18_accepted/`。下文第 3、4 节中「尚未获得」「待 Windows 检查」等句子是**当时交付环境**的记录，保留为历史；最新口径以文末[附：2026-10-14 Windows 实测结果](#附2026-10-14-windows-实测结果r18-收尾验收)为准。

## 状态（先读）

- **R17 正式 A/B 已于 2026-10-13 在用户 Windows 侧完成并验收，不重新运行。** 原始 JSON 逐字节收录在 `benchmarks/b03/r17_accepted/r17_accepted_original.json`，同时放在前端 `public/evidence` 供网页下载。
- R17 归档的场景 SHA256 `592ece17d7f190cad52cc53b594a2da060586255e16dafa039121866773be2df`，单轮/深度每组预算 90 秒、距离 56 km、20/20 服务且原校验 passed；订单级累计交接等待 4500→2400 秒（减少 2100 秒 / 46.7%），端到端耗时 75945→87617 毫秒。
- `backend/tools/r18_evidence_audit.py` 读取原始 JSON，按 20 单明细逐笔复算车辆**出仓时间 − ready_at**、订单覆盖、总距离、候选方案一致性和 SHA256；输出 `benchmarks/b03/r17_accepted/r17_arithmetic_audit.json`。**这仅是指标/文件证据再核算，不等同重新运行优化器或独立执行所有冷链硬约束检查。**
- R18 新增的是**5 组不同 Seed/负载的预注册合成场景 + 批量 paired A/B 工具 + 逐组保存 + 严格可比性判断 + CSV/JSON/Markdown 报表**。R18 的新求解结果尚未在本交付环境实际获得，不能宣称已通过多场景实证。
- 本版本不更改 R17 仓储 CP-SAT、Routing、深度反馈、订单校验、B-04/SimPy、API/数据库契约或 R16 旧 B-06 评测；更换前端左侧版本字样，新增只读归档面板。

## 为什么优先这个任务

R17 的 46.7% 目前是一组正式有效案例；评委会追问 **(1) 其他负载能否复现？(2) 深度求解增时多少？(3) 有失败怎样处理？** R18 直接为这些问题提供可重复的、完整留痕的实验协议。真实路网、更多异常、Agent 集成以后再安排。

## 预注册五组场景（都从已有 20 单、2 仓、4 车原始快照**确定性生成**）

| 场景 | 订单数 | 随机 Seed | 约束变化 |
|---|---:|---:|---|
| s12_seed17 | 12 | 17 | 4 个（仓×温区）子组各取 3 单，轻微调整装载作业释放时刻、订单服务时长 |
| s16_seed42 | 16 | 42 | 各子组各取 4 单，轻微调整上述业务参数 |
| s20_seed66 | 20 | 66 | 全订单保留、轻微调整上述业务参数 |
| s20_seed88 | 20 | 88 | 同订单量、不同 Seed/释放与服务时间 |
| s20_seed101 | 20 | 101 | 同订单量、不同 Seed/释放与服务时间 |

保留原本固定路网矩阵、车辆和仓库，不伪造外部路况；所有场景均用 `PlanningSnapshot` 校验。它们是来自同一基础合成模型的场景扰动，**不是五个真实地区的数据**，也不构成独立样本的显著性检验。不人工挑选有利样本。预算、输入快照和算法求解函数对每个场景的两组模式完全一致。

## Windows PowerShell：最快可执行步骤

先解压新 ZIP 到 `D:\1aaaqianduan\R18_B06_MULTI_SCENE_EVIDENCE`。务必保留旧 `915_B03_DEEP_JOINT_OPTIMIZATION_R17` 文件夹，不覆盖它。以下代码都粘贴在新文件夹中运行。若解压位置不同，修改 `cd` 路径。

### 1. 后端依赖与自动测试（首次安装需要联网）

```powershell
cd "D:\1aaaqianduan\R18_B06_MULTI_SCENE_EVIDENCE\backend"
python -m pip install -r requirements.txt
python -m pip install simpy
python -m pytest -q tests
```

### 2. 先**只生成新场景预览**（不求解、不重复 R17）

```powershell
python -m tools.r18_multiscene_ablation --dry-run --case-count 5
```

会显示预览文件夹路径；场景 `.json` + `manifest.json` 均为尚未求解状态。

### 3. 开始 R18 **新**跨场景正式消融（并非已经验收过的 R17 20 单命令）

```powershell
python -m tools.r18_multiscene_ablation --case-count 5 --budget-ms 90000
```

本次会跑 5 组场景 × 2 模式；每模式拥有相同 **90 秒总预算**，不是保证每组恰好用完 90 秒。计算量较大，可能持续一段时间。工具逐场景保存完整方案与失败，并每做完一组就更新汇总，禁止悄悄忽略失败。**测试集使用合成样例；用户可以先选 `--case-count 3` 减少组数，但应在结果文档中明确数量，正式比较不要临时改一方预算。**

运行结果默认在 `benchmarks/b03/r18_runs/run_日期时间/` 下，有：

- `manifest.json`：原始快照哈希、预先确定的 Seed/规模、每组 SHA256 与预算。
- `scenarios/*.json`：5 份可重建业务快照。
- `raw/*_paired.json`：每组**两条**全量候选方案、约束校验、轮次、耗时；异常失败不会删除。
- `summary.json`、`summary.csv`、`summary.md`：完整状态、可比较对数量和等待变化；不能证明的百分比留空。

**判定口径**：必须两模式服务全部订单、原生独立校验通过、订单交接和车辆出发的实算值自洽。若运距不同，鉴于目标函数先比较距离，等待改善率标记不可比；仅同距离的完整有效成对结果显示等距离等待改善百分比。至少三组可比样本才展示描述性的平均改善率；无显著性宣称。

### 4. 网页演示（新旧 B-06 功能并存）

新开两个 PowerShell 窗口：

```powershell
# 窗口 A
cd "D:\1aaaqianduan\R18_B06_MULTI_SCENE_EVIDENCE\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
# 窗口 B
cd "D:\1aaaqianduan\R18_B06_MULTI_SCENE_EVIDENCE\frontend"
npm ci
npm run test:evidence
npm run test:speed
npm run build
npm run dev
```

浏览器进入 `http://127.0.0.1:5173/` → **评测与证据 → B-06 实验与证据**。新增 R17 已验收证据面板：显示两组真实档案数据，并提供原始 JSON 和复算审计 JSON 下载。现有 R16 规则基线批量评测为另一种协议，不要把它误标成 R18 深度协同的正式跨场景对照。R18 新多场景结果目前由 PowerShell 生成文件，不会伪装为页面里的实时试验数据。

## 设计约束/未完成

- 未扩大 OR-Tools 求解模型或新增场景业务规则。单轮、深度都调用 R17 原来的 `coordinate()`，未改参数和解的选择逻辑。
- 本次交付环境缺少 `ortools` 和 `simpy`，而且无联网安装能力，无法执行新的真实 CP-SAT / Routing / SimPy，也缺前端 `node_modules`，所以无法完成 Vite 正式构建；**这些是待 Windows 实机检查项**。本地仅能进行 Pytest、stdlib 指标独立复算、合成场景预生成和现有 Node 逻辑测试。
- 旧架构 `scripts/check_project.py` 存在历史 application→adapter 直接引用提示；这不是 R18 引入，未临赛大规模重构。

## 项目保留/交接

- 完整源代码在本 ZIP 唯一顶层 `R18_B06_MULTI_SCENE_EVIDENCE/`。R17 旧包请原样备份。
- 详细证据：`benchmarks/b03/r17_accepted/`。
- 新功能代码：`backend/tools/r18_evidence_audit.py`、`backend/tools/r18_multiscene_ablation.py`、`backend/tests/test_r18_multiscene_evidence.py`；页面：`frontend/src/features/experiments/Page.tsx`、`frontend/src/App.tsx`。
- 后续 B-04 「不重排 / 全量 / 局部」消融仍为下一独立阶段，不宣称已实现。

## 附：2026-10-14 Windows 实测结果（R18 收尾验收）

本节由收尾验收追加，不修改上文任何历史记录。

- 实测环境：Python 3.14.3、ortools 9.15.6755、simpy 4.1.2；node v24.19.0、npm 11.17.0；`frontend/node_modules` 已存在。
- 命令：`python -m tools.r18_multiscene_ablation --case-count 5 --budget-ms 90000`
- 运行目录：`benchmarks/b03/r18_runs/run_20261014_212550_205783/`（2026-10-15 交接清理时删除该运行目录；证据以冻结归档为准）（此前还有一次只生成场景的 dry-run：`run_20261014_212531_930726/`）。
- 冻结归档：`benchmarks/b03/r18_accepted/`，逐文件 SHA256 见 `r18_accepted_manifest.json`，独立逐单复算见 `r18_multiscene_audit.json`。

| 场景 | 订单 | 单轮等待(s) | 深度等待(s) | 节省(s) | 改善率 | 距离(单轮/深度) | 深度额外耗时(ms) |
|---|---:|---:|---:|---:|---:|---|---:|
| s12_seed17 | 12 | 1260 | 900 | 360 | 28.57% | 50/50 km | +10507 |
| s16_seed42 | 16 | 2880 | 1680 | 1200 | 41.67% | 54/54 km | +10568 |
| s20_seed66 | 20 | 4500 | 2400 | 2100 | 46.67% | 56/56 km | +11674 |
| s20_seed88 | 20 | 4500 | 2700 | 1800 | 40.00% | 56/56 km | +11674 |
| s20_seed101 | 20 | 4800 | 2700 | 2100 | 43.75% | 56/56 km | +11674 |

- 5/5 均为 `complete_validated_pair` + `equal_distance`；改善/持平/变差 = 5/0/0；描述性平均改善率 40.13%。
- 五组共同满足：订单全部服务、原生独立校验 passed、逐单实算等待自洽、两组同为 90 秒预算、运输距离完全相同。
- `s20_seed66` 的等待与距离与 R17 已验收档案一致，作为一致性佐证；R18 的 s20 场景是另行扰动生成的独立合成快照，不替代 R17 证据。
- 口径不变：合成压力场景、无显著性检验；不得表述为真实县域普遍收益，也不得表述为距离或成本改善。
- 与初版交付环境的差异（已修复）：初版 `backend/requirements.txt` 缺 `simpy`、`requirements-lock.txt` 缺 `ortools/simpy`，按 README 安装会 ImportError 或无法求解；收尾已补齐并实测。

