"""PC Agent 按需查询陌生术语的 MCP 工具。"""

import asyncio
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field

from fastmcp import FastMCP

_CACHE_TTL_SECONDS = 24 * 60 * 60
_CACHE_MAX_ENTRIES = 128
_MAX_TERM_LENGTH = 100
_MAX_SNIPPET_LENGTH = 500
_MAX_RESULT_LENGTH = 1200

_CACHE: OrderedDict[str, tuple[float, str]] = OrderedDict()
@dataclass
class _LookupFlight:
    """同一术语并发查询时共享一次网络请求的结果。"""

    completed: threading.Event = field(default_factory=threading.Event)
    summary: str = ""


_IN_FLIGHT: dict[str, _LookupFlight] = {}
_CACHE_LOCK = threading.Lock()


def _call_web_search(query: str) -> str:
    """延迟导入共享搜索工具，避免 PC MCP 启动时依赖搜索 API 可用。"""
    from agent.tools.web_search import web_search

    return str(web_search.invoke({"query": query}))


def _compact_results(raw_results: str) -> str:
    """最多保留 3 段搜索摘要，并限制总长度。"""
    content = (raw_results or "").strip()
    if not content or content == "没有搜索到任何内容！" or content.startswith("搜索失败"):
        return ""

    snippets = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
    compacted = "\n\n".join(part[:_MAX_SNIPPET_LENGTH] for part in snippets[:3])
    return compacted[:_MAX_RESULT_LENGTH]


def _cached_summary(key: str) -> str | None:
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached is None:
            return None
        expires_at, summary = cached
        if expires_at <= now:
            _CACHE.pop(key, None)
            return None
        _CACHE.move_to_end(key)
        return summary


def _store_summary(key: str, summary: str) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic() + _CACHE_TTL_SECONDS, summary)
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_MAX_ENTRIES:
            _CACHE.popitem(last=False)


def lookup_pc_term(term: str) -> dict:
    """查询并缓存一个需要澄清的 PC、游戏或 AI 术语。"""
    normalized_term = " ".join((term or "").split()).strip('"“”')
    if not normalized_term:
        return {"status": "invalid_term", "message": "请提供要解释的术语。"}
    if len(normalized_term) > _MAX_TERM_LENGTH:
        return {
            "status": "invalid_term",
            "message": f"术语过长，请只提供名称（最多 {_MAX_TERM_LENGTH} 个字符）。",
        }

    key = normalized_term.casefold()
    summary = _cached_summary(key)
    if summary is not None:
        return {"status": "success", "term": normalized_term, "summary": summary, "cached": True}

    with _CACHE_LOCK:
        flight = _IN_FLIGHT.get(key)
        is_owner = flight is None
        if is_owner:
            flight = _LookupFlight()
            _IN_FLIGHT[key] = flight

    if not is_owner:
        # 并发请求等待首次查询完成，并共享它的成功或失败结果。
        flight.completed.wait()
        if flight.summary:
            return {"status": "success", "term": normalized_term, "summary": flight.summary, "cached": True}
        return {
            "status": "search_unavailable",
            "term": normalized_term,
            "message": "暂时没有查到可靠的术语解释；请向用户追问，不要猜测。",
            "cached": False,
        }

    query = f'"{normalized_term}" 是什么 用途 游戏 软件 硬件 AI'
    try:
        try:
            summary = _compact_results(_call_web_search(query))
        except Exception:
            summary = ""

        flight.summary = summary
        if summary:
            # 在释放并发请求前写入缓存，避免边界时刻再次发起相同搜索。
            _store_summary(key, summary)
            return {"status": "success", "term": normalized_term, "summary": summary, "cached": False}

        return {
            "status": "search_unavailable",
            "term": normalized_term,
            "message": "暂时没有查到可靠的术语解释；请向用户追问，不要猜测。",
            "cached": False,
        }
    finally:
        with _CACHE_LOCK:
            if _IN_FLIGHT.get(key) is flight:
                _IN_FLIGHT.pop(key, None)
            flight.completed.set()


def register_term_lookup_tools(mcp: FastMCP) -> None:
    """仅向 PC MCP 注册术语解释能力，不暴露给汽车 Agent。"""

    @mcp.tool(name="pc_term_lookup")
    async def pc_term_lookup(term: str) -> dict:
        """仅在无法判断某个 PC、游戏或 AI 名称的含义且会影响配置时搜索解释。不要用来查价格、库存或实时行情。"""
        return await asyncio.to_thread(lookup_pc_term, term)
