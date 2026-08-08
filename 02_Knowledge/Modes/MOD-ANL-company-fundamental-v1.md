---
id: MOD-ANL-company-fundamental-v1
type: analysis_mode
title: Company Fundamental Mode
created_at: 2026-08-08
updated_at: '2026-08-08'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
valid_from: 2026-08-08
tags: []
name: 公司基本面分析
purpose: 评估公司基本面：收入来源、客户、商业模式、成本、毛利、资本开支、现金流、竞争优势与风险。
applicable_scopes: [company, event, thesis]
required_input_types: [event]
optional_input_types: [source, thesis]
required_questions:
- 收入来源与客户结构如何？
- 商业模式、成本结构与毛利？
- 资本开支与现金流？
- 竞争优势与风险？
required_output_sections: [Revenue sources and customers, Business model and margins, Capital expenditure and cash flow, Competitive advantages and risks]
assumption_policy: 显式列出经营与估值假设。
evidence_policy: 只引用冻结输入事件；AI-specific 指标须与公司整体指标分开。
counterevidence_policy: 对优势/风险判断列出反向证据，或说明为何缺失。
time_horizons: [quarter, year, multi_year]
prohibited_conclusions:
- 不得混淆 AI-specific 指标与公司整体指标。
- 不得输出投资建议或买卖指令。
output_schema_path: 00_System/Analysis_Modes/output_contract_schema.json
evaluator_version: ""
---

# Company Fundamental Mode

## Purpose

评估公司基本面：收入来源、客户、商业模式、成本、毛利、资本开支、现金流、竞争优势与风险（Phase 4 §4.4）。

## Scope

- 适用范围：company / event / thesis
- 必填输入：event；可选输入：source / thesis

## Questions

- 收入来源与客户结构如何？
- 商业模式、成本结构与毛利？
- 资本开支与现金流？
- 竞争优势与风险？

## Output requirements

必须输出收入来源与客户、商业模式与毛利、资本开支与现金流、竞争优势与风险。

## Prohibitions

- 不得混淆 AI-specific 指标与公司整体指标。
- 不得输出投资建议或买卖指令。

## Review

Activated 2026-08-08 by max review（REV-20260808-007）。
