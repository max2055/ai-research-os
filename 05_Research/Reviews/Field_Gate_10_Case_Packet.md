# D-019 Field Gate — 10-case 多模式真实比较核验包

状态：`in_progress`（max 判定；阈值见 Phase 4 §11）
批次：2026-08-09（第一批 3 Sector case × 4 modes，DeepSeek deepseek-v4-flash）

运行 32 个；确定性 Gate 通过 32/32；整体均分 1.000

## Case: case-1-dram-share（事件 EVT-20260601-044）
| Run | 模式 | 均分 | Gate | citation/outside/sections/questions/counterev/placeholders |
|---|---|---|---|---|
| ANL-20260809-034 | open-discovery | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
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
- ANL-20260809-034  [open-discovery]  as_of=2026-08-09  review=pending  signal=positive

## Shared facts
EVT-20260601-044

## Distinct modes
MOD-ANL-open-discovery-v1, MOD-ANL-red-team-v1, MOD-ANL-scenario-v1, MOD-ANL-supply-demand-v1, MOD-ANL-value-chain-v1

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
- 存在哪些异常或弱信号？
- 库存与需求匹配吗？
- 扩产周期多长？
- 敏感性、催化剂与证伪条件？
- 时间错配或价值无法被公司捕获？
- 有哪些跨板块组合或未建模关系？
- 每个假设的最小所需证据是什么？
- 瓶颈和利润池正在向哪里移动？
- 监管/执行风险与不可观察变量？
- 谁获得或失去议价权？

## Evidence omitted by each run (used by another, not itself)
- ANL-20260809-002: —
- ANL-20260809-003: —
- ANL-20260809-004: —
- ANL-20260809-016: —
- ANL-20260809-034: —

## Conflicting signals (heuristic — human review required)
- ANL-20260809-002 (negative) vs ANL-20260809-003 (positive)
- ANL-20260809-002 (negative) vs ANL-20260809-016 (positive)
- ANL-20260809-002 (negative) vs ANL-20260809-034 (positive)
- ANL-20260809-003 (positive) vs ANL-20260809-004 (negative)
- ANL-20260809-004 (negative) vs ANL-20260809-016 (positive)
- ANL-20260809-004 (negative) vs ANL-20260809-034 (positive)

No majority voting: convergence weight must come from evidence quality, mechanism completeness, scope fit, calibration history or explicit researcher judgment (Phase 4 §6).

## Case: case-10-sap（事件 EVT-20260723-011）
| Run | 模式 | 均分 | Gate | citation/outside/sections/questions/counterev/placeholders |
|---|---|---|---|---|
| ANL-20260809-033 | competitive-dynamics | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-032 | value-chain | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |

多模式比较（D-011）：
# Mode comparison

## Runs
- ANL-20260809-032  [value-chain]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-033  [competitive-dynamics]  as_of=2026-08-09  review=pending  signal=positive

## Shared facts
EVT-20260723-011

## Distinct modes
MOD-ANL-competitive-dynamics-v1, MOD-ANL-value-chain-v1

## Distinct horizons
multi_year, quarter, year

## Questions
- 主要竞争者与替代品？
- 传导路径与时间滞后是什么？
- 供应依赖与商业模式冲突？
- 分发、数据、权限与标准控制力？
- 哪个环节增长但无法保留利润？
- 哪个环节控制稀缺资源、入口、标准或客户关系？
- 瓶颈和利润池正在向哪里移动？
- 谁获得或失去议价权？
- 进入壁垒与生态位？

## Evidence omitted by each run (used by another, not itself)
- ANL-20260809-032: —
- ANL-20260809-033: —

## Conflicting signals (heuristic — human review required)
- none

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
| ANL-20260809-035 | open-discovery | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-019 | scenario | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-018 | supply-demand | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-010 | value-chain | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |

多模式比较（D-011）：
# Mode comparison

## Runs
- ANL-20260809-010  [value-chain]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-018  [supply-demand]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-019  [scenario]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-035  [open-discovery]  as_of=2026-08-09  review=pending  signal=negative

## Shared facts
EVT-20260520-032

## Distinct modes
MOD-ANL-open-discovery-v1, MOD-ANL-scenario-v1, MOD-ANL-supply-demand-v1, MOD-ANL-value-chain-v1

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
- 存在哪些异常或弱信号？
- 库存与需求匹配吗？
- 扩产周期多长？
- 敏感性、催化剂与证伪条件？
- 有哪些跨板块组合或未建模关系？
- 每个假设的最小所需证据是什么？
- 瓶颈和利润池正在向哪里移动？
- 谁获得或失去议价权？

## Evidence omitted by each run (used by another, not itself)
- ANL-20260809-010: —
- ANL-20260809-018: —
- ANL-20260809-019: —
- ANL-20260809-035: —

## Conflicting signals (heuristic — human review required)
- ANL-20260809-010 (positive) vs ANL-20260809-035 (negative)
- ANL-20260809-018 (positive) vs ANL-20260809-035 (negative)
- ANL-20260809-019 (positive) vs ANL-20260809-035 (negative)

No majority voting: convergence weight must come from evidence quality, mechanism completeness, scope fit, calibration history or explicit researcher judgment (Phase 4 §6).

## Case: case-4-nvidia-fy27（事件 EVT-20260520-038）
| Run | 模式 | 均分 | Gate | citation/outside/sections/questions/counterev/placeholders |
|---|---|---|---|---|
| ANL-20260809-037 | company-fundamental | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-020 | red-team | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |

多模式比较（D-011）：
# Mode comparison

## Runs
- ANL-20260809-037  [company-fundamental]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-020  [red-team]  as_of=2026-08-09  review=pending  signal=positive

## Shared facts
EVT-20260520-038

## Distinct modes
MOD-ANL-company-fundamental-v1, MOD-ANL-red-team-v1

## Distinct horizons
immediate, multi_year, quarter, year

## Questions
- 估值是否已反映该预期？
- 共同上游与替代机制？
- 商业模式、成本结构与毛利？
- 存在哪些反面证据？
- 收入来源与客户结构如何？
- 时间错配或价值无法被公司捕获？
- 监管/执行风险与不可观察变量？
- 竞争优势与风险？
- 资本开支与现金流？

## Evidence omitted by each run (used by another, not itself)
- ANL-20260809-037: —
- ANL-20260809-020: —

## Conflicting signals (heuristic — human review required)
- none

No majority voting: convergence weight must come from evidence quality, mechanism completeness, scope fit, calibration history or explicit researcher judgment (Phase 4 §6).

## Case: case-5-skhynix-2q26（事件 EVT-20260728-036）
| Run | 模式 | 均分 | Gate | citation/outside/sections/questions/counterev/placeholders |
|---|---|---|---|---|
| ANL-20260809-038 | company-fundamental | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-039 | open-discovery | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-021 | red-team | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |

多模式比较（D-011）：
# Mode comparison

## Runs
- ANL-20260809-038  [company-fundamental]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-021  [red-team]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-039  [open-discovery]  as_of=2026-08-09  review=pending  signal=neutral

## Shared facts
EVT-20260728-036

## Distinct modes
MOD-ANL-company-fundamental-v1, MOD-ANL-open-discovery-v1, MOD-ANL-red-team-v1

## Distinct horizons
immediate, multi_year, quarter, year

## Questions
- 估值是否已反映该预期？
- 共同上游与替代机制？
- 商业模式、成本结构与毛利？
- 存在哪些反面证据？
- 存在哪些异常或弱信号？
- 收入来源与客户结构如何？
- 时间错配或价值无法被公司捕获？
- 有哪些跨板块组合或未建模关系？
- 每个假设的最小所需证据是什么？
- 监管/执行风险与不可观察变量？
- 竞争优势与风险？
- 资本开支与现金流？

## Evidence omitted by each run (used by another, not itself)
- ANL-20260809-038: —
- ANL-20260809-021: —
- ANL-20260809-039: —

## Conflicting signals (heuristic — human review required)
- none

No majority voting: convergence weight must come from evidence quality, mechanism completeness, scope fit, calibration history or explicit researcher judgment (Phase 4 §6).

## Case: case-6-tsmc-2q26（事件 EVT-20260716-037）
| Run | 模式 | 均分 | Gate | citation/outside/sections/questions/counterev/placeholders |
|---|---|---|---|---|
| ANL-20260809-023 | company-fundamental | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-024 | red-team | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-022 | value-chain | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |

多模式比较（D-011）：
# Mode comparison

## Runs
- ANL-20260809-022  [value-chain]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-023  [company-fundamental]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-024  [red-team]  as_of=2026-08-09  review=pending  signal=positive

## Shared facts
EVT-20260716-037

## Distinct modes
MOD-ANL-company-fundamental-v1, MOD-ANL-red-team-v1, MOD-ANL-value-chain-v1

## Distinct horizons
immediate, multi_year, quarter, year

## Questions
- 传导路径与时间滞后是什么？
- 估值是否已反映该预期？
- 共同上游与替代机制？
- 哪个环节增长但无法保留利润？
- 哪个环节控制稀缺资源、入口、标准或客户关系？
- 商业模式、成本结构与毛利？
- 存在哪些反面证据？
- 收入来源与客户结构如何？
- 时间错配或价值无法被公司捕获？
- 瓶颈和利润池正在向哪里移动？
- 监管/执行风险与不可观察变量？
- 竞争优势与风险？
- 谁获得或失去议价权？
- 资本开支与现金流？

## Evidence omitted by each run (used by another, not itself)
- ANL-20260809-022: —
- ANL-20260809-023: —
- ANL-20260809-024: —

## Conflicting signals (heuristic — human review required)
- none

No majority voting: convergence weight must come from evidence quality, mechanism completeness, scope fit, calibration history or explicit researcher judgment (Phase 4 §6).

## Case: case-7-samsung-hbm4（事件 EVT-20260316-042）
| Run | 模式 | 均分 | Gate | citation/outside/sections/questions/counterev/placeholders |
|---|---|---|---|---|
| ANL-20260809-036 | open-discovery | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-025 | red-team | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |

多模式比较（D-011）：
# Mode comparison

## Runs
- ANL-20260809-025  [red-team]  as_of=2026-08-09  review=pending  signal=neutral
- ANL-20260809-036  [open-discovery]  as_of=2026-08-09  review=pending  signal=neutral

## Shared facts
EVT-20260316-042

## Distinct modes
MOD-ANL-open-discovery-v1, MOD-ANL-red-team-v1

## Distinct horizons
immediate, quarter, year

## Questions
- 估值是否已反映该预期？
- 共同上游与替代机制？
- 存在哪些反面证据？
- 存在哪些异常或弱信号？
- 时间错配或价值无法被公司捕获？
- 有哪些跨板块组合或未建模关系？
- 每个假设的最小所需证据是什么？
- 监管/执行风险与不可观察变量？

## Evidence omitted by each run (used by another, not itself)
- ANL-20260809-025: —
- ANL-20260809-036: —

## Conflicting signals (heuristic — human review required)
- none

No majority voting: convergence weight must come from evidence quality, mechanism completeness, scope fit, calibration history or explicit researcher judgment (Phase 4 §6).

## Case: case-8-asml-euv（事件 EVT-20260225-034）
| Run | 模式 | 均分 | Gate | citation/outside/sections/questions/counterev/placeholders |
|---|---|---|---|---|
| ANL-20260809-028 | red-team | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-027 | scenario | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-040 | technology-curve | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-026 | value-chain | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |

多模式比较（D-011）：
# Mode comparison

## Runs
- ANL-20260809-026  [value-chain]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-040  [technology-curve]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-027  [scenario]  as_of=2026-08-09  review=pending  signal=neutral
- ANL-20260809-028  [red-team]  as_of=2026-08-09  review=pending  signal=positive

## Shared facts
EVT-20260225-034

## Distinct modes
MOD-ANL-red-team-v1, MOD-ANL-scenario-v1, MOD-ANL-technology-curve-v1, MOD-ANL-value-chain-v1

## Distinct horizons
immediate, multi_year, quarter, year

## Questions
- Downside / Base / Upside 结果与时间？
- 传导路径与时间滞后是什么？
- 估值是否已反映该预期？
- 共同上游与替代机制？
- 关键驱动变量与情景概率？
- 哪个环节增长但无法保留利润？
- 哪个环节控制稀缺资源、入口、标准或客户关系？
- 存在哪些反面证据？
- 性能、成本、能效的演进轨迹如何？
- 成熟度与所处阶段（实验室/产品/规模生产）？
- 扩散速度与工程约束？
- 敏感性、催化剂与证伪条件？
- 时间错配或价值无法被公司捕获？
- 替代路径有哪些？
- 瓶颈和利润池正在向哪里移动？
- 监管/执行风险与不可观察变量？
- 谁获得或失去议价权？

## Evidence omitted by each run (used by another, not itself)
- ANL-20260809-026: —
- ANL-20260809-040: —
- ANL-20260809-027: —
- ANL-20260809-028: —

## Conflicting signals (heuristic — human review required)
- none

No majority voting: convergence weight must come from evidence quality, mechanism completeness, scope fit, calibration history or explicit researcher judgment (Phase 4 §6).

## Case: case-9-oracle（事件 EVT-20260610-007）
| Run | 模式 | 均分 | Gate | citation/outside/sections/questions/counterev/placeholders |
|---|---|---|---|---|
| ANL-20260809-030 | competitive-dynamics | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-031 | red-team | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |
| ANL-20260809-029 | value-chain | 1.00 | PASS | cite 1.00 / out 1 / sec 1.00 / q 1.00 / ce 1 / ph 1 |

多模式比较（D-011）：
# Mode comparison

## Runs
- ANL-20260809-029  [value-chain]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-030  [competitive-dynamics]  as_of=2026-08-09  review=pending  signal=positive
- ANL-20260809-031  [red-team]  as_of=2026-08-09  review=pending  signal=positive

## Shared facts
EVT-20260610-007

## Distinct modes
MOD-ANL-competitive-dynamics-v1, MOD-ANL-red-team-v1, MOD-ANL-value-chain-v1

## Distinct horizons
immediate, multi_year, quarter, year

## Questions
- 主要竞争者与替代品？
- 传导路径与时间滞后是什么？
- 估值是否已反映该预期？
- 供应依赖与商业模式冲突？
- 共同上游与替代机制？
- 分发、数据、权限与标准控制力？
- 哪个环节增长但无法保留利润？
- 哪个环节控制稀缺资源、入口、标准或客户关系？
- 存在哪些反面证据？
- 时间错配或价值无法被公司捕获？
- 瓶颈和利润池正在向哪里移动？
- 监管/执行风险与不可观察变量？
- 谁获得或失去议价权？
- 进入壁垒与生态位？

## Evidence omitted by each run (used by another, not itself)
- ANL-20260809-029: —
- ANL-20260809-030: —
- ANL-20260809-031: —

## Conflicting signals (heuristic — human review required)
- none

No majority voting: convergence weight must come from evidence quality, mechanism completeness, scope fit, calibration history or explicit researcher judgment (Phase 4 §6).

## 人工评分表（§11 八维，0-1）
| Case | Run | 引用准确 | 无外事实 | 问题覆盖 | 反证完整 | 假设显式 | 分歧可解释 | 节省时间 | 过度结论 |
|---|---|---|---|---|---|---|---|---|---|
| case-1-dram-share | ANL-20260809-034（open-discovery） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-1-dram-share | ANL-20260809-016（red-team） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-1-dram-share | ANL-20260809-004（scenario） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-1-dram-share | ANL-20260809-003（supply-demand） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-1-dram-share | ANL-20260809-002（value-chain） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-10-sap | ANL-20260809-033（competitive-dynamics） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-10-sap | ANL-20260809-032（value-chain） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-2-ai-demand | ANL-20260809-015（red-team） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-2-ai-demand | ANL-20260809-017（scenario） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-2-ai-demand | ANL-20260809-014（supply-demand） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-2-ai-demand | ANL-20260809-006（value-chain） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-3-lead-times | ANL-20260809-035（open-discovery） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-3-lead-times | ANL-20260809-019（scenario） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-3-lead-times | ANL-20260809-018（supply-demand） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-3-lead-times | ANL-20260809-010（value-chain） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-4-nvidia-fy27 | ANL-20260809-037（company-fundamental） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-4-nvidia-fy27 | ANL-20260809-020（red-team） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-5-skhynix-2q26 | ANL-20260809-038（company-fundamental） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-5-skhynix-2q26 | ANL-20260809-039（open-discovery） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-5-skhynix-2q26 | ANL-20260809-021（red-team） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-6-tsmc-2q26 | ANL-20260809-023（company-fundamental） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-6-tsmc-2q26 | ANL-20260809-024（red-team） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-6-tsmc-2q26 | ANL-20260809-022（value-chain） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-7-samsung-hbm4 | ANL-20260809-036（open-discovery） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-7-samsung-hbm4 | ANL-20260809-025（red-team） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-8-asml-euv | ANL-20260809-028（red-team） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-8-asml-euv | ANL-20260809-027（scenario） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-8-asml-euv | ANL-20260809-040（technology-curve） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-8-asml-euv | ANL-20260809-026（value-chain） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-9-oracle | ANL-20260809-030（competitive-dynamics） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-9-oracle | ANL-20260809-031（red-team） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| case-9-oracle | ANL-20260809-029（value-chain） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

## 阈值（§11）
- 引用/归属 100% 可解析
- 无 Source 外关键事实
- 必填问题覆盖 ≥ 90%
- 关键反证遗漏率 < 10%
- 人工认为「有增量价值」的 Run ≥ 70%
- Open Discovery 候选中至少一半可判定 investigate/reject
- 不使用多数投票产生权威结论

## 人工评分结果（2026-08-09，max 确认）

状态：**PASS**（32 run；确定性 32/32 PASS overall 1.0；人工整体均分 0.992）

| Case | Run | 引用准确 | 无外事实 | 问题覆盖 | 反证完整 | 假设显式 | 分歧可解释 | 节省时间 | 过度结论(反) | 均分 |
|---|---|---|---|---|---|---|---|---|---|---|
| case-1-dram-share | 002 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-1-dram-share | 003 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-1-dram-share | 004 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-1-dram-share | 016 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-1-dram-share | 034 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-2-ai-demand | 006 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-2-ai-demand | 014 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-2-ai-demand | 017 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 0.9 | 1.0 | 1.0 | 0.97 |
| case-2-ai-demand | 015 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-3-lead-times | 010 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 0.9 | 1.0 | 1.0 | 0.97 |
| case-3-lead-times | 018 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-3-lead-times | 019 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 0.9 | 1.0 | 1.0 | 0.97 |
| case-3-lead-times | 035 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 0.99 |
| case-4-nvidia-fy27 | 037 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-4-nvidia-fy27 | 020 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-5-skhynix-2q2 | 038 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-5-skhynix-2q2 | 021 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-5-skhynix-2q2 | 039 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-6-tsmc-2q26 | 022 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-6-tsmc-2q26 | 023 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-6-tsmc-2q26 | 024 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-7-samsung-hbm | 025 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-7-samsung-hbm | 036 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 1.0 | 1.0 | 0.99 |
| case-8-asml-euv | 026 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-8-asml-euv | 040 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 1.0 | 1.0 | 0.99 |
| case-8-asml-euv | 027 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 1.0 | 1.0 | 0.99 |
| case-8-asml-euv | 028 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-9-oracle | 029 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 1.0 | 1.0 | 0.99 |
| case-9-oracle | 030 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-9-oracle | 031 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-10-sap | 032 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.00 |
| case-10-sap | 033 | 1.0 | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 1.0 | 1.0 | 0.99 |

§11 阈值判定：citation_resolvable_100pct=True；no_outside_facts=True；question_coverage_ge_90pct=True；counterevidence_omission_lt_10pct=True；human_incremental_value_ge_70pct=True；open_discovery_judgeable_ge_half=True；no_majority_voting=True

## 记录缺口（13 个，max 接受为发现，不烧 API 重试）

- scenario: case-4, case-5, case-6, case-7, case-9, case-10
- value-chain: case-4, case-5, case-7
- red-team: case-3, case-10
- technology-curve: case-7
- open-discovery: case-9
- root_causes: scenario mode (6 sections) fragile with deepseek-v4-flash, event-level persistent outside-citation: case-7->SRC-20260806-052, case-9/10->THS-004, case-3 red-team->SRC-20260805-040 (D-004 blocks)

根因：scenario mode (6 sections) fragile with deepseek-v4-flash；event-level persistent outside-citation: case-7->SRC-20260806-052, case-9/10->THS-004, case-3 red-team->SRC-20260805-040 (D-004 blocks)

确认人：max；判断初稿由 agent 起草，扣分仅两处（honest-absence 反证 8 run × 0.9、冲突 case 分歧可解释 13 run × 0.9）。
