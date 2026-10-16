# 智能采购 Agent 平台 MVP 实施计划

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 在现有汽车零部件采购系统上增加独立 PC 配置采购 Agent，并通过统一 Web 入口按领域路由。

**Architecture:** FastAPI 保存会话领域并路由到汽车或 PC DeepAgent。汽车 Agent 复用现有 MCP/Java ERP 服务；PC Agent 只调用独立 FastMCP 服务，FastMCP 再调用 Spring Boot 模拟硬件服务。硬件服务使用 JSON mock catalog，确定性执行兼容与预算计算。

**Tech Stack:** Python 3.10+, DeepAgents, LangGraph, FastAPI, FastMCP, langchain-mcp-adapters, MongoDB checkpoint/metadata, Java Spring Boot, JSON, Vue 3/Vite.

## Global Constraints

- 只使用模拟数据；不接入电商网站，不连接真实汽车数据源。
- 汽车采购现有功能保持可用，PC Agent 和工具与汽车领域隔离。
- Python Agent 不直接访问业务数据库；PC Agent 必须经 PC MCP 调用 Java REST 服务。
- PC 目录及价格必须显式标记为模拟数据。
- 兼容性与预算约束由确定性逻辑执行，不能只依赖 LLM。
- 遵循当前会话授权，不新增或运行自动化测试；使用构建/导入检查验证可运行性。

---

### Task 1: 增加领域模型与 Router

**Files:**
- Create: src/agent/router.py
- Modify: src/agent/schema.py
- Modify: src/api_view/agent_loader.py

- [x] 定义 car / pc 领域常量与请求字段。
- [x] 实现只负责领域解析的 route_domain(message, selected_domain)：显式领域优先；旧请求按关键词解析；不明确时回退到汽车兼容行为。
- [x] 将 AgentLoader 改为按领域懒加载 Agent，并增加 MongoDB session_metadata 的领域读写与删除。
- [x] 保留 agent_loader.agent 作为汽车 Agent 兼容属性。

### Task 2: 拆分汽车领域边界

**Files:**
- Create: src/agent/agents/__init__.py
- Create: src/agent/agents/car_agent/__init__.py
- Create: src/agent/agents/car_agent/prompt.yaml
- Create: src/agent/agents/car_agent/schema.py
- Create: src/agent/agents/car_agent/tools.py
- Modify: src/agent/main_agent.py
- Modify: src/mcp_server/server_main.py or add src/car_mcp_server/

- [x] 把当前汽车 Agent 工厂以兼容方式暴露为 create_car_agent()；汽车工具池保留现有零件、供应商、库存、订单、图表及 HITL 能力。
- [x] 添加汽车领域工具适配层，命名 car_part_query、vehicle_match_check、car_price_estimate，调用现有汽车 MCP 工具/API，不向汽车领域注入 PC MCP 工具。
- [x] 保持原 MCP URL/启动入口可用，并为汽车 MCP Server 添加清晰领域名称。

### Task 3: 创建模拟硬件 Java 服务

**Files:**
- Create: pc-hardware-service/pom.xml
- Create: pc-hardware-service/src/main/java/com/procurement/pchardware/PcHardwareServiceApplication.java
- Create: pc-hardware-service/src/main/java/com/procurement/pchardware/api/HardwareController.java
- Create: pc-hardware-service/src/main/java/com/procurement/pchardware/service/HardwareCatalogService.java
- Create: pc-hardware-service/src/main/java/com/procurement/pchardware/service/CompatibilityService.java
- Create: pc-hardware-service/src/main/java/com/procurement/pchardware/repository/HardwareCatalogRepository.java
- Create: pc-hardware-service/src/main/java/com/procurement/pchardware/repository/JsonHardwareCatalogRepository.java
- Create: pc-hardware-service/src/main/java/com/procurement/pchardware/model/*.java
- Create: pc-hardware-service/src/main/resources/application.properties
- Create: pc-hardware-service/src/main/resources/data/hardware-catalog.json

- [x] 使用 Spring Boot Web 提供 /hardware/query、/hardware/detail、/hardware/compare、/hardware/compatibility、/hardware/optimize。
- [x] 提供各硬件类别的本地 JSON 模拟目录，覆盖 CPU、GPU、主板、内存、SSD、散热、电源、机箱。
- [x] 实现 socket、芯片组、DDR、显卡尺寸、电源功耗余量和模拟性能平衡提示。
- [x] 实现预算配置优化，优先保留用户指定硬件，并返回清单、总价、预算余额、约束结果和模拟数据标记。

### Task 4: 创建 PC MCP 与 PC Agent

**Files:**
- Create: src/pc_mcp_server/__init__.py
- Create: src/pc_mcp_server/server_config.py
- Create: src/pc_mcp_server/server_main.py
- Create: src/pc_mcp_server/tools/hardware_tools.py
- Create: src/agent/agents/pc_agent/__init__.py
- Create: src/agent/agents/pc_agent/prompt.yaml
- Create: src/agent/agents/pc_agent/schema.py
- Create: src/agent/agents/pc_agent/tools.py
- Create: src/agent/agents/pc_agent/agent.py

- [x] PC MCP 独立监听端口并使用独立 Java URL 配置，通过 HTTPX 调用 Java 服务。
- [x] 注册 hardware_query、hardware_compare、pc_compatibility_check、pc_budget_optimizer。
- [x] PC Agent 独立创建 DeepAgent，仅注入 PC MCP 工具，不接入汽车订单工具或汽车数据。
- [x] 在 prompt 中明确模拟数据、性能定位和指定硬件保留规则。

### Follow-up: PC Agent 与汽车分析链路能力对齐

- [x] 新增 `hardware_detail` MCP Tool，覆盖 Java 已提供的 `/hardware/detail` 接口；PC MCP 全量注册工具并校验必要工具是否加载。
- [x] PC Agent 独立加载分析/图表 MCP，合并图表工具为 `generate_visualization`，保留其他分析工具；不连接汽车 ERP MCP。
- [x] 新增 `pc-hardware-analyst` 与 `pc-build-planner` 两个 PC 子 Agent YAML 配置，分别负责数据分析/图表与预算配置/兼容性。
- [x] 新增 PC 领域操作手册与领域准则，按技能路径渐进加载；接入 OpenSandbox、会话偏好、MongoDB Checkpointer、摘要与工具调用限制。
- [x] 将显卡显存下限作为优化器硬约束，修正 Valorant/电竞游戏与 3A 游戏用途的演示标签，返回 `catalogTotal` 并保留旧字段兼容。
- [x] 对图表 MCP 的裸图片 URL 做工具结果图片解析，避免 Agent 已生成图表但前端只显示链接。
- [x] 按 car/pc 分别缓存 OpenSandbox 并持久化独立 ID；播种和运行时同步分别限制到汽车与 PC 技能目录。
- [x] PC Agent 初始化时校验分析 MCP 的完整 26 种图表能力，并将图表封装之外的 MCP 工具动态交给硬件分析子 Agent。

### Task 5: 串接 FastAPI 流式入口与会话恢复

**Files:**
- Modify: src/api_view/api/chat.py
- Modify: src/api_view/api/history.py
- Modify: src/agent/schema.py
- Modify: src/api_view/agent_loader.py

- [x] 首轮请求按领域路由，并将领域写入会话元数据。
- [x] 后续请求和 resume 从会话元数据读取领域，调用对应 Agent checkpoint。
- [x] 历史会话返回领域字段；历史展示优先从持久展示消息读取，checkpoint 回退读取按领域选择 Agent；删除时同时移除领域元数据。
- [x] 保留 SSE 事件格式和已有 HITL 中断、恢复行为。

### Task 6: Web 领域选择与交互

**Files:**
- Modify: frontend/src/App.vue
- Modify: frontend/src/api/chat.js
- Modify: frontend/src/api/history.js
- Modify: frontend/src/components/ChatArea.vue
- Modify: frontend/src/components/Sidebar.vue
- Modify: frontend/src/styles/main.css

- [x] 首屏以两个领域卡片作为入口，移除旧的研发项目和泛企业 IT 设备卡片。
- [x] PC 卡片提供 8000 元游戏机、RDR2 2K、指定 RTX4070 Super、保留 7800X3D 等示例。
- [x] 发送 SSE 请求携带领域；切换会话时恢复该会话领域；历史侧栏标明领域。
- [x] 工具调用展示及原有流式/中断交互继续工作。

### Task 7: 启动脚本与使用说明

**Files:**
- Create: scripts/start_pc_hardware_service.ps1
- Modify: start_web.py or create scripts/start_platform.ps1
- Modify: README.md

- [x] 提供 Java 服务和 PC MCP 独立启动脚本；PC 服务脚本自动选择可用的 Java 17。
- [x] 写明汽车 ERP Java 服务、PC Java 服务、汽车 MCP、PC MCP、FastAPI、前端的启动顺序及端口。
- [x] 加入领域示例请求和模拟数据说明。
- [x] 执行 Java package、前端 build、Python compile 检查，不运行自动化测试。
