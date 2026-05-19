"""预测策略抽象：统一基线与深度学习实现的契约。"""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from stock_analyzer.domain.models import Quote


class TrendDirection(StrEnum):
    """走势方向标签。"""

    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


class ForecastPoint(BaseModel):
    """单日预测点。"""

    date: date
    value: Decimal
    lower: Decimal | None = None
    upper: Decimal | None = None


class ForecastResult(BaseModel):
    """预测结果。"""

    symbol: str
    strategy: str
    horizon_days: int
    points: list[ForecastPoint]
    trend: TrendDirection


@runtime_checkable
class ForecastStrategy(Protocol):
    """预测策略端口：阶段 A/B 均实现此接口。"""

    @property
    def name(self) -> str:
        """策略唯一标识，如 ma_trend、lstm。"""
        ...

    def predict(self, quotes: list[Quote], horizon_days: int) -> ForecastResult:
        """基于历史行情生成未来 horizon_days 的预测。"""
        ...
