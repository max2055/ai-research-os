# Taxonomy v2 提案（A-003）

状态：`proposed / pending RCP-v03-002 approval`
创建日期：2026-08-05
工作包：WP-100 / A-003（提案草稿，不修改任何规则或对象）
依赖：`Taxonomy_v2_Mapping.md`（A-002 审计）、`02_Phase_0_1_Ontology_and_Universe.md` §3
reviewer（待）：max（按 D9，Wave 1）

> 本文件是 Taxonomy v2 **提案草稿**，不是已生效的 Taxonomy。
> 按 Taxonomy §5，新增一级/二级分类、修改现有含义、合并或废弃稳定标签、改变历史
> 对象使用的标签，均需 RCP-v03-002 人工批准。本提案不改动任何 v0.2 对象。

## 1. v2 设计原则

1. **Taxonomy 表达稳定分类，Ontology 表达实体关系**（沿用 v0.1 §1）。
2. **产业归属从扁平 tag 迁移到 Sector 实体（SEG-ID）**：v0.1 用 INF-GPU/APP-CRM 等扁平 tag 表达产业细分；v2 用 Sector + Technology/Product 实体表达，扁平产业 tag 多数退役为实体引用（见 Mapping §4.1）。
3. **横向维度继续使用并扩展**（Phase 0-1 §3）：MAT/CUS/BM/MOAT/EV 全部 keep，并补齐 v0.1 未定义的项。
4. **历史对象 tag 不自动改写**：v1→v2 从 mapping 表推导，历史对象保留旧 tag + 映射，回填需人工批（Taxonomy §5）。
5. **每一级分类有定义、边界、示例、冲突项**（本文件 §3/§4）。

## 2. 一级扇区（13 个 Sector，作 SEG-ID 实体）

> Sector 是正式实体（`SEG-<slug>`，依 D6），不是 tag。下表给定义、边界、示例、与 v0.1 tag 的映射。

| Sector | 定义 | 边界（in/out） | 示例 | v0.1 tag 映射 |
|---|---|---|---|---|
| Semiconductor Materials & Equipment | 晶圆材料、光刻、气体、EDA、量测 | in: 材料/设备；out: 制造代工 | ASML、信越、EDA | INF-*（材料范畴，v0.1 未细分） |
| Foundry, Packaging & Test | 晶圆代工、先进封装、OSAT、基板 | in: 制造；out: 设计 | TSMC、ASE | INF-DATACENTER（误）；新增 |
| Compute Silicon | GPU、AI ASIC、CPU、边缘加速 | in: 算力芯片；out: 内存/网络 | NVIDIA、AMD、Groq | INF-GPU/ASIC/CPU/EDGE → map |
| Memory & Storage | HBM、DRAM、NAND、企业存储 | in: 存储；out: 算力 | SK hynix、Micron | INF-HBM/DRAM/STORAGE → map |
| Server, Network & Interconnect | 服务器、交换、光模块、互连、机架 | in: 节点与互连；out: 芯片/数据中心物理 | Supermicro、Broadcom | INF-SERVER/INTERCONNECT/DATACENTER-NETWORK → map |
| Datacenter Infrastructure | 电力、散热、UPS、能源、建设 | in: 数据中心物理；out: IT 设备 | Vertiv、Eaton | INF-POWER/COOLING/ENERGY → map |
| Cloud & AI Infrastructure | 云计算、模型平台、推理服务 | in: 云；out: 自建模型层 | AWS、Azure、CoreWeave | INF-CLOUD-AI keep；INF-CLOUD/CLOUD-COMPUTE map |
| Models | 基础、推理、多模态、小型/开放、嵌入 | in: 模型本身；out: 训练平台 | OpenAI、Anthropic、Meta | MOD-FOUNDATION/REASONING/... → map |
| Data & AI Development | 数据、训练、推理、评测、安全、Agent 运行时、编排、记忆、工具协议 | in: AI 开发栈；out: 终端应用 | LangChain、Weights & Biases | DEV-* keep；DEV-AGENT-FRAMEWORK/ORCHESTRATION/MEMORY/TOOL-PROTOCOL |
| Enterprise Applications | CRM/ERP/ITSM/HCM/协作/分析/安全/垂直/法律/研究/设计 | in: 企业软件；out: 消费 | Salesforce、SAP、ServiceNow | APP-CRM/ERP/ITSM/... keep；APP-CODING 升格 |
| Consumer Applications | 助理、内容、教育、搜索、商务 | in: 消费者；out: 企业 | OpenAI ChatGPT、Perplexity | APP-ASSISTANT/CONTENT/EDUCATION keep |
| Services | 咨询、集成、托管、数据服务、标注 | in: 服务；out: 软件产品 | Accenture、Scale | SRV-* keep |
| Physical AI | 机器人、自动驾驶、工业/边缘 AI | in: 物理世界 AI；out: 纯软件 | Tesla、Figure | v0.1 未定义；新增 |

### 2.1 第二级示例（沿用 Phase 0-1 §3 表）

每个 L1 Sector 在 SEG 实体的 `in_scope`/`out_of_scope` 中细化子类（不在本文件
穷举），例：

- Semiconductor Materials & Equipment：wafer / photoresist / gas / EDA / lithography / etch / deposition / inspection
- Compute Silicon：GPU / AI ASIC / CPU / edge accelerator
- Memory & Storage：HBM / DRAM / NAND / enterprise storage
- Models：foundation / reasoning / multimodal / small/open / embedding

## 3. 横向维度（v2 keep 并扩展）

沿用 v0.1 §3，全部 keep；扩展项标 **(new)**。

### 3.1 技术成熟度 MAT（keep）
MAT-RESEARCH / PROTOTYPE / PILOT / PRODUCTION / SCALE

### 3.2 客户类型 CUS（keep）
CUS-CONSUMER / SMB / ENTERPRISE / GOVERNMENT / DEVELOPER

### 3.3 商业模式 BM（keep）
BM-SEAT / SUBSCRIPTION / USAGE / TASK / OUTCOME / TRANSACTION / SERVICE
**新增候选 (new)**：BM-INFERENCE-PASS-THROUGH（推理成本穿透）、BM-LICENSE（许可）
—— 需 RCP 定。

### 3.4 竞争优势 MOAT（keep）
MOAT-TECHNOLOGY / DATA / DISTRIBUTION / WORKFLOW / PERMISSION / ECOSYSTEM / SCALE / BRAND / REGULATION

### 3.5 事件类型 EV（keep）
EV-PRODUCT / PRICING / CUSTOMER / PARTNERSHIP / FINANCIAL / MANAGEMENT / TECHNOLOGY / REGULATION / CAPITAL / COMPETITION

### 3.6 横向维度扩展 (new，v0.1 未定义 ID)
Phase 0-1 §3 列出但 v0.1 无 ID，v2 需定：

| 维度 | 用途 | 建议前缀 |
|---|---|---|
| 地区 | 地理归属/敞口 | REG- |
| 供应风险 | 供应链集中/瓶颈 | SUP- |
| 资本强度 | 资本开支密度 | CAP- |
| 周期属性 | 周期/逆周期/成长 | CYC- |
| 监管敏感度 | 监管暴露 | RGT- |

> 前缀已定（reviewer：max，2026-08-05）：REG-/SUP-/CAP-/CYC-/RGT-，5 个全加。
> REG（地区）与 RGT（监管敏感度）易混，Taxonomy 文档须明确备注区分。

## 4. APP-CODING 处理（已定 R1，reviewer：max，2026-08-05）

`APP-CODING`（30 次使用，PRJ-002 主线）v0.1 放在 "知识工作" 子类。v2 决定：

- **keep 为 tag（方案 A）**，归 Enterprise Applications 下 "AI Developer Tooling" 子域；
- v0.1 历史 tag 不变；若 PRJ-002 后续扩展成独立 Pilot 再考虑升级为子扇区。

## 5. 迁移策略（不自动执行，RCP 批准后由 WP-123 落实）

1. **保留阶段**：v0.2 历史 41 个使用的 tag 全部保留，不回填。
2. **映射表生效**：本提案 + Mapping 表经 RCP-v03-002 批准后作为权威映射。
3. **新对象**：v0.3 新对象用 Sector（SEG-ID）+ Technology/Product 实体表达产业归属；横向维度用 keep 的 tag。
4. **回填选项**：是否对历史对象补 Sector 关系，由人工逐批批（Phase 0-1 §11 回滚要求），不自动改。
5. **兼容窗口**：infrastructure 层退役 tag 在至少一个版本周期保留 mapping 兼容（Phase 0-1 §11）。

## 6. 边界项决定（reviewer：max，2026-08-05；原 Mapping §5 待解项）

| # | 问题 | 决定 | 备注 |
|---|---|---|---|
| R1 | APP-CODING 升格 vs 保留 | **keep 为 tag**（方案 A），归 Enterprise Applications 下 AI Developer Tooling 子域 | 见 §4 |
| R2 | MOD-FOUNDATION / MOD-* keep vs map | **全 map 到 Models 扇区下的 Technology 实体**（foundation/reasoning/multimodal/small/embedding） | 与 INF-* 一致走"产业细分由实体表达" |
| R3 | INF-CLOUD-AI 边界 | **归 Sector=Cloud & AI Infrastructure**；边界 = 云端模型平台/推理服务；与 Models（模型本身）、Data & AI Development（训练/评测/Agent 运行时）不重叠 | 唯一在用的 INF 标签 |
| R4 | 横向维度新前缀 | **5 个全加**：REG-(地区)、SUP-(供应风险)、CAP-(资本强度)、CYC-(周期属性)、RGT-(监管敏感度) | REG 与 RGT 易混，在 Taxonomy 文档中明确区分 |
| R5 | INF 父类 deprecate 后历史对象回填 | **不回填，保留旧 tag**；mapping 表提供语义映射；需补 SEG 关系时由人工逐批核（Taxonomy §5 + Phase 0-1 §11） | 不自动改写历史对象 tag |
| R6 | SRV-DATA-LABELING 归属 | （留 RCP-v03-002 现场定，默认归 Services；若与 Data & AI Development 重叠明显再调） | 本轮未触发 |

## 7. 验收（RCP-v03-002 批准门槛）

- [x] 13 个 L1 扇区 SEG-ID 与定义/边界/示例齐备
- [x] v0.1 每个 keep/map/deprecate 决定有理由
- [x] 横向维度扩展前缀不与既有冲突（REG/SUP/CAP/CYC/RGT，REG 与 RGT 已备注区分）
- [x] APP-CODING、MOD-FOUNDATION、INF-CLOUD-AI 三个边界争议有人工决定（R1/R2/R3）
- [x] 历史对象 tag 回填策略被人工批准（R5：不回填，保留旧 tag）
- [ ] 与 `Metadata_Schema_v0.3_Proposal`（A-005/WP-101）的 Sector 实体 Schema 一致（待 WP-101 提案后核对）
- [ ] SRV-DATA-LABELING 归属（R6）现场定
- [ ] RCP-v03-002 最终人工批准（草案已备齐，待 max 审批生效）

## 8. 不做的事

- 不创建 Sector/Technology/Product 实体（需 RCP-v03-003 + WP-102）。
- 不改任何 v0.2 对象 tag。
- 不定义 Impact / Analysis Mode / Forecast 的关系语义（属后续 RCP）。

## 9. 状态

- 本提案 + `Taxonomy_v2_Mapping.md` 共同构成 RCP-v03-002 的证据与草案输入。
- RCP-v03-002 一旦批准，Taxonomy v2 即生效，Sector SEG-ID 命名约定同时由
  RCP-v03-003 的永久 ID 体系落地。