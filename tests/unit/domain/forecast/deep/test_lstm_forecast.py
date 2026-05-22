"""LSTM 预测测试（需 .[ml]）。"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from stock_analyzer.domain.forecast.deep.lstm_forecast import LstmForecast
from stock_analyzer.domain.models import Quote

torch = pytest.importorskip("torch")


def _make_quotes(n: int) -> list[Quote]:
    quotes: list[Quote] = []
    for i in range(n):
        price = Decimal(str(100 + i * 0.3))
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


@pytest.mark.ml
def test_lstm_forecast_horizon() -> None:
    strategy = LstmForecast(lookback=15, max_epochs=5, patience=3, hidden_size=32)
    result = strategy.predict(_make_quotes(95), horizon_days=5)
    assert result.strategy == "lstm"
    assert len(result.points) == 5
    assert result.metadata is not None
    assert result.metadata.model_version == "lstm-v2"
    assert result.metadata.mae is not None
    assert result.metadata.rmse is not None
    assert result.metadata.explainability == "low"


@pytest.mark.ml
def test_lstm_requires_enough_history() -> None:
    strategy = LstmForecast(lookback=30)
    with pytest.raises(ValueError, match="至少"):
        strategy.predict(_make_quotes(50), horizon_days=5)
