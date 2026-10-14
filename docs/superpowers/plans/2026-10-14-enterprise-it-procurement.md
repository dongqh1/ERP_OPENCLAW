# 企业 IT 设备采购方向 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** 在现有采购助手中交付可追溯、可验证的企业 IT 设备采购评估能力，并保留研发项目采购和人工审批流程。

**Architecture:** 新增纯 Python 策略模块负责确定性约束判定，LangChain Tool 负责参数 Schema 与 Agent 调用。采购分析 Agent 复用现有 ERP 查询和供应商工具；未知设备属性保持待核实，不增加未经证实的 ERP API 或产品数据。

**Tech Stack:** Python 3.10+、Pydantic、LangChain Tool Calling、LangGraph/DeepAgents、Vue 3、pytest。

## Global Constraints

- 不修改 Java ERP 服务或假定新 API 存在。
- 不生成虚构的设备目录、价格、交期、保修或库存数据。
- 订单创建和修改继续由 procurement-order Agent 执行并走现有 HITL 审批。
- 单次策略评估处理同一设备类别和数量；所有金额使用 Decimal。

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

- [ ] 先新增测试：覆盖满足全部约束时推荐最低总价报价；交期或关键规格缺失时待核实且无推荐；预算、设备类型、配置、保修或交期违反时不符合；金额使用 Decimal 精确计算。
- [ ] 运行 `python -m pytest tests/test_it_equipment_policy.py -q`，确认首次因策略模块不存在而失败。
- [ ] 实现一个无 LangChain/Pydantic 依赖的策略入口，解析日期与 Decimal；只有全部必需检查通过时将状态设为 eligible。
- [ ] 再运行上述 pytest，确认策略测试全部通过。

### Task 2: LangChain Tool 与 Agent 工具绑定

**Files:**
- Create: src/agent/tools/it_equipment_procurement.py
- Modify: src/agent/main_agent.py
- Modify: src/agent/subagents/configs/procurement_analyst.yaml
- Modify: tests/test_subagent_loader.py

**Interfaces:**
- Produces: evaluate_it_equipment_procurement LangChain StructuredTool, with Pydantic schema matching evaluate_it_equipment_policy input.
- procurement-analyst receives the new tool through available_tools and YAML tool-name resolution.

- [ ] 先扩展 loader 测试：提供名为 evaluate_it_equipment_procurement 的 stub tool，并断言采购分析 Agent 绑定该工具。
- [ ] 运行 `python -m pytest tests/test_subagent_loader.py -q`，确认新断言因配置缺少工具而失败。
- [ ] 增加嵌套 Pydantic Schema 与 Tool 包装，并在 main_agent.available_tools 和采购分析 YAML 注册工具。
- [ ] 再运行该 pytest 与 Python compileall，确认配置解析和语法通过。

### Task 3: 采购 Agent 指令与业务流程

**Files:**
- Modify: src/agent/memory/prompts.py
- Modify: src/agent/memory/AGENTS.md
- Modify: src/agent/subagents/configs/procurement_analyst.yaml
- Modify: src/agent/subagents/configs/procurement_order.yaml
- Modify: src/skills/procurement/procurement-analysis/SKILL.md

- [ ] 更新路由规则，明确 IT 设备采购分析进入采购分析 Agent，已确认方案下单进入订单 Agent。
- [ ] 在分析指引中写明 ERP/供应商/用户来源、规格字段映射、未知数据不得猜测、工具只做评估不下单。
- [ ] 在订单指引中要求复用已核验的 ERP part_id、将设备型号和确认规格写入订单备注，保留预期交期和 HITL。
- [ ] 检查提示词字段名与 Task 1 Schema 一致。

### Task 4: 前端入口与项目说明

**Files:**
- Modify: frontend/src/components/ChatArea.vue
- Modify: frontend/src/App.vue
- Modify: frontend/index.html
- Modify: README.md

- [ ] 将界面名称改成企业采购决策助手，列出研发项目采购和 IT 设备采购能力。
- [ ] 增加一个可点击 IT 采购示例，由 ChatArea 发出 suggestion 事件并复用 App.handleSend。
- [ ] README 说明两个业务方向、规格/预算/交期/保修判定、数据来源约束和 ERP 设备目录前置条件。
- [ ] 运行 `npm test` 与 `npm run build`，检查交互回归和生产构建。

### Task 5: 整体验证与交付

**Files:**
- Verify: tests/test_it_equipment_policy.py
- Verify: tests/test_subagent_loader.py
- Verify: frontend/

- [ ] 运行 `python -m pytest tests/test_it_equipment_policy.py tests/test_subagent_loader.py -q`。
- [ ] 运行 `python -m compileall -q src/agent`。
- [ ] 运行前端测试和生产构建。
- [ ] 检查 `git diff --check` 与 Git 状态，确保已有用户未提交文件没有进入本次变更。
