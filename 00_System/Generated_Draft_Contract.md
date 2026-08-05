# Generated Draft Contract

版本：v1.0  
生效日期：2026-07-29  
批准：`RCP-20260729-005`

## 1. 两阶段生成

```text
processed Source
→ structured JSON spec
→ deterministic validation/render
→ pending Event
→ human Review Decision
→ reviewed Evidence
→ deterministic Report synthesis
→ pending Report
→ human Review Decision
→ final Report
```

模型或研究者可以准备 JSON spec；只有确定性 service 可以把 spec 渲染成正式对象。
生成成功不等于事实正确，也不等于审核通过。

## 2. Fact anchor

每个 Fact 使用稳定 `F1...Fn`，并保存：

- Source ID；
- processed text asset path；
- `Lx` 或 `Lx-Ly` locator；
- exact quote；
- quote SHA-256。

Validator 同时检查 asset ownership、文件存在、行号内容和 hash。语义上“quote 是否
足以支持 Fact”仍由人审。

## 3. 质量 Gate

生成 Event 必须具有：

- 至少一个有 anchor 的 Fact；
- 分开的 Inferences 与 Research judgment；
- substantive Alternative explanations；
- substantive Unknowns；
- Follow-up indicators；
- 完整 Thesis impact proposal；
- Source independence partition。

任一必要字段缺失、含 TODO、引用不一致或 quote 无法定位时，不写 Event。

## 4. 来源独立性

系统递归解析 `upstream_source_ids`。共享任一上游根的 Source 合并为同一
independence group。它是证据计数约束，不自动判断 publisher 的编辑独立性；未知
上游必须继续作为 unknown 披露。

## 5. Report 综合

- 只接受 reviewed Event。
- 逐 Event 保留 Facts、Inferences、Research judgment。
- Thesis assessment 保留 supporting、contradicting 和 contextual。
- Contradicting Evidence 独立列出，并由 validator 检查不得遗漏。
- Alternative explanations 汇总为 Contrarian view。
- Unknowns 与 follow-up indicators 原样保留。
- 输出只形成研究优先级，不自动产生证券选择结论。

## 6. Incremental Weekly

Metrics snapshot 保存当时的 `reviewed_event_ids`。Weekly synthesis 选择相对
baseline 新增的 reviewed Event；旧 v1 snapshot 缺少该字段时，使用 snapshot
`as_of` 与对象日期作兼容回退。

## 7. 版本与人审

- Report ID 和文件永不覆盖。
- pending 新版只记录 `supersedes` proposal，不修改旧版。
- 人工 approve 新版时，在一个事务中把新版变成 reviewed/final，并把旧版变成
  superseded、写入 `superseded_by`。
- generation fingerprint 在同类型对象内唯一，重复运行拒绝重复创建。

## 8. Company proposal

Company update proposal 只能使用 reviewed 且明确关联目标 Company 的 Event。
Proposal 是非权威 Markdown，不直接编辑 Company；研究者审核后才决定是否合并。
