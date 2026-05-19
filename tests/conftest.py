"""pytest 共享 fixture。"""

import pytest


@pytest.fixture
def sample_quote_kwargs() -> dict:
    """合法日 K 字段。"""
    return {
        "symbol": "600519",
        "trade_date": "2026-05-16",
        "open": "1680.00",
        "high": "1700.00",
        "low": "1670.00",
        "close": "1690.00",
        "volume": 1000000,
    }
