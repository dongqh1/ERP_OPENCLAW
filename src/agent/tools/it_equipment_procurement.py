"""LangChain tool for sourced enterprise IT equipment offer evaluation."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from agent.tools.it_equipment_policy import evaluate_it_equipment_policy


class ITEquipmentOffer(BaseModel):
    """One ERP or supplier offer; unknown facts must remain unset."""

    supplier_name: str | None = Field(default=None, description="供应商名称")
    supplier_id: int | None = Field(default=None, description="ERP 供应商 ID")
    part_id: int | None = Field(default=None, description="已核实的 ERP 物料 ID")
    device_type: str | None = Field(default=None, description="设备类别，如笔记本、服务器")
    model_name: str | None = Field(default=None, description="设备型号")
    unit_price: Decimal | None = Field(default=None, description="有来源依据的设备单价")
    delivery_date: date | None = Field(default=None, description="已核实的供应商交付日期")
    warranty_months: int | None = Field(default=None, description="已核实的保修月数")
    cpu_cores: int | None = Field(default=None, description="已核实的 CPU 核数")
    memory_gb: Decimal | None = Field(default=None, description="已核实的内存容量 GB")
    storage_gb: Decimal | None = Field(default=None, description="已核实的存储容量 GB")
    operating_system: str | None = Field(default=None, description="已核实的操作系统")
    source: str | None = Field(default=None, description="可追溯的 ERP 记录、供应商资料或用户确认")


class ITEquipmentProcurementRequest(BaseModel):
    """Requirements and sourced offers for one device category and quantity."""

    device_type: str = Field(min_length=1, description="本次采购的设备类别")
    requirement: str = Field(min_length=1, description="用户采购需求")
    quantity: int = Field(gt=0, description="本次采购数量")
    budget_remaining: Decimal | None = Field(default=None, description="本次可用预算；未知时留空")
    deadline: date | None = Field(default=None, description="要求到货日期；未知时留空")
    minimum_warranty_months: int | None = Field(default=None, description="最低保修月数")
    min_cpu_cores: int | None = Field(default=None, description="最低 CPU 核数")
    min_memory_gb: Decimal | None = Field(default=None, description="最低内存容量 GB")
    min_storage_gb: Decimal | None = Field(default=None, description="最低存储容量 GB")
    allowed_operating_systems: list[str] = Field(default_factory=list, description="允许的操作系统")
    offers: list[ITEquipmentOffer] = Field(min_length=1, description="有来源依据的候选设备报价")


@tool("evaluate_it_equipment_procurement", args_schema=ITEquipmentProcurementRequest)
def evaluate_it_equipment_procurement(
    device_type: str,
    requirement: str,
    quantity: int,
    offers: list[dict],
    budget_remaining: Decimal | None = None,
    deadline: date | None = None,
    minimum_warranty_months: int | None = None,
    min_cpu_cores: int | None = None,
    min_memory_gb: Decimal | None = None,
    min_storage_gb: Decimal | None = None,
    allowed_operating_systems: list[str] | None = None,
) -> str:
    """逐项核验 IT 设备报价的规格、预算、交期和保修，只推荐已核实的合格方案。"""
    result = evaluate_it_equipment_policy({
        "device_type": device_type,
        "requirement": requirement,
        "quantity": quantity,
        "budget_remaining": budget_remaining,
        "deadline": deadline,
        "minimum_warranty_months": minimum_warranty_months,
        "min_cpu_cores": min_cpu_cores,
        "min_memory_gb": min_memory_gb,
        "min_storage_gb": min_storage_gb,
        "allowed_operating_systems": allowed_operating_systems,
        "offers": [ITEquipmentOffer.model_validate(offer).model_dump() for offer in offers],
    })
    return json.dumps(result, ensure_ascii=False, indent=2)
