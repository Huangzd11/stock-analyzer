"""REST API 接口测试。"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stock_analyzer.application.analysis_service import AnalysisService
from stock_analyzer.config.settings import Settings
from stock_analyzer.domain.models import Quote
from stock_analyzer.infrastructure.persistence import SqliteQuoteRepository
from stock_analyzer.interface.api.app import create_app
from stock_analyzer.interface.deps import get_analysis_service


def _make_quotes(symbol: str, days: int) -> list[Quote]:
    base = date(2024, 1, 1)
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
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()


def test_api_analysis_200(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/analysis/600519",
        params={"start": "2024-01-01", "end": "2024-03-01"},
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


def test_api_realtime_status(api_client: TestClient) -> None:
    body = api_client.get("/api/v1/realtime/status").json()
    assert body["running"] is False
    assert body["symbols"] == []


def test_api_strategies(api_client: TestClient) -> None:
    body = api_client.get("/api/v1/strategies").json()
    assert "ma_trend" in body["baseline"]
    assert "ma_trend" in body["all"]
