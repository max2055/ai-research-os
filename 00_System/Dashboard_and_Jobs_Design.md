# Dashboard and Jobs Design

版本：v1.0  
生效日期：2026-07-29  
批准：`RCP-20260729-006`

## 1. Dashboard information architecture

```text
Project overview
├── Thesis health → Evidence → Source
├── Review queue → Source/Event/Thesis/Company/Report
├── Reports → Evidence and version metadata
├── Operations → overdue Action / review due
├── Metrics → current vs immutable snapshot
└── Health → validation / index / assets / failed jobs
```

任一首页表格对象都直接链接详情；Review queue 为 Source/Event 提供第二条路径，
从首页不超过三次点击。

## 2. Read model

- HTTP request 直接运行 repository validation 和 project scoping。
- 页面只读 canonical Markdown 与本地 Source assets。
- UI 不持久化对象副本；删除任何浏览器或临时 cache 后下一请求自然重建。
- `/api/state` 是派生 JSON read model，不是写入 API。
- `Home_Dashboard.md` 是 Obsidian fallback，可由 index service 重建。

## 3. Pages

- Overview：Project 问题、下一复盘、对象数、Thesis、Report、Action。
- Review Queue：按 Project、对象类型和 review status 筛选。
- Thesis：正反 Evidence、confidence、review date、90 天 freshness。
- Source：provenance、asset/version、hash、integrity、引用 Event、研究笔记。
- Company/Event/Report/Action：metadata、正文和 impact 入口。
- Metrics：当前值与最新 snapshot diff。
- Operations：overdue Action、review due。
- Health：validation、index drift、asset integrity、failed Job Run。

## 4. Web boundary

- `research-os ui` 默认 `127.0.0.1:8765`。
- 只接受 loopback host。
- 无 mutation route。
- 仓库文本在 HTML 输出前 escape。
- Source asset 通过拥有它的 Source 与数组 index 解析，拒绝任意 path。
- v1 不处理登录、账户或公网访问。

## 5. Jobs

```bash
research-os jobs run validate
research-os jobs run indexes [--project PRJ-NNN]
research-os jobs run metrics [--project PRJ-NNN] [--as-of YYYY-MM-DD]
research-os jobs run source-process --target SRC-ID
research-os jobs run refresh [--project PRJ-NNN] [--as-of YYYY-MM-DD]
research-os jobs list [--project PRJ-NNN] [--status failed]
```

`refresh` 执行 validation、global/project index rebuild 和 idempotent metrics
snapshot。所有 job 追加 Job Run，然后在仓库仍可验证时刷新 Home/index，使运行结果
立即可见。

业务幂等：

- validate：只读；
- indexes：相同输入产生相同内容；
- metrics：同日期同内容 no-op，不同内容拒绝覆盖；
- source-process：已成功处理同一版本 no-op；
- refresh：组合上述规则。

Job Run audit 不是业务副作用去重对象，因此每次调度都保留一条 success/failed 记录。
