from types import SimpleNamespace
from pathlib import Path

from agent.memory.prompts import system_prompt

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
        SimpleNamespace(name="supplier_query"),
        SimpleNamespace(name="supplier_search"),
        SimpleNamespace(name="order_create"),
        SimpleNamespace(name="part_search"),
        SimpleNamespace(name="part_by_supplier"),
        SimpleNamespace(name="evaluate_it_equipment_procurement"),
    ]

    subagents = resolve_subagent_tools(configs, tools)

    analyst = next(agent for agent in subagents if agent["name"] == "procurement-analyst")
    order = next(agent for agent in subagents if agent["name"] == "procurement-order")
    assert [tool.name for tool in analyst["tools"] if tool.name.startswith("supplier_")] == ["supplier_query"]
    assert "evaluate_it_equipment_procurement" in [tool.name for tool in analyst["tools"]]
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


def test_it_equipment_routing_and_evidence_rules_are_explicit():
    configs = load_subagent_configs()
    analyst = next(config for config in configs if config["name"] == "procurement-analyst")
    order = next(config for config in configs if config["name"] == "procurement-order")
    memory_rules = (Path(__file__).resolve().parents[1] / "src/agent/memory/AGENTS.md").read_text(encoding="utf-8")
    analysis_skill = (
        Path(__file__).resolve().parents[1] / "src/skills/procurement/procurement-analysis/SKILL.md"
    ).read_text(encoding="utf-8")

    assert "IT 设备采购分析" in system_prompt
    assert "procurement-analyst" in system_prompt
    assert "确认下单" in system_prompt and "procurement-order" in system_prompt
    assert "IT 设备" in memory_rules and "来源" in memory_rules
    assert "研发项目采购" in analysis_skill and "企业 IT 设备采购" in analysis_skill
    assert "evaluate_it_equipment_procurement" in analyst["tools"]
    for field in ("device_type", "budget_remaining", "minimum_warranty_months", "allowed_operating_systems", "offers"):
        assert field in analyst["system_prompt"]
    assert "needs_confirmation" in analyst["system_prompt"]
    assert "part_id" in order["system_prompt"]
    assert "part_search" in order["system_prompt"]
    assert "ERP 记录" in order["system_prompt"]
    assert "停止下单" in order["system_prompt"]
    assert "expectedDeliveryDate" in order["system_prompt"]
    assert order["interrupt_on"]["order_create"]["allowed_decisions"] == ["approve", "reject"]
    assert order["interrupt_on"]["order_update"]["allowed_decisions"] == ["approve", "reject"]
