---
id: MOD-ANL-value-chain-v1
type: analysis_mode
title: Value Chain Mode
created_at: 2026-08-08
updated_at: 2026-08-08
schema_version: 2
project_ids: []
status: proposed
review_status: pending
tags: []
name: 价值链分析
purpose: 定位价值链各环节的控制力、瓶颈与利润池迁移，识别受益/受损环节与传导路径。
applicable_scopes: [sector, company, technology, event, thesis]
required_input_types: [event]
optional_input_types: [source, impact_assertion]
required_questions:
  - 哪个环节控制稀缺资源、入口、标准或客户关系？
  - 瓶颈和利润池正在向哪里移动？
  - 谁获得或失去议价权？
  - 传导路径与时间滞后是什么？
  - 哪个环节增长但无法保留利润？
required_output_sections: [Current chain, Changed chain, Beneficiaries and losers, Mechanism, Falsification indicators]
assumption_policy: 显式列出假设，并与事实分离标注。
evidence_policy: 只引用冻结输入中的事件，按永久 ID 标注；不得引入输入外事实。
counterevidence_policy: 对每个受益/受损判断列出反向证据，或说明为何缺失。
time_horizons: [quarter, year, multi_year]
prohibited_conclusions:
  - 不得输出投资建议或买卖指令。
output_schema_path: 00_System/Analysis_Modes/output_contract_schema.json
evaluator_version: ""
---

# Value Chain Mode

## Purpose

定位价值链各环节的控制力、瓶颈与利润池迁移，识别受益/受损环节与传导路径（Phase 4 §4.1）。

## Scope

- 适用范围：sector / company / technology / event / thesis
- 必填输入：event；可选输入：source / impact_assertion

## Questions

- 哪个环节控制稀缺资源、入口、标准或客户关系？
- 瓶颈和利润池正在向哪里移动？
- 谁获得或失去议价权？
- 传导路径与时间滞后是什么？
- 哪个环节增长但无法保留利润？

## Output requirements

必须输出：当前链、变化后链、受益/受损环节、机制、证伪指标。

## Prohibitions

- 不得输出投资建议或买卖指令。

## Review

Drafted as proposed；pending human review（RCP-v03-007 point 6）before activation。
