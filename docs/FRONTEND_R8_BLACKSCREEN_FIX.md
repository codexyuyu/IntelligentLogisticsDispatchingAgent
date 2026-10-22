# Frontend R8 黑屏修复

## 根因
基准实验页面使用了 `icon="list"`，但 `frontend/src/components/Icons.tsx` 原本没有 `list` 图标定义。`Icon` 组件直接执行 `paths[name].map(...)`，因此 `paths['list']` 为 `undefined`，点击进入/运行基准实验后触发运行时 TypeError，React 根组件崩溃并出现黑屏。

## 修复
1. 增加 `list` 图标定义。
2. 修复 `route` 图标中重复 SVG path key，避免 React duplicate key 警告。
3. 检查当前前端所有 `icon="..."` 使用点，确保都有对应图标定义。

## 未修改
FastAPI、OpenAPI、OR-Tools、CP-SAT、Routing、SimPy、数据库和现有后端接口均未修改。
