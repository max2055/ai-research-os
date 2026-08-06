# Field Gate §9.3 — 10 Core Company 人工核验包

状态：`passed`（max 2026-08-06 全部 approve；REV-20260806-054..063）
日期：2026-08-06
范围：Phase 0-1 A-019 / Field Gate §9.3「10 家 Core Company 身份、证券、板块和来源人工核验」

## 核验四要素

- **身份**：legal_name / aliases / headquarters / region_primary / company_stage
- **证券**：security_ids 挂接的 INS-* 实体（Company 与 Security 分离，RCP-v03-003）
- **板块**：sector_ids 归属
- **来源**：evidence_ids 引用的 reviewed Events 支撑（source_channel_ids 因类型未实现留空，记 Known_Limitation）

## Company 审核表

| Company | 身份 | 证券 | 板块 | 来源（reviewed Events） | Decision |
|---|---|---|---|---|---|
| COM-nvidia | NVIDIA Corp, Santa Clara CA, REG-us, public | INS-NASDAQ-NVDA | SEG-compute-silicon | 9（含 EVT-040/042/048/10-K 链）| ⬜ |
| COM-tsmc | Taiwan Semiconductor, Hsinchu, REG-tw, public | INS-TWSE-2330 + INS-NYSE-TSM (ADR) | SEG-foundry-packaging-test | 4（含 EVT-037 TSMC 2Q26）| ⬜ |
| COM-sk-hynix | SK hynix Inc, Icheon, REG-kr, public | INS-KRX-000660 | SEG-memory-storage | 4（含 EVT-035 NVIDIA 合作）| ⬜ |
| COM-samsung-electronics | Samsung Electronics, Suwon, REG-kr, public | INS-KRX-005930 | SEG-memory-storage | 2（EVT-042 HBM4 + EVT-044）| ⬜ |
| COM-micron | Micron Technology, Boise ID, REG-us, public | INS-NASDAQ-MU | SEG-memory-storage | 2（EVT-043 HBM3E + EVT-044）| ⬜ |
| COM-aws | Amazon subsidiary, Seattle, REG-us, subsidiary | INS-NASDAQ-AMZN (parent) | SEG-cloud-ai-infrastructure | 2（EVT-040 $100B + EVT-047）| ⬜ |
| COM-microsoft | Microsoft Corp, Redmond WA, REG-us, public | INS-NASDAQ-MSFT | SEG-cloud-ai-infrastructure + SEG-enterprise-applications | 6（EVT-039/041/047 等）| ⬜ |
| COM-coreweave | CoreWeave Inc, Roseland NJ, REG-us, public | INS-NASDAQ-CRWV | SEG-cloud-ai-infrastructure | 3（EVT-041/047/048）| ⬜ |
| COM-openai | OpenAI Inc, San Francisco, REG-us, private | 无证券（私企）| SEG-models + SEG-cloud-ai-infrastructure | 5（EVT-040/041/039 等）| ⬜ |
| COM-meta | Meta Platforms, Menlo Park, REG-us, public | INS-NASDAQ-META | SEG-models | 2（EVT-041 Meta $14.2B + EVT-039）| ⬜ |

## 核验记录

### 身份（2026-08-06 Agent 核验）

- 全部 10 家 legal_name / headquarters / region / stage 已核对，与公开事实一致。
- v0.2 老 8 家（MSFT/OpenAI 等）已补身份字段（legal_name/HQ/stage），保持 schema_version=1。
- 51 家 v0.3 Company 身份字段 WP-120 已核（identity complete 51/59）。

### 证券（2026-08-06 新建）

- 新建 10 个 INS-* 实体并 reviewed（REV-044..053）：
  NVDA / TWSE-2330 / NYSE-TSM(ADR) / KRX-000660 / KRX-005930 / MU / MSFT / CRWV / META / AMZN(parent)。
- TSMC 双上市地（TWSE + NYSE ADR）体现 Company 与 Security 分离。
- AWS 为 Amazon 子公司，挂 parent 证券 AMZN（无独立上市）。
- OpenAI 为私有公司，无证券（符合 RCP-v03-003 私有公司处理）。

### 板块（WP-120 已核验，passed）

- 9 Sector + 51 Company 板块归属 WP-120 packet 已全部 approve。
- 本轮 10 家板块归属复核一致（compute-silicon / memory-storage / foundry / cloud-ai / models）。

### 来源（evidence 支撑）

- 全部 10 家有 ≥2 个 reviewed Events 支撑（NVIDIA 9、Microsoft 6、OpenAI 5、TSMC 4 等）。
- source_channel_ids 因 `source_channel` 类型未实现（RCP-v03-003 仅 ID 占位）留空，
  记入 Known_Limitation，待后续 RCP 实现后补登记。

## 批量审核快捷方式

- 回复「**全部 approve**」：10 家 Company 四要素核验通过。
- 逐项指出修改项（如 `COM-xxx 板块改 ...`）。

## 完成标准

- 全部 10 家有明确 human decision（approve/edit/reject）。
- approve 的 Company 维持 reviewed（已 reviewed），REV 决策落盘记录核验结论。
- 未 approve 的标记待改。

## Review command

```bash
research-os review apply --targets <COM-ID> --decision approve --reviewer max \
  --notes "Field Gate §9.3 身份/证券/板块/来源核验通过"
```
