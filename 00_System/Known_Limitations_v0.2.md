# AI Research OS v0.2 Known Limitations

Status: reviewed for release candidate  
Updated: 2026-08-06

## Product boundary

- The product is local-first and single-user. The Dashboard is read-only and only
  binds to loopback; there is no multi-user server, account or permission model.
- Review, editing and final publication use Markdown and CLI workflows rather than
  Web mutation endpoints.
- Markdown scanning is the default query layer. SQLite and JSONL are disposable
  exports, and there is no always-on database or vector store.
- Scheduler commands are entry points for an OS scheduler; the package does not run
  a resident scheduling daemon.
- The tested migration engine is available to release engineering, but v0.2 does not
  expose a generic end-user migration CLI. Each future schema migration must ship as
  a reviewed, version-specific operation with its own plan and rollback record.

## Source capture

- URL capture is bounded single-resource retrieval, not a browser crawler. Pages
  requiring interactive login, client-side rendering, anti-bot bypass or prohibited
  access are not automatically archived.
- Scanned PDFs require an external OCR step. Extraction failure stays visible as
  `failed`; the system does not invent text.
- Source assets are excluded from Git by default for copyright, privacy and size
  reasons. Recovery from an encrypted archive has been tested, but a durable
  off-device destination and key-recovery policy still require owner configuration.
- Three pre-M3 Sources remain registered because standard capture returned HTTP 403
  or timed out. Their Source records were human-approved with the missing-archive
  limitation explicit; no asset was fabricated.
  The other 17 pre-M3 Sources have since been archived and processed.

## Research quality

- AI draft quality is bounded by the captured Source. Exact anchors improve
  traceability but do not replace human interpretation or attribution review.
- Source independence is researcher-specified; common upstream material may still
  be missed.
- Automated investment valuation, portfolio execution and security recommendations
  are outside v0.2. RQ-08 includes one source-governed Microsoft worksheet, but it is
  a reproducible expectations baseline rather than a DCF, target price or advice.
- All current Source and Event records have human decisions; repository validation
  has zero `REV003` warnings. The three capture exceptions remain visible.
- Six new PRJ-001 Events add independent production cases, direct counterevidence and
  commercial-metric separation with individual human Review Decisions.

## Release-candidate gaps

- M4 accuracy, Source/Event review, Company review, research-quality Actions and the
  first PRJ-002 Report are complete.
- PRJ-002 has 12 reviewed Sources, 9 reviewed Events and one reviewed final Report.
  Its three Thesis hypotheses remain pending and retain their initial confidence.
- Two real Weekly reviews, one real Monthly review and the post-cycle release decision
  remain pending; cadence records cannot be backfilled before their dates.
- A private remote and remote CI are not configured in the current local repository.
  Clean-clone testing is used locally, but off-device Git backup must be configured
  by the owner.

## Deferred scale choices

The M6 synthetic baseline passes at 1,000 Sources and 500 Events. A permanent
database, graph store or vector index should only be reconsidered after a measured
query bottleneck or a stable high-frequency relationship-query requirement.

## v0.3 schema registration status

- The five v0.3 entity schemas (Sector/Security/Product/Technology/Metric) are
  registered (WP-102, RCP-v03-003 approved). **WP-120 has created 9 Sector
  entities and 51 Pilot Core Company entities** (Compute Chain), plus v0.3
  extension fields on the 8 v0.2 Companies. The repository now holds 225
  formal objects across 10 types.
- v0.2 Company objects remain at schema_version=1; v0.3 extension fields
  (region_primary, sector_ids, coverage_tier) were added as new fields only —
  historical tags were not rewritten (R1).
- All new entities start `review_status: pending`; human review (via `review
  apply`) is required before any entity becomes `reviewed`. None are approved
  yet.
- Security/Product/Technology/Metric entities do not exist yet; their indexes
  and CLI commands (`research-os universe ...`) arrive in later WPs.
- Sector IDs and Company IDs in `core_company_ids` / `sector_ids` are format-
  validated but cross-object reference integrity is enforced in WP-103.
- Ontology Assertion (REL-*) schema, predicates and reference checks are
  implemented (WP-103) but **no assertions exist yet** — relation data is
  deferred to a follow-up WP (Phase 0-1 Gate requires 100+ exported + 30
  human-reviewed). Reviewed assertions will require >=1 reviewed Evidence.
- **253 Ontology Assertions created (2026-08-05, relation WP)**: Compute
  Chain value-chain relations (SUPPLIES 184, COMPETES_WITH 32 + symmetric
  reverse, DEPENDS_ON 8, ENABLES 18, PARTNERS_WITH 3). 5 problem relations
  removed in max's spot-check (2 dups, 2 self-refs, 1 wrong semantics).
- **Evidence WP (2026-08-05)**: 10 real public Sources captured + reviewed
  (SEC 10-Q/20-F + exhibits, SK hynix/TSMC/Amazon IR) → 10 Events with
  citation anchors → **22 relations approved** (Gate 30: 22/30). Evidence
  quality calibrated: AWS-OpenAI $100B contract (direct, conf 0.8),
  SK hynix-NVIDIA HBM partnership (direct, conf 0.7), SEC-filing indirect
  (conf 0.3-0.5), weak-inference held pending. **9 relations held
  evidence-insufficient** (sources do not name counterparty). Remaining 8
  for Gate 30 need new named-party capture (Samsung/Micron/Alibaba).
- **Gate 30 sprint (2026-08-06)**: 6 new Sources (CoreWeave 10-K SEC A级,
  Samsung GTC 2026, Micron HBM3E, TrendForce 1Q26 DRAM, 阿里云百炼, 百度千帆)
  + 6 Events with citation anchors → **9 relations approved** (31 total:
  SUPPLIES 20, COMPETES_WITH 3, DEPENDS_ON 4, ENABLES 3, PARTNERS_WITH 1).
  **Gate 30 achieved (30/30 + 1 buffer)**. Quality: CoreWeave 10-K direct
  (conf 0.8/0.7), Samsung/Micron HBM named-supply (conf 0.5/0.6), TrendForce
  competitive share (conf 0.6), Aliyun/Baidu model-hosting (conf 0.5).
  7 previously-held relations remain evidence-insufficient (Microsoft/AWS
  ENABLES Anthropic/Meta/xAI, Supermicro COMPETES Dell). Field Gate
  distribution still short: COMPETES_WITH 3/5, DEPENDS_ON 4/5,
  PARTNERS_WITH 1/5.
- **Field Gate distribution fill (2026-08-06)**: zero new capture — reused
  reviewed CoreWeave 10-K (SRC-051) + AWS/Microsoft contract Events. 2 new
  Events (cloud competitors EVT-047, NVIDIA dependency EVT-048) + 9 new
  relations → **39 relations approved**. Distribution now meets §9.3:
  SUPPLIES 20/10, COMPETES_WITH 6/5, DEPENDS_ON 5/5, CUSTOMER_OF 4 +
  PARTNERS_WITH 1 = 5/5 (客户/伙伴). Agent audit caught 2 broken evidence
  chains (Anthropic/Meta CUSTOMER_OF Microsoft reused EVT-039 which does
  not name either) — reverted to pending, replaced with OpenAI/Meta
  CUSTOMER_OF CoreWeave (EVT-041 named contracts). **Remaining Field Gate
  gap: PRODUCES 产品归属 0/5 (needs Product entities, deferred to WP-120)**.
  10 Company human-verification sub-item also still open.
- **Product ownership WP (2026-08-06, WP-120 收尾)**: fixed WP-120 遗漏 —
  OBJECT_PATTERNS 缺 `02_Knowledge/Products/PRD-*.md`（ID_PATTERNS 早已注册
  product），REVIEWABLE_TYPES 缺 product（Sector 先例），两者均已补齐。
  5 Product entities created + reviewed (PRD-hbm4/hbm3e/azure-ai-infra/
  aws-ai-infra/coreweave-cloud) + 5 PRODUCES relations approved
  (REL-261..265). **Field Gate §9.3 分布全部达成**: SUPPLIES 20, COMPETES_WITH
  6, DEPENDS_ON 5, PRODUCES 5, 客户/伙伴 5. **44 relations approved total.**
  Agent audit: 2 fixes (CoreWeave PRD/REL 补 EVT-048 证据覆盖; conf 0.7→0.6
  对齐同类云产品)。**Remaining Field Gate: 10 Company human-verification 子项**.
- **10 Company human-verification (2026-08-06, Field Gate §9.3 完成)**: 补了
  WP-120 遗漏 3 —— OBJECT_PATTERNS 缺 Securities 目录（ID_PATTERNS 早已注册
  security），REVIEWABLE_TYPES 缺 security（同 product/sector 先例）。新建 10
  个 INS-* 证券实体并 reviewed（NVDA/TWSE-2330/NYSE-TSM ADR/KRX-000660/KRX-
  005930/MU/MSFT/CRWV/META/AMZN-parent），挂接 9 家 Company security_ids。
  补 v0.2 老 8 家身份字段（legal_name/HQ/stage）。Review packet passed
  （REV-054..063，max 全 approve）。**Field Gate §9.3 全部完成**（10 Company +
  30 relation 四要素核验）。**Known limitation: source_channel 类型未实现**
  （RCP-v03-003 仅 ID 占位，字段留后续 RCP）——Company source_channel_ids
  无法引用，来源核验改用 evidence_ids/reviewed Events 支撑；59/59 Company
  source_channel_ids 留空，待实现后补登记。**下一个候选: A-020 阶段验收
  （clean-clone + migration rollback）或 v0.3 阶段 1 收口。**
- **A-020 阶段验收通过 (2026-08-06)**: migration rollback 演练（10 Security
  实体 apply→rollback 字节级恢复，0 error）+ clean-clone recovery 重跑
  （633 对象 / 55 Source / 208 资产 / 52 dirs，独立 clone + 新 venv + 加密
  恢复，doctor/validate/index/tests/ruff/mypy 全 PASS）。验收文档
  `00_System/A020_Phase_Acceptance.md`。**Phase 0-1 Gate 清单全部达成**：D4 复核
  （2026-08-06）确认 54 家 Core 全为 AI Compute Chain 关键节点，批准扩容至 54
  （51 v0.3 + 3 v0.2 anthropic/microsoft/openai；5 家 v0.2 老公司为 tracked，
  0 discovery），详见 WP-011 D4 更新。**下一个: v0.3 阶段 1 收口，或 Phase 2
  Candidate Pipeline（需 RCP-v03-004）。**
