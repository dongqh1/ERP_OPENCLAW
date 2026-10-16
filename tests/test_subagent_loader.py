from types import SimpleNamespace
from pathlib import Path

import yaml

from agent.memory.prompts import system_prompt
from agent.router import route_domain

from agent.subagents.loader import (
    _validate_subagent_config,
    load_subagent_configs,
    resolve_subagent_tools,
)


def test_loader_skips_empty_yaml_instead_of_crashing(tmp_path):
    (tmp_path / "empty.yaml").write_text("", encoding="utf-8")

    assert load_subagent_configs(tmp_path) == []


def test_repository_subagent_configs_load_and_resolve_tools():
    configs = load_subagent_configs()
    tools = [
        SimpleNamespace(name="car_part_query"),
        SimpleNamespace(name="vehicle_match_check"),
        SimpleNamespace(name="car_price_estimate"),
        SimpleNamespace(name="supplier_query"),
        SimpleNamespace(name="supplier_search"),
        SimpleNamespace(name="part_query"),
        SimpleNamespace(name="order_create"),
        SimpleNamespace(name="order_update"),
        SimpleNamespace(name="order_search_details"),
        SimpleNamespace(name="inventory_warning"),
        SimpleNamespace(name="part_search"),
        SimpleNamespace(name="part_by_supplier"),
        SimpleNamespace(name="evaluate_project_procurement"),
        SimpleNamespace(name="generate_visualization"),
        SimpleNamespace(name="web_search"),
        # Deliberately include cross-domain tools to verify they are not assigned
        # to the car subagents just because they exist in a shared test pool.
        SimpleNamespace(name="evaluate_it_equipment_procurement"),
        SimpleNamespace(name="pc_compatibility_check"),
    ]

    subagents = resolve_subagent_tools(configs, tools)

    analyst = next(agent for agent in subagents if agent["name"] == "procurement-analyst")
    order = next(agent for agent in subagents if agent["name"] == "procurement-order")
    analyst_tool_names = {tool.name for tool in analyst["tools"]}
    assert [tool.name for tool in analyst["tools"] if tool.name.startswith("supplier_")] == ["supplier_query"]
    assert {
        "car_part_query",
        "vehicle_match_check",
        "car_price_estimate",
        "evaluate_project_procurement",
    }.issubset(analyst_tool_names)
    assert "evaluate_it_equipment_procurement" not in analyst_tool_names
    assert "pc_compatibility_check" not in analyst_tool_names
    assert {"part_search", "part_by_supplier"}.issubset({tool.name for tool in order["tools"]})
    assert "interrupt_on" in order


def test_config_validator_rejects_non_mapping_and_non_string_tool_names():
    assert _validate_subagent_config(None, "empty.yaml")
    invalid_tools = {
        "name": "example",
        "description": "example agent",
        "system_prompt": "instructions",
        "tools": [3],
    }

    assert _validate_subagent_config(invalid_tools, "invalid.yaml")


def test_car_and_pc_routing_and_evidence_rules_are_domain_isolated():
    configs = load_subagent_configs()
    analyst = next(config for config in configs if config["name"] == "procurement-analyst")
    order = next(config for config in configs if config["name"] == "procurement-order")
    project_root = Path(__file__).resolve().parents[1]
    memory_rules = (project_root / "src/agent/memory/AGENTS.md").read_text(encoding="utf-8")
    analysis_skill = (
        project_root / "src/skills/procurement/procurement-analysis/SKILL.md"
    ).read_text(encoding="utf-8")
    pc_prompt = yaml.safe_load(
        (project_root / "src/agent/agents/pc_agent/prompt.yaml").read_text(encoding="utf-8")
    )["system_prompt"]
    pc_configs = load_subagent_configs(
        project_root / "src/agent/agents/pc_agent/subagents/configs"
    )
    pc_analyst = next(config for config in pc_configs if config["name"] == "pc-hardware-analyst")
    pc_planner = next(config for config in pc_configs if config["name"] == "pc-build-planner")

    assert route_domain("帮我配置一台电脑") == "pc"
    assert route_domain("宝马刹车系统采购") == "car"
    assert "PC 电脑配置需求属于独立 PC Agent" in system_prompt
    assert "procurement-analyst" in system_prompt
    assert "订单查询、创建、修改委派 procurement-order" in system_prompt
    assert "本文件仅约束汽车/摩托车零部件采购" in memory_rules
    assert "PC 配置由独立 PC Agent" in analysis_skill
    assert "研发项目采购决策" in analysis_skill
    assert "只分析汽车/摩托车 ERP 采购数据" in analyst["system_prompt"]
    assert "不调用 PC 硬件工具" in analyst["system_prompt"]
    assert "evaluate_it_equipment_procurement" not in analyst["tools"]
    assert "只处理电脑硬件配置与分析" in pc_prompt
    assert "不调用汽车零部件、供应商或订单业务" in pc_prompt
    assert "pc_term_lookup" in pc_analyst["tools"]
    assert "pc_budget_optimizer" in pc_planner["tools"]
    assert "pc_compatibility_check" in pc_planner["tools"]
    assert not ({"car_part_query", "vehicle_match_check", "order_create"} & set(pc_analyst["tools"]))
    assert not ({"car_part_query", "vehicle_match_check", "order_create"} & set(pc_planner["tools"]))
    assert "partId" in order["system_prompt"]
    assert "part_search" in order["system_prompt"]
    assert "按返回记录核对 ID" in order["system_prompt"]
    assert "request_order_info" in order["system_prompt"]
    assert "人工最终审批" in order["system_prompt"]
    assert "expectedDeliveryDate" in order["system_prompt"]
    assert order["interrupt_on"]["order_create"]["allowed_decisions"] == ["approve", "reject"]
    assert order["interrupt_on"]["order_update"]["allowed_decisions"] == ["approve", "reject"]
