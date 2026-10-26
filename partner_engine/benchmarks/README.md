# 基准与证据目录说明

这个目录放**实验证据**与运行脚本的落点。交接时只需认准一条规则：

> **`*_accepted/` 是证据；`*_runs/` 只是过程输出。**

## 已冻结的证据归档

| 目录 | 内容 | 校验方式 |
|---|---|---|
| `b03/r17_accepted/` | R17 正式 A/B 原始 JSON（用户上传件，从未重跑） | `r17_arithmetic_audit.json` 独立复算；场景 SHA256 `592ece17…` |
| `b03/r18_accepted/` | R18 五组多场景同预算对照 | `r18_accepted_manifest.json` 逐文件 SHA256 + `r18_multiscene_audit.json` 逐单复算 |
| `b04/r19_accepted/` | R19 三策略对照 **v1（修复前）**，保留用于缺陷复现 | `r19_accepted_manifest.json` + `r19_recompute_audit.json`（24 组复算 0 不符） |
| `b04/r19_accepted_v2/` | R19 三场景对照 **v2（修复后，当前结论）** | 同上，并额外记录**实现文件**哈希（`ortools_solver.py`、`handle_event.py`） |

两份 R19 归档都要保留：v1 是"修复前"的对照，v2 是当前结论；差异只在 B-04 冻结策略修复，见 `docs/R19_B04_RESCHEDULE_GUIDE.md`。

归档里的 `r18_accepted_manifest.json` / `r19_accepted_manifest.json` 记录了 `source_run`（原始运行目录名）与每个文件的 SHA256，所以**即使原始运行目录已清理，来源仍可追溯**。

## 关于已清理的运行目录（2026-10-15 交接整理）

为便于交接，删除了两个与归档**逐字节重复**的过程目录：

- `b03/r18_runs/`（含 dry-run 与正式运行，20 个文件）
- `b04/r19_runs/`（v1 与 v2 两次正式运行，32 个文件）

删除前逐文件核对过 SHA256：46 个归档证据文件与源目录**全部一致，0 处不符**。唯一不重复的文件是 R18 dry-run 的 `manifest.json`，它与归档版**只差 `status` 字段**（`not_started` vs `complete_validated_pair`），其余字段完全相同，因此判定为冗余后一并清理。

## 如何重新产生运行目录

```powershell
cd backend
python -m tools.r18_multiscene_ablation --case-count 5 --budget-ms 90000   # 输出到 ../benchmarks/b03/r18_runs/
python -m tools.r19_reschedule_ablation --case-count 3 --budget-ms 60000   # 输出到 ../benchmarks/b04/r19_runs/
python -m tools.r19_acceptance_freeze --run-dir ../benchmarks/b04/r19_runs/<时间戳>
```

两个运行目录都在 `scripts/project_files.py` 的打包排除列表与 `.gitignore` 里，不会进交付包、不会进版本库。

## 还没启用的子目录

`joint/`、`llm/`、`simulation/`、`transport/`、`warehouse/` 目前各只有一个占位文件，对应后续模块的基准入口。
