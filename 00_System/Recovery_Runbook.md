# AI Research OS 恢复手册

版本：v1.2
生效日期：2026-08-18

## 1. 恢复目标

从 private Git repository 恢复 Markdown 事实源、规则、模板和自动化，从加密
durable backup 恢复 Candidate SQLite、operations SQLite 与 Source 原始资产，再重建全部派生
索引。恢复必须先落到 disposable directory，不得用备份直接覆盖 live repository。

## 2. 备份边界

Git 跟踪：

- `00_System` 至 `09_Automation` 中的 Markdown、Python 和测试文件；
- `AGENTS.md`、`README.md`；
- 研究对象、审核记录、不可覆盖指标快照。

Git 默认不跟踪：

- Python cache、测试 cache；
- Candidate SQLite、operations SQLite、临时导出和可重建派生数据库；
- `09_Automation/operational/durable_backup.json` 与 durable backup receipts；
- `.env`、token、private identities、密钥和证书；
- `01_Inbox/_assets/` 中可能受许可或隐私约束的原始材料；
- 任何旧 OS scheduler 安装状态。

Durable backup 保持两个远端加密集合。`candidate` 集合包含 Candidate SQLite snapshot、
`operations.db` snapshot 及各自 manifest；`source_assets` 集合包含 Source asset
inventory/archive。两组使用 `age` 加密后，将 ciphertext 和非敏感 outer manifest 作为
不可覆盖 asset 上传到 private GitHub 的固定 prerelease
`research-os-durable-backups-v1`。Git、secrets、private identities、local config 和旧 OS
scheduler 状态不在 payload 中，必须分别恢复。

## 3. 从 Git 恢复

```bash
git clone <PRIVATE_REPOSITORY_URL> AI-Research-OS
cd AI-Research-OS
python3 -m venv ../ai-research-os-venv
../ai-research-os-venv/bin/pip install -e ".[dev,ui]"
../ai-research-os-venv/bin/pytest --cov=research_os --cov-fail-under=80
../ai-research-os-venv/bin/python -B 09_Automation/research_os.py validate --strict
../ai-research-os-venv/bin/python -B 09_Automation/research_os.py index --apply
../ai-research-os-venv/bin/python -B 09_Automation/research_os.py index --check
../ai-research-os-venv/bin/python -B 09_Automation/research_os.py validate
```

在 Source assets 恢复前，strict validation 可能诚实报告缺失 bytes。Hosted CI 的
metadata-only 检查不能替代恢复后的 strict local Gate。

## 4. Durable backup 准备与密钥托管

Operator 使用当前平台的包管理器安装 `age`、GitHub CLI 和 `jq`，然后检查：

```bash
command -v age age-keygen gh jq
age --version
gh auth status
```

目标 repository 必须是 private。固定 backup prerelease 必须已存在且保持
prerelease；它不是 v0.3 产品 release：

```bash
BACKUP_REPOSITORY=OWNER/PRIVATE_REPOSITORY
gh repo view "$BACKUP_REPOSITORY" --json isPrivate
gh release view research-os-durable-backups-v1 \
  --repo "$BACKUP_REPOSITORY" --json tagName,isPrerelease
```

首次配置且该 prerelease 不存在时，由 operator 在确认 repository privacy 后创建一次：

```bash
gh release create research-os-durable-backups-v1 \
  --repo "$BACKUP_REPOSITORY" --prerelease \
  --title "AI Research OS durable backups" \
  --notes "Encrypted operational backup assets; not a product release."
```

A recipient is a public encryption identity. An identity is a private decryption key.
生成主 identity 时限制目录和文件权限，只把 public recipient 写入配置：

```bash
AGE_IDENTITY=/Users/max/.config/ai-research-os/backup/age-identity.txt
mkdir -p /Users/max/.config/ai-research-os/backup
chmod 700 /Users/max/.config/ai-research-os/backup
umask 077
age-keygen -o "$AGE_IDENTITY"
chmod 600 "$AGE_IDENTITY"
age-keygen -y "$AGE_IDENTITY"
```

Generate a second independent identity on a separate trusted system. 将第二把 private
identity 保存在与本机和 GitHub account 分离的 offline custody 中，只把它的 public
recipient 加入配置。任一匹配 identity 都可解密；private identity 不得进入 Git、
GitHub Release、backup config、Job、日志或截图。

固定的 ignored 服务端配置
`09_Automation/operational/durable_backup.json` 只接受 `repository` 与 `recipients`：

```json
{
  "repository": "OWNER/PRIVATE_REPOSITORY",
  "recipients": ["age1PRIMARY...", "age1SECOND..."]
}
```

每次成功 apply 后还会写
`09_Automation/operational/backups/durable/latest-success.json` 和同 ID receipt。CLI 的
verify/restore 需要该 receipt；因此必须把 per-backup receipt 复制到独立的 secure
off-device metadata custody。Remote outer manifests 不等同于当前 CLI 可直接加载的
receipt。

## 5. 创建与验证 durable backup

在网站 `/operations/backups` 选择 Durable backup，预览并确认入队。浏览器不接收配置
路径、recipient 或 token；网站 Worker 只读取上述固定服务端配置。运行完成后，在
`/operations/jobs` 与 `/health` 检查结果。需要执行远端恢复校验时使用内部恢复命令：

```bash
BACKUP_CONFIG=09_Automation/operational/durable_backup.json
BACKUP_ID=$(jq -r .backup_id \
  09_Automation/operational/backups/durable/latest-success.json)
python3 09_Automation/research_os.py backup durable verify-remote --backup-id "$BACKUP_ID" \
  --config "$BACKUP_CONFIG"
```

Durable Job 会检查 `age`、private repository、recipient、两个 SQLite 数据库、Source
inventory 和 remote name collision，再为两组数据创建 snapshot/archive、验证
plaintext、加密、上传并核验 remote metadata。成功后才推进 `latest-success.json` 并将
`backup-durable` run 标为 success。已有 remote asset 不覆盖；partial upload 不得标成
latest success。

`verify-remote` 下载 outer manifests 与 ciphertext 并复核 size/hash，不解密。正常
Dashboard Health 只读 local receipt，不发起 remote request；operator 必须定期显式
运行 verify。

## 6. 从 durable backup 恢复

先从独立 custody 恢复 matching private identity、backup config 和所选 backup 的 local
receipt 到预期 ignored 路径。再选择 absent 或 empty disposable destination：

```bash
BACKUP_CONFIG=09_Automation/operational/durable_backup.json
AGE_IDENTITY=/Users/max/.config/ai-research-os/backup/age-identity.txt
RESTORE_DESTINATION=09_Automation/operational/restores/$BACKUP_ID
python3 09_Automation/research_os.py backup durable verify-remote --backup-id "$BACKUP_ID" \
  --config "$BACKUP_CONFIG"
python3 09_Automation/research_os.py backup durable restore --backup-id "$BACKUP_ID" \
  --identity "$AGE_IDENTITY" \
  --destination "$RESTORE_DESTINATION" \
  --config "$BACKUP_CONFIG"
python3 09_Automation/research_os.py backup durable restore --backup-id "$BACKUP_ID" \
  --identity "$AGE_IDENTITY" \
  --destination "$RESTORE_DESTINATION" \
  --config "$BACKUP_CONFIG" --apply
```

无 `--apply` 的 restore 只做 local safety preflight。Apply 会重新下载并核验 ciphertext，
用指定 identity 解密，拒绝 traversal/link/device/duplicate members，并验证 Candidate
与 operations SQLite 的 integrity/schema/hash，以及每个 Source asset inventory hash。
它只写 disposable destination，不会直接覆盖 live databases 或 authoritative Source
asset path。

验证 disposable restore 后，人工比较并恢复：

1. 将 Candidate snapshot 放到 `09_Automation/operational/candidates.db` 前，确认 live
   path 不存在或已由 operator 明确保存；不得覆盖来源不明的数据库。
2. 将 operations snapshot 放到 `09_Automation/operational/operations.db` 前，确认
   integrity、schema version 和 manifest SHA-256；保留原数据库用于审计和回滚。
3. 将 restored `01_Inbox/_assets/` 合并到 live asset tree；已存在且 hash 不同的文件
   必须停止并调查，不能覆盖。
4. 恢复 secrets/local config，启动 `python -m research_os.ui`；不得加载旧 OS scheduler。
5. 运行完整 local Gate：

```bash
python3 09_Automation/research_os.py source verify-assets
python3 09_Automation/research_os.py validate --strict
python3 09_Automation/research_os.py index --apply
python3 09_Automation/research_os.py index --check
python -m pytest 09_Automation/tests -q
ruff check .
ruff format --check src 09_Automation/tests
mypy src/research_os
```

验收还包括对象数量与最近 Metrics/release record 一致、loopback 网站与 Worker 可启动、
Worker heartbeat 新鲜、网站停止后 Worker PID 退出，以及停机期间 run count 不变。

## 7. 24-hour RPO 与 P1 响应

Durable backup 的目标 RPO 是 no more than 24 hours。Health 将 local Candidate snapshot
age 与 durable receipt age 分开显示；durable 状态为 `missing`、`failed`、`invalid`，
或超过 24 小时成为 `stale` 时，分别产生 `BKP_DURABLE_MISSING`、
`BKP_DURABLE_FAILED`、`BKP_DURABLE_INVALID`、`BKP_DURABLE_STALE`，全部为 P1。

P1 处理：保留 receipt、数据库 run 和日志；停止可能扩大数据损失的 apply；确认 private
repository/config/tool/DB/assets 后重新 dry-run 和 apply；显式 verify-remote；用至少一把
matching identity 做 disposable restore。告警只能在新 verified receipt 生成后消除，
不能通过删除失败记录或修改时间戳消除。

## 8. iCloud 与 Git 冲突处理

- 只在一个工作目录中执行写操作。
- Git 操作前等待 iCloud 同步完成。
- 出现 “conflicted copy” 时保留双方文件，比较 front matter、正文和 Git history 后人工合并。
- 不使用 `git reset --hard` 或批量覆盖解决 iCloud 冲突。
- 索引和数据库可以重建；研究对象与原始资产不可用派生物反向覆盖。

## 9. 定期恢复演练

- 每日至少创建一次 verified durable backup，保持 24-hour RPO。
- 每月用主 identity 或第二把受控 identity 在 disposable directory 做 restore 演练。
- 每季度抽样核对 Source 文件 hash 与 offline key custody。
- 每个正式版本执行一次 clean-clone full recovery。
- 演练结果写入 Monthly Review 或 Release Checklist；工程通过不等于发布批准。

## 10. 当前基线

- Repository mode: local-first, private Git repository required
- Default branch: `main`
- Durable backend: private GitHub prerelease `research-os-durable-backups-v1`
- Backup payload: Candidate + operations snapshots in the candidate set, plus Source
  assets；Git/secrets/旧 OS scheduler 状态分开恢复
- v0.2 release: 18/18 Ready, human-approved and published as `v0.2.0` with attached
  wheel, sdist and SHA-256 manifest
- v0.3 release: BLOCKED at 16/21 F-023 checks; the remaining checks are WP-530
  natural Resolution, WP-620 real Pilot, v0.3 cadence reviews, Known Limitations
  reading acknowledgement, and F-024 human release approval
