# 智能采购 Agent 平台 MVP

基于 LangGraph、DeepAgents、MCP 与 Spring Boot 的多领域采购助手。Web 提供统一入口，由 Router Agent 按前端选择或请求关键词路由到独立的汽车采购 Agent 或 PC 配置采购 Agent。当前版本只使用模拟数据，不抓取电商网站、不连接真实汽车零件数据源。

## 领域与边界

### 汽车零部件采购

复用现有汽车/摩托车 ERP、汽车 FastMCP Server 和采购 DeepAgent，保留物料、供应商、库存、订单查询以及订单创建/修改的 Human-in-the-Loop 审批。新增的领域工具为 car_part_query、vehicle_match_check、car_price_estimate。车型适配只有在模拟 ERP 描述中明确出现时才返回已匹配；未验证时不推断。

### PC 电脑配置采购

独立 PC DeepAgent 只加载 PC 硬件 MCP 和通用分析/图表 MCP，不接触汽车 ERP 工具。主 Agent 委派给 `pc-hardware-analyst`（查询、详情、比较、术语解释、图表及分析 MCP 附带工具）和 `pc-build-planner`（预算优化、硬约束与兼容核验）两个子 Agent；两者分别配置 PC 领域技能。两个领域使用不同的 OpenSandbox ID 和技能范围。

PC MCP 工具包含硬件查询、详情、比较、配置兼容检查、预算优化和按需术语查询；启动时校验 26 种图表/地图/结构图工具全部加载，再合并为 `generate_visualization`，其他分析 MCP 工具也注入硬件分析子 Agent。Java 优化器可将用户指定的显存下限作为硬约束，按目录枚举配置并检查 CPU socket、主板芯片组、DDR 代际、显卡长度、机箱板型、散热器插槽/功耗和电源余量。用户明确已有的硬件会保留，并从本次新购预算中扣除。兼容与预算由确定性 Java 逻辑校验，LLM 负责理解需求和说明取舍。

PC 价格、性能分数和二手条目都是 JSON 模拟数据；`HardwareCatalogRepository` 隔离数据访问，当前由 JSON 实现提供目录，未来可替换为数据库或 ERP 适配器。性能定位不是实测游戏帧数，不代表当前市场报价。PC 配置当前是只读建议流程，不创建真实采购订单，因此没有订单审批中断；如后续增加订单写接口，再为该写操作加入 Human-in-the-Loop。

## 架构

Vue 3 Web → FastAPI SSE → RouterAgent（只选领域）
- 汽车：Car DeepAgent → Car MCP → 现有 Java ERP → 本地模拟汽车/摩托车数据
- PC：PC DeepAgent → 硬件分析子 Agent / 配置规划子 Agent → PC MCP → pc-hardware-service → JSON 模拟硬件目录
- PC 图表与术语辅助：PC 子 Agent → 通用分析 MCP；PC 代码执行和技能文件由 PC 专属 OpenSandbox/DeepAgents 后端提供

会话首次运行时把领域写入 MongoDB session_metadata；后续消息、历史消息和 HITL 恢复都使用同一领域 Agent 图。旧版没有领域元数据的会话按汽车领域兼容。

## 技术栈

- Agent：DeepAgents、LangGraph、Tool Calling
- 工具协议：MCP、FastMCP、langchain-mcp-adapters
- Python 服务：FastAPI、HTTPX、SSE
- 汽车业务服务：现有 Spring Boot ERP 与 MySQL 模拟数据
- PC 业务服务：Spring Boot 3、Java 17、JSON mock catalog
- 会话：MongoDB Checkpointer 与领域元数据
- Web：Vue 3、Vite
- DeepAgents 通过汽车、PC 各自的 OpenSandbox 后端承载领域技能与隔离代码执行；PC 业务数据仍只经 PC MCP 访问

## 服务端口

| 服务 | 端口 | 数据/连接 |
|---|---:|---|
| 现有汽车 Java ERP | 8080 | 本地 MySQL 模拟数据 |
| 汽车 MCP Server | 8000 | Java ERP REST |
| PC Hardware Spring Boot | 8081 | 本地 JSON 模拟目录 |
| PC MCP Server | 8001 | PC Java REST |
| FastAPI | 8090 | Agent/SSE/历史接口 |
| Vue/Vite | 3000 | /api 代理到 8090 |
| MongoDB | 按 .env 配置 | checkpoint、历史消息、会话领域 |

## 本地启动

先启动 MongoDB，并在项目 .env 配好 MONGODB_URI 和模型服务配置。

1. 启动现有汽车 Java ERP（若要测试汽车领域）。在原 Java 项目目录执行 mvn spring-boot:run，确认 API 位于 http://127.0.0.1:8080/api。
2. 单独 PowerShell 窗口启动汽车 MCP：pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_car_mcp.ps1
3. 单独窗口启动 PC 模拟硬件 Java 服务：pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_pc_hardware_service.ps1
4. 单独窗口启动 PC MCP：pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_pc_mcp.ps1
5. 项目根目录启动 FastAPI 与 Vue：python .\start_web.py

打开 http://localhost:3000，首屏选择汽车零部件采购或 PC 电脑配置采购。只体验 PC 时需启动 MongoDB、PC Java、PC MCP 与 Web；汽车 Java 和汽车 MCP 只在使用汽车领域时需要。

## PC 示例

- 预算 8000 元，主要玩《荒野大镖客 2》和 3A，目标 2K/60 FPS，只要全新，生成配置并检查兼容性。
- 预算 4000 元，我已经有 RTX 4070 Super，请保留显卡，搭配其他硬件并核验兼容。
- 预算 6000 元，保留我的 Ryzen 7 7800X3D CPU，给出其余硬件和新购总价。
- 预算 5000 元，所有配件只要二手，优先考虑性价比。

## 主要接口

PC Java REST：GET /hardware/query?type=GPU&keyword=RTX4070&condition=new、GET /hardware/detail?id=GPU-RTX4070S-NEW、POST /hardware/compare、POST /hardware/compatibility、POST /hardware/optimize（可选 `minGpuVramGb` 显存下限）。

PC MCP 工具：hardware_query、hardware_detail、hardware_compare、pc_compatibility_check、pc_budget_optimizer、pc_term_lookup。PC Agent 另外加载通用分析 MCP 的完整 26 种图表能力和其他可用分析工具；缺失任一图表工具时会在 Agent 初始化时明确报错。

统一 Agent API：POST /api/chat/stream 请求体支持 message、thread_id、domain（car 或 pc）；POST /api/chat/{thread_id}/resume 按会话元数据恢复对应领域 Agent；GET /api/history 会话列表包含领域标签。
