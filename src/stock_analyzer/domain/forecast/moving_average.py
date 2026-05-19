"""均线趋势外推预测（阶段 A 基线）。"""

from stock_analyzer.domain.forecast.base import ForecastResult
from stock_analyzer.domain.forecast.trend_utils import (
    build_forecast_points,
    future_dates,
    infer_trend,
    residual_std,
    sorted_closes,
)
from stock_analyzer.domain.indicators import calc_ma
from stock_analyzer.domain.models import Quote

_DEFAULT_MA_PERIOD = 20


class MovingAverageForecast:
    """基于 MA 斜率的外推预测。"""

    def __init__(self, ma_period: int = _DEFAULT_MA_PERIOD) -> None:
        if ma_period < 2:
            msg = f"ma_period 必须 >= 2，当前为 {ma_period}"
            raise ValueError(msg)
        self._ma_period = ma_period

    @property
    def name(self) -> str:
        return "ma_trend"

    def predict(self, quotes: list[Quote], horizon_days: int) -> ForecastResult:
        if horizon_days < 1:
            msg = f"horizon_days 必须 >= 1，当前为 {horizon_days}"
            raise ValueError(msg)
        if len(quotes) < self._ma_period:
            msg = f"至少需要 {self._ma_period} 条历史行情"
            raise ValueError(msg)

        dates, closes = sorted_closes(quotes)
        symbol = quotes[0].symbol
        ma_values = calc_ma(closes, self._ma_period)
        valid_ma = [v for v in ma_values if v is not None]
        if len(valid_ma) < 2:
            msg = "有效均线数据不足"
            raise ValueError(msg)

        slope = valid_ma[-1] - valid_ma[-2]
        last_ma = valid_ma[-1]
        forecast_values = [last_ma + slope * (i + 1) for i in range(horizon_days)]
        forecast_dates = future_dates(dates[-1], horizon_days)

        fitted = [v if v is not None else closes[i] for i, v in enumerate(ma_values)]
        std = residual_std(closes, fitted)
        points = build_forecast_points(forecast_dates, forecast_values, std)

        return ForecastResult(
            symbol=symbol,
            strategy=self.name,
            horizon_days=horizon_days,
            points=points,
            trend=infer_trend(forecast_values),
        )
