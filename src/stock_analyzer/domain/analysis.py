"""技术分析结果模型。"""

from datetime import date

from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    """技术分析输出。"""

    symbol: str
    as_of: date = Field(..., description="分析截止交易日")
    indicators: dict[str, float | dict[str, float | None]] = Field(default_factory=dict)
    summary: dict[str, float | None] = Field(default_factory=dict)
