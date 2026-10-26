# 历史教学探针，非正式接口

这三个探针来自本项目前期验证：仓储、运输、边界故障重排；曾在 Windows/Python 3.12 通过11项检查。它们使用整数分钟和简化字典，不能直接导入正式业务代码。

单独安装本目录 requirements-lock.txt 后运行 `python reference_demos/run.py all`，测试 `python -m unittest discover -s reference_demos -p test_demos.py`。这是独立测试，不计入当前骨架业务完成度。当前主包契约见 contracts/README.md。

OR-Tools 9.15 已测包的 SetAllowedVehiclesForIndex 有 Span 绑定问题，transport.py 用 VehicleVar.RemoveValue 排除不兼容车辆；后续应保留温区反例。参考 [上游问题](https://github.com/google/or-tools/issues/4982)。
