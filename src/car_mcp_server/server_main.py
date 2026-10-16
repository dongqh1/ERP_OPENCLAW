"""汽车 MCP Server 入口，兼容旧的 mcp_server 启动命令。"""

from mcp_server.server_main import main, mcp

__all__ = ["main", "mcp"]

if __name__ == "__main__":
    main()
