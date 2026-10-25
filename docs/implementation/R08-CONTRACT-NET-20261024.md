# R08 合同网协议核心移植

## 结论

R08 的**协调者/协议核心**已移植到当前 `packages/agents`，20 条协议测试通过。  
仓储/运输/异常三个具体角色尚未移植，因此不能声称 R08 四角色集成完成。

## 移植内容

- `packages/agents/src/logistics_agents/contract_net.py`
  - CFP / bid / conflict / award / confirm / revoke / close
  - 有界轮数、响应截止、确认保护
  - 过期/越界/陈旧轮次拒绝
  - 冲突排名与授标
  - append-only transcript + SHA-256 digest
  - idempotency 重放
  - `format_transcript`
- `tests/unit/test_contract_net_protocol.py`
  - 移植对方 20 条协议测试

## 验证

```text
tests/unit/test_contract_net_protocol.py：20 passed
全量：329 passed in 137.82s，exit 0
architecture：123 modules，0 violations
schema --check：exit 0
```

## 未移植

- `WarehouseWindowRole`
- `TransportWindowRole`
- `ExceptionRecoveryRole`
- `negotiation_link`（把协商绑定到真实计划）
- HTTP/API/持久化/transcript 展示
- 与 R09 observations 的联动

下一步把这些角色绑定到当前 `PlanningSnapshot` / `CandidatePlan` / 资源日历，再做 R09。
