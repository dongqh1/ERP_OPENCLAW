"""独立加载 PC MCP Server 工具，不混入汽车业务工具。"""

from langchain_mcp_adapters.client import MultiServerMCPClient

from agent.tools.chart_generator import CHART_TYPE_GUIDE
from agent.tools.analysis_mcp_client import load_analysis_mcp_tools
from pc_mcp_server.server_config import PC_MCP_HOST, PC_MCP_PATH, PC_MCP_PORT

PC_MCP_SERVER_CONFIG = {
    "pc-hardware": {
        "url": f"http://{PC_MCP_HOST}:{PC_MCP_PORT}{PC_MCP_PATH}",
        "transport": "streamable_http",
    }
}
PC_TOOL_NAMES = frozenset({
    "hardware_query",
    "hardware_detail",
    "hardware_compare",
    "pc_compatibility_check",
    "pc_budget_optimizer",
    "pc_term_lookup",
})
PC_REQUIRED_CHART_TOOL_NAMES = frozenset(
    f"generate_{chart_type}"
    if chart_type.endswith(("_map", "_diagram", "_graph"))
    else f"generate_{chart_type}_chart"
    for chart_type in CHART_TYPE_GUIDE
)


async def load_pc_tools() -> list:
    client = MultiServerMCPClient(PC_MCP_SERVER_CONFIG)
    tools = await client.get_tools(server_name="pc-hardware")
    loaded_names = {tool.name for tool in tools}
    missing = PC_TOOL_NAMES.difference(loaded_names)
    if missing:
        raise RuntimeError(f"PC MCP Server 缺少工具：{', '.join(sorted(missing))}")
    print(f"[INFO] PC MCP 全量工具已加载: {sorted(loaded_names)}")
    # PC MCP 是独立服务；返回服务暴露的全部工具，避免白名单静默丢弃新能力。
    return tools


async def load_pc_analysis_tools() -> list:
    """加载完整分析 MCP；缺少任一图表工具时在 Agent 启动阶段明确失败。"""
    tools = await load_analysis_mcp_tools()
    names = {tool.name for tool in tools}
    missing = PC_REQUIRED_CHART_TOOL_NAMES.difference(names)
    if missing:
        raise RuntimeError(
            "分析 MCP 未完整加载 PC 所需的 26 种可视化工具，缺少："
            + ", ".join(sorted(missing))
        )
    print(
        f"[INFO] PC 分析 MCP 已加载 {len(names)} 个工具，"
        f"其中 {len(PC_REQUIRED_CHART_TOOL_NAMES)} 种图表/地图/结构图完整"
    )
    return tools
