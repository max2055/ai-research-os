# M4 研究工作流与智能生成工程验收

验收日期：2026-07-29  
工程结论：`accepted`  
真实资料人审 Gate：`pending`

## 1. 范围

覆盖 `Productization_Roadmap_v1.md` M4-01～M4-10 的产品能力。治理变更由
`RCP-20260729-005` 批准。10 个真实新 Source 的 Fact 准确率人审记录独立保存在
`05_Research/Reviews/M4_Field_Review_Packet.md`，未用自动测试替代。

## 2. 工程交付

| ID | 结果 | 交付 |
|---|---|---|
| M4-01 | PASS | structured JSON spec→pending Event；Facts/Inferences/Judgment 分区 |
| M4-02 | PASS | Fact ID、processed asset、line locator、exact quote 与 quote SHA-256 |
| M4-03 | PASS | supporting/contradicting/contextual proposal 与 metadata/table 一致性 |
| M4-04 | PASS | Alternative explanations/Unknowns 缺失或 TODO 时拒绝写入 |
| M4-05 | PASS | 递归 upstream graph 与 Source independence partition |
| M4-06 | PASS | reviewed-only Report synthesis，无 TODO，保留 Event 各分区 |
| M4-07 | PASS | metrics snapshot reviewed Event state 与 baseline 增量 Weekly selection |
| M4-08 | PASS | immutable version、fingerprint dedup、人工 approve 时原子 supersession |
| M4-09 | PASS | reviewed、company-linked Evidence→non-authoritative Company proposal |
| M4-10 | PASS | 所有 Event/Report 输出 pending/draft；Review Decision 仍需独立人工命令 |

## 3. 自动化 Gate

- 每个 generated Fact 的 anchor ownership、文件、行号、quote 和 hash 可验证。
- 重复 Event/Report generation fingerprint 会在写入前拒绝。
- Thesis links 与 impact rows 由既有 validator 双向检查。
- Report synthesis 拒绝 pending/rejected Event。
- selected Event 的 contradicting relationship 会进入独立 Report section，遗漏时
  validator 报错。
- pending 新 Report 不修改旧 Report；人工 approve 后新旧状态和指针在同一事务更新。
- Company proposal 不直接编辑 Company。
- CLI Event workflow 已验证 dry-run 不写、`--apply` 写入并同步 Source checklist。

## 4. 质量结果

- tests：80/80。
- coverage：83%，高于 80% Gate。
- Ruff：通过。
- mypy strict：46 个 source files 通过。
- formal Schema：56/56 既有真实对象。
- validation：0 error、18 个既有 `REV003` warning。
- global 与 PRJ-001 index drift：0。
- `research-os doctor`：全部检查通过。
- M4 commit 的独立 clean clone 可重新安装依赖、运行 80 tests 并通过 doctor。

## 5. 未完成的人审 Gate

路线图要求“真实抽取 10 个新 Source，人工检查 Fact 准确率”。当前：

- 工程 fixtures 已覆盖成功、缺 quote、缺反方、anchor 篡改、重复、pending Evidence、
  contradicting preservation、incremental selection 和 supersession。
- 真实仓库未擅自新增或批准任何 Event。
- Field packet 为 0/10，必须由研究者逐 Fact 检查后才能把 M4 总 Gate 标为 completed。

工程工作不因此阻塞 M5 Dashboard 开发；v0.2 发布前必须完成或由研究者作出正式延期
决定。
