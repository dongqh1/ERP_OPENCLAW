"""轻量采购领域路由；只选择领域，不处理采购业务。"""

from dataclasses import dataclass
from typing import Literal

ProcurementDomain = Literal["car", "pc"]


@dataclass(frozen=True)
class RouterDecision:
    domain: ProcurementDomain
    reason: str


class RouterAgent:
    """优先采用前端选择；兼容旧接口时根据关键词选择领域。"""

    PC_KEYWORDS = (
        "电脑", "pc", "cpu", "gpu", "显卡", "主板", "内存", "装机",
        "配置", "大表哥", "rdr2", "3a", "游戏本",
    )
    CAR_KEYWORDS = (
        "汽车", "摩托", "零部件", "刹车", "火花塞", "宝马", "车型",
        "发动机", "离合器", "制动系统", "车架", "轮胎",
    )

    def route(self, message: str, selected_domain: str | None = None) -> RouterDecision:
        if selected_domain in ("car", "pc"):
            return RouterDecision(selected_domain, "frontend_selection")

        normalized = (message or "").lower()
        has_pc = any(keyword in normalized for keyword in self.PC_KEYWORDS)
        has_car = any(keyword in normalized for keyword in self.CAR_KEYWORDS)
        if has_pc and not has_car:
            return RouterDecision("pc", "message_keywords")
        if has_car and not has_pc:
            return RouterDecision("car", "message_keywords")
        # 旧客户端不传 domain 时维持原有汽车 Agent 默认行为。
        return RouterDecision("car", "legacy_default")


router_agent = RouterAgent()


def route_domain(message: str, selected_domain: str | None = None) -> ProcurementDomain:
    return router_agent.route(message, selected_domain).domain
