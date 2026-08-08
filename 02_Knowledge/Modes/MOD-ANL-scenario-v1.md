---
id: MOD-ANL-scenario-v1
type: analysis_mode
title: Scenario Mode
created_at: 2026-08-08
updated_at: 2026-08-08
schema_version: 2
project_ids: []
status: proposed
review_status: pending
tags: []
name: 情景分析
purpose: 构建 Downside/Base/Upside 情景：驱动变量、概率、时间、结果、敏感性、催化剂与证伪条件。
applicable_scopes: [sector, company, technology, event, thesis]
required_input_types: [event]
optional_input_types: [thesis, impact_assertion]
required_questions:
  - 关键驱动变量与情景概率？
  - Downside / Base / Upside 结果与时间？
  - 敏感性、催化剂与证伪条件？
required_output_sections: [Drivers and probabilities, Downside scenario, Base scenario, Upside scenario, Sensitivity and catalysts, Falsification conditions]
assumption_policy: 显式列出每情景假设与概率依据。
evidence_policy: 只引用冻结输入；情景是判断，须与事实分离。
counterevidence_policy: 对每情景列出反面因素，或说明为何缺失。
time_horizons: [quarter, year, multi_year]
prohibited_conclusions:
  - 情景概率是 Judgment，不得伪装为客观概率。
  - 不得输出投资建议或买卖指令。
output_schema_path: 00_System/Analysis_Modes/output_contract_schema.json
evaluator_version: ""
---

# Scenario Mode

## Purpose

构建 Downside/Base/Upside 情景：驱动变量、概率、时间、结果、敏感性、催化剂与证伪条件（Phase 4 §4.7）。

## Scope

- 适用范围：sector / company / technology / event / thesis
- 必填输入：event；可选输入：thesis / impact_assertion

## Questions

- 关键驱动变量与情景概率？
- Downside / Base / Upside 结果与时间？
- 敏感性、催化剂与证伪条件？

## Output requirements

必须输出驱动变量与概率、Downside/Base/Upside 三情景、敏感性/催化剂、证伪条件。

## Prohibitions

- 情景概率是 Judgment，不得伪装为客观概率。
- 不得输出投资建议或买卖指令。

## Review

Drafted as proposed；pending human review（RCP-v03-007 point 6）before activation。
