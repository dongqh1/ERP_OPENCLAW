import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest

_module_path = Path(__file__).resolve().parents[1] / 'src' / 'agent' / 'tools' / 'it_equipment_policy.py'
_spec = importlib.util.spec_from_file_location('it_equipment_policy', _module_path)
_policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_policy)
evaluate_it_equipment_policy = _policy.evaluate_it_equipment_policy


@pytest.fixture
def request_data():
    return {
        "device_type": "laptop",
        "requirement": "开发用笔记本",
        "quantity": 2,
        "budget_remaining": "5000.00",
        "deadline": "2026-11-30",
        "minimum_warranty_months": 24,
        "min_cpu_cores": 8,
        "min_memory_gb": 16,
        "min_storage_gb": 512,
        "allowed_operating_systems": ["Windows 11 Pro", "Ubuntu 24.04"],
        "offers": [
            {
                "supplier_name": "甲供应商",
                "supplier_id": 1,
                "part_id": 101,
                "device_type": "laptop",
                "model_name": "Model A",
                "unit_price": "1200.10",
                "delivery_date": "2026-11-20",
                "warranty_months": 36,
                "cpu_cores": 8,
                "memory_gb": 16,
                "storage_gb": 512,
                "operating_system": "Windows 11 Pro",
                "source": "正式报价单 Q-1",
            },
            {
                "supplier_name": "乙供应商",
                "supplier_id": 2,
                "part_id": 202,
                "device_type": "laptop",
                "model_name": "Model B",
                "unit_price": "1199.99",
                "delivery_date": "2026-11-25",
                "warranty_months": 24,
                "cpu_cores": 8,
                "memory_gb": 16,
                "storage_gb": 512,
                "operating_system": "Ubuntu 24.04",
                "source": "正式报价单 Q-2",
            },
        ],
    }


def test_recommends_lowest_total_eligible_offer(request_data):
    result = evaluate_it_equipment_policy(request_data)

    assert result["recommendation"]["supplier_name"] == "乙供应商"
    assert result["recommendation"]["status"] == "eligible"
    assert result["offers"][1]["status"] == "eligible"
    assert result["summary"]


def test_missing_delivery_or_critical_spec_is_unverified_and_never_recommended(request_data):
    request_data["offers"] = request_data["offers"][:1]
    offer = request_data["offers"][0]
    offer["delivery_date"] = None
    offer["cpu_cores"] = None

    result = evaluate_it_equipment_policy(request_data)

    assert result["recommendation"] is None
    assert result["offers"][0]["status"] == "needs_confirmation"
    assert "delivery_date" in result["offers"][0]["unverified_constraints"]
    assert "min_cpu_cores" in result["offers"][0]["unverified_constraints"]


@pytest.mark.parametrize(
    ("field", "value", "constraint"),
    [
        ("unit_price", "2500.01", "budget_remaining"),
        ("device_type", "desktop", "device_type"),
        ("cpu_cores", 4, "min_cpu_cores"),
        ("memory_gb", 8, "min_memory_gb"),
        ("storage_gb", 256, "min_storage_gb"),
        ("operating_system", "Windows 10", "allowed_operating_systems"),
        ("warranty_months", 12, "minimum_warranty_months"),
        ("delivery_date", "2026-12-01", "deadline"),
    ],
)
def test_constraint_violation_makes_offer_ineligible(request_data, field, value, constraint):
    request_data["offers"] = request_data["offers"][:1]
    offer = request_data["offers"][0]
    offer[field] = value

    result = evaluate_it_equipment_policy(request_data)

    assert result["offers"][0]["status"] == "ineligible"
    assert constraint in result["offers"][0]["failed_constraints"]


def test_estimated_total_uses_exact_decimal_arithmetic(request_data):
    request_data["quantity"] = 3
    request_data["offers"] = [request_data["offers"][0]]

    result = evaluate_it_equipment_policy(request_data)

    assert result["offers"][0]["estimated_total"] == "3600.30"
    assert Decimal(result["offers"][0]["estimated_total"]) == Decimal("3600.30")
