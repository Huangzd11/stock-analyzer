"""均线趋势预测测试。"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from stock_analyzer.domain.forecast import MovingAverageForecast, TrendDirection
from stock_analyzer.domain.models import Quote


def _make_quotes(n: int) -> list[Quote]:
    quotes: list[Quote] = []
    for i in range(n):
        price = Decimal(str(100 + i))
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


def test_ma_trend_forecast_horizon() -> None:
    strategy = MovingAverageForecast(ma_period=20)
    result = strategy.predict(_make_quotes(30), horizon_days=5)
    assert result.strategy == "ma_trend"
    assert len(result.points) == 5
    assert result.trend in TrendDirection


def test_ma_trend_requires_enough_history() -> None:
    strategy = MovingAverageForecast(ma_period=20)
    with pytest.raises(ValueError, match="至少"):
        strategy.predict(_make_quotes(10), horizon_days=5)
