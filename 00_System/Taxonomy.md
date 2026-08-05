# AI 产业分类体系 v0.1

## 1. 使用原则

Taxonomy 用于稳定分类，Ontology 用于表达实体之间的关系。

当前阶段只使用 Taxonomy，不提前引入图数据库。

每个 Source、Event、Thesis 和 Knowledge 对象应尽量使用以下稳定标签。新增一级分类需要人工审核；新增公司、产品或技术实体不等于修改分类体系。

## 2. 产业层级

### INF：AI 基础设施

#### INF-COMPUTE：计算

- `INF-GPU`：通用 GPU
- `INF-ASIC`：专用 AI 加速器
- `INF-CPU`：CPU 与主机计算
- `INF-EDGE`：端侧和边缘计算

#### INF-MEMORY：存储与内存

- `INF-HBM`：高带宽内存
- `INF-DRAM`：通用内存
- `INF-STORAGE`：数据存储

#### INF-NETWORK：网络

- `INF-INTERCONNECT`：芯片和服务器互连
- `INF-DATACENTER-NETWORK`：数据中心网络

#### INF-DATACENTER：数据中心

- `INF-SERVER`：服务器与机架
- `INF-COOLING`：散热
- `INF-POWER`：供配电
- `INF-ENERGY`：能源供给

#### INF-CLOUD：云

- `INF-CLOUD-COMPUTE`：云端算力
- `INF-CLOUD-AI`：云 AI 平台

### MOD：模型层

- `MOD-FOUNDATION`：基础模型
- `MOD-REASONING`：推理模型
- `MOD-MULTIMODAL`：多模态模型
- `MOD-SMALL`：小型与端侧模型
- `MOD-OPEN`：开放权重模型
- `MOD-EMBEDDING`：嵌入与检索模型

### DEV：AI 开发与运行平台

- `DEV-TRAINING`：训练平台
- `DEV-INFERENCE`：推理平台
- `DEV-EVALUATION`：评测与可观测性
- `DEV-DATA`：数据工程与合成数据
- `DEV-SECURITY`：AI 安全与治理
- `DEV-AGENT-FRAMEWORK`：Agent 框架
- `DEV-TOOL-PROTOCOL`：工具调用协议与互操作标准
- `DEV-MEMORY`：上下文和记忆基础设施
- `DEV-ORCHESTRATION`：Agent 编排与运行时

### APP：AI 应用

#### APP-ENTERPRISE：企业应用

- `APP-CRM`：客户关系管理
- `APP-ERP`：企业资源计划
- `APP-ITSM`：IT 服务管理
- `APP-HCM`：人力资本管理
- `APP-COLLABORATION`：办公与协作
- `APP-DATA-ANALYTICS`：数据与分析
- `APP-CYBERSECURITY`：网络安全
- `APP-VERTICAL`：垂直行业企业应用

#### APP-KNOWLEDGE：知识工作

- `APP-CODING`：软件开发
- `APP-RESEARCH`：研究与信息分析
- `APP-DESIGN`：设计与内容生产
- `APP-LEGAL`：法律服务

#### APP-CONSUMER：消费者应用

- `APP-ASSISTANT`：个人助理
- `APP-CONTENT`：内容生成与娱乐
- `APP-EDUCATION`：教育

### SRV：服务层

- `SRV-CONSULTING`：咨询
- `SRV-INTEGRATION`：实施和系统集成
- `SRV-MANAGED`：托管服务
- `SRV-DATA-LABELING`：数据标注

## 3. 横向研究维度

以下标签描述横向变量，可与产业标签组合使用。

### 技术成熟度

- `MAT-RESEARCH`
- `MAT-PROTOTYPE`
- `MAT-PILOT`
- `MAT-PRODUCTION`
- `MAT-SCALE`

### 客户类型

- `CUS-CONSUMER`
- `CUS-SMB`
- `CUS-ENTERPRISE`
- `CUS-GOVERNMENT`
- `CUS-DEVELOPER`

### 商业模式

- `BM-SEAT`
- `BM-SUBSCRIPTION`
- `BM-USAGE`
- `BM-TASK`
- `BM-OUTCOME`
- `BM-TRANSACTION`
- `BM-SERVICE`

### 竞争优势

- `MOAT-TECHNOLOGY`
- `MOAT-DATA`
- `MOAT-DISTRIBUTION`
- `MOAT-WORKFLOW`
- `MOAT-PERMISSION`
- `MOAT-ECOSYSTEM`
- `MOAT-SCALE`
- `MOAT-BRAND`
- `MOAT-REGULATION`

### 事件类型

- `EV-PRODUCT`
- `EV-PRICING`
- `EV-CUSTOMER`
- `EV-PARTNERSHIP`
- `EV-FINANCIAL`
- `EV-MANAGEMENT`
- `EV-TECHNOLOGY`
- `EV-REGULATION`
- `EV-CAPITAL`
- `EV-COMPETITION`

## 4. 首个专题的分类映射

“AI Agent 时代的企业软件价值链”主要使用：

- `DEV-AGENT-FRAMEWORK`
- `DEV-TOOL-PROTOCOL`
- `DEV-MEMORY`
- `DEV-ORCHESTRATION`
- `APP-CRM`
- `APP-ERP`
- `APP-ITSM`
- `APP-COLLABORATION`
- `APP-DATA-ANALYTICS`
- `CUS-ENTERPRISE`
- `BM-SEAT`
- `BM-USAGE`
- `BM-TASK`
- `BM-OUTCOME`
- `MOAT-DATA`
- `MOAT-DISTRIBUTION`
- `MOAT-WORKFLOW`
- `MOAT-PERMISSION`
- `MOAT-ECOSYSTEM`

## 5. Taxonomy 变更规则

可以直接新增：

- 具体公司。
- 具体人物。
- 具体产品。
- 具体事件。

需要人工审核：

- 新增一级或二级产业分类。
- 修改现有分类含义。
- 合并或废弃稳定标签。
- 改变历史对象使用的标签。

变更时必须记录：

- 变更原因。
- 受影响对象。
- 迁移方案。
- 生效日期。
