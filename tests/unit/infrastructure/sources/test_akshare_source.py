"""AkShare 数据源单元测试（Mock 网络）。"""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from stock_analyzer.infrastructure.sources.akshare_source import (
    AkShareSource,
    QuoteSourceError,
    symbol_to_prefixed,
)


def test_symbol_to_prefixed_sh() -> None:
    assert symbol_to_prefixed("600519") == "sh600519"


def test_symbol_to_prefixed_sz() -> None:
    assert symbol_to_prefixed("000001") == "sz000001"


def test_fetch_daily_uses_em_first() -> None:
    source = AkShareSource(request_timeout=10.0)
    df = pd.DataFrame(
        {
            "日期": ["2024-01-02"],
            "开盘": [10.0],
            "最高": [11.0],
            "最低": [9.5],
            "收盘": [10.5],
            "成交量": [1000],
            "成交额": [10500.0],
        }
    )
    with patch(
        "akshare.stock_zh_a_hist",
        return_value=df,
        create=True,
    ) as mock_em:
        with patch.object(source, "_fetch_tx_sync", side_effect=AssertionError):
            with patch.object(source, "_fetch_sina_sync", side_effect=AssertionError):
                quotes = source._fetch_daily_sync("600519", date(2024, 1, 1), date(2024, 1, 31))
    mock_em.assert_called_once()
    assert len(quotes) == 1
    assert quotes[0].symbol == "600519"


def test_fetch_daily_falls_back_to_tx_when_em_fails() -> None:
    source = AkShareSource(request_timeout=10.0)
    tx_df = pd.DataFrame(
        {
            "date": [date(2024, 1, 2)],
            "open": [10.0],
            "close": [10.5],
            "high": [11.0],
            "low": [9.5],
            "amount": [10000.0],
        }
    )
    with patch(
        "akshare.stock_zh_a_hist",
        side_effect=requests.Timeout("em timeout"),
        create=True,
    ):
        with patch.object(source, "_fetch_tx_sync", return_value=tx_df) as mock_tx:
            with patch.object(source, "_fetch_sina_sync", side_effect=AssertionError):
                quotes = source._fetch_daily_sync("600519", date(2024, 1, 1), date(2024, 1, 31))
    mock_tx.assert_called_once()
    assert len(quotes) == 1
    assert quotes[0].volume == 0


def test_fetch_daily_raises_when_all_sources_fail() -> None:
    source = AkShareSource(request_timeout=5.0)
    with patch(
        "akshare.stock_zh_a_hist",
        side_effect=requests.ConnectionError("em"),
        create=True,
    ):
        with patch.object(
            source,
            "_fetch_tx_sync",
            side_effect=requests.Timeout("tx"),
        ):
            with patch.object(
                source,
                "_fetch_sina_sync",
                side_effect=requests.Timeout("sina"),
            ):
                with pytest.raises(QuoteSourceError, match="所有数据源均不可用"):
                    source._fetch_daily_sync("600519", date(2024, 1, 1), date(2024, 1, 31))


def test_proxy_env_sets_and_restores() -> None:
    import os

    source = AkShareSource(
        request_timeout=10.0,
        http_proxy="http://127.0.0.1:7890",
        https_proxy="http://127.0.0.1:7890",
    )
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(key, None)
    with source._proxy_env():
        assert os.environ.get("HTTP_PROXY") == "http://127.0.0.1:7890"
        assert os.environ.get("HTTPS_PROXY") == "http://127.0.0.1:7890"
    assert os.environ.get("HTTP_PROXY") is None
    assert os.environ.get("HTTPS_PROXY") is None
