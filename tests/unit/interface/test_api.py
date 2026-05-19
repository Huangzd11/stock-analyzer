"""REST API 接口测试。"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stock_analyzer.application.analysis_service import AnalysisService
from stock_analyzer.domain.models import Quote
from stock_analyzer.infrastructure.persistence import SqliteQuoteRepository
from stock_analyzer.interface.api.app import app, get_analysis_service


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
    repo = SqliteQuoteRepository(tmp_path / "api.db")

    async def _setup() -> AnalysisService:
        await repo.initialize()
        await repo.upsert_quotes(_make_quotes("600519", 60))
        return AnalysisService(repo)

    analysis = asyncio.run(_setup())

    async def _override() -> AnalysisService:
        return analysis

    app.dependency_overrides[get_analysis_service] = _override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_api_analysis_200(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/analysis/600519",
        params={"start": "2024-01-01", "end": "2024-03-01"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "600519"
    assert "ma_20" in body["indicators"]


def test_api_openapi_accessible() -> None:
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/analysis/{symbol}" in response.text


def test_api_health() -> None:
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}
