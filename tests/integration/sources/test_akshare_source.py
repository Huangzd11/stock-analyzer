"""AkShare 数据源集成测试（需网络）。"""

from datetime import date, timedelta

import pytest
import requests

from stock_analyzer.infrastructure.sources import AkShareSource

pytest.importorskip("akshare")


def _skip_if_network_error(exc: BaseException) -> None:
    pytest.skip(f"网络或代理不可用，跳过集成测试: {exc}")


@pytest.mark.slow
@pytest.mark.asyncio
async def test_akshare_source_fetch_daily() -> None:
    source = AkShareSource()
    end = date.today()
    start = end - timedelta(days=30)
    try:
        quotes = await source.fetch_daily("600519", start, end)
    except (requests.RequestException, OSError) as exc:
        _skip_if_network_error(exc)
    assert quotes
    assert all(q.symbol == "600519" for q in quotes)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_akshare_source_fetch_stock_info() -> None:
    source = AkShareSource()
    try:
        stock = await source.fetch_stock_info("600519")
    except (requests.RequestException, OSError) as exc:
        _skip_if_network_error(exc)
    assert stock.symbol == "600519"
    assert stock.name
