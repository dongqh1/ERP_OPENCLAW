from contextlib import asynccontextmanager

import httpx
from fastmcp import FastMCP

from pc_mcp_server.server_config import (
    PC_HARDWARE_API_BASE_URL,
    PC_MCP_HOST,
    PC_MCP_PATH,
    PC_MCP_PORT,
)
from pc_mcp_server.tools.hardware_tools import register_hardware_tools
from pc_mcp_server.tools.term_lookup_tools import register_term_lookup_tools


@asynccontextmanager
async def lifespan(server: FastMCP):
    client = httpx.AsyncClient(
        base_url=PC_HARDWARE_API_BASE_URL,
        timeout=20.0,
        limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
    )
    try:
        yield {"http_client": client}
    finally:
        await client.aclose()


mcp = FastMCP(
    name="PC-Hardware-Procurement-MCP",
    instructions="通过 Java PC Hardware Service 查询本地模拟硬件；仅在术语不明确时可搜索其含义，不查询电商价格或库存。",
    version="1.0.0",
    lifespan=lifespan,
)
register_hardware_tools(mcp)
register_term_lookup_tools(mcp)


def main() -> None:
    mcp.run(
        transport="streamable-http",
        host=PC_MCP_HOST,
        port=PC_MCP_PORT,
        path=PC_MCP_PATH,
    )


if __name__ == "__main__":
    main()
