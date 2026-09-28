import json
from types import SimpleNamespace

import pytest

from api_view.api import chat


def _event_lines(chunks):
    events = []
    for chunk in chunks:
        if chunk.startswith("data: "):
            events.append(json.loads(chunk[6:].strip()))
    return events


@pytest.mark.asyncio
async def test_chat_stream_emits_tokens_and_persists_tool_results(monkeypatch):
    class FakeAgent:
        async def astream(self, **kwargs):
            chunks = [
                SimpleNamespace(type="ai", content="", tool_call_chunks=[{"name": "supplier_query"}]),
                SimpleNamespace(type="ai", content="", tool_call_chunks=[{"args": '{"name":"博世"}'}]),
                SimpleNamespace(
                    type="tool",
                    name="supplier_query",
                    content='[{"name":"博世"}]',
                    tool_call_chunks=[],
                ),
                SimpleNamespace(type="ai", content="查到博世供应商", tool_call_chunks=[]),
            ]
            for token in chunks:
                yield {"type": "messages", "data": (token, {}), "ns": ()}

    saved = []

    monkeypatch.setattr(chat.agent_loader, "_agent", FakeAgent())
    monkeypatch.setattr(chat.agent_loader, "create_config", lambda thread_id: {"thread_id": thread_id})
    monkeypatch.setattr(chat.agent_loader, "get_display_messages", _async_return(None))
    monkeypatch.setattr(
        chat.agent_loader,
        "save_display_messages",
        lambda thread_id, messages: _append(saved, thread_id, messages),
    )
    monkeypatch.setattr(chat, "write_debug_log", lambda *args, **kwargs: None)

    events = _event_lines([
        chunk async for chunk in chat.stream_chat_response("查博世", "thread-1")
    ])

    assert [event["type"] for event in events] == [
        "tool_start", "tool_args", "tool_result", "tool_end", "token", "done"
    ]
    assert events[2]["text"] == '[{"name":"博世"}]'
    assert events[4]["content"] == "查到博世供应商"
    assert events[-1]["thread_id"] == "thread-1"
    assert saved[0][1][-1]["content"] == "查到博世供应商"
    assert saved[0][1][1]["tool_status"] == "done"


@pytest.mark.asyncio
async def test_chat_stream_emits_supplement_interrupt_and_saves_partial_messages(monkeypatch):
    class FakeAgent:
        async def astream(self, **kwargs):
            interrupt = SimpleNamespace(value={
                "type": "order_info_request",
                "missing_fields": ["supplier_id"],
                "collected_data": {"order_number": "PO123"},
            })
            yield {"type": "values", "interrupts": [interrupt]}

    saved = []
    existing = [{"id": "old-user", "role": "user", "content": "创建订单"}]

    monkeypatch.setattr(chat.agent_loader, "_agent", FakeAgent())
    monkeypatch.setattr(chat.agent_loader, "create_config", lambda thread_id: {"thread_id": thread_id})
    monkeypatch.setattr(chat.agent_loader, "get_display_messages", _async_return(existing))
    monkeypatch.setattr(
        chat.agent_loader,
        "save_display_messages",
        lambda thread_id, messages: _append(saved, thread_id, messages),
    )
    monkeypatch.setattr(chat, "write_debug_log", lambda *args, **kwargs: None)

    events = _event_lines([
        chunk async for chunk in chat.stream_chat_response(
            thread_id="thread-2",
            resume_data={"supplement": "供应商编号 7"},
        )
    ])

    assert events[0]["type"] == "interrupt"
    assert events[0]["interrupt_type"] == "order_info_supplement"
    assert events[0]["missing_fields"] == ["supplier_id"]
    assert events[1]["type"] == "done"
    assert events[1]["interrupted"] is True
    assert saved[0][1] == existing


def _async_return(value):
    async def result(*args, **kwargs):
        return value

    return result


async def _append(target, thread_id, messages):
    target.append((thread_id, messages))
    return True
