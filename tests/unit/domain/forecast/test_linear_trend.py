"""线性趋势预测测试。"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from stock_analyzer.domain.forecast import LinearTrendForecast, TrendDirection
from stock_analyzer.domain.models import Quote


def _make_quotes(n: int) -> list[Quote]:
    quotes: list[Quote] = []
    for i in range(n):
        price = Decimal(str(100 + i * 0.8))
        quotes.append(
            Quote(
                symbol="600519",
                trade_date=date(2024, 1, 1) + timedelta(days=i),
                open=price,
                high=price + Decimal("1"),
                low=price - Decimal("1"),
                close=price,
                volume=1000,
            )
        )
    return quotes


def test_linear_trend_forecast_horizon() -> None:
    strategy = LinearTrendForecast(lookback=30)
    result = strategy.predict(_make_quotes(35), horizon_days=7)
    assert result.strategy == "linear_trend"
    assert len(result.points) == 7
    assert result.trend in TrendDirection


def test_linear_trend_requires_enough_history() -> None:
    strategy = LinearTrendForecast(lookback=30)
    with pytest.raises(ValueError, match="至少"):
        strategy.predict(_make_quotes(20), horizon_days=5)
