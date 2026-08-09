---
id: MOD-ANL-scenario-v2
type: analysis_mode
title: Scenario Mode
created_at: 2026-08-09
updated_at: '2026-08-09'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
valid_from: 2026-08-09
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
prompt_template_path: 00_System/Analysis_Modes/templates/scenario.md
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

v2 使用场景专用 prompt 模板（`00_System/Analysis_Modes/templates/scenario.md`），显式枚举全部 15 个
## 分区并声明机器校验（缺任一标题即失败），针对 D-019 暴露的「模型跳过 scenario 专属 6 分区」
问题（v1 在 10 case 中 6 个顽固失败）。PoC 验证：同一组合（EVT-20260520-038 scenario）v1
默认模板失败 4+ 次，v2 模板首次即产出全部 15 分区。

## Prohibitions

- 情景概率是 Judgment，不得伪装为客观概率。
- 不得输出投资建议或买卖指令。

## Review

Activated 2026-08-09 by max review（REV-20260809-001）。scenario v2 硬化：专用 prompt 模板
显式枚举全部 15 个 ## 分区并声明机器校验；针对 D-019 暴露的「v1 模型跳过 scenario 专属 6 分区」
问题（v1 在 10 case 中 6 个顽固失败）。PoC 验证：EVT-20260520-038 scenario 组合 v1 默认模板
失败 4+ 次，v2 模板首次即产出全部 15 分区。
