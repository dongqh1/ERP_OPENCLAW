import json
from types import SimpleNamespace

from api_view.api.chat import (
    create_sse_message,
    extract_content_from_token,
    is_likely_uuid,
    serialize_tool_result,
)
from api_view.api.history import (
    extract_images_from_content,
    get_message_content,
    get_message_role,
    serialize_messages_from_checkpoint,
)


def test_token_content_and_uuid_filtering():
    token = SimpleNamespace(content=["hello", {"type": "text", "text": "采购"}, {"type": "image_url", "image_url": "ignored"}])

    assert extract_content_from_token(token) == "hello采购"
    assert is_likely_uuid("3576bba4-42e5-a769-c2f7-ea8444829951")
    assert not is_likely_uuid("有意义的回复")


def test_tool_result_serialization_keeps_text_and_image_data():
    result = serialize_tool_result([
        {"type": "text", "text": "报告已生成"},
        {"type": "image_url", "image_url": {"url": "https://example.test/chart"}},
        {"type": "image", "data": "data:image/png;base64,AAAA"},
    ])

    assert result == {
        "text": "报告已生成",
        "images": ["https://example.test/chart", "data:image/png;base64,AAAA"],
    }


def test_sse_event_is_valid_json_and_preserves_chinese():
    encoded = create_sse_message({"type": "done", "content": "采购建议"})

    assert encoded.startswith("data: ")
    assert json.loads(encoded[6:].strip()) == {"type": "done", "content": "采购建议"}


def test_checkpoint_serialization_pairs_tool_calls_with_results():
    messages = [
        {"role": "human", "content": "查博世供应商"},
        {
            "role": "assistant",
            "content": "正在查询",
            "tool_calls": [{"name": "supplier_query", "args": {"name": "博世"}}],
        },
        {"role": "tool", "name": "supplier_query", "content": "[{\"id\":1}]"},
        {"role": "assistant", "content": "找到了 1 家供应商"},
    ]

    serialized = serialize_messages_from_checkpoint(messages)

    assert [message["role"] for message in serialized] == ["user", "assistant", "tool", "assistant"]
    assert serialized[2]["tool_name"] == "supplier_query"
    assert serialized[2]["tool_status"] == "done"
    assert serialized[2]["text"] == "[{\"id\":1}]"
    assert get_message_role({"role": "ai"}) == "assistant"
    assert get_message_content({"content": [{"type": "text", "text": "A"}, {"content": "B"}]}) == "AB"


def test_image_extraction_supports_structured_and_markdown_content():
    assert extract_images_from_content([
        {"type": "image_url", "image_url": {"url": "https://example.test/a"}},
        {"type": "image", "data": "data:image/png;base64,BBBB"},
    ]) == ["https://example.test/a", "data:image/png;base64,BBBB"]
    assert extract_images_from_content("![chart](https://example.test/chart.png)") == [
        "https://example.test/chart.png"
    ]
