# 企业采购决策助手

基于 LangGraph、DeepAgents 与 MCP 构建的采购 Agent，支持**研发项目采购**与**企业 IT 设备采购**两种分析方向。用户用自然语言提供需求、预算和到货期限，系统查询现有 ERP 物料、库存、供应商与订单数据，结合确定性策略工具评估候选方案。订单创建或修改需人工审批。

## 业务场景

### 研发项目采购

围绕项目需求、总预算和交付期限查询 ERP 数据及已核实的供应商报价。`evaluate_project_procurement` 使用 Decimal 计算金额并校验预算、交期；缺少交期证据时标记待核实，避免把未知条件当成可执行方案。

### 企业 IT 设备采购

围绕设备类型、数量、CPU、内存、存储、操作系统、总预算、到货日期和保修期分析候选设备。`evaluate_it_equipment_procurement` 对已核实数据逐项校验，区分可选、待确认和不符合约束的方案；仅对满足全部条件的候选方案按总价排序。缺少配置、报价、交期或保修信息时，先提示核实，不推测采购结果。

两个方向复用现有 ERP 查询和订单工具。分析时须保留 ERP、供应商报价或用户确认的数据来源；订单只能使用已核实的 ERP 物料 ID，并经 Human-in-the-Loop 审批。

## 技术栈

- Agent 编排：LangGraph、DeepAgents
- 业务工具：MCP、FastMCP、LangChain Tool Calling
- 服务端：FastAPI、Server-Sent Events
- 会话状态：MongoDB Checkpointer
- 执行隔离：OpenSandbox
- 前端：Vue 3

## 关键实现

- 采购分析与采购订单两个子 Agent 通过 YAML 配置职责和工具，分别处理查询决策与订单操作。
- FastMCP 将现有 ERP 供应商、物料、库存和订单 REST API 暴露为 MCP Tools。
- 两类采购策略工具计算金额并校验业务约束；缺失数据保留待确认状态，不作为合格方案推荐。
- LangGraph interrupt 与 Command resume 处理信息补充和写操作审批，MongoDB Checkpointer 保存可恢复状态。
- FastAPI SSE 与 Vue 展示对话、工具执行及审批流程；Agent 代码任务在 OpenSandbox 中隔离执行。

## 启用 IT 设备场景

本仓库复用现有 ERP 接口，**未内置 IT 设备目录、真实供应商报价，也未新增 ERP API**。要得到可执行的 IT 设备推荐，需要在 ERP、供应商报价或用户提供的数据中核实设备型号及对应物料 ID、设备类型、CPU/内存/存储/操作系统规格、单价、预计到货日期和保修期。数据不完整时，助手会列出待确认项。

例如可输入：“需要 20 台笔记本电脑，至少 8 核 CPU、16GB 内存、512GB 存储，Windows 11，总预算 16 万元，2026-11-30 前到货，保修不少于 24 个月。请基于已核实的设备与报价分析候选方案。”

## 本地验证

在项目根目录打开 PowerShell，运行：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1
```

该脚本运行仓库配置的 Python 与前端验证流程。连接 ERP、MongoDB、模型服务和 OpenSandbox 的完整演示还需配置对应服务地址及凭据。
