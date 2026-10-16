"""PC 领域的持久偏好读取、校验与保存。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Literal

from langchain.agents.middleware import AgentMiddleware
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import SystemMessage
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pymongo import ASCENDING

from agent.schema import ProcurementContext


PreferenceCondition = Literal["new", "used", "any", "best_value"]
PreferenceOutput = Literal["table", "chart"]
PreferenceChart = Literal["bar", "line", "pie", "radar"]


class PCOwnedComponent(BaseModel):
    """明确确认过的自有硬件，带确认时间以便判断信息是否过期。"""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(description="CPU、GPU、MOTHERBOARD、MEMORY、STORAGE、COOLER、POWER 或 CASE")
    model: str = Field(min_length=1, description="硬件型号")
    confirmed_at: datetime | None = Field(default=None, description="用户确认该硬件仍持有的时间")


class PCPreferenceUpdate(BaseModel):
    """用户明确要求长期保存的 PC 偏好字段。"""

    model_config = ConfigDict(extra="forbid")

    default_budget_cny: int | None = Field(default=None, gt=0, description="今后配置电脑时的默认预算")
    preferred_gpu_brands: list[str] | None = Field(default=None, description="偏好的显卡品牌")
    preferred_cpu_brands: list[str] | None = Field(default=None, description="偏好的 CPU 品牌")
    condition_preference: PreferenceCondition | None = Field(default=None, description="新件、二手、均可或性价比偏好")
    default_use_cases: list[str] | None = Field(default=None, description="默认用途，例如 AI 研究、游戏")
    default_resolution: str | None = Field(default=None, description="默认游戏分辨率")
    preferred_output: PreferenceOutput | None = Field(default=None, description="偏好的输出形式")
    preferred_chart_type: PreferenceChart | None = Field(default=None, description="偏好的图表类型")
    owned_components: list[PCOwnedComponent] | None = Field(default=None, description="用户明确要求长期记住的自有硬件")

    @field_validator("preferred_gpu_brands", "preferred_cpu_brands", "default_use_cases")
    @classmethod
    def clean_string_lists(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class PCPreferences(PCPreferenceUpdate):
    """MongoDB 中按 user_id 隔离保存的 PC 偏好记录。"""

    model_config = ConfigDict(extra="ignore")

    user_id: str
    updated_at: datetime | None = None


_PERSISTENT_INTENT_PATTERNS = (
    r"记住",
    r"以后(?:默认|都|优先|配置)",
    r"今后(?:默认|都|优先|配置)",
    r"长期偏好",
    r"每次都",
    r"from\s+now\s+on",
    r"always",
    r"remember",
)
_NEGATED_MEMORY_PATTERNS = (
    r"(?:不要|不必|不需要|不用|无需|别|没必要)记住",
    r"(?:don't|do not|never)\s+remember",
)


def has_explicit_persistent_intent(user_message: str) -> bool:
    """只接受明确的长期记忆表达，避免把单次任务条件存成默认值。"""
    message = user_message.strip().lower()
    if not message or any(re.search(pattern, message) for pattern in _NEGATED_MEMORY_PATTERNS):
        return False
    return any(re.search(pattern, message) for pattern in _PERSISTENT_INTENT_PATTERNS)


class PCPreferencesRepository:
    """对 PC 专属 MongoDB 集合的最小读写封装。"""

    def __init__(self, collection: Any) -> None:
        self.collection = collection

    def ensure_indexes(self) -> None:
        self.collection.create_index([("user_id", ASCENDING)], unique=True)

    def get(self, user_id: str) -> PCPreferences:
        if not user_id.strip():
            raise ValueError("user_id 不能为空")
        document = self.collection.find_one({"user_id": user_id}) or {}
        document.pop("_id", None)
        document.pop("user_id", None)
        return PCPreferences(user_id=user_id, **document)

    def update(self, user_id: str, updates: dict[str, Any] | PCPreferenceUpdate) -> PCPreferences:
        if not user_id.strip():
            raise ValueError("user_id 不能为空")
        typed_updates = (
            updates if isinstance(updates, PCPreferenceUpdate)
            else PCPreferenceUpdate.model_validate(updates)
        )
        changes = typed_updates.model_dump(exclude_unset=True, mode="python")
        if not changes:
            return self.get(user_id)
        changes["updated_at"] = datetime.now(timezone.utc)
        self.collection.update_one(
            {"user_id": user_id},
            {
                "$set": changes,
                "$setOnInsert": {"user_id": user_id},
            },
            upsert=True,
        )
        return self.get(user_id)

    def update_if_explicit(
        self,
        user_id: str,
        user_message: str,
        updates: dict[str, Any] | PCPreferenceUpdate,
    ) -> tuple[bool, PCPreferences]:
        if not has_explicit_persistent_intent(user_message):
            return False, self.get(user_id)
        typed_updates = (
            updates if isinstance(updates, PCPreferenceUpdate)
            else PCPreferenceUpdate.model_validate(updates)
        )
        if not typed_updates.model_dump(exclude_unset=True):
            return False, self.get(user_id)
        return True, self.update(user_id, typed_updates)


def _latest_user_message(messages: list[Any]) -> str:
    for message in reversed(messages):
        role = getattr(message, "type", None)
        if role is None and isinstance(message, dict):
            role = message.get("role")
        if role not in {"human", "user"}:
            continue
        content = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            content = message.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        return str(content or "")
    return ""


def create_save_pc_preferences_tool(repository: PCPreferencesRepository):
    """创建只使用运行时身份的 PC 偏好保存工具。"""

    @tool("save_pc_preferences")
    def save_pc_preferences(
        default_budget_cny: int | None = None,
        preferred_gpu_brands: list[str] | None = None,
        preferred_cpu_brands: list[str] | None = None,
        condition_preference: PreferenceCondition | None = None,
        default_use_cases: list[str] | None = None,
        default_resolution: str | None = None,
        preferred_output: PreferenceOutput | None = None,
        preferred_chart_type: PreferenceChart | None = None,
        owned_components: list[PCOwnedComponent] | None = None,
        runtime: ToolRuntime[ProcurementContext] = None,
    ) -> str:
        """保存用户明确要求长期记住的 PC 配置偏好；不能保存单次任务条件。"""
        context = getattr(runtime, "context", None)
        user_id = getattr(context, "user_id", None)
        if not user_id:
            return "无法保存 PC 偏好：运行时缺少用户身份。"

        updates = {
            "default_budget_cny": default_budget_cny,
            "preferred_gpu_brands": preferred_gpu_brands,
            "preferred_cpu_brands": preferred_cpu_brands,
            "condition_preference": condition_preference,
            "default_use_cases": default_use_cases,
            "default_resolution": default_resolution,
            "preferred_output": preferred_output,
            "preferred_chart_type": preferred_chart_type,
            "owned_components": owned_components,
        }
        updates = {key: value for key, value in updates.items() if value is not None}
        messages = getattr(runtime, "state", {}).get("messages", [])
        latest_message = _latest_user_message(messages)
        saved, preferences = repository.update_if_explicit(user_id, latest_message, updates)
        if not saved:
            return "未保存：本轮消息未明确要求记住长期偏好，或没有提供可保存字段。"
        payload = preferences.model_dump(exclude_none=True, mode="json")
        return "已保存 PC 长期偏好：" + json.dumps(payload, ensure_ascii=False)

    return save_pc_preferences


class PCPreferenceContextMiddleware(AgentMiddleware):
    """在 PC Agent 开始处理任务时注入该用户独立的 PC 长期偏好。"""

    def __init__(self, repository: PCPreferencesRepository) -> None:
        super().__init__()
        self.repository = repository

    def before_agent(self, state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
        context = getattr(runtime, "context", None)
        user_id = getattr(context, "user_id", None)
        if not user_id:
            return None
        preferences = self.repository.get(user_id)
        values = preferences.model_dump(
            exclude={"user_id", "updated_at"},
            exclude_none=True,
            mode="json",
        )
        if not values:
            return None
        notice = (
            "【PC 用户长期偏好】以下内容只适用于 PC 配置，且仅在当前请求没有明确相反约束时应用。"
            "将相关偏好传给配置规划子 Agent；不能把当前请求中的临时预算或临时保留硬件写成长期偏好。\n"
            + json.dumps(values, ensure_ascii=False)
        )
        return {"messages": [SystemMessage(content=notice)]}

    async def abefore_agent(self, state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
        return self.before_agent(state, runtime)
