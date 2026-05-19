"""预测契约模型测试。"""

from datetime import date
from decimal import Decimal

from stock_analyzer.domain.forecast import ForecastPoint, ForecastResult, TrendDirection


def test_forecast_result_structure() -> None:
    result = ForecastResult(
        symbol="600519",
        strategy="ma_trend",
        horizon_days=5,
        points=[
            ForecastPoint(
                date=date(2026, 5, 19),
                value=Decimal("1700"),
                lower=Decimal("1650"),
                upper=Decimal("1750"),
            )
        ],
        trend=TrendDirection.UP,
    )
    assert result.strategy == "ma_trend"
    assert result.trend == TrendDirection.UP
    assert len(result.points) == 1
