# C-018 Field Gate — 20 真实事件人工影响路径核验包

状态：`in_progress`（max 判定；阈值见 Phase 3 §11）
日期：2026-08-07
范围：Phase 3 C-018「20 个真实事件的人工影响路径 Gate」

## 样本组成（§11）

| 桶 | 配额 | 已分配 |
|---|---|---|
| supply-capacity | 5 | 5 |
| pricing | 3 | 1 |
| product-technology | 3 | 2 |
| customer-demand | 3 | 3 |
| financial-capex | 2 | 1 |
| competition | 2 | 2 |
| regulation-other | 2 | 0 |

## 事件审核表

每事件逐项审计五列：target 精度 / mechanism 支撑 / direction 合理 / horizon 合理 /
重大反面路径遗漏。

| Event | 桶 | 事件 | 建议 direct impact（C-004 提案）| Decision |
|---|---|---|---|---|
| EVT-20240226-043 | supply-capacity | Micron: HBM3E volume production will be part of NVIDIA H200 Tensor Core GPUs | COM-micron capacity (positive); COM-micron supply (positive); COM-micron technology (positive); COM-nvidia capacity (positive); COM-nvidia supply (positive) | ⬜ |
| EVT-20260225-034 | customer-demand | ASML 20-F describes EUV 0.33/0.55 NA lithography platforms | COM-asml capacity (positive); COM-asml demand (positive); COM-asml supply (mixed); COM-asml technology (positive); COM-tsmc capacity (positive); COM-tsmc demand (positive); COM-tsmc supply (mixed); COM-tsmc technology (positive) | ⬜ |
| EVT-20260302-041 | product-technology | CoreWeave 10-K FY2025: OpenAI $6.5B+$11.9B and Meta $14.2B committed contracts named | COM-coreweave capacity (positive); COM-coreweave demand (positive); COM-coreweave revenue (positive); COM-coreweave supply (positive); COM-coreweave technology (positive); COM-meta capacity (positive); COM-meta demand (positive); COM-meta revenue (positive); COM-meta supply (positive); COM-openai capacity (positive); COM-openai demand (positive); COM-openai revenue (positive); COM-openai supply (positive) | ⬜ |
| EVT-20260302-047 | competition | CoreWeave 10-K: names AWS, Google Cloud, Microsoft Azure, Oracle as key cloud competitors | COM-aws competition (mixed); COM-aws price (negative); COM-aws revenue (negative); COM-google-cloud competition (mixed); COM-google-cloud price (negative); COM-google-cloud revenue (negative); COM-microsoft competition (mixed); COM-microsoft price (negative); COM-microsoft revenue (negative) | ⬜ |
| EVT-20260302-048 | supply-capacity | CoreWeave 10-K: deploys NVIDIA GB200/GB300 NVL72, among first to deploy NVIDIA Rubin platform | COM-coreweave capacity (positive); COM-coreweave supply (positive); COM-coreweave technology (positive); COM-nvidia supply (positive) | ⬜ |
| EVT-20260316-042 | product-technology | Samsung: HBM4 in mass production designed for NVIDIA Vera Rubin platform (GTC 2026) | COM-nvidia capacity (positive); COM-nvidia supply (positive); COM-samsung-electronics capacity (positive); COM-samsung-electronics supply (positive); COM-samsung-electronics technology (positive) | ⬜ |
| EVT-20260416-033 | supply-capacity | TSMC discloses advanced 2nm process and CoWoS packaging for AI accelerators | COM-nvidia capacity (positive); COM-nvidia supply (mixed); COM-tsmc capacity (positive); COM-tsmc supply (mixed) | ⬜ |
| EVT-20260429-039 | customer-demand | Microsoft FY26 Q3: Azure growth with continued AI infrastructure investment | COM-microsoft capacity (positive); COM-microsoft demand (positive); COM-microsoft supply (positive); COM-microsoft technology (positive); COM-openai capacity (positive); COM-openai demand (positive); COM-openai supply (positive); COM-openai technology (positive) | ⬜ |
| EVT-20260429-046 | pricing | 百度千帆 Day 0 适配提供 DeepSeek-V4 预览版 API 服务（2026-04-29） | COM-baidu-cloud capacity (positive); COM-baidu-cloud price (mixed); COM-baidu-cloud supply (mixed); COM-deepseek capacity (positive); COM-deepseek price (mixed); COM-deepseek supply (mixed) | ⬜ |
| EVT-20260520-032 | supply-capacity | NVIDIA discloses long lead times and capacity commitments in AI supply chain | COM-nvidia supply (mixed); COM-sk-hynix supply (mixed); COM-tsmc supply (mixed) | ⬜ |
| EVT-20260520-038 | supply-capacity | NVIDIA FY27 Q1: record Data Center revenue $75.2B, $119B supply commitments | COM-dell capacity (positive); COM-dell supply (positive); COM-nvidia capacity (positive); COM-nvidia supply (positive); COM-supermicro capacity (positive); COM-supermicro supply (positive) | ⬜ |
| EVT-20260601-044 | competition | TrendForce 1Q26 DRAM: Samsung 38.5%, SK hynix 28.8%, Micron 22.4% market share; SK hynix highest HBM bit shipment ratio | COM-micron competition (mixed); COM-micron price (negative); COM-micron revenue (negative); COM-samsung-electronics competition (mixed); COM-samsung-electronics price (negative); COM-samsung-electronics revenue (negative); COM-sk-hynix competition (mixed); COM-sk-hynix price (negative); COM-sk-hynix revenue (negative) | ⬜ |
| EVT-20260610-007 | financial-capex | Oracle AI 基础设施增长伴随高资本开支，云应用增速较低 | — | ⬜ |
| EVT-20260731-040 | customer-demand | AWS and OpenAI expand $38B commitment by $100B over 8 years (AWS chips) | COM-aws capacity (positive); COM-aws demand (positive); COM-aws supply (positive); COM-aws technology (positive); COM-openai capacity (positive); COM-openai demand (positive); COM-openai supply (positive); COM-openai technology (positive) | ⬜ |

## 阈值（§11）

- 直接影响 precision ≥ 85%
- mechanism 无来源外事实 ≥ 95%
- 二跳路径人工保留率 ≥ 60%
- 三跳只作探索，不设高权威阈值
- 所有重大反面路径遗漏必须修复后通过
- 未知项不得被强制赋方向或强度

## 批量审核快捷方式

- 回复「**全部 approve**」：20 事件全部 target/mechanism/direction/horizon 通过。
- 逐项指出修改项（如 `EVT-xxx target 改 ...`）。


## 判断初稿与指标（2026-08-07 刷新，agent 撰写，待 max 复核）

来源：`Field_Gate_20_Impact_Judgments.json`（15 事件逐条 5 维审计，C-004 改进后刷新）。

| 指标 | 值 | §11 阈值 | 通过 |
|---|---|---|---|
| 直接影响 precision | 93.3% | ≥85% | ✅ |
| mechanism 无来源外事实 | 100.0% | ≥95% | ✅ |
| direction 合理 | 80.0% | — | ⚠️ |
| horizon 合理 | 100.0% | — | ⚠️ |
| 重大反面路径遗漏 | 2 | 0 | ❌ |

样本组成缺口：pricing: 1/3; product-technology: 2/3; financial-capex: 1/2; regulation-other: 0/2

### 关键结论（agent 分析，C-004 改进后）

1. **维度补全生效**：全类型提案让 price/margin/revenue/cost 浮出（定价桶 3/3 满），direction 内容推断对干净事件（HBM3E/HBM4 量产、NVIDIA 创纪录营收）修正为 positive。
2. **方向推断误伤**：10-K 风险因素正文的负面词污染 valence（EVT-048 cost/negative、EVT-046 negative）；mixed 信号事件（EVT-032 长交期）推断错误；EVT-044 逐 target 价格方向（三星+ / SK hynix−）事件级推断仍丢失（手工 IMP-005/006 已正确处理）。
3. **仍缺维度**：EVT-039 毛利率下滑（margin）无 REL 映射到 margin，全 positive 提案掩盖了头部事实。
4. **过度提案**：EVT-047 仅"点名竞争者"却产出 margin/price/revenue 负向提案——不证据支撑。
5. **桶分类伪影**：EVT-033（2nm）、EVT-038（营收）按提案类型归入 pricing，实际是 product-technology/financial——gate_sample 按提案 impact_type 分桶的局限。

### 结论

C-018 可判定为：**precision 与机制锚定达标**（两项硬阈值），direction/contrary 仍须人工修正；regulation 桶为真实数据缺口。多跳保持 inactive，待完整 Gate 通过后由 max 放行。
