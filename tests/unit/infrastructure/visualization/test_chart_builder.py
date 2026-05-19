"""图表构建器测试。"""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from stock_analyzer.domain.forecast import MovingAverageForecast
from stock_analyzer.domain.models import Quote
from stock_analyzer.infrastructure.visualization import ChartBuilder


def _make_quotes(n: int) -> list[Quote]:
    quotes: list[Quote] = []
    for i in range(n):
        price = Decimal(str(100 + i))
        quotes.append(
            Quote(
                symbol="600519",
                trade_date=date(2024, 1, 1) + timedelta(days=i),
                open=price,
                high=price + Decimal("2"),
                low=price - Decimal("1"),
                close=price + Decimal("0.5"),
                volume=5000 + i * 10,
            )
        )
    return quotes


def test_chart_builder_writes_html(tmp_path: Path) -> None:
    builder = ChartBuilder()
    output = tmp_path / "600519.html"
    path = builder.build_candlestick(_make_quotes(30), output)
    assert path.exists()
    assert path.stat().st_size > 0
    content = path.read_text(encoding="utf-8")
    assert "plotly" in content.lower()


def test_chart_builder_with_forecast(tmp_path: Path) -> None:
    quotes = _make_quotes(30)
    forecast = MovingAverageForecast().predict(quotes, horizon_days=5)
    output = tmp_path / "600519_forecast.html"
    path = ChartBuilder().build_candlestick(quotes, output, forecast=forecast)
    assert path.exists()


def test_chart_builder_rejects_empty_quotes(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="为空"):
        ChartBuilder().build_candlestick([], tmp_path / "empty.html")
