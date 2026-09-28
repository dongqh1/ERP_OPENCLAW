from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api_view.api import history


@pytest.mark.asyncio
async def test_session_list_sorts_and_paginates(monkeypatch):
    now = datetime(2026, 9, 28)
    thread_ids = ["older", "newer", "empty"]
    message_sets = {
        "older": [{"role": "human", "content": "旧采购"}, {"role": "ai", "content": "已完成"}],
        "newer": [{"role": "human", "content": "新采购"}, {"role": "ai", "content": "已完成"}],
        "empty": [],
    }

    monkeypatch.setattr(history.agent_loader, "get_all_thread_ids", lambda: thread_ids)
    monkeypatch.setattr(
        history.agent_loader,
        "get_current_messages",
        lambda thread_id: _async_value(message_sets[thread_id]),
    )
    monkeypatch.setattr(
        history.agent_loader,
        "get_session_updated_at",
        lambda thread_id: now + timedelta(days=thread_ids.index(thread_id)),
    )

    response = await history.get_sessions(page=1, limit=1)

    assert response.total == 2
    assert response.sessions[0].thread_id == "newer"
    assert response.sessions[0].title == "新采购"
    assert response.sessions[0].message_count == 1


@pytest.mark.asyncio
async def test_session_messages_prefers_saved_display_messages(monkeypatch):
    display = [{"id": "m1", "role": "assistant", "content": "完整记录"}]
    checkpoint_calls = []

    async def get_display_messages(thread_id):
        return display

    async def get_current_messages(thread_id):
        checkpoint_calls.append(thread_id)
        return []

    monkeypatch.setattr(history.agent_loader, "get_display_messages", get_display_messages)
    monkeypatch.setattr(history.agent_loader, "get_current_messages", get_current_messages)

    response = await history.get_session_messages("thread-1")

    assert response.thread_id == "thread-1"
    assert response.messages[0].content == "完整记录"
    assert checkpoint_calls == []


@pytest.mark.asyncio
async def test_session_messages_falls_back_to_checkpoint(monkeypatch):
    async def get_display_messages(thread_id):
        return None

    async def get_current_messages(thread_id):
        return [
            {"role": "human", "content": "旧会话"},
            {"role": "ai", "content": "兼容读取"},
        ]

    monkeypatch.setattr(history.agent_loader, "get_display_messages", get_display_messages)
    monkeypatch.setattr(history.agent_loader, "get_current_messages", get_current_messages)

    response = await history.get_session_messages("legacy-thread")

    assert [message.role for message in response.messages] == ["user", "assistant"]
    assert response.messages[0].content == "旧会话"


@pytest.mark.asyncio
async def test_delete_session_returns_loader_result(monkeypatch):
    deleted = []

    async def delete_session(thread_id):
        deleted.append(thread_id)
        return True

    monkeypatch.setattr(history.agent_loader, "delete_session", delete_session)

    response = await history.delete_session("thread-2")

    assert response.success is True
    assert deleted == ["thread-2"]


def _async_value(value):
    async def result():
        return value

    return result()


def test_history_route_rejects_invalid_pagination():
    app = FastAPI()
    app.include_router(history.router)

    with TestClient(app) as client:
        assert client.get("/history?page=0").status_code == 422
        assert client.get("/history?limit=101").status_code == 422
