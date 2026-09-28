import yaml

from agent.middlewares.memory_update import _merge_preferences
from agent.schema import UserPreferences


def test_merge_preferences_preserves_settings_and_orders_recent_items_first():
    current = [
        "preferred_output: chart",
        "preferred_currency: CNY",
        "recent_suppliers:",
        "  - 大陆",
        "  - 博世",
        "recent_queries: [旧查询]",
    ]

    merged = yaml.safe_load(_merge_preferences(current, ["博世", "电装"], "新查询"))

    assert merged["preferred_output"] == "chart"
    assert merged["preferred_currency"] == "CNY"
    assert merged["recent_suppliers"] == ["博世", "电装", "大陆"]
    assert merged["recent_queries"] == ["新查询", "旧查询"]


def test_merge_preferences_caps_supplier_and_query_history():
    suppliers = [f"supplier-{index}" for index in range(12)]
    queries = [f"query-{index}" for index in range(7)]
    current = ["recent_suppliers:", *[f"  - {item}" for item in suppliers]]
    current.extend(["recent_queries:", *[f"  - {item}" for item in queries]])

    merged = yaml.safe_load(_merge_preferences(current, ["new-supplier"], "new-query"))

    assert len(merged["recent_suppliers"]) == 10
    assert len(merged["recent_queries"]) == 5
    assert merged["recent_suppliers"][0] == "new-supplier"
    assert merged["recent_queries"][0] == "new-query"


def test_user_preference_history_defaults_are_not_shared():
    first = UserPreferences()
    second = UserPreferences()
    first.recent_suppliers.append("博世")

    assert second.recent_suppliers == []
    assert second.recent_queries == []
