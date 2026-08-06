# launchd Runbook（B-021）

macOS `launchd` 调度 AI Research OS 的每日情报发现与 retention sweep。
单机 scheduler，不引入分布式任务队列（Phase 2 §7）。

## 工作原理

```text
launchd (StartInterval 6h, RunAtLoad)
  → 09_Automation/launchd/run_daily.sh
      → research-os discover due --as-of <now>     # 按 Channel schedule 算到期
      → research-os jobs run discover --target CHN-…  # 逐 channel（per-channel lock）
      → research-os jobs run expire                 # retention sweep（expire + purge）
```

每次 `jobs run` 都会写一条不可变的 Job Run 记录
（`05_Research/Operations/Jobs/JOB-*.md`），失败也在记录里留痕。

## 无重叠（no-overlap）

- **per-channel lock**：`discover run --apply` 开始时在 `discovery_runs`
  写一条 `running` 行；同一 Channel 已有 `running` 行则拒绝启动（§5.1）。
  StartInterval 与 run 时间重叠时，第二个触发只会失败并记录，不会双跑。
- wrapper 对单 channel 失败不中止（`|| echo FAILED`），整轮 sweep 继续。

## 重启后恢复（restart recovery）

- launchd `RunAtLoad=true`：机器重启后（LaunchAgent 已 load）自动补跑。
- **stale lock 回收**：崩溃/被杀留下的 `running` 行超过 30 分钟
  （`LOCK_STALE`）会在下一次运行被标记为 `failed` 并回收，通道不会被
  永久锁死。

## 安装

```bash
# 1. 校验 plist
plutil -lint 09_Automation/launchd/com.aioresearchos.discovery.plist

# 2. 安装到用户 LaunchAgents 并加载
cp 09_Automation/launchd/com.aioresearchos.discovery.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.aioresearchos.discovery.plist

# 3. 确认已加载
launchctl list | grep aioresearchos
```

加载后 `RunAtLoad` 立即触发一次，之后每 6 小时一次。

## 卸载 / 暂停

```bash
launchctl unload ~/Library/LaunchAgents/com.aioresearchos.discovery.plist
rm ~/Library/LaunchAgents/com.aioresearchos.discovery.plist
```

全局 pause 语义（§13）：卸载 launchd 即暂停；已有 Candidate 保留，不影响
`candidates list`。

## 手动运行（不经过 launchd）

```bash
# 单 channel
research-os jobs run discover --target CHN-skhynix-ir

# 只看当前到期的 channel（dry）
research-os discover due

# 手动 retention sweep（expire + purge，dry 先看）
research-os jobs run expire
research-os candidates expire --as-of 2026-11-06T00:00:00Z   # dry-run 预览
research-os candidates purge                                   # dry-run 预览
```

## 日志

- sweep 明细：`09_Automation/launchd/logs/sweep.log`
- launchd stdout/stderr：`…/launchd/logs/launchd.stdout.log`、
  `…/launchd.logs/launchd.stderr.log`
- 每 job 结果：`05_Research/Operations/Jobs/JOB-*.md`

## Retention（ADR §3 / B-020+B-021）

- `new`/`triaged`：保留 30 天（per-channel `retention_days`）。
- `dismissed`/`expired`：`jobs run expire` 先按 retention 标 `expired`，再
  `candidates purge` 物理删除候选行，**保留 candidate_actions 审计行**
  （schema v2 已去掉 FK）。
- `promoted`：永久保留（promoted_source_id 永久链接）。

## 备份与故障处理（§13）

- Candidate DB（`09_Automation/operational/candidates.db`）为派生数据，
  按 Recovery_Runbook 加密备份；可从 Channel 重跑重建。
- 单 Channel 可 `channels disable`，不删除配置。
- Adapter 失败不得创建 processed Source（promote 才写权威仓库）。
- 许可变为 restricted 时停抓、保留合规记录。

## 已知边界

- `discover due` 对解析不了的 schedule 视为**不到期**（不自动跑无法排期的
  channel），用 `channels check` 人工发现。
- `jobs run expire` 是纯自动动作（actor=`system`）；promote 永远是人工
  `--apply`（Agent 不自动提升，RCP-v03-004）。
