from types import SimpleNamespace

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
    ]

    subagents = resolve_subagent_tools(configs, tools)

    analyst = next(agent for agent in subagents if agent["name"] == "procurement-analyst")
    order = next(agent for agent in subagents if agent["name"] == "procurement-order")
    assert [tool.name for tool in analyst["tools"] if tool.name.startswith("supplier_")] == ["supplier_query"]
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
