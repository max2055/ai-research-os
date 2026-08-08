---
id: MOD-ANL-red-team-v1
type: analysis_mode
title: Red Team Mode
created_at: 2026-08-08
updated_at: 2026-08-08
schema_version: 2
project_ids: []
status: proposed
review_status: pending
tags: []
name: 红队检验
purpose: 对现有判断或叙事作对抗式检验：寻找反面证据、共同上游、替代机制、时间错配、价值捕获、估值已反映、监管/执行风险与不可观察变量。
applicable_scopes: [sector, company, technology, event, thesis]
required_input_types: [event]
optional_input_types: [thesis, impact_assertion]
required_questions:
  - 存在哪些反面证据？
  - 共同上游与替代机制？
  - 时间错配或价值无法被公司捕获？
  - 估值是否已反映该预期？
  - 监管/执行风险与不可观察变量？
required_output_sections: [Counter-evidence, Shared upstream and alternative mechanisms, Timing mismatch, Value capture risk, Valuation already priced in, Regulatory and execution risk, Unobservable variables]
assumption_policy: 显式列出被检验的假设。
evidence_policy: 只引用冻结输入；红队必须寻找反面证据，不得忽略支持证据。
counterevidence_policy: 本模式以寻找反证为首要任务。
time_horizons: [immediate, quarter, year]
prohibited_conclusions:
  - 不得为了反驳而忽略支持证据。
  - 不得输出投资建议或买卖指令。
output_schema_path: 00_System/Analysis_Modes/output_contract_schema.json
evaluator_version: ""
---

# Red Team Mode

## Purpose

对现有判断或叙事作对抗式检验：寻找反面证据、共同上游、替代机制、时间错配、价值捕获、估值已反映、监管/执行风险与不可观察变量（Phase 4 §4.8）。

## Scope

- 适用范围：sector / company / technology / event / thesis
- 必填输入：event；可选输入：thesis / impact_assertion

## Questions

- 存在哪些反面证据？
- 共同上游与替代机制？
- 时间错配或价值无法被公司捕获？
- 估值是否已反映该预期？
- 监管/执行风险与不可观察变量？

## Output requirements

必须输出反面证据、共同上游/替代机制、时间错配、价值捕获风险、估值已反映、监管/执行风险、不可观察变量。

## Prohibitions

- 不得为了反驳而忽略支持证据。
- 不得输出投资建议或买卖指令。

## Review

Drafted as proposed；pending human review（RCP-v03-007 point 6）before activation。
