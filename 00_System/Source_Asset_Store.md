# Source Asset Store

版本：v1.0  
生效日期：2026-07-29  
批准：`RCP-20260729-004`

## 1. 事实源与边界

- Source Markdown 是 provenance、审核状态和研究摘要的事实源。
- `01_Inbox/_assets/<SOURCE_ID>/` 保存可复核原始 bytes 与提取物。
- 原始资产永不静默覆盖；每次内容变化创建新版本。
- 提取文本和 extraction metadata 是可重建派生物。
- assets 默认不提交 Git，必须单独加密备份。

## 2. 目录与命名

```text
01_Inbox/_assets/SRC-YYYYMMDD-NNN/
├── YYYYMMDDhhmmss-<sha12>.html|pdf|txt|bin
├── YYYYMMDDhhmmss-<sha12>.metadata.json
├── YYYYMMDDhhmmss-<sha12>.<ext>.extracted.txt
└── YYYYMMDDhhmmss-<sha12>.<ext>.extraction.json
```

文件名中的时间来自 `captured_at`，`sha12` 是完整 SHA-256 的前 12 位。
完整 hash 保存在 Source 和 manifest 中。

## 3. Capture manifest

每个原始版本的 metadata 至少包含：

- Source ID
- captured time
- original/final locator
- media type
- byte count
- content SHA-256
- raw asset path
- HTTP metadata 或本地文件 metadata
- published date proposal

## 4. 去重

- URL 在比较前移除 fragment、默认端口和常见 tracking parameters。
- canonical URL 相同会提示重复。
- 已归档内容 SHA-256 相同会提示重复。
- 默认拒绝创建重复 Source；显式 override 时记录
  `upstream_source_ids`，不会合并或覆盖对象。
- 跨 Project 复用通过给同一 Source 增加 `project_ids` 完成。

## 5. 版本

- 首次 `source add` 原子创建 Source、raw asset 和 manifest。
- `source fetch` 仅在内容 hash 变化时创建新版本。
- Source `content_sha256` 指向最新原始版本；`asset_paths` 保留全部历史。
- 失败、重复或 preflight 冲突不得留下半写入 Source 或 asset。

## 6. 提取与日期

- HTML 使用标准库可见文本提取，跳过 script/style/noscript/svg。
- PDF 使用 pypdf；扫描 PDF 无文本时明确要求 OCR，不伪造结果。
- 提取记录 raw hash、method、text hash 和 warning。
- HTML metadata/JSON-LD 日期只形成 `published_date_proposal`。
- `source confirm-date --apply` 是唯一确认日期的产品命令；proposal 与确认值
  不同需要显式 override。
- 成功处理清空 `processing_error`；解析或完整性失败时 Source 进入 `failed`
  并记录可操作错误。相同版本成功重跑为幂等 no-op。

## 7. 操作与恢复

```bash
research-os source verify-assets
```

结果：

- `REGISTERED`：尚未归档，不视为 hash 错误。
- `OK`：路径存在且最新原始内容 hash 与 Source 一致。
- `MISSING`：本地资产缺失，需要从加密备份恢复。
- `HASH_MISMATCH`：禁止继续处理，先调查损坏或未授权改写。

恢复不得用提取文本反向覆盖原始 bytes。

## 8. 受限发现 Adapter

发现与采集是两个独立步骤。`source discover` 只返回候选 JSON，不创建 Source、
不下载候选正文，也不改变任何研究状态：

```bash
research-os source discover rss \
  --feed-url <URL> --allow-hosts <host,...> --publisher <name> --limit 20
research-os source discover github --repository <owner/repo> --limit 20
research-os source discover arxiv --query <explicit-query> --limit 20
research-os source discover sec \
  --cik <CIK> --forms <10-K,10-Q> --user-agent "<name contact>" --limit 20
```

共同约束：

- 每次只接受明确 feed、repository、query 或 CIK/form allowlist。
- 返回数量为 1～100，默认 20；不分页遍历和不递归跟踪链接。
- RSS feed 自身及候选链接必须匹配显式 host allowlist。
- GitHub 只读取一个 repository 的 release endpoint。
- arXiv 只运行一个明确 query；SEC 只保留明确 form allowlist。
- 候选必须由研究者选择后，再通过 `source add` 归档。
- 调用者负责确认 robots、许可、访问频率和 API 使用条款；Adapter 不能绕过访问控制。
