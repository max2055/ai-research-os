# 阶段 1 验收

## 当前结论

本地文件系统骨架、对象模板、元数据和 Agent 工作边界均已建立，阶段状态为 `completed`。

## 目录骨架

- [x] `00_System`：规则、Schema、Workflow 和验收。
- [x] `01_Inbox`：Source 与原始材料入口。
- [x] `02_Knowledge`：稳定实体画像。
- [x] `03_Theses`：研究假设生命周期。
- [x] `04_Evidence`：Event Card。
- [x] `05_Research`：项目、队列、复盘和工作笔记。
- [x] `06_Reports`：主题与周期报告。
- [x] `07_Templates`：标准对象和复盘模板。
- [x] `08_Indexes`：机器维护索引。
- [x] `09_Automation`：脚本、提示词、测试和运行手册。

## 核心文件

- [x] `README.md` 定义目标、闭环、原则和阶段。
- [x] `AGENTS.md` 定义 Research Engineering Agent 边界。
- [x] `Repository_Structure.md` 定义目录所有权和对象生命周期。
- [x] `Metadata_Schema.md` 定义五类核心对象字段。
- [x] `Workflow.md` 定义 Source→Event→Thesis→Report→Review 流程。

## 标准模板

- [x] Source。
- [x] Event Card。
- [x] Thesis Card。
- [x] Company Profile。
- [x] Research Memo。

后续阶段新增 Weekly Review、Monthly Review、Rule Change Proposal、Research Project 和 Research Handoff 模板，没有破坏阶段 1 的核心对象结构。

## 生命周期与安全边界

- [x] 永久 ID 规则明确。
- [x] `pending`、`reviewed`、`rejected`、`superseded` 明确。
- [x] 机器生成对象默认 pending。
- [x] 原始材料不得覆盖。
- [x] Agent 不得自动批准 Evidence 或改变 Thesis 置信度。
- [x] final/reviewed Report 的权威化规则明确。

## 验证证据

- 十个顶层目录全部存在。
- 五个核心模板全部存在。
- 后续统一校验器可以读取并验证阶段 1 定义的元数据。

