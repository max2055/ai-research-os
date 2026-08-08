---
id: MOD-ANL-competitive-dynamics-v1
type: analysis_mode
title: Competitive Dynamics Mode
created_at: 2026-08-08
updated_at: 2026-08-08
schema_version: 2
project_ids: []
status: proposed
review_status: pending
tags: []
name: 竞争格局分析
purpose: 评估竞争格局：竞争者、替代品、进入壁垒、生态、分发、数据、权限、标准、供应依赖与商业模式冲突。
applicable_scopes: [company, sector, event, thesis]
required_input_types: [event]
optional_input_types: [source, impact_assertion]
required_questions:
  - 主要竞争者与替代品？
  - 进入壁垒与生态位？
  - 分发、数据、权限与标准控制力？
  - 供应依赖与商业模式冲突？
required_output_sections: [Competitors and substitutes, Barriers and ecosystem, "Distribution, data and standards", Supply dependence and conflicts]
assumption_policy: 显式说明竞争格局判断的时点与口径。
evidence_policy: 只引用冻结输入；护城河判断须有证据，不得仅依据产品功能列表。
counterevidence_policy: 对护城河/竞争地位判断列出反向证据，或说明为何缺失。
time_horizons: [quarter, year]
prohibited_conclusions:
  - 不得仅依据产品功能列表判定护城河。
  - 不得输出投资建议或买卖指令。
output_schema_path: 00_System/Analysis_Modes/output_contract_schema.json
evaluator_version: ""
---

# Competitive Dynamics Mode

## Purpose

评估竞争格局：竞争者、替代品、进入壁垒、生态、分发、数据、权限、标准、供应依赖与商业模式冲突（Phase 4 §4.5）。

## Scope

- 适用范围：company / sector / event / thesis
- 必填输入：event；可选输入：source / impact_assertion

## Questions

- 主要竞争者与替代品？
- 进入壁垒与生态位？
- 分发、数据、权限与标准控制力？
- 供应依赖与商业模式冲突？

## Output requirements

必须输出竞争者与替代品、壁垒与生态、分发/数据/标准、供应依赖与冲突。

## Prohibitions

- 不得仅依据产品功能列表判定护城河。
- 不得输出投资建议或买卖指令。

## Review

Drafted as proposed；pending human review（RCP-v03-007 point 6）before activation。
