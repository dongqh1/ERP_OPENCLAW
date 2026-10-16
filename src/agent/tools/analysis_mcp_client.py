"""通用分析 MCP 客户端；不依赖汽车或 PC 领域业务服务。"""

from langchain_mcp_adapters.client import MultiServerMCPClient


ANALYSIS_MCP_SERVER_CONFIG = {
    "analysis": {
        "url": "https://mcp.api-inference.modelscope.net/934b733c19fd43/mcp",
        "transport": "streamable_http",
    },
}


async def load_analysis_mcp_tools() -> list:
    """连接通用分析 MCP 并返回服务暴露的全部工具。"""
    client = MultiServerMCPClient(ANALYSIS_MCP_SERVER_CONFIG)
    tools = await client.get_tools(server_name="analysis")
    print(f"[INFO] 已加载通用分析 MCP 工具: {[tool.name for tool in tools]}")
    return tools
