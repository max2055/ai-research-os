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
| customer-demand | 3 | 2 |
| financial-capex | 2 | 1 |
| competition | 2 | 1 |
| regulation-other | 2 | 0 |

## 事件审核表

每事件逐项审计五列：target 精度 / mechanism 支撑 / direction 合理 / horizon 合理 /
重大反面路径遗漏。

| Event | 桶 | 事件 | 建议 direct impact（C-004 提案）| Decision |
|---|---|---|---|---|
| EVT-20240226-043 | supply-capacity | Micron: HBM3E volume production will be part of NVIDIA H200 Tensor Core GPUs | COM-micron supply (mixed); COM-micron capacity (positive); COM-nvidia supply (mixed) | ⬜ |
| EVT-20260225-034 | product-technology | ASML 20-F describes EUV 0.33/0.55 NA lithography platforms | COM-asml supply (mixed); COM-asml technology (positive); COM-tsmc supply (mixed); COM-tsmc technology (positive) | ⬜ |
| EVT-20260302-041 | customer-demand | CoreWeave 10-K FY2025: OpenAI $6.5B+$11.9B and Meta $14.2B committed contracts named | COM-coreweave supply (mixed); COM-coreweave supply (mixed); COM-coreweave demand (positive); COM-coreweave demand (positive); COM-coreweave capacity (positive); COM-meta supply (mixed); COM-meta demand (positive); COM-openai supply (mixed); COM-openai demand (positive) | ⬜ |
| EVT-20260302-047 | competition | CoreWeave 10-K: names AWS, Google Cloud, Microsoft Azure, Oracle as key cloud competitors | COM-aws competition (mixed); COM-aws competition (mixed); COM-google-cloud competition (mixed); COM-google-cloud competition (mixed); COM-microsoft competition (mixed); COM-microsoft competition (mixed) | ⬜ |
| EVT-20260302-048 | supply-capacity | CoreWeave 10-K: deploys NVIDIA GB200/GB300 NVL72, among first to deploy NVIDIA Rubin platform | COM-coreweave supply (mixed); COM-coreweave capacity (positive); COM-nvidia supply (mixed) | ⬜ |
| EVT-20260316-042 | supply-capacity | Samsung: HBM4 in mass production designed for NVIDIA Vera Rubin platform (GTC 2026) | COM-nvidia supply (mixed); COM-samsung-electronics supply (mixed); COM-samsung-electronics capacity (positive) | ⬜ |
| EVT-20260416-033 | supply-capacity | TSMC discloses advanced 2nm process and CoWoS packaging for AI accelerators | COM-nvidia supply (mixed); COM-nvidia supply (mixed); COM-tsmc supply (mixed); COM-tsmc supply (mixed) | ⬜ |
| EVT-20260429-039 | customer-demand | Microsoft FY26 Q3: Azure growth with continued AI infrastructure investment | COM-microsoft supply (mixed); COM-microsoft supply (mixed); COM-microsoft supply (mixed); COM-microsoft supply (mixed); COM-microsoft technology (positive); COM-microsoft technology (positive); COM-microsoft demand (positive); COM-microsoft capacity (positive); COM-openai supply (mixed); COM-openai technology (positive); COM-openai technology (positive); COM-openai demand (positive) | ⬜ |
| EVT-20260429-046 | supply-capacity | 百度千帆 Day 0 适配提供 DeepSeek-V4 预览版 API 服务（2026-04-29） | COM-baidu-cloud supply (mixed); COM-deepseek supply (mixed) | ⬜ |
| EVT-20260601-044 | pricing | TrendForce 1Q26 DRAM: Samsung 38.5%, SK hynix 28.8%, Micron 22.4% market share; SK hynix highest HBM bit shipment ratio | COM-micron competition (mixed); COM-micron competition (mixed); COM-samsung-electronics competition (mixed); COM-samsung-electronics competition (mixed); COM-sk-hynix competition (mixed); COM-sk-hynix competition (mixed) | ⬜ |
| EVT-20260610-007 | financial-capex | Oracle AI 基础设施增长伴随高资本开支，云应用增速较低 | — | ⬜ |
| EVT-20260731-040 | product-technology | AWS and OpenAI expand $38B commitment by $100B over 8 years (AWS chips) | COM-aws supply (mixed); COM-aws technology (positive); COM-aws demand (positive); COM-aws capacity (positive); COM-openai supply (mixed); COM-openai technology (positive); COM-openai demand (positive) | ⬜ |

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


## 判断初稿与指标（2026-08-07，agent 撰写，待 max 复核）

来源：`Field_Gate_20_Impact_Judgments.json`（12 事件逐条 5 维审计）。

| 指标 | 值 | §11 阈值 | 通过 |
|---|---|---|---|
| 直接影响 precision | 91.7% | ≥85% | ✅ |
| mechanism 无来源外事实 | 100% | ≥95% | ✅ |
| direction 合理 | 50% | — | ⚠️ |
| horizon 合理 | 66.7% | — | ⚠️ |
| 重大反面路径遗漏 | 2 | 0 | ❌ |

### 关键结论（agent 分析）

1. **target 选择与证据锚定是可靠的**（两项硬阈值通过）：C-004 的提案 target 正确、机制不编造来源外事实。
2. **direction 默认「mixed」系统性过度使用**：多数 supply 事件实际方向明确（HBM3E/HBM4 量产 = positive、HBM 合约价下滑 = negative），规则映射默认 mixed 丢失事件真实正负。
3. **缺维度**：EVT-039 头部事实是毛利率降至 66%（缺 margin/negative）；EVT-033 缺 technology（2nm）；EVT-044 缺 price（已手工补）；EVT-007 缺 capex（已手工补）；EVT-038 缺 revenue（已手工补）。
4. **缺反证/背景**：EVT-047 竞争对手同时是客户、EVT-039 Azure 效率提升部分抵消——提案未体现。
5. **冗余**：多 REL 产生重复提案（EVT-039 12 条、EVT-041 9 条），样本膨胀。
6. **补桶**：pricing 1/3、financial-capex 1/2 已用手工 draft IMP 填（IMP-005..009，evidence 锚定）；regulation 桶为真实数据缺口（无监管事件源）。

### 结论

C-018 Gate 可判定为：**部分通过**——precision 与机制锚定达标，但方向/反证需人工修正后才满足 §11；regulation 桶需补真实监管事件。多跳（2-3 hop）仍按治理门保持 inactive，待本 Gate 完整通过后由 max 放行。
