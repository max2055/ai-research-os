# D-019 Field Gate — 10-case 多模式真实比较核验包

状态：`in_progress`（max 判定；阈值见 Phase 4 §11）
批次：2026-08-09（第一批 3 Sector case × 4 modes，DeepSeek deepseek-v4-flash）

运行 11 个；确定性 Gate 通过 11/11；整体均分 1.000

## Case: case-1-dram-share（事件 EVT-20260601-044）
| Run | 模式 | 均分 | Gate | citation/outside/sections/questions/counterev/placeholders |
|---|---|---|---|---|
| ANL-20260809-016 | red-team | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-004 | scenario | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-003 | supply-demand | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-002 | value-chain | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |

多模式比较（D-011）：
# Mode comparison

## Runs
- ANL-20260809-002  [value-chain]  as_of=2026-08-09  review=pending  signal=negative
- ANL-20260809-003  [supply-demand]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-004  [scenario]  as_of=2026-08-09  review=pending  signal=negative
- ANL-20260809-016  [red-team]  as_of=2026-08-09  review=pending  signal=positive

## Shared facts
EVT-20260601-044

## Distinct modes
MOD-ANL-red-team-v1, MOD-ANL-scenario-v1, MOD-ANL-supply-demand-v1, MOD-ANL-value-chain-v1

## Distinct horizons
immediate, multi_year, quarter, year

## Questions
- Downside / Base / Upside 结果与时间？
- 产能与供给弹性如何变化？
- 传导路径与时间滞后是什么？
- 估值是否已反映该预期？
- 共同上游与替代机制？
- 关键驱动变量与情景概率？
- 利用率与价格走向如何？
- 哪个环节增长但无法保留利润？
- 哪个环节控制稀缺资源、入口、标准或客户关系？
- 存在哪些反面证据？
- 库存与需求匹配吗？
- 扩产周期多长？
- 敏感性、催化剂与证伪条件？
- 时间错配或价值无法被公司捕获？
- 瓶颈和利润池正在向哪里移动？
- 监管/执行风险与不可观察变量？
- 谁获得或失去议价权？

## Evidence omitted by each run (used by another, not itself)
- ANL-20260809-002: —
- ANL-20260809-003: —
- ANL-20260809-004: —
- ANL-20260809-016: —

## Conflicting signals (heuristic — human review required)
- ANL-20260809-002 (negative) vs ANL-20260809-003 (positive)
- ANL-20260809-002 (negative) vs ANL-20260809-016 (positive)
- ANL-20260809-003 (positive) vs ANL-20260809-004 (negative)
- ANL-20260809-004 (negative) vs ANL-20260809-016 (positive)

No majority voting: convergence weight must come from evidence quality, mechanism completeness, scope fit, calibration history or explicit researcher judgment (Phase 4 §6).

## Case: case-2-ai-demand（事件 EVT-20260302-041）
| Run | 模式 | 均分 | Gate | citation/outside/sections/questions/counterev/placeholders |
|---|---|---|---|---|
| ANL-20260809-015 | red-team | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-017 | scenario | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-014 | supply-demand | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-006 | value-chain | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |

多模式比较（D-011）：
# Mode comparison

## Runs
- ANL-20260809-006  [value-chain]  as_of=2026-08-09  review=pending  signal=neutral
- ANL-20260809-014  [supply-demand]  as_of=2026-08-09  review=pending  signal=negative
- ANL-20260809-017  [scenario]  as_of=2026-08-09  review=pending  signal=negative
- ANL-20260809-015  [red-team]  as_of=2026-08-09  review=pending  signal=positive

## Shared facts
EVT-20260302-041

## Distinct modes
MOD-ANL-red-team-v1, MOD-ANL-scenario-v1, MOD-ANL-supply-demand-v1, MOD-ANL-value-chain-v1

## Distinct horizons
immediate, multi_year, quarter, year

## Questions
- Downside / Base / Upside 结果与时间？
- 产能与供给弹性如何变化？
- 传导路径与时间滞后是什么？
- 估值是否已反映该预期？
- 共同上游与替代机制？
- 关键驱动变量与情景概率？
- 利用率与价格走向如何？
- 哪个环节增长但无法保留利润？
- 哪个环节控制稀缺资源、入口、标准或客户关系？
- 存在哪些反面证据？
- 库存与需求匹配吗？
- 扩产周期多长？
- 敏感性、催化剂与证伪条件？
- 时间错配或价值无法被公司捕获？
- 瓶颈和利润池正在向哪里移动？
- 监管/执行风险与不可观察变量？
- 谁获得或失去议价权？

## Evidence omitted by each run (used by another, not itself)
- ANL-20260809-006: —
- ANL-20260809-014: —
- ANL-20260809-017: —
- ANL-20260809-015: —

## Conflicting signals (heuristic — human review required)
- ANL-20260809-014 (negative) vs ANL-20260809-015 (positive)
- ANL-20260809-017 (negative) vs ANL-20260809-015 (positive)

No majority voting: convergence weight must come from evidence quality, mechanism completeness, scope fit, calibration history or explicit researcher judgment (Phase 4 §6).

## Case: case-3-lead-times（事件 EVT-20260520-032）
| Run | 模式 | 均分 | Gate | citation/outside/sections/questions/counterev/placeholders |
|---|---|---|---|---|
| ANL-20260809-019 | scenario | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-018 | supply-demand | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-010 | value-chain | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |

多模式比较（D-011）：
# Mode comparison

## Runs
- ANL-20260809-010  [value-chain]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-018  [supply-demand]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-019  [scenario]  as_of=2026-08-09  review=pending  signal=positive

## Shared facts
EVT-20260520-032

## Distinct modes
MOD-ANL-scenario-v1, MOD-ANL-supply-demand-v1, MOD-ANL-value-chain-v1

## Distinct horizons
multi_year, quarter, year

## Questions
- Downside / Base / Upside 结果与时间？
- 产能与供给弹性如何变化？
- 传导路径与时间滞后是什么？
- 关键驱动变量与情景概率？
- 利用率与价格走向如何？
- 哪个环节增长但无法保留利润？
- 哪个环节控制稀缺资源、入口、标准或客户关系？
- 库存与需求匹配吗？
- 扩产周期多长？
- 敏感性、催化剂与证伪条件？
- 瓶颈和利润池正在向哪里移动？
- 谁获得或失去议价权？

## Evidence omitted by each run (used by another, not itself)
- ANL-20260809-010: —
- ANL-20260809-018: —
- ANL-20260809-019: —

## Conflicting signals (heuristic — human review required)
- none

No majority voting: convergence weight must come from evidence quality, mechanism completeness, scope fit, calibration history or explicit researcher judgment (Phase 4 §6).

## 人工评分表（§11 八维，0-1）
| Case | Run | 引用准确 | 无外事实 | 问题覆盖 | 反证完整 | 假设显式 | 分歧可解释 | 节省时间 | 过度结论 |
|---|---|---|---|---|---|---|---|---|---|
| case-1-dram-share | ANL-20260809-016（red-team） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-1-dram-share | ANL-20260809-004（scenario） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-1-dram-share | ANL-20260809-003（supply-demand） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-1-dram-share | ANL-20260809-002（value-chain） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-2-ai-demand | ANL-20260809-015（red-team） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-2-ai-demand | ANL-20260809-017（scenario） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-2-ai-demand | ANL-20260809-014（supply-demand） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-2-ai-demand | ANL-20260809-006（value-chain） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-3-lead-times | ANL-20260809-019（scenario） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-3-lead-times | ANL-20260809-018（supply-demand） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-3-lead-times | ANL-20260809-010（value-chain） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

## 阈值（§11）
- 引用/归属 100% 可解析
- 无 Source 外关键事实
- 必填问题覆盖 ≥ 90%
- 关键反证遗漏率 < 10%
- 人工认为「有增量价值」的 Run ≥ 70%
- Open Discovery 候选中至少一半可判定 investigate/reject
- 不使用多数投票产生权威结论
## 已知缺口（记录在案，非静默跳过）

- **case-3-lead-times / red-team 未落盘**：EVT-20260520-032 的 red-team run 6 次尝试全部被
  D-004 契约拒绝——模型持续引用冻结输入外的 SRC-20260805-040（真实 NVIDIA 源）。契约正确拦截
  （no facts outside inputs）。结论：red-team 对单事件输入（NVIDIA 交期）难以约束在冻结证据内，
  是该模式的真实失败模式，需在人工评审时专项关注（或考虑为 red-team 提供更丰富的冻结输入）。

## 人工评分结果（2026-08-09，max 确认）

状态：**PASS**（11/11 run；整体均分 0.989）

| Case | Run | 引用准确 | 无外事实 | 问题覆盖 | 反证完整 | 假设显式 | 分歧可解释 | 节省时间 | 过度结论(反) | 均分 |
|---|---|---|---|---|---|---|---|---|---|---|
| case-1-dram-shar | ANL-20260809-002 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-1-dram-shar | ANL-20260809-003 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-1-dram-shar | ANL-20260809-004 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-1-dram-shar | ANL-20260809-016 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-2-ai-demand | ANL-20260809-006 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-2-ai-demand | ANL-20260809-014 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-2-ai-demand | ANL-20260809-015 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-2-ai-demand | ANL-20260809-017 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-3-lead-time | ANL-20260809-010 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 1.0 | 1.0 | 0.99 |
| case-3-lead-time | ANL-20260809-018 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 1.0 | 1.0 | 0.99 |
| case-3-lead-time | ANL-20260809-019 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |

§11 阈值判定：citation_resolvable_100pct=True；no_outside_facts=True；question_coverage_ge_90pct=True；counterevidence_omission_lt_10pct=True；human_incremental_value_ge_70pct=True；open_discovery_judgeable=n/a-batch1；no_majority_voting=True

**Open gap**：case-3-lead-times red-team: 6 attempts blocked by D-004 (persistent SRC-20260805-040 citation outside frozen inputs); recorded as documented gap, remediation pending max decision

确认人：max；判断初稿由 agent 起草，扣分仅两处（case-1/2 分歧可解释 0.9，NVIDIA run 反证诚实缺失 0.9）。
