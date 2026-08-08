---
id: MOD-ANL-technology-curve-v1
type: analysis_mode
title: Technology Curve Mode
created_at: 2026-08-08
updated_at: 2026-08-08
schema_version: 2
project_ids: []
status: proposed
review_status: pending
tags: []
name: 技术曲线分析
purpose: 评估技术性能、成本、能效、成熟度、替代路径、扩散速度与工程约束。
applicable_scopes: [technology, company, sector, event]
required_input_types: [event]
optional_input_types: [source]
required_questions:
  - 性能、成本、能效的演进轨迹如何？
  - 成熟度与所处阶段（实验室/产品/规模生产）？
  - 替代路径有哪些？
  - 扩散速度与工程约束？
required_output_sections: [Performance-cost-efficiency trajectory, Maturity and adoption stage, Alternative paths, Engineering constraints]
assumption_policy: 显式标注技术阶段判断依据。
evidence_policy: 只引用冻结输入；区分 benchmark、实验室结果、产品发布、客户试点与规模生产。
counterevidence_policy: 对成熟度/扩散判断列出反证，或说明为何缺失。
time_horizons: [year, multi_year]
prohibited_conclusions:
  - 不得把实验室或 benchmark 结果当作规模生产事实。
  - 不得输出投资建议或买卖指令。
output_schema_path: 00_System/Analysis_Modes/output_contract_schema.json
evaluator_version: ""
---

# Technology Curve Mode

## Purpose

评估技术性能、成本、能效、成熟度、替代路径、扩散速度与工程约束（Phase 4 §4.3）。

## Scope

- 适用范围：technology / company / sector / event
- 必填输入：event；可选输入：source

## Questions

- 性能、成本、能效的演进轨迹如何？
- 成熟度与所处阶段（实验室/产品/规模生产）？
- 替代路径有哪些？
- 扩散速度与工程约束？

## Output requirements

必须输出性能-成本-能效轨迹、成熟度与采用阶段、替代路径、工程约束。

## Prohibitions

- 不得把实验室或 benchmark 结果当作规模生产事实。
- 不得输出投资建议或买卖指令。

## Review

Drafted as proposed；pending human review（RCP-v03-007 point 6）before activation。
