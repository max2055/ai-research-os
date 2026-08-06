# Channel 试跑验证记录（2026-08-06）

## 目标

启用首批 Channel 并验证 discovery 链路可用（Channel → adapter → SourceCandidate）。

## 启用

`channels enable --apply` 启用 4 个 license=reviewed 的 Channel：
- CHN-sec-edgar / CHN-arxiv / CHN-github-releases / CHN-skhynix-ir
- CHN-trendforce-news（restricted）与 CHN-company-ir（pending）保持禁用（RP-6）

`channels check`：4 个 schedulable。

## Discovery 试跑（`source discover`，全部真实抓取）

| Adapter | 目标 | 结果 |
|---|---|---|
| rss | SK hynix `/en/feed/` | ✅ 3 候选（HBF/FMS 公告）|
| sec | NVIDIA CIK 1045810（10-Q/8-K）| ✅ 8-K 归档候选 |
| arxiv | cs.SE coding-agent query | ✅ 2 候选（2026-08-05 论文）|
| github | modelcontextprotocol/servers | ✅ Release 候选 |

## 试跑暴露的问题

1. **Channel locator 配置 bug（已修）**：CHN-skhynix-ir 原 locator 是 `/en/`
   （网页页）但 channel_type=rss；真实 feed 是 `/en/feed/`。RSS discover 对网页
   页报 XML parse error——试跑暴露并已修正 locator。
2. **重复候选**：SK hynix 同一条 HBF 公告出现 3 次（`-01`/`-02`/`-` URL 变体）。
   验证了 B-014（exact/near dedup）的必要性——WP-220 实现。

## 结论

Discovery 链路（Channel → adapter → SourceCandidate）已验证可用。剩余 Phase 2
工程：B-007 discovery service（写 Candidate DB）、B-014 dedup、B-017 scoring、
B-018/019 Candidate Queue + promote。
