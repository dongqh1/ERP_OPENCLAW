from fastmcp import Context, FastMCP
from agent.agents.pc_agent.schema import PCBuildRequest


def register_hardware_tools(mcp: FastMCP) -> None:
    """注册仅面向模拟 PC 硬件目录的工具。"""

    @mcp.tool(name="hardware_query")
    async def hardware_query(
        type: str | None = None,
        keyword: str | None = None,
        condition: str = "any",
        ctx: Context = None,
    ) -> dict:
        """按类别、关键词和新旧偏好查询本地模拟硬件目录。类别示例：CPU、GPU、MOTHERBOARD、MEMORY、STORAGE、COOLER、POWER、CASE。"""
        client = ctx.request_context.lifespan_context["http_client"]
        response = await client.get(
            "/hardware/query",
            params={"type": type, "keyword": keyword, "condition": condition},
        )
        response.raise_for_status()
        return response.json()

    @mcp.tool(name="hardware_detail")
    async def hardware_detail(id: str, ctx: Context) -> dict:
        """按模拟目录 ID 查询单个硬件的完整规格。"""
        client = ctx.request_context.lifespan_context["http_client"]
        response = await client.get("/hardware/detail", params={"id": id})
        response.raise_for_status()
        return response.json()

    @mcp.tool(name="hardware_compare")
    async def hardware_compare(ids: list[str], ctx: Context) -> dict:
        """比较多个模拟硬件条目的规格、价格和演示性能指标。"""
        client = ctx.request_context.lifespan_context["http_client"]
        response = await client.post("/hardware/compare", json={"ids": ids})
        response.raise_for_status()
        return response.json()

    @mcp.tool(name="pc_compatibility_check")
    async def pc_compatibility_check(components: dict[str, str], ctx: Context) -> dict:
        """校验配置兼容性；每项返回 PASSED、INCOMPATIBLE 或 NEEDS_VERIFICATION。未知尺寸保留配置并标待核实，只有明确冲突才判不兼容。components 的键为硬件类别，值为目录 ID 或型号名。"""
        client = ctx.request_context.lifespan_context["http_client"]
        response = await client.post(
            "/hardware/compatibility",
            json={"components": components},
        )
        response.raise_for_status()
        return response.json()

    @mcp.tool(name="pc_budget_optimizer")
    async def pc_budget_optimizer(
        budget: float,
        use_case: str = "日常办公",
        resolution: str = "未指定",
        target_fps: int = 60,
        min_gpu_vram_gb: int | None = None,
        condition_preference: str = "any",
        keep_components: list[dict] | None = None,
        ctx: Context = None,
    ) -> dict:
        """按预算和用途生成完整配置。min_gpu_vram_gb 可传用户要求的显存下限。keep_components 项包含 type、keyword、owned；owned=true 表示用户已有硬件，必须保留且不计入新购预算。condition_preference 支持 new、used、any、best_value。"""
        request = PCBuildRequest(
            budget=budget,
            use_case=use_case,
            resolution=resolution,
            target_fps=target_fps,
            min_gpu_vram_gb=min_gpu_vram_gb,
            condition_preference=condition_preference,
            keep_components=keep_components or [],
        )
        client = ctx.request_context.lifespan_context["http_client"]
        response = await client.post(
            "/hardware/optimize",
            json={
                "budget": request.budget,
                "useCase": request.use_case,
                "resolution": request.resolution,
                "targetFps": request.target_fps,
                "minGpuVramGb": request.min_gpu_vram_gb,
                "conditionPreference": request.condition_preference,
                "keepComponents": [item.model_dump() for item in request.keep_components],
            },
        )
        response.raise_for_status()
        return response.json()
