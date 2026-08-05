# WP-120 Pilot Universe 实体人审包

状态：`passed`（max 2026-08-05 全部 approve：9 Sector + 51 Company → reviewed）

审核记录：9 个 Sector 一个 REV 决策；51 家 Company 按 8 环节分 8 个 REV 决策。
所有实体 `review_status: reviewed`，0 pending。REV 决策落盘
`05_Research/Reviews/Decisions/REV-20260805-001..009`。

## 使用方法

1. 下表逐项检查：公司身份、region、coverage_tier、sector 归属是否正确。
2. 同意的实体在下方勾选批（或回复"全部 approve"）。
3. 不同意的标注修改（`edit`：改字段；`reject`：删除）。
4. 批准后由 Agent 批量 `review apply --apply --decision approve` 转 reviewed。
5. 所有实体默认 pending；不 approved 的保持 pending。

## Sector 审核表

| Sector ID | 定义 | core_company_ids 数量 | Region 关注点 | Decision |
|---|---|---|---|---|
| SEG-semiconductor-materials-equipment | 材料/设备 | 8 | 非中美节点：ASML(荷)/TEL/信越(日) | ⬜ |
| SEG-foundry-packaging-test | 制造/封装/测试 | 7 | 非中美节点：TSMC/ASE(台) | ⬜ |
| SEG-compute-silicon | 算力芯片 | 8 | 中美优先 | ⬜ |
| SEG-memory-storage | 存储 | 5 | 非中美节点：SK hynix/Samsung(韩) | ⬜ |
| SEG-server-network-interconnect | 服务器/网络 | 7 | 中美优先 | ⬜ |
| SEG-datacenter-infrastructure | DC 基础设施 | 4 | 非中美节点：Schneider(法) | ⬜ |
| SEG-cloud-ai-infrastructure | 云/AI 基建 | 7 | 中美优先 | ⬜ |
| SEG-models | 模型 | 8 | 中美优先 | ⬜ |
| SEG-enterprise-applications | 企业应用 | 6 | v0.2 存量 | ⬜ |

## Company 审核表（按环节）

### 环节 1 材料设备（8）
| Company | Region | Tier | Sector | Decision |
|---|---|---|---|---|
| COM-asml | REG-nl | core | 材料设备 | ⬜ |
| COM-lam-research | REG-us | core | 材料设备 | ⬜ |
| COM-applied-materials | REG-us | core | 材料设备 | ⬜ |
| COM-kla | REG-us | core | 材料设备 | ⬜ |
| COM-tokyo-electron | REG-jp | core | 材料设备 | ⬜ |
| COM-shin-etsu | REG-jp | core | 材料设备 | ⬜ |
| COM-amec | REG-cn | core | 材料设备 | ⬜ |
| COM-naura | REG-cn | core | 材料设备 | ⬜ |

### 环节 2 制造/封装/测试（7）
| Company | Region | Tier | Sector | Decision |
|---|---|---|---|---|
| COM-tsmc | REG-tw | core | 制造封装 | ⬜ |
| COM-samsung-foundry | REG-kr | core | 制造封装 | ⬜ |
| COM-globalfoundries | REG-us | core | 制造封装 | ⬜ |
| COM-smic | REG-cn | core | 制造封装 | ⬜ |
| COM-jcet | REG-cn | core | 制造封装 | ⬜ |
| COM-ase | REG-tw | core | 制造封装 | ⬜ |
| COM-amkor | REG-us | core | 制造封装 | ⬜ |

### 环节 3 算力芯片（8）
| Company | Region | Tier | Sector | Decision |
|---|---|---|---|---|
| COM-nvidia | REG-us | core | 算力芯片 | ⬜ |
| COM-amd | REG-us | core | 算力芯片 | ⬜ |
| COM-intel | REG-us | core | 算力芯片 | ⬜ |
| COM-broadcom | REG-us | core | 算力芯片 | ⬜ |
| COM-marvell | REG-us | core | 算力芯片 | ⬜ |
| COM-cambricon | REG-cn | core | 算力芯片 | ⬜ |
| COM-hygon | REG-cn | core | 算力芯片 | ⬜ |
| COM-huawei-hisilicon | REG-cn | core | 算力芯片 | ⬜ |

### 环节 4 存储（5）
| Company | Region | Tier | Sector | Decision |
|---|---|---|---|---|
| COM-sk-hynix | REG-kr | core | 存储 | ⬜ |
| COM-samsung-electronics | REG-kr | core | 存储 | ⬜ |
| COM-micron | REG-us | core | 存储 | ⬜ |
| COM-ymtc | REG-cn | core | 存储 | ⬜ |
| COM-cxmt | REG-cn | core | 存储 | ⬜ |

### 环节 5 服务器/网络（7）
| Company | Region | Tier | Sector | Decision |
|---|---|---|---|---|
| COM-supermicro | REG-us | core | 服务器网络 | ⬜ |
| COM-dell | REG-us | core | 服务器网络 | ⬜ |
| COM-hpe | REG-us | core | 服务器网络 | ⬜ |
| COM-arista | REG-us | core | 服务器网络 | ⬜ |
| COM-cisco | REG-us | core | 服务器网络 | ⬜ |
| COM-inspur | REG-cn | core | 服务器网络 | ⬜ |
| COM-zhongji-innolight | REG-cn | core | 服务器网络 | ⬜ |

### 环节 6 DC 基础设施（4）
| Company | Region | Tier | Sector | Decision |
|---|---|---|---|---|
| COM-vertiv | REG-us | core | DC 基建 | ⬜ |
| COM-eaton | REG-us | core | DC 基建 | ⬜ |
| COM-schneider-electric | REG-fr | core | DC 基建 | ⬜ |
| COM-catl | REG-cn | core | DC 基建 | ⬜ |

### 环节 7 云/AI 基建（6 新建 + COM-microsoft）
| Company | Region | Tier | Sector | Decision |
|---|---|---|---|---|
| COM-aws | REG-us | core | 云/AI 基建 | ⬜ |
| COM-google-cloud | REG-us | core | 云/AI 基建 | ⬜ |
| COM-coreweave | REG-us | core | 云/AI 基建 | ⬜ |
| COM-aliyun | REG-cn | core | 云/AI 基建 | ⬜ |
| COM-bytedance-cloud | REG-cn | core | 云/AI 基建 | ⬜ |
| COM-baidu-cloud | REG-cn | core | 云/AI 基建 | ⬜ |

### 环节 8 模型需求（6 新建 + COM-openai/anthropic）
| Company | Region | Tier | Sector | Decision |
|---|---|---|---|---|
| COM-meta | REG-us | core | 模型 | ⬜ |
| COM-xai | REG-us | core | 模型 | ⬜ |
| COM-deepseek | REG-cn | core | 模型 | ⬜ |
| COM-zhipu | REG-cn | core | 模型 | ⬜ |
| COM-tongyi | REG-cn | core | 模型 | ⬜ |
| COM-doubao | REG-cn | core | 模型 | ⬜ |

## 批量审核快捷方式

- 回复"**全部 approve**"：9 Sector + 51 Company 全转 reviewed。
- 回复"**除 X 外全部 approve**"：X 保持 pending，其余转 reviewed。
- 逐项指出修改项（如 `COM-oracle 改 tracked→core`）。

## 完成标准

- 全部实体有明确 human decision（approve/edit/reject）。
- approve 的实体 `review_status: reviewed`，REV 决策落盘。
- 未 approve 的保持 pending，不自动转。
