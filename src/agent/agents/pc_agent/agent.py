"""PC 采购规划 DeepAgent 工厂，与汽车领域使用独立提示词、子 Agent 和工具池。"""

from pathlib import Path

import yaml
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StoreBackend
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware

from agent.agents.pc_agent.tools import load_pc_analysis_tools, load_pc_tools
from agent.backends.sandbox_lifecycle import get_shared_sandbox_backend
from agent.config import (
    CHECKPOINTER,
    DOWNLOAD_DIR,
    MAIN_MODEL,
    MONGODB_CLIENT,
    MONGODB_DB_NAME,
    MONGODB_PC_PREFERENCES_COLLECTION,
    SANDBOX_CONFIG,
    SKILLS_STORE_NAMESPACE,
    STORE,
    SUMMARY_MODEL,
)
from agent.middleware_config import create_analyst_middleware
from agent.middlewares.skills_sync import SkillsSyncMiddleware
from agent.middlewares.tools_summarization import build_summarization_middleware
from agent.middlewares.user_skills_restore import UserSkillsRestoreMiddleware
from agent.agents.pc_agent.preferences import (
    PCPreferenceContextMiddleware,
    PCPreferencesRepository,
    create_save_pc_preferences_tool,
)
from agent.schema import ProcurementContext
from agent.subagents.loader import load_subagent_configs, resolve_subagent_tools
from agent.tools.assign_skill import create_assign_skill_tool
from agent.tools.chart_generator import create_generate_chart_tool
from agent.tools.download_sandbox_file import create_download_tool
from agent.tools.web_search import web_search

PROMPT_FILE = Path(__file__).with_name("prompt.yaml")
PC_SUBAGENT_CONFIG_DIR = Path(__file__).with_name("subagents") / "configs"
PC_REQUIRED_SKILL_FILES = (
    "/skills/pc/AGENTS.md",
    "/skills/pc/chart_params.md",
    "/skills/pc/analysis/pc-hardware-analysis/SKILL.md",
    "/skills/pc/planning/pc-build-planning/SKILL.md",
)


def _load_system_prompt() -> str:
    config = yaml.safe_load(PROMPT_FILE.read_text(encoding="utf-8"))
    return str(config.get("system_prompt", ""))


def _build_backend(sandbox_backend):
    """与汽车 Agent 复用文件系统能力，但通过 Store 路由用户记忆/技能。"""
    return lambda rt: CompositeBackend(
        default=sandbox_backend,
        routes={
            "/memories/": StoreBackend(
                runtime=rt,
                namespace=lambda rt: (
                    getattr(rt.runtime.context, "user_id", "laoxiao"),
                    "pc",
                ),
            ),
            "/persisted-skills/": StoreBackend(
                runtime=rt,
                namespace=lambda rt: SKILLS_STORE_NAMESPACE,
            ),
        },
    )


def _ensure_pc_skill_files(sandbox_backend) -> None:
    """Fail early if the isolated PC sandbox is missing any required skill file."""
    missing = [
        path
        for path in PC_REQUIRED_SKILL_FILES
        if sandbox_backend.execute(f"test -f {path}").exit_code != 0
    ]
    if missing:
        raise RuntimeError(
            "PC OpenSandbox 技能文件未完整同步：" + ", ".join(missing)
        )
    print(f"[INFO] PC 技能文件已就绪: {list(PC_REQUIRED_SKILL_FILES)}")


async def create_pc_agent():
    """创建完整的 PC 领域主 Agent、两个职责子 Agent 和 PC 专属工具池。"""
    # 沿用汽车 Agent 的沙箱复用策略，但使用独立 PC 容器与技能范围。
    sandbox_backend = get_shared_sandbox_backend(
        SANDBOX_CONFIG,
        domain="pc",
        skill_scopes={"main", "pc"},
    )
    _ensure_pc_skill_files(sandbox_backend)
    backend = _build_backend(sandbox_backend)

    pc_mcp_tools = await load_pc_tools()
    analysis_mcp_tools = await load_pc_analysis_tools()
    generate_visualization, extra_analysis_tools = create_generate_chart_tool(
        analysis_mcp_tools,
        params_path="/skills/pc/chart_params.md",
    )

    assign_skill = create_assign_skill_tool(
        sandbox_backend,
        store=STORE,
        skills_namespace=SKILLS_STORE_NAMESPACE,
    )
    download_sandbox_file = create_download_tool(sandbox_backend, DOWNLOAD_DIR)
    preferences_repository = PCPreferencesRepository(
        MONGODB_CLIENT[MONGODB_DB_NAME][MONGODB_PC_PREFERENCES_COLLECTION]
    )
    preferences_repository.ensure_indexes()
    save_pc_preferences = create_save_pc_preferences_tool(preferences_repository)
    print("[INFO] PC 长期偏好 MongoDB 集合已就绪（user_id 独立隔离）")

    available_tools = (
        list(pc_mcp_tools)
        + list(extra_analysis_tools)
        + [generate_visualization, web_search, assign_skill, download_sandbox_file]
    )
    print(f"[INFO] PC Agent 工具池: {[tool.name for tool in available_tools]}")

    raw_configs = load_subagent_configs(PC_SUBAGENT_CONFIG_DIR)
    # 将图表包装器以外的 MCP 能力（例如表格导出）完整交给 PC 分析子 Agent。
    analysis_extra_names = [tool.name for tool in extra_analysis_tools]
    for config in raw_configs:
        if config.get("name") == "pc-hardware-analyst":
            config["tools"] = list(dict.fromkeys(
                [*config.get("tools", []), *analysis_extra_names]
            ))
    if {config.get("name") for config in raw_configs} != {
        "pc-hardware-analyst",
        "pc-build-planner",
    }:
        raise RuntimeError("PC Agent 必须配置 pc-hardware-analyst 与 pc-build-planner 两个子 Agent")

    extra_middleware = {
        "pc-hardware-analyst": create_analyst_middleware(SUMMARY_MODEL, backend),
        "pc-build-planner": create_analyst_middleware(SUMMARY_MODEL, backend),
    }
    subagents = resolve_subagent_tools(
        raw_configs,
        available_tools,
        extra_middleware=extra_middleware,
        require_all_tools=True,
    )

    main_middleware = [
        PCPreferenceContextMiddleware(preferences_repository),
        SkillsSyncMiddleware(sandbox_backend, allowed_scopes={"main", "pc"}),
        UserSkillsRestoreMiddleware(
            sandbox_backend,
            SKILLS_STORE_NAMESPACE,
            allowed_scopes={"main", "pc"},
        ),
        build_summarization_middleware(backend, SUMMARY_MODEL),
        ModelCallLimitMiddleware(run_limit=50),
        ToolCallLimitMiddleware(run_limit=200),
    ]

    return create_deep_agent(
        model=MAIN_MODEL,
        system_prompt=_load_system_prompt(),
        skills=[
            "/skills/main/skill-management/",
            "/skills/pc/analysis/pc-hardware-analysis/",
            "/skills/pc/planning/pc-build-planning/",
        ],
        memory=["/skills/pc/AGENTS.md"],
        tools=[web_search, save_pc_preferences, assign_skill, download_sandbox_file],
        subagents=subagents,
        middleware=main_middleware,
        backend=backend,
        store=STORE,
        checkpointer=CHECKPOINTER,
        context_schema=ProcurementContext,
    )
