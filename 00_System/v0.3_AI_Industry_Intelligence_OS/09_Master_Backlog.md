# v0.3 Master Backlog 与实施波次

状态：`wave5-completed`（Wave 0-4 已完成；Wave 5 工程完成（WP-530 future-date dependent）；Wave 6 ready）
规则：本文件是执行索引；任务细节以各 Phase 文件为准。Agent 不得只读本表就开工。

## 1. 状态枚举

- `proposed`：尚未批准；
- `ready`：依赖/RCP/owner/Gate 已明确；
- `in_progress`：已分配唯一 owner；
- `verification`：实现完成，正在全仓库/真实 Gate；
- `blocked`：有明确外部/人工阻断；
- `completed`：Definition of Done 全部满足；
- `cancelled`：有人工作出决定和原因。

初始状态：所有 v0.3 工作包为 `proposed`。

## 2. 关键路径

```text
WP-000 Baseline
→ WP-010 Governance
→ WP-100 Taxonomy/Schema
→ WP-120 Pilot Universe
→ WP-200 Candidate Store/Channels
→ WP-230 Discovery/Scoring/Daily Brief
→ WP-300 Impact Schema/Direct
→ WP-320 Multi-hop/Field Gate
→ WP-400 Mode Contract/Runner
→ WP-430 Mode Field Gate
→ WP-500 Forecast/Valuation
→ WP-530 Recommendation/Resolution
→ WP-600 Unified Product
→ WP-630 30-day Pilot/Release
```

## 3. Wave 0：Baseline 与治理

| WP | 包含任务 | 交付 | 依赖 | 状态 |
|---|---|---|---|---|
| WP-000 | baseline audit | v0.2 commit/object/test/release snapshot | 无 | proposed |
| WP-001 | v0.2 cadence completion | 真实 Weekly/Monthly/final decision | 无（release check 18/18，2026-08-08 max 发布）| completed |
| WP-010 | A-001 | RCP-v03-001 产品/Candidate 边界 | WP-000 | proposed |
| WP-011 | charter decisions | Pilot、Core 上限、Sector ID、Recommendation ceiling | WP-010 | proposed |
| WP-012 | RCP schedule | RCP-v03-002～010 owner/date | WP-010 | proposed |
| WP-013 | engineering ADR set | Candidate DB、store boundaries、version strategy | WP-010 | proposed |

Wave 0 Gate：RCP-v03-001 获批，所有关键人工选择记录，后续 WP 有 owner 和 stop condition。

## 4. Wave 1：Taxonomy、Schema、Universe

| WP | 包含任务 | 可并行 | 主要交付 | 状态 |
|---|---|---|---|---|
| WP-100 | A-002～004 | 否 | Taxonomy audit/mapping/v2 RCP | completed |
| WP-101 | A-005～007 | 与 WP-100 设计协调 | Schema/ID/migration proposal | completed |
| WP-102 | A-008～010 | Product/Metric 可拆子包 | Entity schemas/services | completed |
| WP-103 | A-011～012 | 在 Schema 稳定后 | Relation assertion + ontology export | completed |
| WP-104 | A-013～015 | index/UI 可并行 | Registry CLI/index/dashboard | completed |
| WP-120 | A-016 | 按 Sector 分包 | 30–50 Core Company Universe | completed |
| WP-121 | A-017 | 按关系类型分包 | 100–200 relation proposals | completed |
| WP-122 | A-018～019 | 否 | coverage metrics + field review | completed |
| WP-123 | A-020 | 否 | migration/recovery/acceptance | completed |

并行限制：

- WP-120 可按 Sector 分配研究 Agent，但 Company ID registry 由一个 integration owner 维护；
- WP-121 可按 supplier/competition/product ownership 分包，但 predicate 定义不可并行修改；
- WP-102 未稳定前不要做 WP-104 UI。

## 5. Wave 2：Candidate Intelligence

| WP | 包含任务 | 主要交付 | 状态 |
|---|---|---|---|
| WP-200 | B-001～004 | RCP + Candidate DB ADR/migration | completed |
| WP-201 | B-005～007 | Channel Registry + discovery orchestration | completed |
| WP-210 | B-008～013 | P0 adapters；每个 Adapter 独立子包 | completed |
| WP-220 | B-014～017 | dedup/entity/sector/scoring | completed |
| WP-230 | B-018～020 | Candidate Queue + promote transaction | completed |
| WP-231 | B-021～022 | launchd + Daily Brief | completed |
| WP-232 | B-023～024 | metrics/health/secret redaction | completed |
| WP-240 | B-025～026 | 14-day real Pilot + acceptance | in_progress |

Adapter 子包接口冻结后可以并行。任何新 Adapter 先有明确 Channel、allowlist、rate、许可和
fixture，不允许以“先抓到再治理”为理由跳过。

WP-210 close-out（2026-08-07，agent 审计 + max 复核）：B-008 Adapter contract v2（DiscoveryAdapter
Protocol + SourceCandidate）、B-009 RSS、B-010 SEC（多 CIK composite）、B-011 arXiv、B-012 GitHub
（多 repo composite）均已实现并经 20 通道真实运行 + composite/multi-target 测试验证（test_discovery、
test_m3_ingestion）。B-013 IR/list-page：SK hynix IR 以 RSS 通道实现（Phase 2 §6 P0 "IR RSS 或明确
列表页"二选一）；独立 list-page / 本地手工 dropbox 未单独实现为 discovery adapter（`adapters/file.py`
覆盖本地文件 capture），记 Known Limitations。

## 6. Wave 3：Impact

| WP | 包含任务 | 主要交付 | 状态 |
|---|---|---|---|
| WP-300 | C-001～003 | RCP、Schema、rule map | completed |
| WP-301 | C-004～005 | direct impact + mechanism validator | completed |
| WP-310 | C-006～010 | temporal multi-hop/conflict/confidence | completed |
| WP-311 | C-011～012 | spec/renderer/review | completed |
| WP-312 | C-013～016 | index/CLI/UI/report integration | completed（C-013～015 落地；C-016 report 集成 deferred → Phase 6 F-007）|
| WP-320 | C-017～018 | metrics + 20-event field Gate | completed |
| WP-321 | C-019～020 | benchmark/recovery/acceptance | completed |

先通过 direct impact Field Gate，再决定是否把 2–3 hop proposal 设为 active。

WP-300 close-out（2026-08-07）：C-001 RCP-v03-006 已批准（`bc3ecf5`）；C-002 Impact Schema
落地（`IMP-YYYYMMDD-NNN` 正式对象，接入 ID_PATTERNS/OBJECT_PATTERNS/SCHEMAS/REVIEWABLE_TYPES/
validate_refs/reviewed-evidence，`ImpactEntityReference` 含 EVT/INS 引用，ontology EntityReference
未改动）；C-003 rule map 交付 `IMPACT_RULE_MAP.md`（12×13 allowlist + 方向/限制，2026-08-07 max 复核通过）。240 tests 全绿，validate 0 error。**Next：C-004 direct impact
proposal（WP-301）。**

WP-301 close-out（2026-08-07）：C-004 `services/impact_proposal.py propose_direct_impacts`
（reviewed Event → pending IMP 提案：桥接 reviewed+as-of 有效 REL → event 自身命名实体 ∩
REL 端点 为 target → 规则映射投影 PRIMARY_IMPACT_TYPE/DEFAULT_IMPACT_DIRECTION 定
impact_type/direction → 证据锚定确定性 mechanism；pending Event 拒绝，不写文件不权威化）
+ C-005 `validate_mechanism`（空/太短/TODO-TBD-占位 拒绝）。规则映射代码投影
`PRIMARY_IMPACT_TYPE`/`DEFAULT_IMPACT_DIRECTION` 入 `domain/policies.py`。真实冒烟：
EVT-20260225-034 → 4 提案（SUPPLIES→supply、ENABLES→technology）。258 tests 全绿。
**CLI `impact propose` 属 C-014（WP-312），现有 `impact --id` ontology 图命令不动。Next：WP-310（C-006 path expansion 等）。**

WP-310 close-out（2026-08-07）：C-006 `services/impact_path.py expand_impact_paths`（BFS 路径展开：hop1=direct，hop2+ 经 reviewed+as-of 有效 REL 前向边+对称反向边，per-path 防环、fan-out 上限、剪枝原因记录 pruned；**治理门：max_depth 默认 1=direct-only，多跳机制可测可调但不激活，待 C-018 Field Gate 后由 max 放行 2-3**）+ C-007 `is_valid_as_of`（valid_from/valid_to 窗口）+ C-008 `detect_contradictions`（同 target 正负/多 horizon 并存可见，不净额合并）+ C-009 `dedup_paths`（同序列同 REL 折叠，variant_count）+ C-010 `path_confidence`（weakest-link min，不乘，任一跳 unknown → None）。真实冒烟：EVT-20260225-034 → 4 direct + 10 两跳路径（EVT→COM-asml→COM-tsmc→COM-nvidia/AMD 传导链）。285 tests 全绿。**Next：WP-311（C-011 impact spec 契约 / C-012 review workflow）或 WP-312（C-013~014 index/CLI）。**

C-018 最小闭环 enablement（2026-08-07）：打通「物化 → review → Gate 评估」闭环，C-018 现在可执行。
- **C-011 物化**：`services/impact_draft.py`（prepare/apply impact draft，镜像 REL 先例；extra 字段 relation_id/predicate 追踪）。
- **C-012 review**：已验证可用（impact_assertion 已在 REVIEWABLE_TYPES，`review apply --targets IMP-x` 原子写 REV-* + 翻转 status），无需改 review 系统。
- **C-014 impact CLI**：`impact` 叶→组（`impact graph` 保留旧行为 / `impact propose --event [--apply]` / `impact queue`）；`review --type` 加 impact_assertion。
- **C-018 工具**：`services/impact_gate.py`（gate_sample §11 分桶 + 缺口诚实报告 / render_gate_packet / gate_metrics §11 阈值 / gate_metrics_from_reviews）。
- 真实演示：EVT-20260225-034 → 4 个 pending IMP 落盘（IMP-20260807-001..004），validate 0 error；review dry-run 证明 pending→reviewed 翻转；评估包 `05_Research/Reviews/Field_Gate_20_Impact_Packet.md` 落盘（11 events 采样，**缺口：pricing 0/3、financial-capex 0/2、regulation-other 0/2、product-technology 2/3、customer-demand 2/3**——当前 48 reviewed Event 不足以填满 §11 组成，需补这些类型的事件或说明样本偏差）。
- 修 bug：`prepare_impact_batch` 原先全量算 ID 后统一写盘致 ID 撞车，改为逐提案 prepare+apply + 已存在跳过。
- 299 tests 全绿。**未完成（留待 WP-311/312/320）：C-011 完整 spec 契约模板、C-013 index、C-015 UI、C-016 report 集成、C-017 metrics 全量、20-event 人工 judgment（max 用评估包开始）。多跳仍待 C-018 通过后由 max 放行。**

## 7. Wave 4：Analysis Modes

| WP | 包含任务 | 主要交付 | 状态 |
|---|---|---|---|
| WP-400 | D-001～004 | RCP、Mode/Run Schema、contract | completed |
| WP-401 | D-005～009 | registry、resolver、runner transaction | completed |
| WP-410 | D-010 | 9 mode definitions；可按 mode 分包 | completed |
| WP-411 | D-011～013 | compare、Red Team、discovery sandbox | completed |
| WP-412 | D-014～016 | CLI/UI/promotion proposal | completed |
| WP-420 | D-017～018 | evaluator/metrics | completed |
| WP-430 | D-019～020 | 10-case field Gate/recovery | completed |

所有 Mode 子包必须共用同一 output contract，不得各自创造不兼容的 Facts/Inference 字段。

WP-420 close-out（2026-08-08）：D-017~018 落地，Phase 4 评估层完成。
- **D-017 evaluator**：`services/analysis_evaluator.py`——确定性评分卡（每 completed run）：citation（被引 ID 可解析率，§11 目标 100%）/ outside_facts（被引证据是否全为声明输入，硬门）/ sections（共享契约 + mode 必输分区非空率）/ questions（必答问题内容词覆盖率，CJK bigram 保守启发式，无特色词问题诚实排除）/ counterevidence（反证非裸否认）/ placeholders。整体 = 均分，gate_pass = 全维度达标。`render_evaluation_packet` 输出 §11 八维人工评估包（D-019 用）；`evaluator_metrics` 聚合 gate 通过率。
- **D-018 mode metrics**：`services/mode_metrics.py`——按 mode 聚合 completed run：edit（输出多样性 = 同 mode run 体两两归一化距离，近 0 提示 boilerplate）/ agreement（共享证据 run 对信号一致率，浮出分歧不自动裁决）/ evidence omission（他 mode 用过而本 mode 未用的证据清单，聚合 D-011）。纯启发式、只读。
- **CLI**：`analyze eval --run [--packet]` + `analyze metrics [--mode]`。真实冒烟：ANL-001 scorecard（citation 1.0 / outside_facts 1.0 / sections 1.0 / questions 0.8 / counterevidence 0 / placeholders 1.0，gate FAIL 诚实反映管线验证 run 薄反证）。
- **Dashboard**：run detail 加 D-017 评分卡 + 确定性 Gate；`/analysis/eval?run=` 人工评估包；`/analysis/metrics` + 概览 D-018 模式指标面板；导航不变。已重启 8765 真实渲染通过。
- 440 tests 全绿（+20），validate 0 error，ruff/mypy clean。
- **Known limitations**：questions 覆盖是内容词启发式（非语义）；edit 是词法距离非语义新颖度；agreement 是信号一致非结论同一。
- **Next：D-019 10-case field Gate（WP-430）——需真实 model provider 跑多模式真实 run + max 用 D-017 评估包人工评分；或先接真实模型 provider。**

## LLM 供应商适配（D-008 后续，2026-08-09）

参考 CC Switch「供应商预设 + 服务端加载模型 + 下拉选择」的必要部分，落地真实 provider 接入（砍掉视觉分离/自定义供应商/大目录/测速/代理管理）。

- **`research_os/llm/` 四模块**：
  - `provider_catalog.py`：DeepSeek preset（base_url `https://api.deepseek.com`、api_format `openai_chat`、api_key_url、default_params max_tokens 4096、recommended_models、default_model `deepseek-chat`、timeout 120），结构化便于新增供应商；协议由 preset 决定，绝不靠失败猜测。
  - `llm_config.py`：服务端 Key 存储 `00_System/llm.local.json`（`*.local.json` gitignored + 0600）；`public_config` 永不含 Key（masked `sk-***`）；编辑留空保留已有 Key、无 Key 留空报错；`get_api_key` config store 优先、env `DEEPSEEK_API_KEY` 兜底。
  - `llm_adapter.py`：openai_chat（`/chat/completions` + `messages` + `choices[].message.content`）与 openai_responses（`/responses` + `input`/`max_output_tokens` + `output[]/output_text`）独立 builder/parser；**`content:null + reasoning_content` 是合法成功包**（test_connection 不要求非空 content、不把 max_tokens 压小）；错误映射 auth/not_found/rate_limited/server_error/timeout/invalid_response。
  - `model_fetch.py`：服务端代理 `GET /models`（Bearer Key），标准化 `{id, ownedBy}` 排序，Key 不出现在输出/错误。
- **ModelAdapter Protocol 扩展**：`generate(prompt, *, timeout, model_id, model_parameters)`——冻结的 model_id == 实际调用模型（此前 `--model-id` 名不副实）；DeepSeekAdapter 按 preset 绑定 + generate 时从 config store/env 解析 Key；runner 透传 model_id/params。
- **`/llm` dashboard 配置页**：供应商下拉（不显示 URL 输入框）→ API Key 输入（显隐 + 获取 API Key 链接）→ 加载模型按钮 → 可搜索模型下拉（按 ownedBy 分组、不允许手输 ID）→ 测试连接 → 保存配置；供应商切换清空模型选择；模型列表仅会话缓存。**仅新增 POST /llm/config、/llm/models、/llm/test 三个写端点**（dashboard 其余保持只读，测试断言唯一写路由）。
- **CLI**：`analyze run --model-provider deepseek --model-id deepseek-chat`（空则用已保存 config，缺 Key 给出可操作报错）。
- **测试**：`test_llm_provider.py` 31 项——模型列表加载排序、Key 不出现客户端响应/错误、content:null 合法、chat/responses 端点与解析器分离、401/404/429/超时/非法响应映射、留空保留 Key、供应商切换清模型、真实 DeepSeek 连接 E2E（`DEEPSEEK_API_KEY` 门控，无 Key skipped）。471 tests 全绿（+31），validate 0 error，ruff/mypy clean。
- **已知边界**：仅 DeepSeek（openai_chat，responses 已实现+测试但无 preset）；无视觉供应商分离（项目无视觉功能）；无自定义供应商高级入口（缩窄攻击面）；token/cost 未捕获（D-008 协议仍只返回 str）；真实连接需 max 在 `/llm` 填 Key 或用 `! DEEPSEEK_API_KEY=... pytest ...` 跑 E2E。
- **Next：max 在 /llm 配置 DeepSeek Key 并跑通真实 analyze run → D-019 10-case Gate（WP-430）。**

## D-019 第一批（3 Sector case × 4 modes，2026-08-09）

max 在 /llm 配好 Key（deepseek-v4-flash）后，D-019 10-case 真实比较 Gate 启动。

- **运行**：第一批 3 个 Sector case（EVT-20260601-044 DRAM 份额 / EVT-20260302-041 AI 需求 / EVT-20260520-032 交期）× 4 modes（value-chain/supply-demand/scenario/red-team）= 12 组合。真实 DeepSeek 调用 `--apply` 落盘，失败自动重试。
- **关键发现①（语言不一致）**：首轮 12 run 中 7 个模型输出为英文（red-team 全英文、case-2/3 的 supply-demand/scenario 英文、value-chain 全中文）——prompt 未指定输出语言，模板中文+分区名英文导致模型选择不一致。D-017 questions 启发式只查中文 bigram → 英文 run 假性 q=0.00。**修复：prompt 模板加「输出使用中文」规则 + 重跑 7 个英文 run**。
- **关键发现②（契约拦截外部事实）**：case-3（NVIDIA 交期）的 red-team 6 次尝试全部被 D-004 拒绝——模型持续引用冻结输入外的 SRC-20260805-040（真实 NVIDIA 源）。契约正确拦截（no facts outside inputs）。**记录为真实失败模式**：red-team 对单事件输入难以约束在冻结证据内，case-3 缺 red-team run（3/4 模式落盘）。
- **关键发现③（分区越多越不稳定）**：red-team（7 分区）/scenario（6 分区）比 value-chain/supply-demand（5 分区）更易漏分区，需重试。
- **结果**：11 个中文 run 落盘（ANL-20260809-002/003/004/006/010/014-019），**确定性 Gate 11/11 PASS、整体 1.000**（citation/outside/sections/questions/counterev/placeholders 全满分）；case-3 red-team 缺（已记录）。评估包 `05_Research/Reviews/Field_Gate_10_Case_Packet.md`（含每 run 评分卡 + 每 case 多模式 D-011 比较 + §11 八维人工评分表 + 缺口注记）。
- **顺带修复**：`_resolved_model` 改为按 repo root 读 llm 配置（避免 CLI 操作其他 root 时串入机器全局配置——曾致 test_cli echo 测试意外调真实 API）；test_cli pin echo。
- **新增**：`services/field_gate.py`（D-019 review packet 服务：逐 run D-017 scorecard + 逐 case D-011 compare + 人工评分表 + 缺口/不匹配报告）。
- 474 tests 全绿（+3 field_gate），validate 0 error，ruff/mypy clean。
- **下一步：max 用评估包做 §11 八维人工评分（含 case-3 red-team 缺口的专项判断）→ 确认后再跑剩余 7 case（33 run，含 5 open-discovery）。**

## D-019 完成（10-case 全量，2026-08-09）

max 确认第一批 §11 评分 PASS（`f49e592`）后，跑完剩余 7 case + 5 open-discovery。

- **运行量**：累计 46 组合，**32 个真实 run 落盘**（ANL-20260809-002..040，覆盖全部 8 模式），14 组合失败（4-7 次尝试后确认顽固）。
- **确定性 Gate：32/32 PASS、整体 1.0**（citation 100% / 无外事实 / sections / questions / counterevidence / placeholders 全满分）。
- **§11 人工判断（2026-08-09 max 确认，整体 0.992）**：32 run 八维评分定稿于 `Field_Gate_10_Case_Judgments.json`（confirmed/reviewer=max）；仅两处诚实扣分——honest-absence 反证 8 run × 0.9（单事件无反向信号，已明确说明"缺失≠确认"）、冲突 case 分歧可解释 13 run × 0.9（case-1/2/3 跨模式信号冲突，可解释需调和）。§11 阈值全达标（引用 100% / 无外事实 / 覆盖 ≥90% / 反证遗漏 <10% / 有增量价值 100% / **open-discovery 4 run 假设全部可判定**：HBM 价值稀释、非显性瓶颈 ABF、竞争性宣示、HBM 迭代 18-24→12 个月 / 非多数投票）。
- **13 个记录缺口（max 接受为发现，不烧 API 重试）**：scenario ×6（case-4/5/6/7/9/10）、value-chain ×3（case-4/5/7）、red-team ×2（case-3/10）、technology-curve ×1（case-7）、open-discovery ×1（case-9）。**根因两类**：①**scenario 模式脆弱**（6 分区含 Downside/Base/Upside，deepseek-v4-flash 输出不稳定，6/10 case 失败）；②**事件级顽固外部引用**（case-7 Samsung→SRC-20260806-052、case-9/10 Oracle/SAP→THS-004、case-3 red-team→SRC-20260805-040，D-004 契约持续拦截——模型对特定事件从训练记忆引入真实对象）。
- **D-019 判定：PASS**（确定性 32/32 + 人工 0.992 + OD 门达标 + 缺口记录）。评估包 `05_Research/Reviews/Field_Gate_10_Case_Packet.md`（完整 10-case + 已确认人工评分 + 缺口文档）。
- **Phase 4 结论**：多模式真实比较可行，但**scenario 模式需 prompt 强化/分区精简，外部引用需更强约束**（D-020 acceptance 项目）；model 输出语言已修（中文）。**WP-430 剩 D-020（acceptance/recovery：replay/hash/rebuild 通过验证）。**

## D-020 验收（2026-08-09，WP-430 完成）

`00_System/D020_Phase_4_Acceptance.md`（status passed）。Phase 4 §10/§12 验收通过：

- **replay 创建新 ID**：`analyze replay ANL-20260809-002` dry-run → 预览新 ID ANL-20260809-041，不覆盖旧 run；`write_new_file` 拒绝已存在路径（FileExistsError）。
- **hash 可重建**：input_snapshot_hash（重跑 resolve_inputs == 存储）、output_hash（sha256(body) == 存储）全部通过；prompt_hash 在模板未变时重建（020/040 ==）；**002 的 prompt_hash 因中文规则模板改动（`bd80478`）前创建而不匹配——正确行为，run 冻结创建时模板**。
- **rebuild**：validate 0 error / index --apply 9 indexes 无 drift。
- **失败不留半成品**：畸形输出（echo）/provider-failure → RunError 无半写入。
- **回滚 §12**：模式 append-only 版本、run 不反向修改 Evidence、误生成 run 用 rejected/superseded（ANL-001 先例）、D-004 契约拦截外部引用即回滚防线。
- 新增 `test_phase4_acceptance.py`（4 项）。**478 tests 全绿（+4），validate 0 error，ruff/mypy clean。**
- **WP-430（D-019+D-020）全部完成，Phase 4 主线关闭。** 后续候选：Phase 5（Forecast/Decision，需 RCP-v03-008/009）、scenario 模式 prompt 强化、真实 provider 的其他接入。

## scenario v2 强化（2026-08-09）

D-019 暴露项收尾：scenario 模式在 10 case 中 6 个顽固失败（模型跳过 6 个 scenario 专属分区）。

- **根因**：默认 prompt 模板把 9 个共享分区当"全部"，模型不产出 mode 专属分区；scenario 6 分区是全部模式最重的（15 个 ## 标题）。
- **修复**：新增场景专用模板 `00_System/Analysis_Modes/templates/scenario.md`——显式枚举全部 15 个 ## 分区（含 Downside/Base/Upside）+ 机器校验警告（缺任一标题即失败）+ Downside/Base/Upside 内容结构要求（驱动/概率/结果/时间）。
- **v2 模式**：`MOD-ANL-scenario-v2`（REV-20260809-001 max 激活，active+reviewed+valid_from 2026-08-09），v1 未动（append-only）。
- **PoC + 实跑验证**：EVT-20260520-038 scenario 组合 v1 默认模板失败 4+ 次 → v2 首次即产出全部 15 分区；实跑 6 个失败组合 → **2 恢复**（case-9/10 → ANL-041/042，全维度 1.0），**4 剩余缺口全部重新归类为事件级顽固外部引用**（SRC-20260805-048/044/047/052，D-004 契约拦截）——section 缺失问题已修复，外部引用是独立发现（模板无法约束）。
- **D-019 记录更新**：34 run 判定（整体 0.992），评估包已更新（scenario v2 恢复注记 + 缺口重新分类）。
- 测试更新：ModeDefinitionsTests（10 modes、v2 active+runnable）、test_schemas（analysis_mode 10、review 178）。**479 tests 全绿，validate 0 error，ruff/mypy clean。**

WP-412 close-out（2026-08-08）：D-014~016 落地，Phase 4 命令层完成。
- **D-014 CLI**：`modes list/show/check` + `analyze run/show/compare/replay/propose-thesis`。`modes check` 用 `require_runnable` 逐模式门禁；`analyze run` 走 D-009 全事务（dry-run 默认/`--apply`）；`analyze replay` 复用冻结输入以当前模型重放（创建新 ID，不覆盖）；错误退出码 2。
- **D-015 Dashboard**：`/analysis` 工作区（概览 + modes/runs 列表 + mode/run detail + `?runs=` compare），只读 GET，渲染输入引用/版本/冻结哈希/共享事实与冲突信号；导航加「分析」。
- **D-016 promote insight**：`services/insight_proposal.py`——reviewed completed run → `05_Research/Analysis_Proposals/Thesis_Proposal_<ANL>.md`（pending proposal）。门禁：rejected/pending run 拒绝、red-team 反证须实质（RT001/RT002）、open-discovery 只产候选 Hypothesis（D-013）。**永不经由此服务改写 THS-\***（RCP-v03-007 points 3/6）。
- **修复**：Wave 4 表 WP-400/401/410/411 状态补齐为 completed（此前未更新）。
- **Known limitations**：`analyze run` 当前仅 echo/deterministic adapter（真 provider 接入是后续 WP）；proposal 文档非正式对象（不在 OBJECT_PATTERNS，validate 不扫 `05_Research/Analysis_Proposals/`）。
- 420 tests 全绿（+29），validate 0 error，ruff/mypy clean。
- **Next：WP-420（D-017 evaluator / D-018 mode metrics），或接真实模型 provider 跑真实 multi-mode run 后做 D-019 10-case Gate。**

## 8. Wave 5：Forecast 与 Decision

| WP | 包含任务 | 主要交付 | 状态 |
|---|---|---|---|
| WP-500 | E-001～006 | RCP + Forecast/Resolution/Valuation/REC Schema | completed |
| WP-501 | E-007～010 | forecast lifecycle/resolution | completed |
| WP-510 | E-011～013 | valuation/scenario/recommendation workflow | completed |
| WP-511 | E-014～015 | supersession/calibration | completed |
| WP-512 | E-016～018 | CLI/UI/alerts | completed |
| WP-520 | E-019～021 | license + 10 forecast + 3 company Pilot | completed |
| WP-530 | E-022～023 | natural resolution + acceptance | future-date dependent |

WP-530 不能用回填或合成 outcome 提前完成。

## 9. Wave 6：统一产品与发布

| WP | 包含任务 | 主要交付 | 状态 |
|---|---|---|---|
| WP-600 | F-001～003 | IA/read model/Industry Home | completed |
| WP-601 | F-004～006 | Sector/Company/Candidate UI | completed |
| WP-602 | F-007～009 | Impact/Analysis/Decision UI | completed |
| WP-603 | F-010～011 | Operations/Health | completed |
| WP-610 | F-012～014 | profile/SLO/security | proposed |
| WP-611 | F-015～018 | license/backup/recovery/migration | proposed |
| WP-612 | F-019～020 | runbook/limitations | proposed |
| WP-620 | F-021～022 | 30-day Pilot/resolutions | future-date dependent |
| WP-630 | F-023～025 | release check/human decision/tag | WP-620 | proposed |

Wave 6 开工前置已满足：RCP-v03-010 已获批（2026-08-09，`6e5aa8e` 修订 + approval）；F-001 页面/查询/边界按 RCP 批准时点同步完成。WP-600 起可开工。

WP-600 close-out（2026-08-09）：F-001~003 落地，Wave 6 第一个 WP。
- **F-001**：`00_System/Dashboard_Design_v2.md`（Product IA v2——IA 树、页面→查询/边界表、read model 约定、GET-only 不变量、loopback、WP-600 范围；镜像 v1 先例 `Dashboard_and_Jobs_Design.md`）。
- **F-002**：`services/read_model.py` `industry_home_snapshot(root, *, as_of, db_path)`——组合 `daily_brief` + `forecast_status_report` + `action_rows` + `pipeline_metrics`，新增 `impacts_today`/`stale_core_companies`（core 公司→stale 通道 rollup）/`due_actions`/`sector_heatmap`（原始计数非情绪分）/`freshness`；校验 error 即拒。
- **F-003**：`/home` GET 路由（`_industry_home` 渲染，产业级无 project 过滤）+ nav「产业首页」；保留 `/` 为项目概览（方案 B）。只读不变量维持（非 GET 路由仍恰为 3 个 `/llm`）。
- 测试：`test_m5_dashboard_jobs.py` +8（TestIndustryHomeSnapshot 5 + IndustryHomeTests 3）。**578 tests 全绿（+8）、validate 0 error、ruff/mypy clean、index drift 0**。真实仓库 /home 冒烟 200（22 COM/9 SEG 引用，FCT-0 正确因均未到期）。
- **Known limitation**：`industry_home_snapshot` 多次调 `validate_repository`（每日历 4+ 次），诚实无缓存；超 §5 SLO 时由 WP-610 F-012 优化（传预载 objects，不改 `daily_brief` 公共签名）。stale_core_companies 依赖 `source_channel_ids`/channel `entity_ids`（当前多为空，面板常空——诚实）。

WP-601 close-out（2026-08-09）：F-004~006 落地，Sector/Company/Candidate 页面增强。
- **F-004**：`services/read_model.py` `sector_snapshot(root, sector_id)` + `_sector_detail`（app.py）——定义/范围/价值链、上下游断言、核心与追踪企业、产品/技术/指标、事件时间线、reviewed 影响路径、活跃观点/预测、成员覆盖完整度 rollup（聚合 universe_coverage）。
- **F-005**：`company_snapshot(root, company_id)` + `_company_detail`（企业雷达）——主体与证券分离（issuer_company_id）、产品/技术/板块、供应链断言（按 predicate 分组）、来源通道新鲜度、指标、证据时间线、分析运行、预测/估值/推荐历史、覆盖 badge。
- **F-006**：候选详情结构化——entity/sector proposals 从 raw JSON 改字段表；`queue_show` 附 `scoring`（重算 `score_candidate`，仅 model_version==SCORING_VERSION，否则 badge mismatch）；promote/dismiss 只读建议；候选区 vs 已评审证据区（existing_source 链接 + entity 相关 reviewed 事件）。列表加发布时间列 + 实体/板块链接。
- **路由策略**：`generic_detail`（app.py）按 `object_type` 分支到 `_company_detail`/`_sector_detail`，其余类型保持 generic——不加路由、自动保只读不变量。
- 测试：`test_m5_dashboard_jobs.py` +5（SectorCompanyDetailTests 2 + CandidateDetailTests 3）。**583 tests 全绿（+5）、validate 0 error、ruff/mypy clean、index drift 0**。真实仓库冒烟 `/companies/COM-nvidia`（证券/事件/运行面板）+ `/sectors/SEG-memory-storage`（覆盖 rollup）200。
- **Known limitation**：company/sector 详情多处 inline 过滤（含一次 universe_coverage 调用）——诚实无缓存；sector 上下游仅展示 sector 自身的 ontology_assertion（成员级上下游未聚合，数据稀疏）；候选评分分项需 model_version 匹配才重算（评分版本演进时数值面板自动隐藏并提示）。

WP-602 close-out（2026-08-09）：F-007~009 落地，三类研究工作台改由只读 read model 组合。
- **F-007**：`impact_explorer_snapshot` + `/impact`——reviewed 直接断言、1～3 跳逐跳机制/Evidence、weakest-link confidence、剪枝、正负/多 horizon 冲突、反向因素和替代解释。当前 22 个 Impact Assertion 均为 pending，页面诚实显示 reviewed 直接断言为 0，不自动提升；多跳查询仅使用 reviewed Event/ontology relation。
- **F-008**：`analysis_workspace_snapshot` + `/analysis`——冻结输入 ID、Mode/model/template 版本、input/prompt/output hash、Evaluator、D-018 metrics 及双 Run shared facts/evidence omitted/conflicting signals 比较；无 Thesis/Recommendation 自动提升。
- **F-009**：`decision_desk_snapshot` + `/decision`——open/due/overdue Forecast、校准样本、Valuation freshness、Recommendation catalysts/falsifiers/risks/unknowns/Scenario 引用、Resolution history。当前真实 Resolution 为 0，明确 `insufficient_sample`，不回填未来 outcome。
- **边界与测试**：Dashboard 写路由仍仅 3 个 `/llm` 本地配置例外；WP-530/WP-620 不变。`test_impact_path.py`、`test_analysis_evaluator.py`、`test_mode_metrics.py`、`test_phase5_lifecycle.py`、`test_phase5_valuation.py`、`test_m5_dashboard_jobs.py` 全绿；相关 ruff/mypy clean。

WP-603 close-out（2026-08-09）：F-010~011 落地，Operations/Health 由统一只读 snapshot 驱动。
- **F-010**：`operations_snapshot` + `/operations`——汇总 due Channel schedule、最近 Jobs、open/in-progress Actions、到期研究评审、due/overdue Forecast 与 stale active Recommendation；所有空队列保留明确空态，页面不触发调度或权威写入。
- **F-011**：`health_snapshot` + `/health`——覆盖 repository validation、global/project index drift、Source asset integrity、Candidate DB `quick_check`/schema version、Channel review/license/robots metadata、failed Job/Analysis Run、Candidate backup age、disk/timezone、secret/config presence 与 model/cost status。secret 仅返回 `present/missing`，不返回值。
- **Candidate DB**：新增 `candidate_db_health`，read-only URI 打开，不存在时不创建、不迁移；区分 `ok/missing/corrupt/migration_required`，不返回 Candidate 内容。
- **测试**：`test_candidate_db.py`、`test_channels.py`、`test_schedule.py`、`test_m5_dashboard_jobs.py` 全绿；相关 ruff/mypy clean。当前 backup 缺失与 cost budget 未配置会诚实显示注意状态，由 WP-611/F-016 接续。

## 10. 建议首批派发顺序

在用户批准 v0.3 后，按以下顺序逐包派发，避免一次给 Agent 过大范围：

1. WP-000：只读 baseline audit。
2. WP-010：产品与 Candidate 边界 RCP 草稿。
3. WP-011：列出需用户选择的明确选项，不编码。
4. WP-100：Taxonomy v1 audit/mapping。
5. WP-101：Schema/ID/migration proposal，不 apply。
6. 用户批准 RCP-v03-002/003。
7. WP-102：Entity schemas 垂直实现。
8. WP-103：关系 assertion 与 export。
9. WP-120：按 Pilot Sector 建立 Universe。
10. WP-122：真实抽检后再进入 Candidate Pipeline。

## 11. Backlog 维护规则

- 只有 integration owner 修改本文件状态；
- Agent 在 handoff 中建议状态，但不自行标记整个 Phase completed；
- `blocked` 必须写 blocker、owner、解除条件和下一检查日；
- future-date Gate 保持明确日期，不能提前回填；
- 新任务用现有 Phase 前缀追加，不重编号已发布任务；
- 取消任务保留 ID 和理由；
- 任务拆分后原 ID 变 parent，不复用；
- 每次 Weekly review 更新完成、阻断、风险、coverage 和下周 WP；
- 每次 Monthly review评估是否扩大 Universe 或改变存储，不由 Agent 自动决定；
- 每条 RCP 批准需同步 `05_Research/Reviews/Rule_Change_Log.md` 汇总行（Date/Target/Decision/Summary/Validation 齐备），Backlog §13 记决策细节；v0.3 曾只有 §13 无汇总，001–006 已补录。

## 12. 全局风险登记

| 风险 | 早期信号 | 缓解 | Owner |
|---|---|---|---|
| Universe 扩张过快 | coverage 下降、stale 增加 | Core 上限、分批 Gate | researcher |
| Candidate 噪声 | Top-N precision 下降 | Channel/评分/去重 review | ingestion owner |
| 数据许可 | restricted/unknown 增加 | Channel enable Gate | researcher/legal |
| Ontology 过度建模 | predicate 频繁变更 | 先 Pilot、append-only version | ontology owner |
| 因果幻觉 | 多跳编辑率高 | direct-first、mechanism review | impact owner |
| 模式同质化 | 输出差异只在措辞 | 固定问题/禁区/field rubric | analysis owner |
| 投资过度结论 | 缺估值仍给方向 | Recommendation validator | decision owner |
| 后见偏差 | Forecast 被改写 | immutable Forecast + Resolution | forecast owner |
| SQLite 瓶颈 | lock/p95 超 Gate | profile 后再评估 PostgreSQL | platform owner |
| iCloud 冲突 | conflicted copy/hash 问题 | 单写者、Git remote、离机资产备份 | owner |
| Agent scope drift | 无 RCP 改 Schema | WP contract/stop conditions | integration owner |
| 成本失控 | model/API cost 超预算 | per-channel/run budget | operations owner |

## 13. 决策日志模板

每个关键选择在对应 RCP/ADR 中记录：

```text
Decision ID:
Date:
Question:
Options considered:
Decision:
Reason:
Evidence/benchmark:
Consequences:
Migration:
Rollback:
Reviewer:
Revisit trigger/date:
```

### 13.1 已记录决策

#### D1 产品定位（2026-08-05）
- Decision ID: D1
- Date: 2026-08-05
- Question: 是否接受 v0.3 产品定位（AI Industry Intelligence & Decision OS）？
- Options considered: 接受 / 修改目标闭环 / 拒绝
- Decision: 接受。在 v0.2 Evidence Kernel 之上建设 Universe/每日情报/Ontology/Impact/Analysis Mode/Forecast/Recommendation，保留 v0.2 全部继承原则。
- Reason: 现有 single-topic 边界无法承载 AI 全产业链；目标闭环见 Roadmap §1。
- Evidence/benchmark: WP-000_Baseline_Audit.md（v0.2 基线 166 对象、0 error）。
- Consequences: 启用 v0.3 全阶段规划；Charter/Schema/ID 推进需逐项 RCP 批准。
- Migration: 无数据迁移；治理边界变更由 RCP-v03-001 承载。
- Rollback: 撤销 RCP-v03-001 即回退定位（不影响既有对象）。
- Reviewer: max
- Revisit trigger/date: 30-day Pilot Gate / v0.3 发布决定（D12）。

#### D2 cadence 先后（2026-08-05）
- Decision ID: D2
- Decision: 并行推进。WP-001（2×Weekly + 1×Monthly + ACT-20260729-009 + 最终发布决定）保持日期阻塞；v0.3 只读/文档型 WP 先行，不争用同一人审时段。
- Reviewer: max
- Revisit trigger/date: v0.2 最终发布时或 cadence 出现与 v0.3 争用时。

#### D3 第一 Pilot value chain（2026-08-05）
- Decision ID: D3
- Decision: AI Compute Infrastructure Chain（半导体材料与设备 → 制造/封装/测试 → GPU/ASIC → HBM/DRAM/Storage → Server/Network/Optics → Datacenter/Power/Cooling → Cloud AI Infra → Foundation Model Demand）。
- Reason: 多板块、多公司、多跳关系；原始来源相对丰富；供给/成本/产能/资本开支机制可观察。
- Consequences: Universe 首批围绕此链建 Core；第二 Pilot 再覆盖 Model-Agent-Enterprise。
- Reviewer: max
- Revisit trigger/date: 第一 Pilot Gate 后扩 Universe 时（D10）。

#### D4 Universe Core 上限（2026-08-05）
- Decision ID: D4
- Decision: Pilot Core 规模 30–50 家公司；未经批准不得扩大。
- Reviewer: max
- Revisit trigger/date: 每个 Pilot Gate 后评估（D10）。

#### D5 Candidate store（2026-08-05）
- Decision ID: D5
- Decision: 使用 SQLite 作为可重建 operational store，保存高频候选与调度状态；非事实源。须提供 Schema version、deterministic migration、export/import、backup/snapshot、retention、Candidate 提升为 Source 的永久关联。
- Reviewer: max
- Revisit trigger/date: 量化瓶颈出现时评估 PostgreSQL（D11）。

#### D6 Sector ID 前缀（2026-08-05）
- Decision ID: D6
- Decision: `SEG-<slug>`。避免与美国 SEC Adapter/披露混淆。
- Reviewer: max
- Revisit trigger/date: 引入 Security 对象并需区分监管实体时复核。

#### D7 Recommendation 最高权威等级（2026-08-05）
- Decision ID: D7
- Decision: Recommendation 最高为人工批准的个人研究建议；不得自动执行、不自动下单、不按模型置信度自动计算仓位。
- Reviewer: max
- Revisit trigger/date: Phase 5（RCP-v03-009）细化等级时。

#### D8 批准 RCP-v03-001（2026-08-05）
- Decision ID: D8
- Decision: 批准 RCP-v03-001（proposed → approved）。产品边界 + Candidate/Source 权威边界生效。
- Reviewer: max
- Revisit trigger/date: 实施发现边界不可行时提修改 RCP。

#### D9 RCP-v03-002~010 排期（2026-08-05）
- Decision ID: D9
- Decision: 按默认 Wave 排期（002/003 Wave1；004/005 Wave2；006 Wave3；007 Wave4；008/009 Wave5；010 Wave6）。reviewer 统一 max；计划日期在对应阶段开始前滚动落定。
- Reviewer: max
- Revisit trigger/date: 任一 Wave 开始前排当个 RCP 并记录日期。

#### R1-R5 Taxonomy v2 边界项（2026-08-05，ref: RCP-v03-002）
- Decision ID: WP-100-R1..R5
- Date: 2026-08-05
- Question: Taxonomy v2 的 5 个边界争议（见 A-002 §5）。
- Options considered: per item（Mapping §5 / Proposal §6）。
- Decision:
  - R1 历史 tag 不回填，保留旧 tag；mapping 表提供映射；补 SEG 关系时人工逐批核。
  - R2 APP-CODING keep 为 tag，归 Enterprise Applications 下 AI Developer Tooling 子域。
  - R3 MOD-* 6 个全 map 到 Models 扇区下 Technology 实体。
  - R4 INF-CLOUD-AI 归 Cloud & AI Infrastructure；边界=云端模型平台/推理服务。
  - R5 INF 父类聚合 tag deprecate，历史沿用 R1 不回填。
  - R6 SRV-DATA-LABELING 默认归 Services，RCP-v03-002 现场定。
- Reason: 见 A-002 审计（usage 41/93、INF 层近废）与 Phase 0-1 §3 扇区草案；保持"产业细分由实体表达"+"不自动改写历史"。
- Evidence/benchmark: `Taxonomy_v2_Mapping.md`、`Taxonomy_v2_Proposal.md`、`research-os validate` 0 error。
- Consequences: RCP-v03-002 草案备齐待 max 批准；WP-101 Schema 须与 Taxonomy v2 一致。
- Migration: 不回填（R1）；新对象用 SEG-ID；WP-123 落实。
- Rollback: 保留 v0.1 Taxonomy 与兼容窗口（Phase 0-1 §11）。
- Reviewer: max
- Revisit trigger/date: RCP-v03-002 最终审批时；与 WP-101 Sector Schema 核对时。

#### RCP-v03-002 批准（2026-08-05）

- Decision ID: RCP-v03-002-approval
- Date: 2026-08-05
- Decision: 批准 RCP-v03-002（proposed → approved）。Taxonomy v2 与稳定板块 ID 体系生效：13 个 L1 扇区作 Sector 实体（SEG-ID）、5 个横向维度扩展前缀（REG/SUP/CAP/CYC/RGT）、v1→v2 权威映射表、边界项 R1–R5 整体接受。
- Reason: A-002 审计 + A-003 草案备齐，边界项已由 reviewer max 拍板。
- Effective date: 2026-08-05。
- Consequences: Taxonomy v2 成为权威；v0.1 Taxonomy 标注 superseded 但保留为历史参考；v0.2 历史 tag 不回填（R1）；后续 WP-101 Schema 须与 Taxonomy v2 一致。SRV-DATA-LABELING 归属（R6）在 WP-101/Schema 阶段现场定。
- Reviewer: max
- Revisit trigger/date: 与 WP-101 Sector Schema 核对；任一扇区边界实施遇阻时提修改 RCP。

#### 地区优先级范围约束（2026-08-05）

- Decision ID: D-REGION-SCOPE
- Date: 2026-08-05
- Question: Universe 研究对象的地区范围？（上下文：在 RCP-v03-002 批准后，开 WP-101 前）
- Options considered: 仅中美 / 中美为主其他为辅 / 全球无优先级。
- Decision: 研究对象以中国、美国 AI 企业为主，其他地区的重点企业为辅。
- Reason: 研究者明确范围；中美当前是 AI 产业最具区分度的市场，其他地区保留关键节点（卡位/稀缺供给）。
- Evidence/benchmark: 研究者陈述（2026-08-05）；`02_Phase_0_1_...md` §6.1。
- Consequences: Core 席位优先中美；非中美企业进 Core 须写明价值链区分度理由（如 ASML/TSMC/SK hynix）。`REG-` 地区维度按国别细分中美、其他归 Country/Region 级。D10（扩 Universe Gate）复核地区覆盖平衡。
- Migration: 无；`REG-` 前缀已由 RCP-v03-002 批准承载该维度。
- Rollback: 不适用（范围约束，可在 D10 Gate 重新评估）。
- Reviewer: max
- Revisit trigger/date: WP-120 Universe 建设时；D10 扩 Universe Gate 时评估地区平衡。

#### RCP-v03-003 草案起草（2026-08-05，status: proposed）

- Decision ID: RCP-v03-003-drafting
- Date: 2026-08-05
- Question: 是否将 A-005/006/007 整理为 RCP-v03-003 草案提交人审？
- Decision: 起草 RCP-v03-003 `05_Research/Reviews/Proposals/RCP-v03-003_Entity_Schema_and_Permanent_IDs.md`（proposed，待 max 批准）。集中 7 项人审点：schema_version=2 启用、5 实体 Schema 字段、Company v0.3 扩展不回填、14 新前缀+parser 歧义 D1–D7、Company/Security 分离、migration 顺序 MIG-001→002→003、禁用单段 `MOD-`。
- Reason: A-005/006/007 已齐备且与 Taxonomy v2/R1–R5/地区约束一致，可直接包成 RCP 草案供人审。
- Effective date: 待 max 批准（MIG-v0.3-001 注册 Schema 起按 WP-102 落地）。
- Reviewer: max（待最终审批）
- Revisit trigger/date: max 批准 RCP-v03-003 时转 approved；WP-102 实现遇架构问题提修改。

#### 批准 RCP-v03-003（2026-08-05）

- Decision ID: RCP-v03-003-approval
- Date: 2026-08-05
- Decision: 批准 RCP-v03-003（proposed → approved）。新实体 Schema 与永久 ID 体系生效：5 个 Phase 0-1 实体（Sector/Security/Product/Technology/Metric）Schema 字段、14 新前缀 + parser 歧义处理 D1–D7、schema_version=2 启用（v0.2 保持 1 无损读取）、Company v0.3 扩展 optional 不回填（R1）、Company 与 Security 分离（security_ids 引用）、Migration 顺序 MIG-001→WP-102→002→003、禁用单段 `MOD-` 作 Model 前缀。
- Reason: 7 项人审点经 max 逐项确认采纳默认；A-005/006/007 与 Taxonomy v2/R1–R5/地区约束一致。
- Effective date: 2026-08-05（MIG-v0.3-001 注册 Schema 由 WP-102 起落地）。
- Consequences: Metadata_Schema_v0.3_Proposal 转 authoritative；v0.2 Metadata_Schema 仍存作历史参考；WP-102 起进入代码实现（Pydantic schemas + validator + ID parser + index + migration）。不创建任何实体（实体创建属后续 WP-120，需人工席位审）。
- Reviewer: max
- Revisit trigger/date: WP-102 实现遇架构问题；任一新实体 Schema 字段实施遇阻时提修改 RCP。

#### D-CALENDAR-DECOUPLE 开发进度与日历解耦（2026-08-07）

- Decision ID: D-CALENDAR-DECOUPLE
- Date: 2026-08-07
- Question: 开发进度是否应被具体时间/日期阻塞（Pilot Day 14 = 2026-08-20、v0.2 Weekly/Monthly cadence、RCP 排期"到点"）？
- Options considered: A) 维持日历门（到期再判定，日期即阻塞）；B) 门改以状态与证据判定，日期仅作记录（推荐）；C) 完全无门。
- Decision: 采用 B。进度门改以依赖就绪与证据质量判定，日期不再作为阻塞条件：
  1. **B-026 / WP-240 Pilot 验收**：触发从"Day 14（2026-08-20）"改为"G1–G10 全部满足 + 稳定性证据达最小连续干净轮次"（`Phase_Acceptance_B026.md` §触发条件）。全部满足即可随时验收，含早于 2026-08-20。
  2. **WP-001 v0.2 发布决定**：不再以 Weekly/Monthly 日期为阻塞；release check 达成 18/18 即进入最终发布决定。cadence 记录仍按真实工作产出，但发布判定看状态不看日历。
  3. **RCP-v03-006~010 排期（D9 的"对应阶段开始前"）**：以依赖就绪/前置 Gate 达成为触发，不由日历日期决定。
  4. **真时间依赖保留**：仅 WP-530 预测自然到期解析（E-022~023）保持真实时间依赖，不得用回填或合成 outcome 提前完成——该依赖是观测真实世界结果，与本决定不冲突。
  5. **后继阶段**：Phase 3–6 及未来 Pilot 的验收 Gate 沿用同一"状态触发"语义，在其规划时明确，不再写固定日期。
- Reason: 进度应由依赖就绪与证据质量决定；固定日期会不必要地阻塞已完成工程的状态推进（Phase 2 全部工程 WP completed 却卡 8-20）。稳定性证据以"轮次"而非"自然日"计量，观察强度不降。
- Evidence/benchmark: Phase 2 工程 WP（200/201/210/220/230/231/232）全部 completed；B-026 Day-2 已 G1/G6/G7 达成（20/20 channels、96/20 promoted）。
- Consequences: 本决定取代 Roadmap §4 Phase 2 Gate"连续 14 天稳定运行"与 §9 相关日期语义；B-026 验收可早于 8-20；WP-001 解日期阻塞。实施载体为 `Phase_Acceptance_B026.md` §触发条件。
- Migration: 无数据迁移；仅 Gate 触发语义变更。
- Rollback: 撤销本条即恢复日历门（不涉及数据）。
- Reviewer: max
- Revisit trigger/date: 任一 Gate 触发条件实施遇阻，或研究者认为稳定性证据强度不足时复核。

#### 批准 RCP-v03-006（2026-08-07）

- Decision ID: RCP-v03-006-approval
- Date: 2026-08-07
- Decision: 批准 RCP-v03-006（proposed → approved）。Impact Assertion 语义与传播边界生效：`IMP-YYYYMMDD-NNN` 正式对象类型、`RELATED_TO` ≠ impact、公司经营影响与证券价格影响分离（Phase 3 默认不生成 Security/valuation 价格方向）、仅 reviewed Event 生成权威 Impact（pending → experimental）、多跳传播约束（depth 3 / fan-out 10 / as-of 有效关系 / 正负不静默合并 / 路径默认 pending）、weakest-link confidence policy。
- Reason: 6 项人审点经 max 逐项确认采纳默认；与 Phase 3 §2/§3/§5/§6/§11 一致；前置满足（Phase 2 已积累 48 个 reviewed Event）。
- Effective date: 2026-08-07（批准即生效；WP-300 起落地实施）。
- Consequences: Phase 3 解除 RCP-v03-006 阻塞；WP-300（C-001～003）转 ready，待 WP-300 规划；Roadmap §9"Impact 关系类型与强度语义"决策点已落实。
- Reviewer: max
- Revisit trigger/date: WP-300 实施遇架构问题；任一 Impact 语义字段实施遇阻时提修改 RCP。

C-018 Gate 判定（2026-08-08，agent 判定建议，待 max 拍板）：15 事件样本 **有条件通过**——可测量硬阈值 3/3 达标（direct precision 93.3%、mechanism 锚定 100%、horizon 100%）；direction 86.7%（EVT-047 过度提案 / EVT-044 逐 target 价格 2 事件待人工修正）；contrary 已修复（C-004 从事件 Facts 自动提取 countervailing_factors：EVT-047 竞争-客户二重性、EVT-039 Azure 效率抵消，反面遗漏 0）；direction 87%（EVT-047/044 待 max 人工修正）；regulation 桶 0/2 为数据缺口。**多跳维持 inactive**（Phase 3 §12 治理门），待 max 复核判断初稿 + 修复 contrary + 补事件至 20 + 全绿后拍板放行。判定包：`05_Research/Reviews/Field_Gate_20_Impact_Packet.md`。

C-018 APPROVED（2026-08-08，max 拍板）：14 个 in-scope 事件五维全部通过（direct precision 100%、mechanism 锚定 100%、direction 100%、horizon 100%、contrary 0）；EVT-046（Baidu DeepSeek-V4）按 max 决定剔除出样本（第二 Pilot 模型-平台-企业范围）。**多跳（2-3 hop）已激活（2026-08-08 max 放行，`expand_impact_paths` 默认 max_depth 1→3）**。判定包：`05_Research/Reviews/Field_Gate_20_Impact_Packet.md`；判断初稿 `Field_Gate_20_Impact_Judgments.json`。

数据补充评估（2026-08-08，agent）：样本 14/20、regulation 桶 0/2、pricing/capex 桶缺口。
- **候选库 0 条** pricing/capex/regulation 候选（SEC/arXiv/GitHub/skhynix 通道未产出算力链价格/监管内容）。
- **pricing**：agent 软件定价源（Salesforce/Cursor/GitHub Copilot 定价 SRC-20260729-003/021/024）属第二 Pilot 范围，非算力链。算力链定价（DRAM ASP、GPU 定价）仅 TrendForce EVT-044。
- **capex**：hyperscaler capex（Microsoft FY26 10-Q 的 AI 基建投资）已含于 EVT-039/040，可拆独立 capex 事件但重叠。
- **regulation**：无任何监管源/候选——需**新采集通道**（如出口管制/芯片法规新闻源）或手工 capture，不能编造。
- **结论**：补满 20 需 (a) 建监管采集通道 + (b) 从现有 SEC 源建 capex/pricing 事件（人工 review）。**建议列为 WP-240 之后的采集扩展项**，C-018 判定不受其阻塞（硬阈值已达标）。

#### 批准 RCP-v03-007（2026-08-08）

- Decision ID: RCP-v03-007-approval
- Date: 2026-08-08
- Decision: 批准 RCP-v03-007（proposed → approved）。Analysis Mode Framework 生效：`analysis_mode`（MOD-ANL-<slug>-vN）与 `analysis_run`（ANL-YYYYMMDD-NNN）正式对象类型；模式版本化契约；Run 冻结输入/模式/模型/参数/输出；Run ≠ Thesis/Recommendation（仅 reviewed run 进 Report）；Open Discovery 只产候选 Hypothesis；首批 9 模式。
- Reason: 6 项人审点经 max 逐项确认采纳默认；与 Phase 4 §1-§4 一致。
- Effective date: 2026-08-08（WP-400 起落地）。
- Consequences: Phase 4 解除 RCP 阻塞；WP-400（D-001~004）转 ready。
- Reviewer: max
- Revisit trigger/date: WP-400 实施遇架构问题；任一模式契约字段实施遇阻时提修改 RCP。

#### 批准 RCP-v03-010（2026-08-09）

- Decision ID: RCP-v03-010-approval
- Date: 2026-08-09
- Decision: 批准 RCP-v03-010（proposed → approved）。Phase 6（统一产品与发布）治理生效：Dashboard 保持只读+loopback、权威写入走 CLI+Markdown+dry-run/`--apply`、Web mutation（浏览器写权威对象）必须另行批准（现有 3 个 `/llm` 本地配置端点追认为唯一例外）；Product IA v2 作为基线（F-001 spec 走常规 WP 验收）；30-day Pilot 范围固定（Core 按 D4 上限 54）；v0.3 Release Gate 机器可验证 + 人工 packet，**显式记录发布被 WP-530 自然到期阻塞（最早 2026-10-31），工程/产品完成与发布两条时间线分离**；PostgreSQL/图/向量仅按实测瓶颈触发；备份/安全/许可/cost 预算入 Health。
- Reason: 6 项人审点经 max 逐项确认采纳默认；与 Phase 6 §1-§2、§6-§8、§10-§11 一致；防 UI 绕过 CLI 审计链路、保持唯一真时间依赖诚实。
- Effective date: 2026-08-09（WP-600 起落地）。
- Consequences: Phase 6 解除 RCP 阻塞；Wave 6（WP-600 起）转 ready。
- Reviewer: max
- Revisit trigger/date: WP-600 实施遇架构问题；发布 Gate 需调整时间依赖时提修改 RCP。
