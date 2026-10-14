"""Deterministic project-level procurement feasibility evaluation."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class SupplierOffer(BaseModel):
    """A supplier offer backed by a query result or an explicit quotation."""

    supplier_name: str = Field(min_length=1, description="供应商名称")
    supplier_id: int | None = Field(default=None, description="供应商 ID")
    part_id: int = Field(description="对应物料 ID")
    part_name: str = Field(min_length=1, description="物料名称或已确认的等效物料名称")
    unit_price: Decimal = Field(gt=0, description="有来源依据的单价")
    delivery_date: date | None = Field(
        default=None,
        description="供应商承诺交付日期；没有可靠来源时留空",
    )
    source: str = Field(min_length=1, description="报价或 ERP 数据来源说明")


class ProjectProcurementRequest(BaseModel):
    """Constraints and sourced supplier offers for one project purchase line."""

    project_name: str = Field(min_length=1, description="项目名称")
    requirement: str = Field(min_length=1, description="采购需求或规格")
    quantity: int = Field(gt=0, description="本次采购数量")
    budget_remaining: Decimal = Field(gt=0, description="项目当前可用预算")
    deadline: date = Field(description="项目要求到货日期")
    offers: list[SupplierOffer] = Field(min_length=1, description="候选供应商报价")


@tool("evaluate_project_procurement", args_schema=ProjectProcurementRequest)
def evaluate_project_procurement(
    project_name: str,
    requirement: str,
    quantity: int,
    budget_remaining: Decimal,
    deadline: date,
    offers: list[dict],
) -> str:
    """按项目预算和到货期限评估有来源依据的供应商报价。

    仅当报价总额不超预算且交付日期有来源、并且不晚于项目期限时，
    才将方案标记为可执行。缺少交付日期的方案会标为待核实，不会被推荐。

    Args:
        project_name: 项目名称。
        requirement: 采购需求或规格。
        quantity: 本次采购数量。
        budget_remaining: 项目当前可用预算。
        deadline: 项目要求到货日期。
        offers: 有来源依据的候选报价列表。

    Returns:
        JSON 格式的约束校验结果和最低价可执行方案。
    """
    evaluated = []
    for raw_offer in offers:
        offer = SupplierOffer.model_validate(raw_offer)
        total = (offer.unit_price * quantity).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        budget_ok = total <= budget_remaining
        delivery_ok = (
            None if offer.delivery_date is None else offer.delivery_date <= deadline
        )

        if not budget_ok or delivery_ok is False:
            status = "ineligible"
        elif delivery_ok is None:
            status = "needs_confirmation"
        else:
            status = "eligible"

        evaluated.append({
            "supplier_name": offer.supplier_name,
            "supplier_id": offer.supplier_id,
            "part_id": offer.part_id,
            "part_name": offer.part_name,
            "unit_price": str(offer.unit_price),
            "quantity": quantity,
            "estimated_total": str(total),
            "budget_ok": budget_ok,
            "delivery_date": (
                offer.delivery_date.isoformat()
                if offer.delivery_date is not None
                else None
            ),
            "deadline": deadline.isoformat(),
            "delivery_ok": delivery_ok,
            "status": status,
            "source": offer.source,
        })

    evaluated.sort(key=lambda item: (
        {"eligible": 0, "needs_confirmation": 1, "ineligible": 2}[item["status"]],
        Decimal(item["estimated_total"]),
        item["delivery_date"] or "9999-12-31",
    ))
    recommended = next(
        (item for item in evaluated if item["status"] == "eligible"),
        None,
    )

    result = {
        "project_name": project_name,
        "requirement": requirement,
        "quantity": quantity,
        "budget_remaining": str(budget_remaining),
        "deadline": deadline.isoformat(),
        "recommendation": recommended,
        "offers": evaluated,
        "message": (
            "存在同时满足预算和交期约束的方案。"
            if recommended
            else "当前没有已核实且同时满足预算和交期的方案；请补充报价或交付信息。"
        ),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)
