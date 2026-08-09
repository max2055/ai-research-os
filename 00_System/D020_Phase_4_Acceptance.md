# D-020 Phase 4 验收与恢复记录

状态：`passed`
日期：2026-08-09
工作包：D-020（`05_Phase_4_Analysis_Mode_Framework.md` §10 测试 / §12 回滚）
前置：D-019 10-case Field Gate PASS（`70ec868`）、真实 provider（DeepSeek）接入（`4b3ac95`）

## 验收范围（Phase 4 §10/§12）

replay 创建新 ID、hash 可重建、rebuild 通过、失败不留半成品、回滚约束。

## 验收记录

| 项 | 验证 | 结果 |
|---|---|---|
| 对象可校验 | `research-os validate` | 0 error / 0 warning（32 个 ANL-20260809-* 全部通过 schema）|
| 索引可重建 | `research-os index --apply` → 9 canonical indexes | 无 drift |
| replay 创建新 ID（§10） | `analyze replay ANL-20260809-002 --model-provider deepseek` dry-run | 预览新 ID `ANL-20260809-041`，不覆盖旧 run（真实模型调用、无写盘）|
| replay 不覆盖历史（§12） | `write_new_file` 拒绝已存在路径 | `FileExistsError`（test_phase4_acceptance）|
| retry 不创建重复 Run | 同冻结输入重跑 → 新 ID；失败原子无写 | test_phase4_acceptance ReplayCreatesNewIdTests |
| input_snapshot_hash 可重建 | 用 run 的冻结输入重跑 resolve_inputs | 002/020/040 全部 == 存储值 |
| output_hash 可重建 | sha256(body) | 002/020/040 全部 == 存储值 |
| prompt_hash 可重建 | 同模板重渲染 render_prompt | 020/040 ==（模板改动后创建）；**002 不匹配 = 模板改动前创建（中文规则 `bd80478` 前），run 冻结的是创建时模板——正确行为** |
| 失败不留半成品（§10/§12） | Echo adapter（畸形输出）、provider-failure adapter | RunError(output-contract-failed / provider-failure)，无半写入对象 |
| 模式 append-only 版本（§12） | Mode 定义 MOD-ANL-*-v1，升级=新 vN 文件，不静默改已运行模式 | 结构性保证 |
| Run 不反向修改 Evidence | ANL run 是新对象，不触碰 Event/Source/Thesis | 结构性保证 |
| 误生成 run 用 rejected/superseded | ANL-001（管线验证品）→ review_status=rejected（`c676b12`） | 先例确立，不物理删除 |

## D-019 暴露的 rollback 相关项（记录，非阻塞）

- **scenario 模式脆弱**（6/10 case 顽固失败）：若持续不可靠，按 §12 可停用该 mode（deprecated）不影响其他模式——D-019 判定已 PASS，scenario 的 4 个成功 run 保留，缺 6 个 case 已记录。
- **事件级顽固外部引用**（case-7→SRC-052、case-9/10→THS-004、case-3→SRC-040）：D-004 契约正确拦截（no facts outside inputs），误输出不落盘、不留半成品——契约即回滚防线。
- 模型供应商不可用：run 事务在 provider-failure 时保留确定性 input manifest（snapshot hash 已冻结），不产生半成品 ANL（test_analysis_runner provider-failure 用例）。

## replay 语义确认

`analyze replay ANL-ID --current-model` 复用源 run 的冻结输入（mode/as_of/inputs），以当前模型重跑，**创建新 ANL ID**，永不覆盖旧输出（§10 replay 创建新 ID）。验证：dry-run 预览 ANL-20260809-041，旧 ANL-002 字节不变。

## 测试

- 新增 `09_Automation/tests/test_phase4_acceptance.py`（4 项：replay 新 ID + 不覆盖、hash 可重建、失败无半写入）。
- 全量 478 tests 全绿（+4），ruff/mypy clean，validate 0 error。
