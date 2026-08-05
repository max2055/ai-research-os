# M1 模块化内核与正式 Schema 进度

更新日期：2026-07-29  
状态：`completed`

## 任务状态

| ID | 状态 | 交付与证据 |
|---|---|---|
| M1-01 | completed | `pyproject.toml`、`src/research_os`、console command、`research-os doctor` |
| M1-02 | completed | validation、indexing、status、drafts、metrics、ontology/export 已按 domain/repository/service 分层；原 2,048 行 `legacy_core.py` 缩为 111 行纯兼容门面 |
| M1-03 | completed | Pydantic v2 五类正式 Schema；ruamel.yaml round-trip；49/49 对象通过 |
| M1-04 | completed | Review 状态机与 Report publish/supersede 生命周期 |
| M1-05 | completed | 多文件 `FileTransaction`；preflight、失败回滚；Event 与 Source processing 原子提交 |
| M1-06 | completed | migration plan/apply/rollback、hash precondition、备份 manifest、幂等测试 |
| M1-07 | completed | `09_Automation/research_os.py` 与 `research_os_core.py` 兼容入口保留；旧命令在已安装产品环境中通过 subprocess 测试 |
| M1-08 | completed | Ruff、全 package mypy strict、pytest-cov、GitHub Actions；本地与 clean clone 等价 CI 全绿 |

## Gate 结果

- product tests：49/49。
- product core coverage：86.27%，高于 80% Gate。
- Ruff：通过。
- mypy strict：33 个 source files 通过，无 legacy 排除。
- formal Schema：49/49。
- no-op round-trip：49/49 与原文件字节一致。
- validation：0 error、18 个已解释的 `REV003` warning。
- index drift：0。
- `research-os doctor`：全部检查通过。
- CLI：真实 subprocess 路径和固定输出 golden test 通过。
- clean clone：commit `e4c71c2` 在独立目录重新安装后，lint、format、type、test、coverage、doctor、validate、index 和旧脚本入口全部通过。

## Round-trip 保证

- 49 个研究对象 no-op render 与原文件字节完全一致。
- metadata 编辑后人工正文保持字节一致。
- 未知字段保留。
- YAML 键顺序、引号与人工注释保留。
- 未对 49 个对象执行批量 Schema migration，因此没有产生研究对象 diff。

## 运行环境结论

iCloud 会反复把 workspace 内 editable install 的 `.pth` 标为 hidden；
开发 venv 必须放在同步目录外。产品运行时依赖以 `pyproject.toml` 为准，
旧脚本入口属于命令兼容层，不再维持无依赖的第二套业务内核。

完整验收见 `00_System/M1_Productization_Acceptance.md`。
