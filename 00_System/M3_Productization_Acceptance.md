# M3 Source 采集、原文归档与溯源验收

验收日期：2026-07-29  
结论：`accepted`

## 1. 验收范围

覆盖 `Productization_Roadmap_v1.md` 的 M3-01 至 M3-10。Schema、Source Policy
与采集边界由 `RCP-20260729-004` 批准。

## 2. 交付确认

| ID | 结果 | 交付 |
|---|---|---|
| M3-01 | PASS | ignored `01_Inbox/_assets/<SRC-ID>` immutable asset store、raw/manifest/extraction 命名与备份边界 |
| M3-02 | PASS | 单 URL capture，保存 canonical/final URL、HTTP metadata、时间、media type、bytes 与 SHA-256 |
| M3-03 | PASS | 显式本地文件 copy capture，50 MB 上限和来源文件 metadata |
| M3-04 | PASS | 时间+hash 版本名；内容变化追加版本，旧 bytes 不覆盖；相同成功处理幂等 |
| M3-05 | PASS | canonical URL 与完整内容 hash 双重预写入去重，跨 Project 复用永久 ID |
| M3-06 | PASS | HTML meta/JSON-LD 只生成 date proposal；确认与 override 必须人工显式执行 |
| M3-07 | PASS | registered/captured/processed/failed 状态；失败原因、索引、metrics、doctor 与资产验证 |
| M3-08 | PASS | RSS/Atom Adapter 要求 feed/candidate host allowlist，1～100 条硬上限 |
| M3-09 | PASS | 单 GitHub repository Release Adapter，记录 repo、tag、发布时间和 release URL |
| M3-10 | PASS | arXiv explicit query 与 SEC explicit CIK/form Adapter；只读发现、按项目选择后再采集 |

## 3. Source Gate

隔离仓库 fixtures 验证：

- 新建成功 Source 100% 保存 local path 或 canonical URL、raw bytes、manifest、
  fetched time 和内容 SHA-256。
- canonical URL 重复和相同 bytes 重复均在任何写入前拒绝。
- 内容变化创建新版本并保留旧 raw、manifest 与 extraction。
- HTML 与含文字 PDF 可提取；扫描 PDF 明确进入 `failed` 并记录 OCR 错误。
- 已成功处理的同版本重复运行为 no-op，不重复创建提取物。
- 冲突、超大响应和解析失败不留下半写入资产。
- 发现 Adapter 全部使用本地/mock fixtures；验收未执行无批准的真实网络采集。

现有 20 个真实 Source 是 M3 之前注册的资料，因此按迁移政策保留
`registered`，不通过批量联网回填伪造 Gate。新采集流程的验收样本满足 100%，高于
95% 目标；真实使用中的滚动比率由 M3 metrics 持续观测。

## 4. 数据迁移

- 三个 migration 均记录于 `00_System/M3_Migration_Record.md`。
- 20/20 既有 Source 人工正文 hash 相对 M2 baseline 不变。
- 没有改变 Source/Event/Thesis/Report 审核状态或 Thesis confidence。
- assets 继续由 `.gitignore` 排除，并要求单独加密备份。

## 5. 安全与访问边界

- URL capture 仅处理研究者明确给出的单个 URL，不 crawl。
- RSS、GitHub、arXiv、SEC discovery 不写仓库，不自动采集候选，不遍历分页。
- RSS host、SEC forms、arXiv query、GitHub repository 都必须明确指定。
- 每个 discovery 最多 100 条；URL/PDF/local file 有 byte limit。
- 调用者必须遵守 robots、许可、频率和服务条款；工具不绕过访问控制。
- 日期提取与 Source Review 均保留人工 gate。

## 6. 质量结果

- tests：73/73。
- coverage：83%，高于 80% Gate。
- Ruff：通过。
- mypy strict：45 个 source files 通过。
- formal Schema：56/56。
- validation：0 error、18 个既有且已解释的 `REV003` warning。
- global 与 PRJ-001 index drift：0。
- asset verification：20 registered、0 integrity failure。
- `research-os doctor`：全部检查通过。
- M3 commit 的独立 clean clone 可重新安装依赖、运行 73 tests 并通过 doctor。

## 7. Gate 决策

M3 Gate 通过。后续开发进入 M4 研究工作流与智能生成。
