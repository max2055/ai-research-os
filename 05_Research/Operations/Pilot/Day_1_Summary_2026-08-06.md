# Pilot Day 1 汇总 — 2026-08-06

状态：Day 1/14 完成。Phase 2 Candidate Pipeline 首次完整跑通 + 首轮人工 triage。

## 一、今天搭了什么

**1. launchd 自动调度上线（B-021）**
- `com.aioresearchos.discovery` 已安装（每 6h + RunAtLoad），实测触发 3 轮全链路。
- per-channel no-overlap 锁 + 30min stale 恢复；重启不卡死、不双跑。

**2. 20 个 reviewed+enabled Channel（G1 ✅）**
- 原 4 个（arxiv/SEC/GitHub 聚合/skhynix）→ 拆分为 per-company/repo + 新增：
  - 7× per-company SEC（NVIDIA/TSMC/Micron/Microsoft/Meta/Amazon/CoreWeave，独立 CIK）
  - 5× per-repo GitHub（openai/anthropic/llama-models/DeepSeek-V3/autogen）
  - 6× arXiv 研究分区（cs.CL/CV/DC/AR/MA + econ.GN）
- 修复：SEC 多 CIK composite、GitHub 多 repo composite、CoreWeave CIK 纠错（2015943→1769628）。

**3. 全链路一轮跑通 395 候选**
- 20 通道真实抓取 0 失败；DB 395 候选，median latency 5.0s，dup 率 50%→35.7%。

## 二、今天 triage 了什么（96 promote / 239 dismiss）

| 批次 | Promote | Dismiss | 方法 |
|---|---|---|---|
| SEC 10-K/10-Q | 26 | 0 | 一手财报主源 |
| SEC 8-K | 42 | 25 | Item 启发式（2.02 财报/1.01 协议/7.01 指引=重大；5.07 投票/5.03 章程=例行）|
| GitHub releases | 2 | 63 | release notes 找模型信号（Llama4 / gpt-5.5）|
| arXiv 论文 | 26 | ~114 | AI 算力基础设施相关性人工筛 |
| 聚合重复/已存在 | 0 | 43 | 去重清理 |

**结果：96 个一手 Source 入库**（SRC-20260806-057..152），全部通过资产/hash 检查（G7 ✅）。
分布：SEC 财报/披露 68、arXiv 基础设施论文 26、GitHub 模型信号 2。

## 三、Pilot Gate 进度

| Gate | 目标 | 状态 |
|---|---|---|
| G1 reviewed+enabled Channel | ≥20 | ✅ 20/20 |
| G6 Candidate→Source promote | ≥20 | ✅ 96/20 |
| G7 提升 Source 资产/hash | 全过 | ✅ 96/96 |
| G4 重复入队比例 | <15% | ⬜ 35.7%（可优化 dedup）|
| G5 Top-20 人工相关性 | ≥75% | ⬜ 待人工抽样（现有数据支撑）|
| G9 每日 triage 中位耗时 | ≤45min | ⬜ 待日常节奏验证 |

## 四、剩余 / 下一步

- 队列剩余 60 new（skhynix 30 + tsmc SEC 20 未筛）。
- 进入 Pilot 观察模式：launchd 每 6h 自动抓，每日 `brief daily` + 审新增。
- **领导层演示（3 天内）**：计划扩展 dashboard 加 Pipeline 页面（候选队列/Sources/Channels/Metrics）+ demo runbook，让领导在网页上看到机器在跑。
- 工程 backlog：G4 dup 优化、筛选逻辑沉淀为可复用命令、v0.2 发布（Weekly 8-12）。

## 五、Day-1 数据快照

- 对象：151 Source / 24 source_channel / 170 review / 31 job / 396 关系（SUPPLIES 等）
- 候选：96 promoted / 239 dismissed / 60 new（DB 非权威，可重建）
- 质量门：validate 0 error，index 全 PASS，210 tests
