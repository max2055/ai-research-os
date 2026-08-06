# A-020 Phase 0-1 阶段验收与恢复演练

状态：`passed`
日期：2026-08-06
基线提交：`f80c61e`（Field Gate §9.3 完成）
工作包：A-020（`02_Phase_0_1_Ontology_and_Universe.md` §7 / §9 Gate）

## 验收范围

Phase 0-1 Gate 清单（§10）中 A-020 负责的两项：

1. **migration rollback 通过**：v0.3 新实体（Security/Product 等）可回滚。
2. **clean-clone recovery 通过**：从 Git + 加密 Source 资产备份恢复当前状态。

本验收在独立临时副本执行，主仓库零改动（演练后工作区 clean，0 变更）。

## 1. Migration Rollback 演练

### 方法

使用 `MigrationEngine`（`src/research_os/services/migration.py`）对 v0.3
Security 实体执行 AddFieldMigration → apply → rollback，验证字节级恢复。

- Migration：`MIG-A020-ROLLBACK-DRILL`（AddFieldMigration，`object_types={security}`，
  field `a020_drill_marker` = `rollback-verified`）
- 对象：10 个 Security 实体（INS-*）
- 备份根：`09_Automation/migrations/backups/`（演练后清理）

### 结果

| 步骤 | 结果 |
|---|---|
| Plan | PASS — 10 changes（10 Security 全命中）|
| Apply | PASS — 21 文件写入（10 目标 + 10 备份 + 1 manifest）|
| 标记字段 | PASS — 10/10 Security 含 `a020_drill_marker` |
| Rollback | PASS — 10 文件恢复 |
| 字节级恢复 | PASS — 10/10 与演练前 SHA-256 完全一致 |
| Validate（rollback 后）| PASS — 0 errors |

### 结论

v0.3 实体 migration 具备完整 rollback 能力：hash precondition 校验、
事务回滚、备份 manifest 一致。migration rollback 演练通过。

## 2. Clean-Clone Recovery 演练

### 方法

按 `00_System/Recovery_Runbook.md` §3-4 流程，在当前 633 对象基线执行：

1. 流式打包 `01_Inbox/_assets/` → tar → AES-256-CBC/PBKDF2/salted 加密备份
   （不落明文存档）。
2. `git clone --no-local` 独立 clone（临时目录）。
3. 新 Python venv + `pip install -e ".[dev,ui]"`。
4. 解密流式恢复资产到 clean clone。
5. 全量验证：doctor / validate / index / verify-assets / tests / ruff / mypy。

### 结果

| 检查 | 结果 |
|---|---|
| 加密备份 | PASS — 81,541,152 bytes（SHA-256 `ee517b53...`）|
| 独立 clone | PASS — 633 对象（55 Source / 48 Event / 260 assertion / 5 product / 10 security / 163 review）|
| 新 venv install | PASS — `.[dev,ui]` |
| 资产恢复 | PASS — 52 asset dirs |
| verify-assets | PASS — 52/52 SHA-256 精确匹配 |
| doctor | PASS — 0 warnings, 0 asset failures |
| validate | PASS — 0 errors, 0 warnings |
| index --check | PASS — 0 drift |
| pytest | PASS — 119 passed |
| ruff | PASS |
| mypy | PASS — 57 source files |

### 结论

从 Git commit + 加密 Source 资产备份可在 clean clone 完整恢复当前 633 对象
状态，零 hash / validation / index 失败。clean-clone recovery 演练通过。

## 3. Gate 决策

| Gate | 结果 |
|---|---|
| migration rollback | PASS |
| clean-clone recovery | PASS |

A-020 验收通过。Phase 0-1 Gate 清单（§10）剩余核查项：

- [x] RCP-v03-001～003 已批准
- [x] v0.1 历史对象迁移无语义漂移（MIG 记录 + round-trip 测试）
- [x] 8–10 个 Pilot 板块定义明确（9 Sector）
- [x] 30–50 家 Core Company 注册（51 v0.3 + 3 v0.2 = 54；**2026-08-06 复核批准扩容至 54**）
- [x] Company 与 Security 分离（10 INS-* 实体）
- [x] Product/Technology/Metric 可独立引用（5 PRD + schema 注册）
- [x] 100+ 关系 assertion 可导出，30 条通过真实人审（260 assertion / 44 reviewed）
- [x] 0 validation error；0 index drift
- [x] coverage ≥80%（119 tests）
- [x] migration rollback 和 clean-clone recovery 通过（本验收）

## 4. 已知非阻塞项

- **Core Company 54 家已批准**：D4 复核（2026-08-06）确认 51 v0.3 + 3 v0.2 老公司
  （anthropic/microsoft/openai）全部为 AI Compute Chain 关键节点，批准 Core 上限
  扩容至 54（详见 WP-011 D4 更新）。另有 5 家 v0.2 老公司
  （oracle/palantir/salesforce/sap/servicenow）为 tracked，0 discovery。
- **source_channel 类型未实现**（RCP-v03-003 仅 ID 占位）：59/59 Company
  source_channel_ids 空，来源核验改用 evidence_ids。待后续 RCP 实现。
- **remote 未配置**：clean-clone 以本地 `git clone --no-local` 等价 CI 验收；
  发布 Gate 须在 private remote 配置后确认（M1 同）。
- 加密资产备份为演练临时副本，非持续备份服务；owner 需配置 durable off-device
  加密目标与 key-recovery 策略（Recovery_Runbook §6）。
