"""REST API 接口测试。"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from stock_analyzer.application.analysis_service import AnalysisService
from stock_analyzer.application.crawl_service import CrawlService
from stock_analyzer.application.predict_service import PredictService
from stock_analyzer.application.watchlist_auto_service import WatchlistAutoService
from stock_analyzer.application.watchlist_store import WatchlistStore
from stock_analyzer.config.settings import Settings
from stock_analyzer.domain.forecast.registry import create_baseline_registry
from stock_analyzer.domain.models import Market, Quote, Stock
from stock_analyzer.infrastructure.concurrency import TokenBucket
from stock_analyzer.infrastructure.persistence import SqliteQuoteRepository
from stock_analyzer.interface.api.app import create_app
from stock_analyzer.interface.deps import get_analysis_service
from stock_analyzer.ports.quote_source import IQuoteSource


class _MockQuoteSource:
    def __init__(self, quotes: list[Quote]) -> None:
        self._quotes = quotes

    async def fetch_daily(self, symbol: str, start: date, end: date) -> list[Quote]:
        return [q for q in self._quotes if start <= q.trade_date <= end]

    async def fetch_stock_info(self, symbol: str) -> Stock:
        return Stock(symbol=symbol, name="测试", market=Market.SH)


def _make_quotes(symbol: str, days: int) -> list[Quote]:
    end = date.today()
    base = end - timedelta(days=days - 1)
    quotes: list[Quote] = []
    for i in range(days):
        price = Decimal(str(100 + i * 0.5))
        quotes.append(
            Quote(
                symbol=symbol,
                trade_date=base + timedelta(days=i),
                open=price,
                high=price + Decimal("1"),
                low=price - Decimal("1"),
                close=price,
                volume=10000,
            )
        )
    return quotes


@pytest.fixture
def api_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "api.db"
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{db_path.as_posix()}",
        watchlist_path=str(tmp_path / "watchlist.json"),
        enable_ml_strategies=False,
    )
    repo = SqliteQuoteRepository(db_path)

    async def _setup() -> AnalysisService:
        await repo.initialize()
        await repo.upsert_quotes(_make_quotes("600519", 60))
        return AnalysisService(repo)

    analysis = asyncio.run(_setup())
    application = create_app(settings)

    async def _override() -> AnalysisService:
        return analysis

    application.dependency_overrides[get_analysis_service] = _override
    application.state.test_repo = repo
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()


def test_api_analysis_200(api_client: TestClient) -> None:
    end = date.today()
    start = end - timedelta(days=60)
    response = api_client.get(
        "/api/v1/analysis/600519",
        params={"start": start.isoformat(), "end": end.isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "600519"
    assert "ma_20" in body["indicators"]


def test_api_openapi_accessible(api_client: TestClient) -> None:
    response = api_client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/analysis/{symbol}" in response.text


def test_api_health(api_client: TestClient) -> None:
    assert api_client.get("/health").json() == {"status": "ok"}


def test_api_index_page(api_client: TestClient) -> None:
    response = api_client.get("/")
    assert response.status_code == 200
    assert "Stock Analyzer" in response.text


def test_api_watchlist_crud(api_client: TestClient) -> None:
    assert api_client.get("/api/v1/watchlist").json() == {"symbols": []}
    add = api_client.post("/api/v1/watchlist", json={"symbol": "600519"})
    assert add.status_code == 200
    assert add.json()["symbols"] == ["600519"]
    bad = api_client.post("/api/v1/watchlist", json={"symbol": "12"})
    assert bad.status_code == 422


@patch("stock_analyzer.interface.api.routes.create_watchlist_auto_service")
def test_api_watchlist_auto_add(
    mock_create_service: object,
    api_client: TestClient,
) -> None:
    repo: SqliteQuoteRepository = api_client.app.state.test_repo
    quotes = _make_quotes("600519", 60)

    async def _factory(store: WatchlistStore, settings: Settings) -> WatchlistAutoService:
        crawl = CrawlService(_MockQuoteSource(quotes), repo, TokenBucket(rate=100.0, capacity=10))
        return WatchlistAutoService(
            watchlist=store,
            analysis=AnalysisService(repo),
            predict=PredictService(repo, create_baseline_registry()),
            crawl=crawl,
            max_add=5,
        )

    mock_create_service.side_effect = _factory
    body = api_client.post(
        "/api/v1/watchlist/auto-add",
        json={"symbols": ["600519"], "max_add": 5},
    ).json()
    assert "600519" in body["added"]
    assert body["symbols"] == ["600519"]
    assert body["ranked"][0]["symbol"] == "600519"
    assert body["ranked"][0]["score"] > 0
    assert "600519" in body["fetched"]


def test_api_realtime_status(api_client: TestClient) -> None:
    body = api_client.get("/api/v1/realtime/status").json()
    assert body["running"] is False
    assert body["symbols"] == []


def test_api_strategies(api_client: TestClient) -> None:
    body = api_client.get("/api/v1/strategies").json()
    assert "ma_trend" in body["baseline"]
    assert "ma_trend" in body["all"]
