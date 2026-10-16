"""MCP tools for the ERP's explicitly simulated IT equipment catalog."""

from typing import Optional

from fastmcp import Context, FastMCP


GROUP_NAME = "it_equipment"


def register_it_equipment_tools(mcp: FastMCP) -> None:
    """Register read-only IT catalog search for analysis and order verification."""

    @mcp.tool(name=f"{GROUP_NAME}_search")
    async def search_it_equipment(
        device_type: Optional[str] = None,
        model_name: Optional[str] = None,
        part_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        min_cpu_cores: Optional[int] = None,
        min_memory_gb: Optional[int] = None,
        min_storage_gb: Optional[int] = None,
        operating_system: Optional[str] = None,
        max_price: Optional[float] = None,
        min_warranty_months: Optional[int] = None,
        max_delivery_days: Optional[int] = None,
        limit: Optional[int] = 30,
        ctx: Context = None,
    ) -> list:
        """Search IT demo catalog records from ERP, including verified part IDs.

        Use a broad device_type search for analysis so the deterministic evaluator
        can compare eligible and ineligible candidates. For order verification,
        pass the selected part_id to retrieve the exact ERP record. The returned
        source identifies these offers as simulated local demo data. ERP on-hand
        inventory is not supplier availability.

        Args:
            device_type: laptop, desktop, or server; Chinese names are also accepted.
            model_name: Optional partial model match.
            part_id: Exact ERP material ID, primarily for order verification.
            supplier_id: Optional ERP supplier ID.
            min_cpu_cores: Optional lower bound for CPU cores.
            min_memory_gb: Optional lower bound for memory in GB.
            min_storage_gb: Optional lower bound for storage in GB.
            operating_system: Optional partial operating-system match.
            max_price: Optional maximum unit price in CNY.
            min_warranty_months: Optional minimum warranty period.
            max_delivery_days: Optional maximum demo delivery lead time.
            limit: Maximum rows, capped by the API at 100.
        """
        http_client = ctx.request_context.lifespan_context.get("http_client")
        request_params = {
            "device_type": device_type,
            "model_name": model_name,
            "part_id": part_id,
            "supplier_id": supplier_id,
            "min_cpu_cores": min_cpu_cores,
            "min_memory_gb": min_memory_gb,
            "min_storage_gb": min_storage_gb,
            "operating_system": operating_system,
            "max_price": max_price,
            "min_warranty_months": min_warranty_months,
            "max_delivery_days": max_delivery_days,
            "limit": limit,
        }
        request_params = {
            key: value for key, value in request_params.items() if value is not None
        }

        try:
            response = await http_client.get(
                "/it-equipment/search", params=request_params
            )
            response.raise_for_status()
            result = response.json()
            if result.get("code") != 200:
                return [f"API error: code={result.get('code')}"]
            return result.get("data", [])
        except Exception as exc:
            return [f"IT 设备目录查询失败: {exc}"]
