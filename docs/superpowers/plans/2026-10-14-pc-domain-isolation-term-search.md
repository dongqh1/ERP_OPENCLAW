# PC 会话领域保护与术语查询 Implementation Plan

> **For agentic workers:** 本计划由当前任务直接执行；按步骤完成后做代码/服务检查。

**Goal:** 避免汽车与 PC 会话串域，并让 PC Agent 仅在必要时通过 PC MCP 查询陌生术语。

**Architecture:** 前端保持切换领域时新建会话；FastAPI 对已固定领域的会话拒绝冲突领域参数并给出 SSE 解释。PC MCP 增加一个复用现有 Sogou Web Search 的术语工具，做摘要、长度限制和进程内缓存；汽车 Agent 的工具不变。

**Tech Stack:** FastAPI SSE、DeepAgents、FastMCP、LangChain Tool、Zhipu Sogou Search API、Python `OrderedDict` / `threading`。

## Global Constraints

- 汽车 Agent 和 PC Agent 的业务工具池保持隔离。
- PC 硬件数据继续只通过 PC MCP 调用 Java 模拟服务。
- 搜索只解释术语；不采集电商价格、库存或完整网页。
- 缓存仅驻留 PC MCP 进程，结果最多 3 段且总长约 1200 字。
- 不改动订单、兼容规则、硬件目录及汽车采购流程。
- 当前仓库约束为不新增或运行自动化测试；以编译和工具发现检查验证。

---

### Task 1: 固定会话领域并处理冲突

**Files:**
- Modify: `src/api_view/api/chat.py`
- Modify: `tests/test_chat_stream.py` only if test execution is permitted by the task environment

- [ ] 在会话已有领域与请求显式领域冲突时，不调用任一 Agent，发送说明需通过领域入口新建会话的 SSE error。
- [ ] 新会话仍优先采用前端显式领域；旧客户端无领域时继续采用会话元数据或原路由逻辑。
- [ ] 保留前端已有的“切换领域即新建会话”行为。

### Task 2: 增加 PC MCP 术语查询工具

**Files:**
- Create: `src/pc_mcp_server/tools/term_lookup_tools.py`
- Modify: `src/pc_mcp_server/server_main.py`
- Modify: `src/agent/agents/pc_agent/tools.py`
- Modify: `src/agent/agents/pc_agent/prompt.yaml`
- Modify: `tests/test_mcp_tool_contracts.py` only if test execution is permitted by the task environment

- [ ] 新增 `pc_term_lookup(term)`：归一化并校验术语；只用术语构造搜索词；复用现有 `web_search`；截断为最多 3 段、总长不超过 1200 字。
- [ ] 添加 24 小时 TTL 与最多 128 项的有界缓存；只缓存成功结果；缓存命中时不请求外部搜索。
- [ ] 将工具注册到 PC FastMCP 并加入 `PC_TOOL_NAMES`。
- [ ] 更新 PC Agent 提示词：仅在陌生名称会影响配置判断时查询；禁止用此工具查价格/库存；搜索失败时澄清而非猜测。

### Task 3: 检查并交付

- [ ] 用 `python -m compileall -q src` 检查 Python 语法。
- [ ] 在 PC MCP 工具发现中确认四个硬件工具和 `pc_term_lookup` 均已注册；不发起模型对话或外部搜索。
- [ ] 检查最终 diff，确保未触碰汽车业务逻辑和无关文件。
