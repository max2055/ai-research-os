# M5 Dashboard、Action 与持续运行验收

验收日期：2026-07-29  
结论：`accepted`

## 1. 范围

覆盖 `Productization_Roadmap_v1.md` M5-01～M5-10。Dashboard 与 Job Run
边界由 `RCP-20260729-006` 批准。

## 2. 交付

| ID | 结果 | 交付 |
|---|---|---|
| M5-01 | PASS | `research-os ui` FastAPI shell、HTMX read-only fragment、responsive CSS、loopback-only bind |
| M5-02 | PASS | Project question、next review、counts、Thesis、Report、Action overview |
| M5-03 | PASS | Review Queue 按 Project、type、status 过滤，无 mutation route |
| M5-04 | PASS | Thesis confidence、正反 Evidence、review date、90 天 freshness、正文 |
| M5-05 | PASS | Source metadata、asset versions/extracts、hash/integrity、linked Event、body |
| M5-06 | PASS | Company/对象详情与 1～3 跳 impact view |
| M5-07 | PASS | 当前 metrics 与最近 immutable snapshot diff，明确 baseline 日期 |
| M5-08 | PASS | overdue Action 与 review due 运营页 |
| M5-09 | PASS | global/Project `Home_Dashboard.md`，由 index service 确定性重建 |
| M5-10 | PASS | validate/indexes/metrics/source-process/refresh Job CLI，追加 success/failed audit |

## 3. Dashboard Gate

- 首页直接到 Thesis/Action/Report；经 Review Queue 到 Source/Event，不超过三次点击。
- 所有页面和 `/api/state` 都在 request 时从 Markdown 重建。
- App 未注册 POST、PUT 或 DELETE。
- UI cache 不是事实源；Obsidian Home 删除后可由 `index --apply` 重建。
- Thesis detail 与 overview 都显示 current/stale。
- Health 显示 validation、index drift、asset failure 和 failed Job。
- Source asset route 只按 Source-owned list index 解析；不存在或越界返回 404。
- 非 loopback host 被拒绝。
- 真实仓库 runtime smoke：Overview、filtered Review Queue 和 API 均返回 200；
  smoke 后服务正常关闭。

## 4. Scheduler Gate

- Job Run 是正式可验证的 Markdown operational object。
- validate job 只读；index/home 可重复重建。
- 同日相同 metrics snapshot 第二次运行报告 unchanged，不覆盖。
- 同日不同 snapshot 内容拒绝覆盖。
- processed Source 重跑为 no-op。
- failed job 保留错误类型与消息，并在 Web/Obsidian Health 可见。
- Job 完成后在仓库可验证时刷新 global/Project indexes，避免运行记录造成 drift。

## 5. 质量结果

- tests：86/86。
- coverage：83%，高于 80% Gate。
- Ruff：通过。
- mypy strict：49 个 source files 通过。
- formal Schema：56/56 既有真实对象；Job Schema 在隔离仓库覆盖。
- validation：0 error、18 个既有 `REV003` warning。
- global index：8/8，drift 0。
- PRJ-001 index：8/8，drift 0。
- `research-os doctor`：全部检查通过。
- M5 commit 的独立 clean clone 可安装 `[dev,ui]`、运行 86 tests、通过 doctor
  并从打包后的 CSS 创建 Dashboard app。

## 6. 边界

- Dashboard 未部署公网；仓库不存在 `.openai/hosting.json`，按 local-only 产品要求
  未调用 hosting。
- v1 不从 Web 页面执行审核或编辑事实正文。
- M4 真实 10-Source 人审 Gate 仍 pending，不被 Dashboard 验收改变。

## 7. Gate 决策

M5 Gate 通过。工程继续进入 M6 第二项目试点、性能、恢复和 v0.2 发布准备。
