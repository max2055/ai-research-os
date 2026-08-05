---
id: SRC-20260730-033
type: source
title: "Agentic AI and Human-in-the-Loop Interventions: Field Experimental Evidence from Alibaba's Customer Service Operations"
created_at: 2026-07-30
updated_at: '2026-07-30'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
source_type: report
publisher: arXiv
authors: [Yiwei Wang, Chuan Zhu, Tianjun Feng, Lauren Xiaoyuan Lu, Bingxin Jia]
published_at: 2026-05-14
accessed_at: 2026-07-30
url: https://arxiv.org/pdf/2605.14830
local_path:
source_grade: A
companies: []
technologies: [DEV-AGENT-FRAMEWORK, DEV-EVALUATION, DEV-ORCHESTRATION]
products: []
canonical_url: https://arxiv.org/pdf/2605.14830
asset_paths:
- 01_Inbox/_assets/SRC-20260730-033/20260729232934-086bbf606f5f.pdf
- 01_Inbox/_assets/SRC-20260730-033/20260729232934-086bbf606f5f.metadata.json
- 01_Inbox/_assets/SRC-20260730-033/20260729232934-086bbf606f5f.pdf.extracted.txt
- 01_Inbox/_assets/SRC-20260730-033/20260729232934-086bbf606f5f.pdf.extraction.json
content_sha256: 086bbf606f5fe5b05c53f103666ee97b82f8c664bd4c88af3a42dab0a8d6788e
fetched_at: 2026-07-29T23:29:34.341341+00:00
upstream_source_ids: []
processing_status: processed
processing_error:
published_date_proposal:
tags: [APP-CRM, MAT-PRODUCTION, EV-CUSTOMER, EV-TECHNOLOGY]
---

# Source

## Source summary

基于阿里巴巴淘宝售后客服的随机现场实验，比较由人工处理全部对话与人工监督 Agentic
AI 的处理模式。论文报告了速度、重试率、客户评分以及不同升级类型下人工介入效果。

## Why it matters

它提供了生产环境中的直接反面证据：Agentic AI 可以缩短对话时间，但在适用对话中未必
改善客户体验；人工介入的时机和故障类型会显著影响结果。

## Relevant sections

- 实验范围与人机协作流程：extracted lines 225–240。
- 总体及分组速度、重试率与客户评分：extracted lines 390–430。
- 技术、情绪及人工主动升级的结果：extracted lines 475–512。
- 人工介入努力和时机机制：extracted lines 529–584。

## Reliability notes

A 级作者技术报告、随机现场实验，但目前为 arXiv 预印本。实验限于淘宝售后客服，且
AI-eligible 对话不足总量 10%；不能直接外推到其他行业或全部客服任务。主观评分下降、
重试率和速度是不同结果变量，不应合并解释成单一“成功/失败”结论。

## Processing status

- [x] Event extraction completed
- [ ] Entity links reviewed
- [ ] Thesis links reviewed
