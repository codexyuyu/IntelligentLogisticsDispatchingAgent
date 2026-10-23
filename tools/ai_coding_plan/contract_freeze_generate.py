"""Generate docs/architecture/CONTRACT_FREEZE.json with real sha256 of the frozen set.

P00-02 deliverable generator. Usage: python tools/ai_coding_plan/contract_freeze_generate.py [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/architecture/CONTRACT_FREEZE.json"

SCHEMA_VERSION = "1.0.0"
PLAN_VERSION = "1.0.0"
REVIEWER = "planner-checker:tools/ai_coding_plan/validate_plan.py --self-test --record-g00"
REVIEWED_AT = "2026-09-12T00:00:00+00:00"

# The frozen contract set. Kept in sync with validate_plan.record_g00's required_contracts.
FROZEN: list[tuple[str, str, str]] = [
    ("PROJECT_MASTER_PLAN.md", "总体设计：阶段、目标结构、验收定义", "全部Task的上下文约束"),
    ("TASK_GRAPH.md", "109个Task/40个Gate的依赖与并行写集合", "G00–G39依赖判定"),
    ("docs/architecture/ARCHITECTURE_OVERVIEW.md", "模块图、依赖方向、层禁止项", "P01-02层边界检查、P02起全阶段"),
    ("docs/architecture/DOMAIN_CATALOG.md", "32实体、状态、生命周期", "P02-01..P02-04、P03、P04"),
    ("docs/architecture/DATA_CONTRACTS.md", "边界DTO/Protocol、单位、错误、SolveStatus/JobStatus", "P02-04、P05-01、P06-01"),
    ("docs/architecture/IMPLEMENTATION_CONVENTIONS.md", "包路径、组合根、内部接口接线、文件变更证据", "P01-01、P01-02、P01-03"),
    ("docs/api/API_CONTRACT.md", "HTTP前缀、错误码、幂等/If-Match/actor/trace_id", "P05-01..P05-03、P16、P24-02"),
    ("docs/algorithms/OPTIMIZATION_CONTRACT.md", "候选/硬约束/独立校验/预算与状态", "P06–P10、P15–P16"),
    ("docs/algorithms/SIMULATION_CONTRACT.md", "仿真状态、事件、RNG、快照与分支隔离", "P11–P13、P28"),
    ("docs/algorithms/METRICS_CONTRACT.md", "14项指标公式、分母缺失语义", "P32-01..P32-03、P33"),
    ("docs/plan/TEST_FIXTURES.md", "T1/W1/J1/I1/S1/M1可手算验收数据", "P04-01起全部算法与集成Task"),
    ("docs/plan/PHASE_GATES.md", "40个Gate的必需Task与附加业务断言", "全部Gate"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_revision() -> str:
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return "no-git"
    if head.returncode != 0:
        return "no-git"
    return "git:" + head.stdout.strip()


def build() -> dict:
    artifacts = []
    for relative, role, consumers in FROZEN:
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"frozen contract missing: {relative}")
        artifacts.append({"path": relative, "sha256": sha256(path), "role": role, "consumers": consumers})
    return {
        "schema_version": SCHEMA_VERSION,
        "plan_version": PLAN_VERSION,
        "reviewed_at": REVIEWED_AT,
        "reviewer": REVIEWER,
        "frozen_contract_version": "1.0.0",
        "legacy_contract_version": "0.1.0",
        "code_revision": git_revision(),
        "unresolved_blocking_issues": [],
        "non_blocking_observations": [
            "本轮只冻结文档契约；尚无应用代码、尚无任何应用测试执行证据。",
            "scripts/gates.py 与 scripts/check_architecture.py 由 P01-02 交付；交付前 G01 及之后无法判定 passed。",
            "仓库当前没有 Git；code_revision 使用 no-git，Gate 证据按 PHASE_GATES 用相关源文件清单 hash 替代。",
            "旧 demo 契约版本 0.1.0 只作为迁移输入；v1 契约版本 1.0.0，禁止覆盖旧版本文件。",
            "ARCH-0001（非阻断）：需求追踪表 R08 行的验证 Gate 与其任务所属阶段不一致；详见 docs/architecture/issues/README.md。",
            "ARCH-0002（非阻断）：旧基线清单为登记集合而非穷举集合；详见 docs/architecture/issues/README.md。",
            "ARCH-0003（非阻断）：任务 Prompt 要求的错误码 UNSUPPORTED 未登记在 DATA_CONTRACTS 错误表中，需在 P05-01 错误协议实现前裁定；详见 docs/architecture/issues/README.md。",
        ],
        "change_policy": {
            "major": "破坏字段/单位/enum/路径/必需语义",
            "minor": "新增可选字段",
            "patch": "兼容修复",
            "order": "domain -> DTO -> ports -> callers -> tests -> 生成产物；生成产物禁止手改",
        },
        "artifacts": artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build()
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != text:
            print("CONTRACT_FREEZE.json is stale; regenerate it")
            return 1
        print(f"CONTRACT_FREEZE.json up to date ({len(payload['artifacts'])} artifacts)")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(payload['artifacts'])} artifacts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
