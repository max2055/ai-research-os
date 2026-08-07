# Demo Runbook — 领导层演示：Pipeline 在跑

目标：**在 5–8 分钟内让领导在网页上看到"机器在跑"**——自动抓取 → 自动打分 → 人工筛选 → 正式入库的完整闭环。全程只读演示，不点任何会改动数据的按钮。

当前基准：**Pilot Day 2/14（2026-08-06 启动）**。Dashboard 本地只读，启动命令见「演示前检查清单」。

---

## 演示动线

### 第 0 步 · 打开 Dashboard（10 秒）
浏览器打开 `http://127.0.0.1:8765/pipeline`。
> 开场：这是我们研究的操作系统，数据从公开一手来源自动抓取，全部本地运行、可审计。今天带你看它怎么自己跑。

### 第 1 步 · Pipeline 主页（60 秒）
看 Hero 右上角 **Pilot window day 2/14** + 四张指标卡。
> 讲三点：
> 1. **机器在自动跑**——launchd 每 6 小时自动抓取 20 个通道（SEC 财报、arXiv 论文、GitHub 发行、SK 海力士 IR），已经跑到第 2 天。
> 2. **96 个已入库 Source**——Pilot 目标 20，我们已入库 96（G6 达成）。
> 3. **20/20 通道就绪**——全部经过人工审查 + 授权后才允许调度（G1 达成）。
> 补一句："这些页面全部只读，筛选/驳回/提升都走命令行，页面不改任何研究数据。"

### 第 2 步 · 候选队列（90 秒）
点「Open queue →」，默认看 `status=new`。
> 讲：
> 1. 队列按**优先级降序**排——每个候选有 0–1 的打分（B-017 启发式：渠道质量/实体匹配/去重代表性/板块覆盖加权，重复或不确定减分）。
> 2. 顶部 Filter 可以按状态/渠道/最低分筛选——**演示时建议切一个 status 或输入 min-priority 0.5 演示筛选**。
> 3. 现在有 **210 个待筛候选**在排队，是每日 triage 的原料。

### 第 3 步 · 候选详情（90 秒）
点第一行候选标题进入 `/pipeline/queue/{id}`。
> 讲：
> 1. **Entity proposal**——自动识别的实体（如 SK hynix）；**Sector proposal**——板块归属（如 memory-storage）。
> 2. **Reason codes**——打分理由，每条可追溯，不是黑盒。
> 3. **Action history**——这个候选被谁、何时、做了什么（promote/dismiss），**全程追加式审计，物理不删**。

### 第 4 步 · Promoted Sources（60 秒）
顶部切到 `/pipeline/sources`。
> 讲：
> 1. 这里 96 个是**已经过人工筛选、正式入研究库的一手 Source**（SEC 财报/披露、基础设施论文、模型发行信号）。
> 2. 每个都带着**来源通道**列——能回溯是哪个通道抓的；点 ID 进 `Source 详情页`能看到归档资产 + SHA-256 校验（G7 全过）。
> 3. 强调："候选是**可重建的临时库**，正式 Source 才是权威事实，两者边界清晰。"

### 第 5 步 · Channels & Metrics（90 秒）
切到 `/pipeline/channels`。
> 讲：
> 1. **上区通道表**——24 个通道，20 个 Schedulable（reviewed + enabled 双门槛），4 个 disabled 是聚合通道/受限来源，**演示时指一下这个双门槛设计**。
> 2. **下区指标**——median latency 5.0s、fail rate 0%、triage yield 96 promote。
> 3. 老实说一句瓶颈："重复率 73.86%（G4 目标 <15%）是当前唯一未达标的 Gate，是我们下一阶段的去重工程重点。"

### 第 6 步 ·（可选）Health 收尾（30 秒）
切到 `/health`。
> 收尾："整个系统 validate 0 错误、asset 校验全过、失败 job 已自动恢复。这是一套本地优先、证据可追溯、AI 只提建议人工做决定的系统。"

---

## 演示前检查清单（每次演示前 3 分钟）

```bash
# 1. 启动 dashboard（若有弹窗确认网络，允许仅本机）
/Users/max/.venvs/ai-research-os/bin/research-os ui --port 8765
# 2. 确认数据在
/Users/max/.venvs/ai-research-os/bin/research-os pilot status     # day X/14, 96 promoted
/Users/max/.venvs/ai-research-os/bin/research-os channels check   # 20/20 schedulable
/Users/max/.venvs/ai-research-os/bin/research-os pipeline metrics # dup rate / latency
```

- 浏览器确认 `/pipeline`、`/pipeline/sources`、`/pipeline/queue`、`/pipeline/channels` 全部 200。
- 若 `/pipeline/queue` 为空：跑一次 `research-os candidates enrich --apply` 补打分（需仓库 validate 0 error）。
- 可选：先跑 `research-os brief daily --apply` 生成当天 Brief，作为"机器产出日报"的加分展示。
- 演示前把终端日志清一下，只留一个干净窗口。

---

## 备选路径（卡住时）

| 现象 | 处理 |
|---|---|
| `/pipeline/queue` 无候选 / 空表 | 直接讲 Sources 和 Channels，说"队列刚清空或抓取间隔未到"；或用 `candidates list` 命令行展示同样数据 |
| 候选详情 404 | 换队列里另一个候选；或演示命令行 `candidates show --id <id>` |
| Channels 页 4 个 disabled | 主动讲——"这 4 个是聚合/受限来源，按授权策略不调度"（这是设计，不是故障） |
| 指标卡显示 0 | 当天 launchd 还未跑新轮次，median latency 等是历史累计，正常 |
| 领导问"重复率怎么这么高" | 见 Q&A 第 3 条 |

---

## 常见 Q&A 速查

1. **"数据从哪来？会不会侵权/被墙？"**
   全部公开一手来源：SEC EDGAR、arXiv API、GitHub Releases、公司 IR。每通道入库前做了 license/robots 审查，受限来源（如部分 TrendForce）注册但不调度。本地优先，不外传。

2. **"AI 在里面起什么作用？"**
   AI 做自动抓取、去重、实体/板块识别、优先级打分、每日简报——**全部是建议**。正式 Source 入库、驳回、提升都是**人工决定**，且全程审计记录。证据先于观点。

3. **"重复率 73.86% 是不是质量很差？"**
   这要看口径。我们现在用**入队口径**（7 天窗口内新抓进来的候选里，重复变体占比）衡量 G4——它反映"抓取进来的噪音"，不受历史堆积影响。已做的三道去重：**入站跳过**（内容已是正式 Source 的抓取时直接不插入，SEC 通道实测每轮 20 条里 14 条被跳过）、**队列簇折叠**（重复簇折叠成代表行，425 条 → 53 行）、**already-sourced 标注**（`已有来源 SRC-…` 提示直接驳回）。早期窗口数字高是 Day-1 批量抓取的历史数据，入站跳过后新抓取的重复会明显减少。

4. **"96 个 Source 都是有用的吗？"**
   96 个全部过了人工筛选（SEC 财报/披露 68、基础设施论文 26、模型信号 2），资产与哈希校验全过（G7）。但内容相关性（G5）是持续的人工质量门，不是一次性的。

5. **"这能规模化吗？"**
   设计上就是为规模化：通道/适配器/打分/去重全是可插拔服务，20 通道已跑通全链路；扩容只是加通道 + 审通道，不动内核。

---

## 数字速查（演示口径）

- **Pilot**：Day 2/14 · since 2026-08-06
- **Gate**：G1 20/20 ✅ · G6 96/20 ✅ · G7 96/96 ✅ · **G4 入队重复率 73.86%（7d 窗口，<15%）⬜**
- **当前库**：306 候选（210 待筛 + 96 已提升）；驳回候选按 30 天保留策略清理（审计记录仍在）
- **队列去重**：210 条 new 折叠为 **53 个簇代表行**；84 条标 `already SRC-…`（内容已入库，建议驳回）
- **Triage 指标（按审计动作统计）**：Triaged 335 = Promoted 96 / Dismissed 239 · 中位入库 1.0h
- **通道**：24 注册，20 Schedulable，4 disabled（聚合/受限）
- **运行质量**：32 次抓取 0 失败 · median latency 5.0s · 每日 Brief 已产出
- **测试**：217 passed / 217
