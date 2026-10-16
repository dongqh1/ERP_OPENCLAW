from decimal import Decimal
from typing import Optional

from fastmcp import Context, FastMCP
from agent.agents.car_agent.schema import (
    CarPartQuery,
    CarPriceEstimate,
    VehicleMatchQuery,
)


def register_car_procurement_tools(mcp: FastMCP) -> None:
    """注册汽车/摩托车 ERP 查询与估价工具。"""

    async def search_parts(ctx: Context, keyword: str) -> list[dict]:
        client = ctx.request_context.lifespan_context.get("http_client")
        response = await client.get("/parts/search", params={"name": keyword})
        response.raise_for_status()
        result = response.json()
        if result.get("code") != 200:
            return []
        return result.get("data", [])

    @mcp.tool(name="car_part_query")
    async def car_part_query(
        keyword: str,
        vehicle_model: Optional[str] = None,
        ctx: Context = None,
    ) -> dict:
        """从本地 ERP 模拟目录按关键词查询汽车/摩托车零部件，可附带车型关键词。"""
        query = CarPartQuery(keyword=keyword, vehicle_model=vehicle_model)
        items = await search_parts(ctx, query.keyword)
        if query.vehicle_model:
            terms = query.vehicle_model.lower().replace(" ", "")
            items = [
                item for item in items
                if terms in " ".join(str(value) for value in item.values()).lower().replace(" ", "")
            ]
        return {
            "items": items,
            "count": len(items),
            "vehicle_model_filter": query.vehicle_model,
            "dataSource": "本地 ERP 模拟数据",
        }

    @mcp.tool(name="vehicle_match_check")
    async def vehicle_match_check(vehicle_model: str, part_keyword: str, ctx: Context) -> dict:
        """检查 ERP 零件描述中是否明确包含指定车型；没有明确记录时返回未验证，不推断适配。"""
        query = VehicleMatchQuery(vehicle_model=vehicle_model, part_keyword=part_keyword)
        items = await search_parts(ctx, query.part_keyword)
        normalized_model = query.vehicle_model.lower().replace(" ", "")
        matches = [
            item for item in items
            if normalized_model in " ".join(str(value) for value in item.values()).lower().replace(" ", "")
        ]
        return {
            "vehicle_model": query.vehicle_model,
            "part_keyword": query.part_keyword,
            "fitment_status": "matched_in_mock_description" if matches else "not_verified",
            "matches": matches,
            "message": (
                "模拟 ERP 描述中包含该车型关键词；仍需人工核对零件号与年款。"
                if matches else "模拟 ERP 未找到明确车型适配记录，不能据此确认适配。"
            ),
            "dataSource": "本地 ERP 模拟数据",
        }

    @mcp.tool(name="car_price_estimate")
    async def car_price_estimate(part_keywords: list[str], ctx: Context) -> dict:
        """按本地 ERP 模拟目录中各关键词的最低采购价估算零件清单金额，不代表实时报价。"""
        request = CarPriceEstimate(part_keywords=part_keywords)
        rows = []
        total = Decimal("0")
        missing = []
        for keyword in request.part_keywords:
            items = await search_parts(ctx, keyword)
            priced = [
                item for item in items
                if item.get("purchasePrice") is not None
            ]
            if not priced:
                missing.append(keyword)
                continue
            selected = min(priced, key=lambda item: Decimal(str(item.get("purchasePrice", 0))))
            price = Decimal(str(selected.get("purchasePrice", 0)))
            total += price
            rows.append({"keyword": keyword, "selected": selected, "estimatedPrice": str(price)})
        return {
            "items": rows,
            "missing": missing,
            "estimatedTotal": str(total),
            "currency": "CNY",
            "dataSource": "本地 ERP 模拟数据；非实时市场报价",
        }
