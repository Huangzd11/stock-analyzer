"""SQLite 行情仓储集成测试。"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from stock_analyzer.domain.models import Quote
from stock_analyzer.infrastructure.persistence import SqliteQuoteRepository
from stock_analyzer.ports.repository import IQuoteRepository


@pytest.fixture
async def repo(tmp_path: Path) -> SqliteQuoteRepository:
    """每个测试使用独立临时数据库文件。"""
    repository = SqliteQuoteRepository(tmp_path / "test.db")
    await repository.initialize()
    return repository


def _make_quote(
    symbol: str,
    trade_date: str,
    close: str,
) -> Quote:
    return Quote(
        symbol=symbol,
        trade_date=date.fromisoformat(trade_date),
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=1000,
    )


@pytest.mark.asyncio
async def test_sqlite_repository_implements_port(repo: SqliteQuoteRepository) -> None:
    assert isinstance(repo, IQuoteRepository)


@pytest.mark.asyncio
async def test_sqlite_upsert_idempotent(repo: SqliteQuoteRepository) -> None:
    quote = _make_quote("600519", "2024-06-01", "1700.00")
    assert await repo.upsert_quotes([quote]) == 1
    assert await repo.upsert_quotes([quote]) == 1

    rows = await repo.get_quotes(
        "600519",
        date(2024, 6, 1),
        date(2024, 6, 1),
    )
    assert len(rows) == 1
    assert rows[0].close == Decimal("1700.00")


@pytest.mark.asyncio
async def test_sqlite_upsert_updates_existing_row(repo: SqliteQuoteRepository) -> None:
    base = _make_quote("600519", "2024-06-01", "1700.00")
    await repo.upsert_quotes([base])
    updated = base.model_copy(update={"close": Decimal("1750.00"), "high": Decimal("1750.00")})
    await repo.upsert_quotes([updated])

    rows = await repo.get_quotes("600519", date(2024, 6, 1), date(2024, 6, 1))
    assert len(rows) == 1
    assert rows[0].close == Decimal("1750.00")


@pytest.mark.asyncio
async def test_get_quotes_date_range_inclusive(repo: SqliteQuoteRepository) -> None:
    quotes = [
        _make_quote("000001", "2024-01-01", "10.00"),
        _make_quote("000001", "2024-01-02", "11.00"),
        _make_quote("000001", "2024-01-03", "12.00"),
        _make_quote("000001", "2024-01-04", "13.00"),
        _make_quote("000001", "2024-01-05", "14.00"),
    ]
    await repo.upsert_quotes(quotes)

    result = await repo.get_quotes(
        "000001",
        start=date(2024, 1, 2),
        end=date(2024, 1, 4),
    )
    assert [q.trade_date.isoformat() for q in result] == [
        "2024-01-02",
        "2024-01-03",
        "2024-01-04",
    ]


@pytest.mark.asyncio
async def test_get_quotes_empty_when_no_data(repo: SqliteQuoteRepository) -> None:
    assert await repo.get_quotes("600519", date(2024, 1, 1), date(2024, 1, 31)) == []


@pytest.mark.asyncio
async def test_get_quotes_rejects_invalid_range(repo: SqliteQuoteRepository) -> None:
    with pytest.raises(ValueError, match="start"):
        await repo.get_quotes("600519", date(2024, 2, 1), date(2024, 1, 1))


@pytest.mark.asyncio
async def test_upsert_empty_list_returns_zero(repo: SqliteQuoteRepository) -> None:
    assert await repo.upsert_quotes([]) == 0
