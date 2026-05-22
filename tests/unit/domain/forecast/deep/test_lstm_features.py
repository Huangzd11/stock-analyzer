"""LSTM 特征工程单元测试（无需 torch）。"""

from datetime import date, timedelta
from decimal import Decimal

import numpy as np

from stock_analyzer.domain.forecast.deep.lstm_features import (
    FEATURE_DIM,
    build_feature_matrix,
    min_history_for_lookback,
)
from stock_analyzer.domain.models import Quote


def _make_quotes(n: int) -> list[Quote]:
    quotes: list[Quote] = []
    for i in range(n):
        price = Decimal(str(100 + i * 0.2))
        quotes.append(
            Quote(
                symbol="600519",
                trade_date=date(2024, 1, 1) + timedelta(days=i),
                open=price,
                high=price + Decimal("1"),
                low=price - Decimal("1"),
                close=price,
                volume=10000 + i * 100,
            )
        )
    return quotes


def test_feature_matrix_shape() -> None:
    features, closes = build_feature_matrix(_make_quotes(80))
    assert features.shape == (80, FEATURE_DIM)
    assert closes.shape == (80,)
    assert np.all(np.isfinite(features))


def test_min_history_for_lookback() -> None:
    assert min_history_for_lookback(30) >= 90
