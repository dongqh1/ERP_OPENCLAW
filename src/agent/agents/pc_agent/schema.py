"""PC 配置需求结构。"""

from typing import Literal

from pydantic import BaseModel, Field


class KeptComponent(BaseModel):
    type: str = Field(description="CPU、GPU、MOTHERBOARD、MEMORY、STORAGE、COOLER、POWER 或 CASE")
    keyword: str = Field(description="硬件型号或搜索关键词")
    owned: bool = Field(default=True, description="用户是否已经拥有该硬件")


class PCBuildRequest(BaseModel):
    budget: float = Field(gt=0, description="整机新购预算，人民币")
    use_case: str = Field(default="日常办公", description="办公、开发、游戏或具体游戏名称")
    resolution: str = Field(default="未指定", description="例如 1080p 或 1440p")
    target_fps: int = Field(default=60, ge=30, le=360)
    min_gpu_vram_gb: int | None = Field(
        default=None, ge=1, le=96, description="用户明确提出的显卡显存下限（GB）"
    )
    condition_preference: Literal["new", "used", "any", "best_value"] = "any"
    keep_components: list[KeptComponent] = Field(default_factory=list)
