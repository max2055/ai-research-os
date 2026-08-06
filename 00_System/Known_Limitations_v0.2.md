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
- **阶段 1 收口完成 (2026-08-06)**: 新增 `research-os universe coverage` 命令
  （A-014/A-018 identity/source/relationship completeness）。补全 57 家
  legal_name（Agent 核验）+ 5 家 v0.2 tracked 公司身份字段 → identity
  completeness 3.4% → **100%**。Master Backlog Wave 0/1 全 completed，
  Master Roadmap 阶段 0/1 标记完成。收口文档
  `00_System/v0.3_AI_Industry_Intelligence_OS/Phase_1_Closeout.md`。
  **Remaining coverage: source 39%（23/59，预期随阶段 2 证据累积）**。
  **下一个: Phase 2 Candidate Pipeline（需 RCP-v03-004 SQLite +
  RCP-v03-005 Source Channel/scheduler/许可）。**
- **WP-200/201 完成 (2026-08-06)**: RCP-v03-004/005 已批准。WP-200:
  `ADR_Candidate_Operational_Store.md`（4 表 SQLite operational store）+ 
  `src/research_os/services/candidate_db.py`（B-004 migration engine，
  PRAGMA user_version 版本化 + apply/rollback + 6 测试）。WP-201:
  `source_channel` schema（CHN-*，接入 registry/ID_PATTERNS/OBJECT_PATTERNS/
  REVIEWABLE_TYPES/validation）+ `channels` CLI（list/check/enable/disable，
  enable 守卫生效：未 reviewed 拒绝 + restricted license 拒绝）+ 首批 6
  Channel reviewed（REV-064..069，SEC/SK hynix IR/TrendForce news-only/arXiv/
  GitHub/company IR）。**132 tests**。**下一个: WP-210（P0 adapters:
  SEC/RSS/arXiv/GitHub/IR）或 WP-220（dedup/entity/scoring）。**
- **Channel 试跑 (2026-08-06)**: 启用 4 个 license=reviewed Channel（SEC/arXiv/
  GitHub/SK hynix），4 类 adapter 全部真实 discover 成功。试跑暴露 2 问题：
  (1) SK hynix Channel locator 配置 bug（`/en/` 网页 vs `/en/feed/` RSS，已修）；
  (2) 同公告 3 URL 变体重复——验证 B-014 dedup 必要。记录
  `09_Automation/Channel_Trial_Run_20260806.md`。**发现 WP-210 adapters
  （discovery.py）已实现，B-007 discovery service 未实现。下一个: B-007
  （discovery service 写 Candidate DB）+ B-014（dedup）。**
- **B-007 discovery service 完成 (2026-08-06)**: `src/research_os/services/
  discovery.py`（Channel→adapter 自动映射 + preflight 守卫 reviewed/enabled/
  restricted + 写 Candidate DB candidates/discovery_runs）+ `discover run/due`
  CLI。WP-201 全部完成。真实试跑：SK hynix RSS 10 候选、arXiv 20 候选写入
  Candidate DB。修复 insert_candidates 计数 bug（total_changes→rowcount）。
  **重复候选未去重（同公告多 URL 变体）→ B-014 dedup 是下一个核心。**
  **137 tests。下一个: B-014（dedup）或 B-017（scoring）或 B-018（Queue CLI）。**
- **B-014 dedup 完成 (2026-08-06)**: `src/research_os/services/dedup.py`
  （exact canonical URL/content_fingerprint + near normalized-title 聚类，
  cluster 不丢记录）+ 集成进 discover.run（跨 run 扩展已有 cluster）+ 
  candidate_db 写 duplicate_cluster_id。真实验证：SK hynix 10 候选 → 5
  cluster（HBF 3 变体 / CTI 3 变体 / 2Q26 2 变体各 1 cluster）；20 候选
  （2 run）仍 5 cluster（跨 run 正确扩展）。**144 tests。WP-220 剩余:
  B-015 entity resolution / B-016 sector classification / B-017 scoring。**
- **B-015 entity resolution 完成 (2026-08-06)**: `src/research_os/services/
  entity_resolution.py`（EntityIndex 从 universe 构建 87 归一化名 / 59 公司；
  resolve 输出 matched/ambiguous/unknown；中文括号名独立索引）。真实验证：
  SK hynix 公告 → COM-sk-hynix；SK+NVIDIA 合作 → ambiguous（正确需人审）；
  arXiv 论文 → unknown（作者机构不在 universe）。**151 tests。WP-220 剩余:
  B-016 sector classification / B-017 scoring。**
- **B-016 sector classification 完成 (2026-08-06)**: `src/research_os/services/
  sector_classification.py`（SectorIndex 从 universe 构建，multi-label 关键词
  匹配 title/publisher，输出 sector_ids + reasons；title/definition/token 全
  纳入索引，hyphen 拆 spaced）。真实验证：HBF/AI Memory 标题 → SEG-memory-storage；
  98 关键词 / 9 sector。**已知局限：纯关键词 classifier 对无 sector 词的标题
  （如"2Q26 财报"、"Data Center"）无法判定，需结合 entity 推断（pipeline 组合
  层）。156 tests。WP-220 剩余: B-017 scoring。**
- **B-017 scoring v1 完成 + WP-220 全部完成 (2026-08-06)**: `src/research_os/
  services/scoring.py`（8 维分项：6 正向维度加权和为 1.0 + duplication/
  uncertainty 惩罚从总分扣减；reason_codes + version + weights 配置化）。
  真实验证：NVIDIA 财报 0.81 / SK hynix HBF 代表 0.615 / 重复变体 0.135
  （dup_pen 0.5）/ arXiv 未知 0.0（unc_pen 0.8）。**162 tests。WP-220 全部
  完成（dedup/entity/sector/scoring）。下一个: B-018 Candidate Queue CLI /
  B-019 promote / B-020 dismiss。**
- **B-018 Candidate Queue CLI 完成 (2026-08-06)**: `src/research_os/services/
  candidate_queue.py`（review 队列 list/show + enrich 回填）。`candidates
  list`（--status/--channel/--entity/--tier/--min-priority/--limit，按
  priority 降序）、`candidates show --id`（detail + entity/sector proposal +
  reason codes + action 历史）、`candidates enrich [--apply]`（B-015/016/017
  回填未打分候选，幂等，proposals 不改权威事实）。enrich 已接入
  `discover run --apply` 写路径。真实验证：SK hynix CTI 0.620 / HBF 代表
  0.590 / SK+NVIDIA 合作 ambiguous 0.578 / 重复变体 0.09–0.12。**167 tests
  (+5)。WP-230 剩余: B-019 promote-to-Source / B-020 dismiss/restore。**
- **B-019 promote-to-Source 完成 (2026-08-06)**: `src/research_os/services/
  promote.py`（事务服务）。`candidates promote --id --actor [--source-type
  --source-grade --publisher --project --user-agent --apply]`：URL 实况
  捕获 → Source+assets 原子提交（FileTransaction，§13 不留半个 Source）→
  candidate 置 promoted + promoted_source_id + append-only action。幂等：
  已 promoted 抛 AlreadyPromoted（CLI 打印 IDEMPOTENT exit 0）；dismissed/
  expired/failed 拒绝。source_type 由 channel 映射（rss→article/arxiv→paper/
  sec→report/github→other），companies 取 entity proposal（matched COM-*）。
  真实验证：SK hynix CTI dry-run → SRC-20260806-057，COM-sk-hynix 关联，0 写
  入。**172 tests (+5)。WP-230 剩余: B-020 dismiss/expire/restore。已知局限：
  promote 是权威仓库写入，须人工 --apply；capture 失败/无 URL 候选拒绝；
  crash 窗口（文件已提交、candidate 未链接）靠去重阻断重试，需人工 resolve。**
- **B-020 dismiss/expire/restore 完成 + WP-230 全部完成 (2026-08-06)**:
  `src/research_os/services/triage.py`（append-only action 状态机）。`candidates
  dismiss --id --reason --actor [--apply]`（→ dismissed，reason 必填）、
  `candidates restore --id --actor [--apply]`（dismissed/expired → new）、
  `candidates expire [--channel --as-of --apply]`（batch retention sweep：
  按 channel retention_days 默认 30d，actor=system）。全部动作只追加
  candidate_actions 审计行，**不物理删除审计历史**；promoted 拒 dismiss；
  restore 二次恢复拒。真实验证：dry-run dismiss/expire 正确、0 写入。
  **179 tests (+7)。WP-230（B-018～020）全部 completed。已知局限：ADR §3
  retention 的"dismissed/expired 立即清理（物理删除候选行）"未实现——需先
  处理 candidate_actions FK 与审计保留的关系（schema 决策），留待 retention
  sweep（B-021 runbook 配套）。下一个: B-021 launchd runbook / B-022 Daily
  Brief。**
- **B-021 launchd runbook + scheduler + retention sweep 完成 (2026-08-06)**:
  `schedule.py`（daily/daily Nx/every N hours|minutes|days/weekly → interval；
  不可解析视为不到期）+ `discover due` 变 schedule-aware（按 channel schedule +
  discovery_runs 上次 run）；discovery 加 **per-channel no-overlap lock**
  （running 行 + 30min stale 回收，重启后可恢复）；`jobs run discover
  --target CHN-ID` 与 `jobs run expire`（retention sweep）；launchd runbook
  （`09_Automation/launchd/RUNBOOK.md` + plist + wrapper run_daily.sh）。
  **retention purge 落地**：schema v2（去掉 candidate_actions FK，审计行可
  独立于候选保留）+ `candidates purge [--apply]`。JobSchema job_name 扩到
  discover/expire（实现已批准 §7/§10 CLI）。真实验证：discover due 只列
  3 个 reviewed+enabled 到期 channel（SK hynix 未到期、restricted/pending
  排除）；live DB v1→v2 迁移成功；jobs run expire → 0 expired/0 purged +
  JOB 记录。**192 tests (+13)。WP-231 剩余: B-022 Daily Brief。已知局限：
  schedule 解析不支持 cron 语法（"0 9 * * *"→None→不到期，用 channels check
  人工发现）；expire job 的物理 purge 立即删除 dismissed/expired 行（ADR
  "立即清理"）。**
- **B-022 Daily Brief generator 完成 + WP-231 全部完成 (2026-08-06)**:
  `src/research_os/services/brief.py`。`brief daily --date [--apply]` +
  `jobs run daily-brief --as-of`（幂等：已存在→"already exists"）。8 分区
  （§8）：建议处理顺序 Top5 / 新增高优先级（≥0.5）/ 已提升正式 Source /
  新 reviewed Event / Core Company 影响 / 反面冲突信号（ambiguous 或负面
  关键词）/ 论文技术（arxiv channel）/ 抓取失败+stale+coverage gap。候选
  分区每行标注 **unreviewed candidate**，与 reviewed 事实分区隔离。写
  `05_Research/Operations/Briefs/Daily_Brief_<date>.md`（拒绝覆盖）。真实
  验证：Top5 SK hynix CTI 0.620 / HBF 0.590 / SK+NVIDIA ambiguous 0.578；
  Source/Event 分区正确；job 幂等。**附带修复 B-018 latent bug：enrich 里
  singleton 候选（无 cluster）被误判 non-representative 加 dup_pen 0.5
  （相对排序掩盖，绝对分偏低）——现 singleton 视为自身代表。196 tests
  (+4)。WP-231（B-021～022）全部 completed。已知局限：反面信号是关键词/
  ambiguous 启发式（无 NLP）；论文信号仅按 arxiv channel。下一个: B-023
  metrics/health/secret redaction（WP-232）。**
