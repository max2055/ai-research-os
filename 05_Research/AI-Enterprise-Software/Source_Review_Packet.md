# PRJ-001 Source-level Review Packet

状态：`passed`

建立日期：2026-07-30

目标：完成 `ACT-20260729-001` 要求的 18 个 Source-level Review Decision。Event
曾被批准不等于完整 Source 记录已经审核。

## Machine preparation

- 18 个目标 Source 中，15 个已取得 raw asset、capture metadata、extracted text、
  extraction metadata 和 SHA-256。
- 3 个仍为 `registered`；标准访问分别遇到 403 或超时。没有绕过访问
  控制，也没有写入伪资产。
- 机器准备只证明 provenance/processing 状态，不构成人工 `approve`。

## Review table

人工逐行检查 title、publisher、published/accessed date、URL、grade、summary、
reliability notes 和资产可访问性。Decision 填 `approve`、`edit: ...` 或
`reject: ...`。

| # | Source ID | Used by reviewed Event | Processing | Asset/hash | Human decision | Notes |
|---:|---|---|---|---|---|---|
| 1 | `SRC-20260219-019` | `EVT-20260219-001` | processed | verified | approve | Microsoft promotional slide deck; promotional attribution retained |
| 2 | `SRC-20260225-002` | `EVT-20260225-002` | processed | verified | approve | Salesforce FY26 Q4 results |
| 3 | `SRC-20260415-014` | `EVT-20260415-003` | processed | verified | approve | OpenAI Agents SDK |
| 4 | `SRC-20260429-001` | `EVT-20260429-004` | processed | verified | approve | Lower-case canonical path succeeded after one TLS failure |
| 5 | `SRC-20260514-016` | `EVT-20260514-005` | processed | verified | approve | Anthropic/PwC announcement; partner claims retained |
| 6 | `SRC-20260521-020` | `EVT-20260521-006` | processed | verified | approve | MCP release candidate |
| 7 | `SRC-20260610-017` | `EVT-20260610-007` | processed | verified | approve | Oracle FY26 Q4 results |
| 8 | `SRC-20260611-009` | `EVT-20260611-008` | processed | verified | approve | SAP Joule product announcement |
| 9 | `SRC-20260714-006` | `EVT-20260714-009` | processed | verified | approve | Oracle Fusion agentic builder |
| 10 | `SRC-20260729-007` | `EVT-20260714-009` | processed | verified | approve | Oracle Agent Studio documentation |
| 11 | `SRC-20260722-004` | `EVT-20260722-010` | processed | verified | approve | ServiceNow Q2 2026 results |
| 12 | `SRC-20260723-008` | `EVT-20260723-011` | registered | unavailable | approve | HTTP 403 and missing archive/hash explicitly accepted as governance debt |
| 13 | `SRC-20260729-003` | `EVT-20260729-012` | processed | verified | approve | Salesforce Agentforce pricing |
| 14 | `SRC-20260729-005` | `EVT-20260729-013` | registered | unavailable | approve | Timeout and missing archive/hash explicitly accepted as governance debt |
| 15 | `SRC-20260729-010` | `EVT-20260729-014` | processed | verified | approve | Palantir AIP documentation |
| 16 | `SRC-20260729-011` | `EVT-20260729-014` | processed | verified | approve | Palantir Ontology documentation |
| 17 | `SRC-20260729-012` | `EVT-20260729-014` | processed | verified | approve | Palantir Agents documentation |
| 18 | `SRC-20260729-013` | `EVT-20260729-015` | registered | unavailable | approve | HTTP 403 and missing archive/hash explicitly accepted as governance debt |

## Aggregate

- Human decisions: 18/18
- Processed and hash-verified: 15/18
- Registered with explicit capture exception: 3/18
- `REV003` warnings after decisions: 0
- Gate decision: approve

## Human review protocol

1. 对 processed Source 打开 Source Markdown 和最新 raw/extracted asset。
2. 对 registered Source 决定：接受可访问 URL 的治理缺口、要求替代归档，或 reject。
3. 使用 `research-os source review` 写入不可变 Review Decision；不得直接把
   front matter 改成 reviewed。
4. 运行 `research-os validate`，确认 `REV003` 只按明确批准结果下降。
5. 18/18 完成后再关闭 `ACT-20260729-001`。
