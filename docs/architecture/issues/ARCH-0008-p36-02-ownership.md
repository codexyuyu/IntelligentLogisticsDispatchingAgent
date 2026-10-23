# ARCH-0008 P36-02矩阵源码与任务归属冲突

- id：ARCH-0008
- status：decided
- discovered_by_task：N01对manifest与OWNERSHIP逐路径核验。
- title：P36-02原任务owner为A，matrix.py/matrix_cache.py按路径归B。
- evidence：[OWNERSHIP](../../../OWNERSHIP.json)的最长前缀规则将`packages/optimization/`及`tests/solver/`归B；[catalog](../../../tools/ai_coding_plan/build_catalog.py)原phase=36默认A；矩阵源码实际路径为`packages/optimization/src/logistics_optimization/transport/matrix.py`、`matrix_cache.py`。
- impact：若按任务标题给A矩阵写权限，会违反路径所有权；G36缓存正确性及跨域基准证据需要两方贡献。
- blocking：no（治理分工已裁定；真实贡献和验收尚未运行）。
- decision：B贡献两项矩阵源码及`tests/solver/test_p36_02_bounded_performance_fix.py`，负责缓存命中/版本失效/有界内存/超大entry正反例；A负责既有unit/integration测试、`docs/performance/CHANGE_EVIDENCE.md`、`benchmarks/regression.json`和本任务报告/交接，承担整合责任。catalog生成`contributions`与`integration_owner=A`，贡献集合无交集且并集为任务精确白名单，新增solver测试纳入必需命令。B先交贡献候选/日志/hash，A核验整合后由ZCode独立预验收，再独立Codex审查G36。
- owner：A/B按路径；A整合者不获得B源码权限。B贡献证据由真实B执行者生成；本轮不创建B/DSH记录，不修改矩阵实现。
- links：[manifest](../../plan/TASK_MANIFEST.json)、[迁移说明](../../../contracts/changes/N01-governance-1.0.1.md)。
