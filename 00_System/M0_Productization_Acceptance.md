# M0 产品化稳定门槛验收

验收日期：2026-07-29  
状态：`completed`

## 任务验收

- [x] M0-01：`new-event` 为每个 `thesis_links` 生成合法的 Thesis impact 行。
- [x] M0-02：Report 生命周期、Report 正文、Review Queue 与 Source Processing 状态一致性已建立自动校验。
- [x] M0-03：`RCP-20260729-001` 已批准并明确 Source、Processing 与 Event 审核的独立语义。
- [x] M0-04：已建立本地私有 Git、`.gitignore`、恢复手册、基线提交和干净 clone 演练。
- [x] M0-05：CLI subprocess 测试覆盖 Source、Event、Report 的 dry-run 和 apply 真路径。
- [x] M0-06：Stage 4/5 Design 文档已标记 implemented，设计清单与正式 Acceptance 不再冲突。

## 正确性结果

- validation error：0。
- index drift：0。
- 自动化测试：33/33。
- 带 Thesis link 的新 Event 首次 validate：通过。
- final/reviewed Report 中与自身状态冲突的“待审核”表述：0。
- 已转化但 extraction 未完成的 Source：0。
- 永久 ID 冲突：0。

## 治理 warning

保留 18 条 `REV003`：

- 事实：15 个 reviewed Event 引用 18 个 pending Source。
- 解释：Event 中使用的具体主张已经审核；完整 Source 记录仍待 Source 级审核。
- 决定：根据 `RCP-20260729-001`，这些 warning 是显式治理积压，不是状态漂移或 validation error。
- 行动：由 `ACT-20260729-001` 和产品化并行研究流 RQ-01 继续关闭，自动化不得替研究者批准 Source。

## Git 与恢复

- Baseline commit：`3709a9e`
- Default branch：`main`
- Recovery clone：测试、validate、index check 均通过
- Remote：未配置；GitHub CLI 当前未登录。未来远程必须创建为 private。

## Gate 决定

M0 Gate 通过。工程主线进入 M1 模块化内核与正式 Schema；P1 研究质量行动并行推进，不阻塞产品化。
