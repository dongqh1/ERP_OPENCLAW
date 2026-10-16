"""汽车 MCP 工具名称与子 Agent 分组。"""

CAR_DOMAIN_TOOL_NAMES = frozenset({
    "car_part_query",
    "vehicle_match_check",
    "car_price_estimate",
})
CAR_ANALYST_TOOL_PREFIXES = (
    "car_",
    "vehicle_",
    "part_",
    "supplier_",
    "inventory_",
)
CAR_ORDER_TOOL_PREFIXES = ("order_",)
