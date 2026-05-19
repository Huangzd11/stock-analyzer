"""分析服务单元测试。"""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from stock_analyzer.application import AnalysisService
from stock_analyzer.domain.models import Quote
from stock_analyzer.infrastructure.persistence import SqliteQuoteRepository


def _make_quotes(symbol: str, days: int, start: date | None = None) -> list[Quote]:
    base = start or date(2024, 1, 1)
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
                volume=10000 + i,
            )
        )
    return quotes


@pytest.fixture
async def repo_with_data(tmp_path: Path) -> SqliteQuoteRepository:
    repo = SqliteQuoteRepository(tmp_path / "analysis.db")
    await repo.initialize()
    await repo.upsert_quotes(_make_quotes("600519", 60))
    return repo


@pytest.mark.asyncio
async def test_analysis_service_returns_indicators(repo_with_data: SqliteQuoteRepository) -> None:
    service = AnalysisService(repo_with_data)
    result = await service.analyze(
        "600519",
        date(2024, 1, 1),
        date(2024, 3, 1),
    )
    assert result.symbol == "600519"
    assert "ma_20" in result.indicators
    assert "macd" in result.indicators
    assert "rsi_14" in result.indicators
    macd = result.indicators["macd"]
    assert isinstance(macd, dict)
    assert "dif" in macd
