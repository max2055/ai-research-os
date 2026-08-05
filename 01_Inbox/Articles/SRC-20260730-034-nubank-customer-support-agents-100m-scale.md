---
id: SRC-20260730-034
type: source
title: "Building Customer Support AI Agents at 100M-User Scale: An Evaluation-Driven Framework"
created_at: 2026-07-30
updated_at: '2026-07-30'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
source_type: report
publisher: arXiv
authors: [Aman Gupta, Kevin Rossell, Edesio Alcobaça, Jose Chrystian Lima Pacheco, Carolina Baptista de Lima, Shao Tang, Luiz Paulo Rabachini, Luis Moneda, Herbert Fei, Daniel Silva, Rohan Ramanath]
published_at: 2026-06-07
accessed_at: 2026-07-30
url: https://arxiv.org/pdf/2606.08867
local_path:
source_grade: A
companies: []
technologies: [DEV-AGENT-FRAMEWORK, DEV-EVALUATION, DEV-ORCHESTRATION]
products: []
canonical_url: https://arxiv.org/pdf/2606.08867
asset_paths:
- 01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.pdf
- 01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.metadata.json
- 01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.pdf.extracted.txt
- 01_Inbox/_assets/SRC-20260730-034/20260729233414-af0c2c13515a.pdf.extraction.json
content_sha256: af0c2c13515ad001dc2ff17a7824131407f221400aebaf36d75afd0e5ee84995
fetched_at: 2026-07-29T23:34:14.451012+00:00
upstream_source_ids: []
processing_status: processed
processing_error:
published_date_proposal:
tags: [APP-CRM, MAT-SCALE, EV-CUSTOMER, EV-TECHNOLOGY]
---

# Source

## Source summary

Nubank 团队报告了服务于 1 亿以上用户环境的客服 Agent 开发框架，以及卡片配送、债务
管理、额度支持、卡片管理和产品解释五个生产部署的在线 A/B 测试结果。

## Why it matters

它为“评测、上下文工程、工具和在线测量共同构成生产能力”提供直接案例，并给出相对
前代 Agent 和专家人工客服的结果差距，而不是只报告发布数量。

## Relevant sections

- 框架、五个生产部署与主要结果：extracted lines 140–179。
- 五个用例的在线增量图：extracted lines 240–261。
- 分用例 tNPS、自助率及相对人工差距：extracted lines 895–925。
- 隐私与合规范围：extracted lines 926–930 及后续章节。

## Reliability notes

A 级作者技术报告，论文已说明获 KDD 2026 接收，但作者来自部署团队，结果仍是单一公司
自报。多数比较对象是前代 Agent 版本而非纯人工控制组；tNPS 和自助率不能等同于收入、
成本节省或长期留存。五个部署属于同一公司和同一框架，只算一个独立组织案例。

## Processing status

- [x] Event extraction completed
- [ ] Entity links reviewed
- [ ] Thesis links reviewed
