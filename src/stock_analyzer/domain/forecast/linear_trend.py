"""收盘价线性回归预测（阶段 A 基线）。"""

import numpy as np

from stock_analyzer.domain.forecast.base import ForecastResult
from stock_analyzer.domain.forecast.trend_utils import (
    build_forecast_points,
    future_dates,
    infer_trend,
    residual_std,
    sorted_closes,
)
from stock_analyzer.domain.models import Quote

_DEFAULT_LOOKBACK = 30


class LinearTrendForecast:
    """对近期收盘价做线性回归并外推。"""

    def __init__(self, lookback: int = _DEFAULT_LOOKBACK) -> None:
        if lookback < 2:
            msg = f"lookback 必须 >= 2，当前为 {lookback}"
            raise ValueError(msg)
        self._lookback = lookback

    @property
    def name(self) -> str:
        return "linear_trend"

    def predict(self, quotes: list[Quote], horizon_days: int) -> ForecastResult:
        if horizon_days < 1:
            msg = f"horizon_days 必须 >= 1，当前为 {horizon_days}"
            raise ValueError(msg)
        if len(quotes) < self._lookback:
            msg = f"至少需要 {self._lookback} 条历史行情"
            raise ValueError(msg)

        dates, closes = sorted_closes(quotes)
        symbol = quotes[0].symbol
        window = closes[-self._lookback :]
        x = np.arange(len(window), dtype=np.float64)
        slope, intercept = np.polyfit(x, window, 1)

        forecast_values: list[float] = []
        base_x = len(window)
        for i in range(horizon_days):
            forecast_values.append(float(slope * (base_x + i) + intercept))

        fitted = [float(slope * i + intercept) for i in range(len(window))]
        std = residual_std(window, fitted)
        forecast_dates = future_dates(dates[-1], horizon_days)
        points = build_forecast_points(forecast_dates, forecast_values, std)

        return ForecastResult(
            symbol=symbol,
            strategy=self.name,
            horizon_days=horizon_days,
            points=points,
            trend=infer_trend(forecast_values),
        )
