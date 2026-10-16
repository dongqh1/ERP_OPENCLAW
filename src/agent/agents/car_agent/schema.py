"""汽车采购领域输入结构。"""

from pydantic import BaseModel, Field


class CarPartQuery(BaseModel):
    keyword: str = Field(description="零部件名称、编号或类别")
    vehicle_model: str | None = Field(default=None, description="可选车型关键词")


class VehicleMatchQuery(BaseModel):
    vehicle_model: str = Field(description="车型及年款")
    part_keyword: str = Field(description="待核验零件关键词")


class CarPriceEstimate(BaseModel):
    part_keywords: list[str] = Field(description="需要估价的零件关键词列表")
