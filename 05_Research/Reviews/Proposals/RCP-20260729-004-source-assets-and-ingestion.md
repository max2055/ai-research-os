# Rule Change Proposal

Proposal ID：RCP-20260729-004

状态：approved

创建日期：2026-07-29

提议人：Codex

## Target

- Source provenance Schema
- `01_Inbox/_assets/<SOURCE_ID>/` 原文存储
- URL 与本地文件采集 Adapter
- RSS、GitHub Release、arXiv 与 SEC 受限发现 Adapter
- HTML/PDF 文本提取与发布日期提议
- Python PDF 解析依赖

## Observed problem

当前 Source 主要保留 URL 或本地路径，网页变化、链接失效和本地文件移动会削弱
长期复核能力；系统也无法用内容 hash 识别重复材料或记录上游版本。

## Evidence

- Roadmap: `00_System/Productization_Roadmap_v1.md` M3
- Source Policy: `00_System/Source_Policy.md`
- Recovery Runbook: Source assets 需要单独加密备份
- Current Source objects: 20
- Baseline: M2 56 tests、0 validation error、0 index drift

## Proposed change

Source 新增：

```yaml
canonical_url:
asset_paths: []
content_sha256:
fetched_at:
upstream_source_ids: []
processing_status: registered|captured|processed|failed
processing_error:
published_date_proposal:
```

采集约束：

- 只采集研究者显式指定的单个 URL 或本地文件，不进行无边界爬取。
- 原始 bytes 按 Source ID、版本时间和 hash 保存，永不静默覆盖。
- canonical URL 与 SHA-256 在创建前进行去重检查。
- 重抓内容变化时保留旧版本。
- HTML/PDF 提取物是派生文件，不能替代原始资产。
- Published date 只能生成 proposal，必须由人工确认后才写 `published_at`。
- `01_Inbox/_assets/` 保持 Git ignore，并由单独加密备份保护。
- RSS/GitHub/arXiv/SEC 只读发现使用明确 allowlist/query 与 100 条硬上限，
  不自动注册候选。
- 处理失败写 `processing_status: failed` 和 `processing_error`；成功重跑幂等。

新增 `pypdf` 作为 PDF 文本提取依赖；HTML 提取使用标准库。

## Alternatives considered

- 只依赖 URL：拒绝；无法保证长期复核。
- 把原始材料提交 Git：拒绝；许可、隐私和体积风险过高。
- 引入常驻抓取队列或爬虫：拒绝；超出 local-first 单用户产品边界。
- OCR 所有 PDF：延后；M3 先支持可提取文本 PDF，并显式报告扫描件。

## Risks

- 受许可保护内容被错误传播。
- 大文件耗尽本地空间。
- URL 重定向或动态网页产生不稳定内容。
- PDF/HTML 日期提取误判。

控制：

- assets 默认不进入 Git；显式记录访问时间、media type、最终 URL 和 hash。
- 设置单文件大小上限。
- date 只作为 proposal。
- 失败不修改 Source；写入使用同一事务。

## Migration

1. 对 20 个既有 Source 增加字段，`processing_status` 初始为 `registered`，
   `processing_error` 初始为空。
2. 不下载既有 URL，不伪造 asset/hash。
3. body hash 必须 20/20 不变。
4. 新采集从 CLI `source add/fetch/process` 进入。

## Acceptance tests

- URL 与本地文件均能保存原始 bytes、metadata 和 SHA-256。
- 同 canonical URL 或同内容能在创建前被识别。
- 内容变化产生新版本，旧版本保留。
- HTML/PDF 文本提取有 fixtures。
- published date proposal 不会自动改变 `published_at`。
- 失败或冲突不留下半写入 Source/asset。
- RSS/GitHub/arXiv/SEC discovery 在 fixtures 中验证 allowlist、query、form 和
  数量上限，不执行真实网络写入。

## Human decision

- Decision: approve
- Reviewer: max
- Date: 2026-07-29
- Reason: 用户已批准完整产品化路线与实施；本提案保持显式采集、Markdown 事实源和人工日期确认。

## Implementation record

- Changed files: Source Schema/template/policy、asset store、capture/discovery
  adapters、ingestion/extraction services、CLI、validation/index/metrics/doctor、tests
  与 20 个 Source front matter。
- Migration: MIG-20260729-003、003b、003c；20/20 Source body hash unchanged。
- Test result: 73/73；83% coverage；Ruff 与 mypy strict 通过。
- Validation result: 56/56 formal Schema；0 error；18 个既有 REV003 warning；
  global/PRJ-001 index drift 0；asset integrity failure 0。
- Effective date: 2026-07-29
