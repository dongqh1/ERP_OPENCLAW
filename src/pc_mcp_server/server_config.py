import os

PC_HARDWARE_API_BASE_URL = os.getenv(
    "PC_HARDWARE_API_BASE_URL",
    "http://127.0.0.1:8081",
)
PC_MCP_HOST = os.getenv("PC_MCP_HOST", "127.0.0.1")
PC_MCP_PORT = int(os.getenv("PC_MCP_PORT", "8001"))
PC_MCP_PATH = os.getenv("PC_MCP_PATH", "/mcp")
