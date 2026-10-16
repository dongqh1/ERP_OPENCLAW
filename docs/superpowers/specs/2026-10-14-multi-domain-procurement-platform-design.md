# 智能采购 Agent 平台 MVP 设计

## 目标与边界

在现有 ERP 汽车零部件采购 Agent 上增加 PC 电脑配置采购建议，提供统一 Web 入口和两个隔离领域 Agent。当前阶段只使用本地模拟数据，不接入电商平台、不连接真实汽车零件数据源。既有汽车采购流程和历史会话恢复保持可用。

## 方案

FastAPI 接收用户选择的领域与消息，并交由轻量 Router 解析领域；Router 不调用业务工具、不分析采购内容。前端明确选择优先，兼容旧请求时按汽车/PC关键词路由；未传领域且无法判断时默认汽车，保持旧客户端兼容。每个会话首次路由后将领域写入 MongoDB 元数据，后续消息、历史加载及中断恢复固定使用同一领域 Agent。

汽车 Agent 复用现有 DeepAgents/LangGraph 组装、汽车 ERP MCP 工具与 Java ERP API。为其建立 agents/car_agent/ 的 prompt、schema、tools 边界，并暴露 car_part_query、vehicle_match_check、car_price_estimate 领域工具。既有汽车 MCP 服务器保留，PC 工具不注册到汽车工具池。

PC Agent 是独立 DeepAgent，有自己的 PC 主 Agent、硬件分析子 Agent、配置规划子 Agent、提示词和领域技能，不加载汽车业务工具。汽车和 PC 使用独立 OpenSandbox ID；技能播种、运行时同步及用户技能恢复按领域 scope 过滤。硬件 MCP 通过 REST 调用 Spring Boot pc-hardware-service；服务从 resources 中的模拟 JSON 目录读数据，提供硬件查询、详情、比较、配置兼容检查和预算优化 API。PC MCP 还提供按需术语解释；PC 子 Agent 复用通用分析 MCP 的完整 26 种图表能力及其附带工具，但不加载汽车 ERP MCP。启动 PC Agent 时校验该图表工具集，缺项即报错。兼容规则、显存下限和预算计算由 Java/工具逻辑执行，LLM 负责解析自然语言和解释结果。PC Agent 使用 OpenSandbox 文件/代码执行后端、LangGraph Checkpointer、用户偏好记忆、中间件和渐进式技能加载。

Web 首屏提供“汽车零部件采购”和“PC 电脑配置采购”两个入口；选定后显示对应示例和会话领域。原 SSE 工具流、审批/补充中断、历史会话能力保留。

## PC 配置规则与演示数据

模拟目录至少覆盖 CPU、GPU、主板、内存、SSD、散热、电源、机箱，并记录价格、品牌、型号、接口/协议、规格尺寸、功耗和 data_source=MOCK。兼容性校验检查 CPU socket 与主板 socket、芯片组、DDR 代际、显卡长度与机箱限长、显卡/整机功耗与电源余量。指定保留的 CPU/GPU 必须优先纳入候选，不能被优化器替换；无法组成兼容配置或预算不足时返回明确原因和缺失项。预算优化输出整机清单、总价、预算余额、约束校验和模拟数据提示。

## 主要失败处理

- MCP 或 Java 服务不可用时向 Agent 返回明确的工具错误，不生成虚构报价。
- 无领域参数且关键词无法唯一判断时提示用户选择领域；旧版无参数的汽车请求仍默认汽车领域。
- 已有会话始终按 MongoDB 中持久化的领域恢复，避免用另一个 Agent 读取旧 checkpoint。
- 模拟目录价格及性能定位均标注为演示值，不表述为实时市场价或实测跑分。

## 交付检查

检查 Python 模块可导入、Java 服务可打包、前端生产构建可生成；不新增/运行自动化测试，遵循当前任务环境的测试限制。README 与启动脚本说明三个服务的端口、启动顺序和示例请求。
