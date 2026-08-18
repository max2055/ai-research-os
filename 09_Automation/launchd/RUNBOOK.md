# Legacy Scheduler Evidence

状态：已退出生产，禁止与网站 Worker 并行运行。

本目录中的 plist、`run_daily.sh` 和历史日志仅用于保留 B-021 的实现与运行证据。
当前生产调度由 `python -m research_os.ui` 启动的网站进程托管，计划只在
`/operations/schedules` 管理，运行状态与审计只写入 `operations.db`。

## 强制边界

- 正常运行时，旧 LaunchAgent 必须保持 unloaded，且不得设置登录启动。
- 网站运行时绝不能加载旧 LaunchAgent，也不能直接执行 `run_daily.sh`。
- 不得把旧 Channel Markdown 的 `schedule`/`enabled` 字段重新作为运行权威。
- 不得删除 plist、脚本、历史 `JOB-*.md` 或 `launchd/logs/*`；它们是迁移前证据。
- 旧 scheduler 不认识 `operations.db` 的租约和队列，并行运行会造成重复发现、重复
  retention 与不完整审计。

## 恢复边界

切换已完成，旧 scheduler 不再是受支持的回滚路径。网站 Worker 无法启动时应保持所有
调度停止，保存当前 `operations.db`、Candidate DB、Source assets 和 durable receipt，
然后按 `00_System/Recovery_Runbook.md` 恢复到 disposable directory。不得把本目录中的
plist 或 wrapper 安装回操作系统，也不得让恢复副本访问 canonical 数据目录。

## 历史证据

- plist：`09_Automation/launchd/com.aioresearchos.discovery.plist`
- wrapper：`09_Automation/launchd/run_daily.sh`
- 历史日志：`09_Automation/launchd/logs/*`
- 历史 Job：`05_Research/Operations/Jobs/JOB-*.md`

这些文件不定义当前产品行为。当前故障处理、备份和恢复流程见
`00_System/Recovery_Runbook.md` 与网站 `/health`、`/operations/backups`。
