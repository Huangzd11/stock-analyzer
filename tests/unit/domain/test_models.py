"""领域实体校验测试。"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from stock_analyzer.domain import Market, Quote, Stock


def test_stock_market_enum() -> None:
    stock = Stock(symbol="600519", name="贵州茅台", market=Market.SH)
    assert stock.market == Market.SH
    assert stock.market.value == "SH"


def test_stock_rejects_invalid_symbol() -> None:
    with pytest.raises(ValidationError):
        Stock(symbol="60051", name="无效", market=Market.SH)


def test_quote_accepts_valid_data(sample_quote_kwargs: dict) -> None:
    quote = Quote(**sample_quote_kwargs)
    assert quote.symbol == "600519"
    assert quote.close == Decimal("1690.00")


def test_quote_validation_rejects_negative_price(sample_quote_kwargs: dict) -> None:
    sample_quote_kwargs["open"] = "-1"
    with pytest.raises(ValidationError):
        Quote(**sample_quote_kwargs)


def test_quote_validation_rejects_high_below_close(sample_quote_kwargs: dict) -> None:
    sample_quote_kwargs["high"] = "1680.00"
    sample_quote_kwargs["close"] = "1690.00"
    with pytest.raises(ValidationError) as exc_info:
        Quote(**sample_quote_kwargs)
    assert "最高价" in str(exc_info.value)


def test_quote_validation_rejects_low_above_open(sample_quote_kwargs: dict) -> None:
    sample_quote_kwargs["low"] = "1685.00"
    sample_quote_kwargs["open"] = "1680.00"
    with pytest.raises(ValidationError):
        Quote(**sample_quote_kwargs)


def test_quote_rejects_invalid_symbol(sample_quote_kwargs: dict) -> None:
    sample_quote_kwargs["symbol"] = "ABC"
    with pytest.raises(ValidationError):
        Quote(**sample_quote_kwargs)
