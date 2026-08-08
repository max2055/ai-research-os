---
id: MOD-ANL-expectations-valuation-v1
type: analysis_mode
title: Expectations & Valuation Mode
created_at: 2026-08-08
updated_at: 2026-08-08
schema_version: 2
project_ids: []
status: proposed
review_status: pending
tags: []
name: 预期与估值分析
purpose: 评估当前价格与市场预期隐含的经营结果：dated price、shares、资本结构、预期来源、匹配分母与时效。
applicable_scopes: [company, event, thesis]
required_input_types: [event]
optional_input_types: [thesis]
required_questions:
  - 当前价格隐含什么经营结果？
  - 市场预期来源与时效？
  - 估值分母是否匹配（price / shares / 资本结构）？
required_output_sections: [Current price implication, Expectation source, Valuation denominators, Freshness]
assumption_policy: 显式列出价格、股数、资本结构与预期来源；注明数据时效。
evidence_policy: 只引用冻结输入；价格与预期须有来源。
counterevidence_policy: 对隐含预期判断列出反向解读，或说明为何缺失。
time_horizons: [quarter, year]
prohibited_conclusions:
  - 不把模型 confidence 当作客观概率。
  - 不得输出投资建议或买卖指令。
output_schema_path: 00_System/Analysis_Modes/output_contract_schema.json
evaluator_version: ""
---

# Expectations & Valuation Mode

## Purpose

评估当前价格与市场预期隐含的经营结果：dated price、shares、资本结构、预期来源、匹配分母与时效（Phase 4 §4.6，复用 v0.2 估值合同）。

## Scope

- 适用范围：company / event / thesis
- 必填输入：event；可选输入：thesis

## Questions

- 当前价格隐含什么经营结果？
- 市场预期来源与时效？
- 估值分母是否匹配（price / shares / 资本结构）？

## Output requirements

必须输出当前价格隐含结果、预期来源、估值分母、时效。

## Prohibitions

- 不把模型 confidence 当作客观概率。
- 不得输出投资建议或买卖指令。

## Review

Drafted as proposed；pending human review（RCP-v03-007 point 6）before activation。
