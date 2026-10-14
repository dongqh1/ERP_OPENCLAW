"""Pure, deterministic policy for evaluating IT equipment quotations."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


_REQUIRED_OFFER_FIELDS = (
    "supplier_name",
    "supplier_id",
    "part_id",
    "device_type",
    "model_name",
    "unit_price",
    "delivery_date",
    "warranty_months",
    "cpu_cores",
    "memory_gb",
    "storage_gb",
    "operating_system",
    "source",
)
_SPEC_FIELDS = {
    "warranty_months": "minimum_warranty_months",
    "cpu_cores": "min_cpu_cores",
    "memory_gb": "min_memory_gb",
    "storage_gb": "min_storage_gb",
    "operating_system": "allowed_operating_systems",
}


def _date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result if result.is_finite() else None


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def evaluate_it_equipment_policy(request: dict) -> dict:
    """Evaluate each IT device offer against the request's hard constraints.

    Missing evidence is reported as unverified and cannot produce a recommendation.
    Contradictory evidence is reported as failed and makes the offer ineligible.
    """
    quantity = request.get("quantity")
    quantity_valid = isinstance(quantity, int) and not isinstance(quantity, bool) and quantity > 0
    budget = _decimal(request.get("budget_remaining"))
    deadline = _date(request.get("deadline"))
    allowed_systems = request.get("allowed_operating_systems")
    allowed_systems = list(allowed_systems or [])

    summary = {
        "device_type": request.get("device_type"),
        "requirement": request.get("requirement"),
        "quantity": quantity,
        "budget_remaining": _money(budget) if budget is not None else None,
        "deadline": deadline.isoformat() if deadline else None,
        "minimum_warranty_months": request.get("minimum_warranty_months"),
        "min_cpu_cores": request.get("min_cpu_cores"),
        "min_memory_gb": request.get("min_memory_gb"),
        "min_storage_gb": request.get("min_storage_gb"),
        "allowed_operating_systems": allowed_systems,
    }
    evaluated = []
    for raw in request.get("offers") or []:
        offer = dict(raw)
        failed: list[str] = []
        unverified: list[str] = []

        for key in _REQUIRED_OFFER_FIELDS:
            value = offer.get(key)
            if value is None or value == "":
                constraint = _SPEC_FIELDS.get(key, key)
                if constraint not in unverified:
                    unverified.append(constraint)

        total: Decimal | None = None
        price = _decimal(offer.get("unit_price"))
        if price is None:
            if "unit_price" not in unverified:
                unverified.append("unit_price")
        elif price <= 0:
            failed.append("unit_price")
        elif quantity_valid:
            total = price * quantity
            if budget is None:
                unverified.append("budget_remaining")
            elif total > budget:
                failed.append("budget_remaining")
        else:
            unverified.append("quantity")

        if offer.get("device_type") is not None and offer.get("device_type") != request.get("device_type"):
            failed.append("device_type")

        for offer_field, request_field in (
            ("warranty_months", "minimum_warranty_months"),
            ("cpu_cores", "min_cpu_cores"),
            ("memory_gb", "min_memory_gb"),
            ("storage_gb", "min_storage_gb"),
        ):
            observed = offer.get(offer_field)
            minimum = request.get(request_field)
            constraint = request_field
            if observed is None or observed == "" or minimum is None:
                if constraint not in unverified:
                    unverified.append(constraint)
            else:
                try:
                    if Decimal(str(observed)) < Decimal(str(minimum)):
                        failed.append(constraint)
                except (InvalidOperation, TypeError, ValueError):
                    if constraint not in unverified:
                        unverified.append(constraint)

        system = offer.get("operating_system")
        if not system or not allowed_systems:
            if "allowed_operating_systems" not in unverified:
                unverified.append("allowed_operating_systems")
        elif system not in allowed_systems:
            failed.append("allowed_operating_systems")

        delivery = _date(offer.get("delivery_date"))
        if delivery is None or deadline is None:
            if "deadline" not in unverified:
                unverified.append("deadline")
        elif delivery > deadline:
            failed.append("deadline")

        if failed:
            status = "ineligible"
        elif unverified:
            status = "needs_confirmation"
        else:
            status = "eligible"

        evaluated_offer = {
            "supplier_name": offer.get("supplier_name"),
            "supplier_id": offer.get("supplier_id"),
            "part_id": offer.get("part_id"),
            "device_type": offer.get("device_type"),
            "model_name": offer.get("model_name"),
            "unit_price": _money(price) if price is not None else None,
            "quantity": quantity,
            "estimated_total": _money(total) if total is not None else None,
            "delivery_date": delivery.isoformat() if delivery else None,
            "warranty_months": offer.get("warranty_months"),
            "cpu_cores": offer.get("cpu_cores"),
            "memory_gb": offer.get("memory_gb"),
            "storage_gb": offer.get("storage_gb"),
            "operating_system": offer.get("operating_system"),
            "source": offer.get("source"),
            "status": status,
            "failed_constraints": failed,
            "unverified_constraints": unverified,
        }
        evaluated.append(evaluated_offer)

    evaluated.sort(key=lambda item: (
        {"eligible": 0, "needs_confirmation": 1, "ineligible": 2}[item["status"]],
        Decimal(item["estimated_total"]) if item["estimated_total"] is not None else Decimal("Infinity"),
        item["delivery_date"] or "9999-12-31",
    ))
    recommendation = next((item for item in evaluated if item["status"] == "eligible"), None)
    message = (
        "已找到满足预算、配置、保修及交期要求的合格报价，并推荐总价最低方案。"
        if recommendation
        else "目前没有满足全部要求且信息已核实的报价；请补充缺失信息或调整采购条件。"
    )
    return {
        "request_summary": summary,
        "offers": evaluated,
        "recommendation": recommendation,
        "summary": message,
    }
