"""走势预测策略（阶段 A 基线 → 阶段 B 深度学习）。"""

from stock_analyzer.domain.forecast.base import (
    ForecastPoint,
    ForecastResult,
    ForecastStrategy,
    TrendDirection,
)
from stock_analyzer.domain.forecast.linear_trend import LinearTrendForecast
from stock_analyzer.domain.forecast.moving_average import MovingAverageForecast
from stock_analyzer.domain.forecast.registry import ForecastRegistry, create_baseline_registry

__all__ = [
    "ForecastPoint",
    "ForecastRegistry",
    "ForecastResult",
    "ForecastStrategy",
    "LinearTrendForecast",
    "MovingAverageForecast",
    "TrendDirection",
    "create_baseline_registry",
]
