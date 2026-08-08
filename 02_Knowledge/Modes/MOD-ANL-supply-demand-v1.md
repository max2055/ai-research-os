---
id: MOD-ANL-supply-demand-v1
type: analysis_mode
title: Supply-Demand Mode
created_at: 2026-08-08
updated_at: '2026-08-08'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
valid_from: 2026-08-08
tags: []
name: 供需分析
purpose: 评估供需平衡：产能、供给弹性、库存、需求、利用率、价格与扩产周期。
applicable_scopes: [sector, company, technology, event]
required_input_types: [event]
optional_input_types: [source]
required_questions:
- 产能与供给弹性如何变化？
- 库存与需求匹配吗？
- 利用率与价格走向如何？
- 扩产周期多长？
required_output_sections: [Supply-demand balance, Capacity and elasticity, Inventory, Utilization and price, Expansion cycle]
assumption_policy: 显式说明周期、地区、产品代际与口径。
evidence_policy: 只引用冻结输入事件；公司披露订单不得直接外推为行业需求。
counterevidence_policy: 对供需方向判断列出反向信号，或说明为何缺失。
time_horizons: [quarter, year]
prohibited_conclusions:
- 禁止把公司订单直接外推为行业需求；须说明周期、地区、产品代际与口径。
- 不得输出投资建议或买卖指令。
output_schema_path: 00_System/Analysis_Modes/output_contract_schema.json
evaluator_version: ""
---

# Supply-Demand Mode

## Purpose

评估供需平衡：产能、供给弹性、库存、需求、利用率、价格与扩产周期（Phase 4 §4.2）。

## Scope

- 适用范围：sector / company / technology / event
- 必填输入：event；可选输入：source

## Questions

- 产能与供给弹性如何变化？
- 库存与需求匹配吗？
- 利用率与价格走向如何？
- 扩产周期多长？

## Output requirements

必须输出供需平衡、产能与弹性、库存、利用率与价格、扩产周期。

## Prohibitions

- 禁止把公司订单直接外推为行业需求；须说明周期、地区、产品代际与口径。
- 不得输出投资建议或买卖指令。

## Review

Activated 2026-08-08 by max review（REV-20260808-005）。
