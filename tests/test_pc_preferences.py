import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "agent" / "agents" / "pc_agent" / "preferences.py"


def _preferences_module():
    assert MODULE_PATH.is_file(), "PC preference persistence module has not been implemented"
    return importlib.import_module("agent.agents.pc_agent.preferences")


class FakeCollection:
    def __init__(self):
        self.documents = {}
        self.indexes = []

    def create_index(self, keys, unique=False):
        self.indexes.append((keys, unique))

    def find_one(self, query, projection=None):
        document = self.documents.get(query["user_id"])
        if document is None:
            return None
        return {key: value for key, value in document.items() if key != "_id"}

    def update_one(self, query, update, upsert=False):
        document = self.documents.setdefault(query["user_id"], {"user_id": query["user_id"]})
        document.update(update.get("$setOnInsert", {}))
        document.update(update.get("$set", {}))


def test_pc_preferences_are_persisted_and_isolated_by_user():
    module = _preferences_module()
    collection = FakeCollection()
    repository = module.PCPreferencesRepository(collection)
    repository.ensure_indexes()

    repository.update("user-a", {"default_budget_cny": 12000, "condition_preference": "new"})
    repository.update("user-a", {"preferred_gpu_brands": ["NVIDIA"]})

    user_a = repository.get("user-a")
    user_b = repository.get("user-b")
    assert user_a.default_budget_cny == 12000
    assert user_a.condition_preference == "new"
    assert user_a.preferred_gpu_brands == ["NVIDIA"]
    assert user_b.default_budget_cny is None
    assert collection.indexes and collection.indexes[0][1] is True


def test_one_off_request_is_not_saved_as_a_default():
    module = _preferences_module()
    repository = module.PCPreferencesRepository(FakeCollection())

    saved, preferences = repository.update_if_explicit(
        "user-a",
        "预算8000元，帮我配一台玩游戏的电脑",
        {"default_budget_cny": 8000},
    )

    assert saved is False
    assert preferences.default_budget_cny is None


def test_explicit_long_term_preference_is_saved():
    module = _preferences_module()
    repository = module.PCPreferencesRepository(FakeCollection())

    saved, preferences = repository.update_if_explicit(
        "user-a",
        "以后配置电脑默认优先 NVIDIA，记住这个偏好",
        {"preferred_gpu_brands": ["NVIDIA"]},
    )

    assert saved is True
    assert preferences.preferred_gpu_brands == ["NVIDIA"]


def test_negated_memory_request_is_not_treated_as_persistent_intent():
    module = _preferences_module()

    assert module.has_explicit_persistent_intent("这次预算不用记住") is False


def test_preference_schema_rejects_invalid_budget_and_condition():
    module = _preferences_module()

    with pytest.raises(ValidationError):
        module.PCPreferenceUpdate(default_budget_cny=0)
    with pytest.raises(ValidationError):
        module.PCPreferenceUpdate(condition_preference="refurbished")


def test_save_tool_uses_runtime_identity_without_exposing_user_id_argument():
    module = _preferences_module()
    tool = module.create_save_pc_preferences_tool(
        module.PCPreferencesRepository(FakeCollection())
    )

    schema = tool.tool_call_schema.model_json_schema()
    properties = schema["properties"]

    assert "user_id" not in properties
    assert "runtime" not in properties
    assert "default_budget_cny" in properties


def test_pc_preferences_are_injected_into_agent_context():
    module = _preferences_module()
    repository = module.PCPreferencesRepository(FakeCollection())
    repository.update("user-a", {"preferred_gpu_brands": ["NVIDIA"]})
    middleware = module.PCPreferenceContextMiddleware(repository)
    runtime = SimpleNamespace(context=SimpleNamespace(user_id="user-a"))

    result = middleware.before_agent({}, runtime)

    assert result is not None
    assert "NVIDIA" in result["messages"][0].content
    assert "PC 用户长期偏好" in result["messages"][0].content
