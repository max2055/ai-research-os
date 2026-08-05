# 首次月度研究系统复盘

Review ID：REV-20260729-M01

月份：2026-07

复盘日期：2026-07-29

指标快照：`05_Research/Reviews/Snapshots/METRICS-20260729.json`

审阅状态：system draft completed；行动项已建立，研究判断仍遵循既有人工审核规则。

## System facts

### Object and review queue

- 20 个 Source：20 pending、0 reviewed。
- 15 个 Event：15 reviewed。
- 5 个 Thesis：5 reviewed。
- 8 个 Company：8 pending。
- 1 个 Report：1 final/reviewed。
- 总 review queue 为 28。

### Source conversion and quality

- 18/20 个 Source 被至少一个 Event 引用，转化率为 90%。
- 2 个 Source 尚未进入 Event。
- Source grade 为 19 个 A、1 个 B。
- reviewed Event 引用了 18 个仍为 pending 的 Source，对应 18 条 `REV003` warning。

### Evidence quality

- 15 个 Event 共包含 18 条 Source link，平均每个 Event 1.20 个 Source。
- 0 个 Event 缺少 Thesis link。
- 审阅记录包含 15 个 approve、0 个 reject。

### Thesis health

| Thesis | Confidence | Supporting | Contradicting |
|---|---:|---:|---:|
| THS-001 | 0.29 | 1 | 0 |
| THS-002 | 0.40 | 4 | 1 |
| THS-003 | 0.28 | 1 | 1 |
| THS-004 | 0.40 | 4 | 2 |
| THS-005 | 0.32 | 4 | 0 |

- 0 个 Thesis 缺少支持 Evidence。
- 2 个 Thesis 缺少直接反面 Evidence：THS-001、THS-005。
- 平均 Thesis 置信度为 0.34。

### Knowledge, Reports and automation

- 8/8 个公司画像已关联 reviewed Evidence，但公司对象本身仍 pending。
- 1 篇 Report 为 final/reviewed。
- validation error 为 0。
- validation warning 为 18。
- index drift 为 0。
- 自动化测试为 26/26 通过。

## Interpretation

### What improved

- 最小研究闭环已经从 Source 延伸到 reviewed Event、reviewed Thesis 和 final Report。
- 每个 Event 都进入 Thesis 关系，说明结构化 Evidence 没有成为孤立信息。
- 自动化可以检测引用、权威化边界和索引漂移。

### What remains weak

- Source 审核状态与 Event 审核状态之间存在治理落差。Event 已经人工批准，但底层 Source 对象没有单独记录审核决定。
- 证据高度依赖公司、产品和投资者关系官方材料。高等级不等于独立性。
- THS-001 只有一个支持 Event；THS-001 和 THS-005 没有直接反面 Event。
- 缺少独立客户采用、任务成功率、留存、单位经济性和收入替代数据。
- 公司画像虽有关联 Evidence，但仍未经过对象级审核。

### Alternative explanations

- Source pending 可能只是状态记录没有同步，不一定意味着研究者没有看过底层材料。
- 早期主题以官方资料建立事实基线是合理起点，不能仅凭第一轮来源结构判断系统长期偏差。
- 缺少直接反面 Evidence 可能来自公开披露不足，而非 Thesis 正确。

## Decisions

- 不机械提高任何 Thesis 置信度。
- 不通过自动化批量把 Source 或 Company 标为 reviewed。
- 把 Source 审核、独立客户证据和 THS-001/005 反证列为下一轮优先事项。
- 本月不修改 Research Rules、Source Policy、Taxonomy 或 Metadata Schema。

## Action items

行动项已登记于 `05_Research/Reviews/Action_Register.md`：

- ACT-20260729-001 至 ACT-20260729-006。

## Next reviews

- Weekly review：2026-08-05。
- Monthly review：2026-08-29。
