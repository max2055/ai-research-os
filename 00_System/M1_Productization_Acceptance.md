# M1 模块化内核与正式 Schema 验收

验收日期：2026-07-29  
结论：`accepted`  
基线提交：`e4c71c2bfe7bca5412d0da0939c9dd481d7a5237`

## 1. 验收范围

本次验收覆盖 `Productization_Roadmap_v1.md` 的 M1-01 至 M1-08。
没有修改研究对象结论、Review history、Thesis confidence 或人工正文。

## 2. 交付确认

| Gate | 结果 | 证据 |
|---|---|---|
| 可安装 package 与 CLI | PASS | clean clone 中 editable install 成功，`research-os doctor` 通过 |
| 单体 core 拆分 | PASS | 原 2,048 行实现缩为 111 行纯 re-export 门面；产品 CLI 只依赖 `runtime.product` |
| 正式 Schema | PASS | Source、Event、Thesis、Company、Report 共 49/49 通过 Pydantic v2 |
| 无损 round-trip | PASS | 49/49 no-op render 字节一致；正文、未知字段、顺序、引号和注释保留 |
| 生命周期 | PASS | 非法 Review 迁移拒绝；Report publish/supersede 联动有测试 |
| 事务与回滚 | PASS | preflight、半途失败回滚、Event+Source 原子提交有测试 |
| Migration Framework | PASS | plan/apply/idempotency/rollback/hash precondition 有测试 |
| CLI 兼容 | PASS | 旧脚本路径在安装环境中通过；新旧命令行为由 subprocess/golden tests 覆盖 |
| 质量门槛 | PASS | 49 tests；86.27% coverage；Ruff、mypy strict 全绿 |
| 仓库健康 | PASS | 0 validation error；0 index drift；49 formal Schema objects |

## 3. 干净环境演练

执行方式：

```bash
git clone --no-local <local-repository> <clean-directory>
python3 -m venv <clean-venv>
<clean-venv>/bin/pip install -e "<clean-directory>[dev]"
ruff check src 09_Automation/tests 09_Automation/research_os.py 09_Automation/research_os_core.py
ruff format --check src 09_Automation/tests
mypy src/research_os
pytest --cov=research_os --cov-fail-under=80
research-os doctor
research-os validate
research-os index --check
python -B 09_Automation/research_os.py validate
```

结果：

- Python 3.14.6 本地 clean clone 全部通过。
- CI workflow 固定使用 Python 3.12，包含相同 lint、type、test、coverage、doctor、validate 和 index Gate。
- private remote 尚未配置，因此本次以 clean clone 等价 CI 验收；远程 CI 首次运行不阻塞 M2，但发布 Gate 必须再次确认。

## 4. 数据保护确认

- Git 工作树中的 49 个研究对象未发生批量改写。
- Markdown 继续作为事实源。
- SQLite、JSONL 和指标展示仍为可重建派生视图。
- 所有新生成对象默认 `review_status: pending`。
- 自动化没有提高 Thesis confidence，也没有自动批准研究对象。

## 5. 已知非阻塞项

- 18 个 `REV003` warning 表示 reviewed Event 引用仍待 Source 级审核的 Source；语义已由 RCP-001 固定，不属于 validation error。
- 远程 GitHub CI 等 private remote 配置后补跑。
- Project、Review、Action 正式 Schema 和多项目过滤属于 M2。

## 6. Gate 决策

M1 Gate 通过。后续开发进入 M2“多项目与通用审核”，不再向
`legacy_core.py` 添加业务逻辑。
