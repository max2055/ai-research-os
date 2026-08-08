---
id: MOD-ANL-open-discovery-v1
type: analysis_mode
title: Open Discovery Mode
created_at: 2026-08-08
updated_at: '2026-08-08'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
valid_from: 2026-08-08
tags: []
name: 开放发现
purpose: 在范围内寻找异常、弱信号、跨板块组合与未建模关系，只输出候选 Hypothesis，不直接权威化。
applicable_scopes: [sector, company, technology, event, thesis]
required_input_types: []
optional_input_types: [source, event, impact_assertion, thesis]
required_questions:
- 存在哪些异常或弱信号？
- 有哪些跨板块组合或未建模关系？
- 每个假设的最小所需证据是什么？
required_output_sections: [Hypothesis proposal, Why surprising, Minimum evidence needed, Disconfirming search plan, Related entities, Spurious-correlation risk]
assumption_policy: 显式说明每个假设的检验边界。
evidence_policy: 假设只基于冻结输入，不引入输入外事实。
counterevidence_policy: 每个假设须附伪相关风险与证伪搜索计划。
time_horizons: [quarter, year]
prohibited_conclusions:
- 不得直接产生 reviewed Thesis 或 Recommendation。
- 不得输出投资建议或买卖指令。
output_schema_path: 00_System/Analysis_Modes/output_contract_schema.json
evaluator_version: ""
---

# Open Discovery Mode

## Purpose

在范围内寻找异常、弱信号、跨板块组合与未建模关系，只输出候选 Hypothesis，不直接权威化（Phase 4 §4.9）。

## Scope

- 适用范围：sector / company / technology / event / thesis
- 必填输入：无；可选输入：source / event / impact_assertion / thesis

## Questions

- 存在哪些异常或弱信号？
- 有哪些跨板块组合或未建模关系？
- 每个假设的最小所需证据是什么？

## Output requirements

只能输出：hypothesis proposal、why surprising、minimum evidence needed、disconfirming search plan、related entities、spurious-correlation risk。

## Prohibitions

- 不得直接产生 reviewed Thesis 或 Recommendation。
- 不得输出投资建议或买卖指令。

## Review

Activated 2026-08-08 by max review（REV-20260808-007）。
