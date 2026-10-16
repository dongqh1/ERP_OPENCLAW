# 企业 IT 设备采购方向 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [x]) syntax for tracking.

**Goal:** 在现有采购助手中交付可查询、可评估、可走原订单审批链路的企业 IT 设备采购演示场景，同时保留摩托车零部件和研发项目采购功能。

**Architecture:** Java ERP 新增独立 IT 目录查询 API、规格扩展表与幂等模拟数据；新物料通过现有 `part`、`supplier`、`inventory` 记录关联，订单仍复用原有 `part_id`、订单 API 与 HITL 审批。FastMCP 新增目录工具，采购分析和订单子 Agent 通过该工具查询/复核 IT 设备；现有 IT 硬约束评估器继续决定预算、配置、交期和保修是否满足。所有演示记录带 `IT-DEMO-*` 前缀，并明确标注为模拟数据。

**Tech Stack:** Java 17、Spring Boot、JdbcTemplate、MySQL、FastMCP、Python 3.10+、Pydantic、LangChain Tool Calling、LangGraph/DeepAgents、Vue 3。

## Global Constraints

- 不修改现有摩托车数据初始化器、既有 API 的行为或原订单流程；只新增独立 IT 功能。
- IT 目录是显式标注的本地模拟数据，不得包装成真实市场报价或真实供应商数据；库存字段只代表 ERP 账面库存。
- Java ERP 仓库已有用户未提交文件。只新增本功能所需的新 Java 文件，不能重写或清理现有未提交修改。
- 订单创建和修改继续由 procurement-order Agent 执行并走现有 HITL 审批。
- 单次策略评估处理同一设备类别和数量；所有金额使用 Decimal。
- 前端保留原有项目采购和 IT 入口，并添加摩托车零部件示例，不删除既有页面和交互。

---

### Task 1: 确定性 IT 设备采购策略

**Files:**
- Create: tests/test_it_equipment_policy.py
- Create: src/agent/tools/it_equipment_policy.py

**Interfaces:**
- Produces: evaluate_it_equipment_policy(request: dict) -> dict in the pure policy module.
- Input keys: device_type, requirement, quantity, budget_remaining, deadline, minimum_warranty_months, min_cpu_cores, min_memory_gb, min_storage_gb, allowed_operating_systems, offers.
- Each offer has supplier_name, supplier_id, part_id, device_type, model_name, unit_price, delivery_date, warranty_months, cpu_cores, memory_gb, storage_gb, operating_system, source.
- Returns: request summary, offers with status/failed_constraints/unverified_constraints/estimated_total, eligible recommendation or null, and a Chinese summary.

- [x] 先新增测试：覆盖满足全部约束时推荐最低总价报价；交期或关键规格缺失时待核实且无推荐；预算、设备类型、配置、保修或交期违反时不符合；金额使用 Decimal 精确计算。
- [x] 运行 `python -m pytest tests/test_it_equipment_policy.py -q`，确认首次因策略模块不存在而失败。
- [x] 实现一个无 LangChain/Pydantic 依赖的策略入口，解析日期与 Decimal；只有全部必需检查通过时将状态设为 eligible。
- [x] 再运行上述 pytest，确认策略测试全部通过。

### Task 2: LangChain Tool 与 Agent 工具绑定

**Files:**
- Create: src/agent/tools/it_equipment_procurement.py
- Modify: src/agent/main_agent.py
- Modify: src/agent/subagents/configs/procurement_analyst.yaml
- Modify: tests/test_subagent_loader.py

**Interfaces:**
- Produces: evaluate_it_equipment_procurement LangChain StructuredTool, with Pydantic schema matching evaluate_it_equipment_policy input.
- procurement-analyst receives the new tool through available_tools and YAML tool-name resolution.

- [x] 先扩展 loader 测试：提供名为 evaluate_it_equipment_procurement 的 stub tool，并断言采购分析 Agent 绑定该工具。
- [x] 运行 `python -m pytest tests/test_subagent_loader.py -q`，确认新断言因配置缺少工具而失败。
- [x] 增加嵌套 Pydantic Schema 与 Tool 包装，并在 main_agent.available_tools 和采购分析 YAML 注册工具。
- [x] 再运行该 pytest 与 Python compileall，确认配置解析和语法通过。

### Task 3: 采购 Agent 指令与业务流程

**Files:**
- Modify: src/agent/memory/prompts.py
- Modify: src/agent/memory/AGENTS.md
- Modify: src/agent/subagents/configs/procurement_analyst.yaml
- Modify: src/agent/subagents/configs/procurement_order.yaml
- Modify: src/skills/procurement/procurement-analysis/SKILL.md

- [x] 更新路由规则，明确 IT 设备采购分析进入采购分析 Agent，已确认方案下单进入订单 Agent。
- [x] 在分析指引中写明 ERP/供应商/用户来源、规格字段映射、未知数据不得猜测、工具只做评估不下单。
- [x] 在订单指引中要求复用已核验的 ERP part_id、将设备型号和确认规格写入订单备注，保留预期交期和 HITL。
- [x] 检查提示词字段名与 Task 1 Schema 一致。

### Task 4: 前端入口与项目说明

**Files:**
- Modify: frontend/src/components/ChatArea.vue
- Modify: frontend/src/App.vue
- Modify: frontend/index.html
- Modify: README.md

- [x] 将界面名称改成企业采购决策助手，列出研发项目采购和 IT 设备采购能力。
- [x] 增加一个可点击 IT 采购示例，由 ChatArea 发出 suggestion 事件并复用 App.handleSend。
- [x] README 说明两个业务方向、规格/预算/交期/保修判定、数据来源约束和 ERP 设备目录前置条件。
- [x] 运行 `npm test` 与 `npm run build`，检查交互回归和生产构建。

### Task 5: 整体验证与交付

**Files:**
- Verify: tests/test_it_equipment_policy.py
- Verify: tests/test_subagent_loader.py
- Verify: frontend/

- [x] 运行 `python -m pytest tests/test_it_equipment_policy.py tests/test_subagent_loader.py -q`。
- [x] 运行 `python -m compileall -q src/agent`。
- [x] 运行前端测试和生产构建。
- [x] 检查 `git diff --check` 与 Git 状态，确保已有用户未提交文件没有进入本次变更。

---

## 增量扩展：可查询的 IT 设备采购演示目录

### Task 6: Java ERP IT 目录 API 与隔离演示数据

**Files:**
- Create: Java ERP `src/main/java/com/motorparts/init/ItEquipmentDemoInitializer.java`
- Create: Java ERP `src/main/java/com/motorparts/controller/ItEquipmentController.java`
- Create: Java ERP `src/main/java/com/motorparts/service/ItEquipmentCatalogService.java`
- Create: Java ERP `src/main/java/com/motorparts/dto/ItEquipmentOffer.java`

- [x] 增加 IT 规格扩展表，数据按稳定物料编码关联到 `part`；新增演示供应商、IT 物料和账面库存时只使用 `IT-DEMO-*` 编码，初始化重复运行不会覆盖用户订单或既有摩托车记录。
- [x] 增加 `/api/it-equipment/search`，支持类别、CPU、内存、存储、操作系统、单价、保修和交期筛选，返回 ERP `part_id`、供应商、规格、账面库存、模拟来源和预计交付日期。
- [x] 响应显式写出本地模拟来源，预计交付日期从当前日期与演示交期天数计算，不将账面库存解释为供应商供货量。
- [x] 只新增文件；不修改 Java 仓库中已有未提交的控制器、服务、配置和初始化器。

### Task 7: FastMCP 与 Agent 目录查询/订单复核

**Files:**
- Create: `src/mcp_server/tools/it_equipment_tools.py`
- Modify: `src/mcp_server/server_main.py`
- Modify: `src/agent/tools/mcp_client.py`
- Modify: `src/agent/subagents/configs/procurement_analyst.yaml`
- Modify: `src/agent/subagents/configs/procurement_order.yaml`
- Modify: `src/agent/memory/AGENTS.md`
- Modify: `src/skills/procurement/procurement-analysis/SKILL.md`

- [x] 新增 `it_equipment_search` FastMCP Tool，映射查询参数并原样保留可核验来源与 ERP ID。
- [x] 让分析 Agent 获取该工具；让订单 Agent 在已有订单审批之前用该工具复核 IT `part_id`、型号、供应商和配置。
- [x] 保留“不得把模拟报价冒充真实市场来源”“账面库存不是供应商可供量”指引；保留原人工 approve/reject 流程。

### Task 8: 前端入口与运行说明

**Files:**
- Modify: `frontend/src/components/ChatArea.vue`
- Modify: `README.md`

- [x] 保留研发项目采购和 IT 采购卡片，并增加原摩托车零部件采购示例卡片；三个入口共用已有的对话发送流程。
- [x] 页面与文档清楚标注 IT 数据为本地模拟目录，写明启动 Java ERP 后由 API/MCP 查询，并说明订单仍经过人工审批。

### Task 9: 收尾检查

- [x] 检查新增/修改清单，确保摩托车 SQL、初始化器及原 API 行为没有被改动。
- [x] 检查差异和空白错误；按当前任务约束不新增或运行测试。
