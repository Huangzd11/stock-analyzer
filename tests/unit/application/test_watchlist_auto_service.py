"""自选股自动添加服务单元测试。"""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from stock_analyzer.application.analysis_service import AnalysisService
from stock_analyzer.application.crawl_service import CrawlService
from stock_analyzer.application.predict_service import PredictService
from stock_analyzer.application.watchlist_auto_service import WatchlistAutoService
from stock_analyzer.application.watchlist_store import WatchlistStore
from stock_analyzer.domain.forecast.registry import create_baseline_registry
from stock_analyzer.domain.models import Market, Quote, Stock
from stock_analyzer.infrastructure.concurrency import TokenBucket
from stock_analyzer.infrastructure.persistence import SqliteQuoteRepository
from stock_analyzer.ports.quote_source import IQuoteSource


def _make_quotes(symbol: str, days: int, step: float = 0.5) -> list[Quote]:
    base = date(2024, 1, 1)
    quotes: list[Quote] = []
    for i in range(days):
        price = Decimal(str(100 + i * step))
        d = base + timedelta(days=i)
        quotes.append(
            Quote(
                symbol=symbol,
                trade_date=d,
                open=price,
                high=price + Decimal("1"),
                low=price - Decimal("1"),
                close=price,
                volume=10000,
            )
        )
    return quotes


class MockQuoteSource:
    """按股票返回不同走势的 Mock 数据源。"""

    def __init__(self, quotes_by_symbol: dict[str, list[Quote]]) -> None:
        self._quotes_by_symbol = quotes_by_symbol

    async def fetch_daily(self, symbol: str, start: date, end: date) -> list[Quote]:
        return [
            q
            for q in self._quotes_by_symbol.get(symbol, [])
            if start <= q.trade_date <= end
        ]

    async def fetch_stock_info(self, symbol: str) -> Stock:
        return Stock(symbol=symbol, name="测试", market=Market.SH)


@pytest.fixture
async def auto_service(tmp_path: Path) -> WatchlistAutoService:
    repo = SqliteQuoteRepository(tmp_path / "auto.db")
    await repo.initialize()
    source = MockQuoteSource(
        {
            "600519": _make_quotes("600519", 60, step=1.0),
            "000001": _make_quotes("000001", 60, step=0.0),
            "600036": _make_quotes("600036", 60, step=0.8),
        }
    )
    crawl = CrawlService(source, repo, TokenBucket(rate=100.0, capacity=10))
    store = WatchlistStore(tmp_path / "watchlist.json")
    registry = create_baseline_registry()
    return WatchlistAutoService(
        watchlist=store,
        analysis=AnalysisService(repo),
        predict=PredictService(repo, registry),
        crawl=crawl,
        min_score=50.0,
        max_add=2,
    )


@pytest.mark.asyncio
async def test_auto_add_fetches_without_prior_data(auto_service: WatchlistAutoService) -> None:
    """无需提前入库，爬取后即可评分并添加。"""
    result = await auto_service.auto_add(
        ["000001", "600519"],
        end=date(2024, 3, 1),
    )
    assert set(result.fetched) == {"000001", "600519"}
    assert "600519" in result.added
    assert result.added[0] == "600519"


@pytest.mark.asyncio
async def test_auto_add_adds_top_n_by_score(auto_service: WatchlistAutoService) -> None:
    result = await auto_service.auto_add(
        ["000001", "600519", "600036"],
        end=date(2024, 3, 1),
        max_add=2,
    )
    assert len(result.added) == 2
    assert result.added == ["600519", "600036"]


@pytest.mark.asyncio
async def test_auto_add_skips_existing(auto_service: WatchlistAutoService) -> None:
    auto_service.watchlist.add_symbol("600519")
    result = await auto_service.auto_add(["600519", "000001"], end=date(2024, 3, 1))
    assert "600519" not in result.added
    assert "600519" in result.skipped_existing
