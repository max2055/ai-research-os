# 证据 WP Handoff — Compute Chain 真实证据 + 关系 approve（22/30）

Handoff ID：HOF-20260805-EVWP
日期：2026-08-05
发送人：Claude（Agent）
接收人：max（研究者）
Project ID：PRJ-001 / PRJ-002（Universe 为跨项目基元）

## Scope

按 `08_Agent_Execution_Protocol` 工作包输入合同，证据 WP 范围 = 为 Compute
Chain 关系（REL-*）采集真实公开证据（Source + Event），人审 approve 关系，
完成 Phase 0-1 Gate 的"30 条人审"子项。本 WP 达成 **22/30**。

范围决定（reviewer：max，2026-08-05）：
- 公开来源（SEC 10-Q/20-F + exhibits、官方 IR 公告）
- Event 级人审 + 关系级 approve（引用 reviewed Evidence）
- Agent 审核 + max 授权模式（判断 Agent、批准人）

## Rules and templates read

- `AGENTS.md`、`README.md`、`00_System/Research_Rules.md`、`Source_Policy.md`
- `00_System/v0.3_.../02_Phase_0_1_...md`（§5 关系约束、§7 A-017/019）、
  `08_Agent_Execution_Protocol.md`
- `07_Templates/Research_Handoff.md`

## Objects created or changed

| Object | Action | Path | Review status |
|---|---|---|---|
| 10 × Source（SRC-20260805-040..050） | 新增 | `01_Inbox/Earnings|Articles/` | **reviewed**（全） |
| 10 × Event（EVT-20260520-032..20260731-040） | 新增 | `04_Evidence/Events/` | **reviewed**（全） |
| 22 × 关系 approve（REL-*） | 状态流转 | `05_Research/Assertions/` | reviewed |
| 9 × 关系标记证据不足 | 打回 | `05_Research/Assertions/` | pending |
| 36 × REV 决策（REV-20260805-00X..036） | 新增 | `05_Research/Reviews/Decisions/` | applied |
| `--user-agent` / `--max-bytes` | 代码 | `src/research_os/cli.py`、`adapters/url.py` | — |
| REVIEWABLE_TYPES +ontology_assertion | 代码 | `services/reviews.py` | — |

## Sources used

- 真实公开来源（SEC EDGAR + 官方 IR）：
  - NVIDIA 10-Q FY26 Q1（SRC-040）、NVIDIA FY27 Q1 CFO 注释 exhibit（SRC-048）
  - TSMC 20-F 2025（SRC-041）、TSMC 2Q26 财报 exhibit（SRC-047）
  - ASML 20-F 2025（SRC-042，50MB 上限扩展）
  - SK hynix IR：NVIDIA 合作（SRC-043）、2Q26 财报（SRC-044）、FMS HBF（SRC-046）
  - Microsoft 10-Q FY26 Q3（SRC-049）、Amazon 10-Q Q2 2026（SRC-050）

## Facts established

- **22 条关系 approved**（Gate 30 的 22/30），证据质量分层：
  - **直接证据（0.7-0.8）**：AWS-OpenAI $100B 合同（EVT-040）、SK hynix-NVIDIA
    HBM 合作（EVT-035）
  - **硬数据间接（0.5）**：TSMC 先进制程 77% 收入（EVT-037）、NVIDIA 数据中心
    $75.2B（EVT-038）、微软 Azure AI 基建（EVT-039）
  - **间接（0.3-0.4）**：SEC 财报推断链
- **9 条打回**（来源未点名对方，标记 evidence-insufficient）
- 验证的采集路径：SEC index.json 找 exhibit URL（TSMC/ NVIDIA 财报附件）、
  官方 IR RSS（SK hynix）、SEC 10-Q/20-F

## Inferences proposed

- **Agent 审核 + 人授权模式**：Agent 做证据链分析（来源是否点名、推断链长度）
  并给出差异化判断，max 授权 approve——判断 Agent、批准人，符合治理。
- 8 条打回关系（微软/AWS ENABLES Anthropic/Meta/xAI 等）需点名式来源
  （三星/美光/阿里云）后重审。

## Conflicts and unknowns

- 无冲突。validate 0 error；index 无 drift；测试全绿。
- **Gate 未完全达成**：22/30（剩 8 条需新采集）。
- 空壳 8-K/6-K（44/39 行封面）采集后删除——SEC 主文件常是封面，实质在
  exhibit（index.json 路径已验证）。

## Human decisions required

- **Gate 30 剩余 8 条**：待下一 WP 采三星/美光/阿里云点名式来源后重审。
- 打回 9 条关系的重审时机：证据到位后。

## Verification

- Validate：0 errors / 0 warnings（对象 58+：10 source、10 event、36 review）
- Index check：global + PRJ-001 + PRJ-002 全 PASS
- Tests：119 passed；coverage ≥80%；ruff / mypy：pass
- 证据完整性：10 Source hash 验证、10 Event citation anchors 逐条可解析

## Recommended next action

- **Gate 30 冲刺 WP**：定向采三星/美光（HBM COMPETES_WITH）+ 阿里云/字节
  （云 SUPPLIES 模型）点名式来源 → 补 8 条 approve → Gate 30 达成
- 或 WP-122（Universe coverage 指标 + 真实抽检）
- 或 Phase 0-1 验收（A-020，clean-clone + migration rollback 演练）
