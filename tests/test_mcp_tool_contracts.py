import asyncio
from contextlib import asynccontextmanager

from fastmcp import Client, FastMCP

from mcp_server.tools.inventory_tools import register_inventory_tools
from mcp_server.tools.order_tools import register_order_tools
from mcp_server.tools.parts_tools import register_parts_tools
from mcp_server.tools.suppliers_tools import register_supplier_tools


class FakeResponse:
    def __init__(self, path):
        if path == "/parts/page":
            data = {"records": [{"id": 7, "name": "spark plug"}]}
        elif path.startswith("/orders/") and path != "/orders/search-details":
            data = {"id": 42, "orderNumber": "PO-test"}
        else:
            data = [{"id": 7, "name": "spark plug"}]
        self.payload = {"code": 200, "data": data}

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class RecordingHttpClient:
    def __init__(self):
        self.calls = []

    async def get(self, path, **kwargs):
        self.calls.append(("GET", path, kwargs))
        return FakeResponse(path)

    async def post(self, path, **kwargs):
        self.calls.append(("POST", path, kwargs))
        return FakeResponse(path)

    async def put(self, path, **kwargs):
        self.calls.append(("PUT", path, kwargs))
        return FakeResponse(path)


def invoke_tool(tool_name, arguments):
    http_client = RecordingHttpClient()

    @asynccontextmanager
    async def lifespan(server):
        yield {"http_client": http_client}

    mcp = FastMCP("offline-contract-tests", lifespan=lifespan)
    register_supplier_tools(mcp)
    register_parts_tools(mcp)
    register_order_tools(mcp)
    register_inventory_tools(mcp)

    async def call():
        async with Client(mcp) as client:
            result = await client.call_tool(tool_name, arguments)
            assert not result.is_error
            return result.data

    result = asyncio.run(call())
    return result, http_client.calls


def test_all_erp_tools_are_registered():
    async def list_names():
        mcp = FastMCP("offline-registration-test")
        register_supplier_tools(mcp)
        register_parts_tools(mcp)
        register_order_tools(mcp)
        register_inventory_tools(mcp)
        async with Client(mcp) as client:
            return {tool.name for tool in await client.list_tools()}

    assert asyncio.run(list_names()) == {
        "supplier_query",
        "part_query",
        "part_search",
        "part_by_supplier",
        "order_create",
        "order_update",
        "order_search_details",
        "inventory_warning",
    }


def test_supplier_search_sends_the_expected_query_parameter():
    _, calls = invoke_tool("supplier_query", {"name": "Bosch"})

    assert calls == [("GET", "/suppliers/search", {"params": {"name": "Bosch"}})]


def test_part_page_maps_optional_filters_to_api_field_names():
    result, calls = invoke_tool(
        "part_query",
        {"current": 2, "size": 5, "category": "制动类", "supplier_id": 11},
    )

    assert result == [{"id": 7, "name": "spark plug"}]
    assert calls == [(
        "GET",
        "/parts/page",
        {"params": {"current": 2, "size": 5, "category": "制动类", "supplierId": 11}},
    )]


def test_part_search_and_supplier_lookup_use_the_expected_routes():
    _, search_calls = invoke_tool("part_search", {"name": "plug"})
    _, supplier_calls = invoke_tool("part_by_supplier", {"supplier_id": 11})

    assert search_calls == [("GET", "/parts/search", {"params": {"name": "plug"}})]
    assert supplier_calls == [("GET", "/parts/supplier/11", {})]


def test_order_create_computes_missing_subtotals_and_total():
    _, calls = invoke_tool(
        "order_create",
        {"order_detail": [
            {"partId": 3, "quantity": 3, "unitPrice": 1.1},
            {"partId": 8, "quantity": 2, "unitPrice": 4.2},
        ]},
    )
    payload = calls[0][2]["json"]

    assert calls[0][0:2] == ("POST", "/orders/create")
    assert payload["orderDetail"] == [
        {"partId": 3, "quantity": 3, "unitPrice": 1.1, "subtotal": 3.3},
        {"partId": 8, "quantity": 2, "unitPrice": 4.2, "subtotal": 8.4},
    ]
    assert payload["totalAmount"] == 11.7
    assert payload["status"] == 1
    assert payload["orderNumber"].startswith("PO")
    assert "orderTime" in payload


def test_order_update_does_not_add_creation_defaults_to_partial_update():
    _, calls = invoke_tool("order_update", {"order_id": 42, "status": 2, "remark": "reviewed"})

    assert calls == [(
        "PUT",
        "/orders/update/42",
        {"json": {"status": 2, "remark": "reviewed"}},
    )]


def test_order_detail_search_maps_filters_and_inventory_warning_is_parameterless():
    _, search_calls = invoke_tool(
        "order_search_details",
        {"part_name": "plug", "start_date": "2026-01-01", "end_date": "2026-01-31"},
    )
    _, warning_calls = invoke_tool("inventory_warning", {})

    assert search_calls == [(
        "GET",
        "/orders/search-details",
        {"params": {"partName": "plug", "startDate": "2026-01-01", "endDate": "2026-01-31"}},
    )]
    assert warning_calls == [("GET", "/inventory/warning", {})]
