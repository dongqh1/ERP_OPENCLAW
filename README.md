# 研发项目采购决策助手

基于 LangGraph、DeepAgents 与 MCP 构建的项目制采购 Agent。用户以自然语言提供项目需求、可用预算和期望到货日期，系统查询 ERP 物料、供应商及历史采购信息，评估有来源依据的报价，并生成采购建议。订单写入仍需人工审批。

## 项目场景

通用采购查询通常只能返回物料或供应商信息，难以直接回答“这个项目能否在预算内按期采购”。本项目在现有 ERP REST API 适配层上增加项目约束决策能力：

1. 采购分析 Agent 收集项目约束及候选报价，并保留 ERP、供应商报价或用户确认的数据来源。
2. `evaluate_project_procurement` 使用 Decimal 金额计算，逐项校验预算和交付期限；缺少可靠交期时标记为待核实，不将未知数据当成可执行方案。
3. 用户确认采购后，订单 Agent 生成订单草稿；订单创建和修改继续通过 LangGraph Human-in-the-Loop 审批。

## 技术栈

- Agent 编排：LangGraph、DeepAgents
- 业务工具：MCP、FastMCP、LangChain Tool Calling
- 服务端：FastAPI、Server-Sent Events
- 会话状态：MongoDB Checkpointer
- 执行隔离：OpenSandbox
- 前端：Vue 3

## 关键实现

- 以采购分析和采购订单两个子 Agent 分工处理查询决策与订单操作，按 YAML 配置工具集和职责。
- 通过 FastMCP 将 ERP 供应商、物料、库存和订单 REST API 暴露为 MCP Tools。
- 使用独立确定性策略工具计算项目采购金额并校验交期；推荐结果带报价来源，缺少交期证据时不输出“可执行推荐”。
- 使用 LangGraph interrupt 与 Command resume 处理订单信息补充和写操作审批，MongoDB Checkpointer 保存可恢复状态。
- 通过 FastAPI SSE 和 Vue 展示对话、工具执行及审批流程；Agent 代码任务运行在 OpenSandbox。

## 本地验证

在项目根目录打开 PowerShell，运行：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1
```

该脚本会运行仓库配置的 Python 与前端验证流程。连接 ERP、MongoDB、模型服务和 OpenSandbox 的完整演示仍需配置对应服务地址及凭据。
