"""爬取服务单元测试（Mock 数据源）。"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from stock_analyzer.application import CrawlRequest, CrawlService
from stock_analyzer.domain.models import Market, Quote, Stock
from stock_analyzer.infrastructure.concurrency import TokenBucket
from stock_analyzer.infrastructure.persistence import SqliteQuoteRepository
from stock_analyzer.ports.quote_source import IQuoteSource


class MockQuoteSource:
    """可配置的行情源 Mock。"""

    def __init__(self, quotes_by_symbol: dict[str, list[Quote]]) -> None:
        self._quotes_by_symbol = quotes_by_symbol
        self.fetch_calls: list[tuple[str, date, date]] = []

    async def fetch_daily(self, symbol: str, start: date, end: date) -> list[Quote]:
        self.fetch_calls.append((symbol, start, end))
        return [q for q in self._quotes_by_symbol.get(symbol, []) if start <= q.trade_date <= end]

    async def fetch_stock_info(self, symbol: str) -> Stock:
        return Stock(symbol=symbol, name="测试股", market=Market.SH)


def _quote(symbol: str, trade_date: str, close: str) -> Quote:
    return Quote(
        symbol=symbol,
        trade_date=date.fromisoformat(trade_date),
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=1000,
    )


@pytest.fixture
async def repo(tmp_path: Path) -> SqliteQuoteRepository:
    repository = SqliteQuoteRepository(tmp_path / "crawl.db")
    await repository.initialize()
    return repository


@pytest.mark.asyncio
async def test_crawl_service_persists_quotes(repo: SqliteQuoteRepository) -> None:
    quotes = [
        _quote("600519", "2024-06-01", "1700.00"),
        _quote("600519", "2024-06-02", "1710.00"),
    ]
    source = MockQuoteSource({"600519": quotes})
    service = CrawlService(
        source=source,
        repository=repo,
        rate_limiter=TokenBucket(rate=100.0, capacity=10),
    )
    result = await service.crawl_daily("600519", date(2024, 6, 1), date(2024, 6, 2))
    assert result.fetched_count == 2
    assert result.persisted_count == 2
    stored = await repo.get_quotes("600519", date(2024, 6, 1), date(2024, 6, 30))
    assert len(stored) == 2


@pytest.mark.asyncio
async def test_crawl_service_implements_quote_source_port() -> None:
    assert isinstance(MockQuoteSource({}), IQuoteSource)


@pytest.mark.asyncio
async def test_crawl_batch_uses_all_requests(repo: SqliteQuoteRepository) -> None:
    source = MockQuoteSource(
        {
            "600519": [_quote("600519", "2024-06-01", "1700.00")],
            "000001": [_quote("000001", "2024-06-01", "10.00")],
        }
    )
    service = CrawlService(
        source=source,
        repository=repo,
        rate_limiter=TokenBucket(rate=100.0, capacity=10),
    )
    results = await service.crawl_batch(
        [
            CrawlRequest("600519", date(2024, 6, 1), date(2024, 6, 1), tenant_id="a"),
            CrawlRequest("000001", date(2024, 6, 1), date(2024, 6, 1), tenant_id="b"),
        ]
    )
    assert len(results) == 2
