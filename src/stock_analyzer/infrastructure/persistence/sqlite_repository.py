"""SQLite 行情仓储实现。"""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import aiosqlite

from stock_analyzer.domain.models import Market, Quote
from stock_analyzer.infrastructure.persistence.schema import SCHEMA_SQL

_UPSERT_QUOTE_SQL = """
INSERT INTO daily_quotes (
    symbol, trade_date, open, high, low, close, volume, amount, adj_factor
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(symbol, trade_date) DO UPDATE SET
    open = excluded.open,
    high = excluded.high,
    low = excluded.low,
    close = excluded.close,
    volume = excluded.volume,
    amount = excluded.amount,
    adj_factor = excluded.adj_factor
"""

_SELECT_QUOTES_SQL = """
SELECT symbol, trade_date, open, high, low, close, volume, amount, adj_factor
FROM daily_quotes
WHERE symbol = ? AND trade_date >= ? AND trade_date <= ?
ORDER BY trade_date ASC
"""


class SqliteQuoteRepository:
    """基于 aiosqlite 的日 K 仓储。"""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(database_path)

    @property
    def database_path(self) -> str:
        return self._database_path

    async def initialize(self) -> None:
        """创建表结构（幂等）。"""
        async with aiosqlite.connect(self._database_path) as conn:
            await conn.executescript(SCHEMA_SQL)
            await conn.commit()

    async def upsert_quotes(self, quotes: list[Quote]) -> int:
        if not quotes:
            return 0
        async with aiosqlite.connect(self._database_path) as conn:
            await conn.execute("PRAGMA foreign_keys = ON")
            for symbol in {q.symbol for q in quotes}:
                await self._ensure_stock(conn, symbol)
            for quote in quotes:
                await conn.execute(_UPSERT_QUOTE_SQL, _quote_to_params(quote))
            await conn.commit()
        return len(quotes)

    async def get_quotes(self, symbol: str, start: date, end: date) -> list[Quote]:
        if start > end:
            msg = f"start ({start}) 不能晚于 end ({end})"
            raise ValueError(msg)
        async with aiosqlite.connect(self._database_path) as conn:
            cursor = await conn.execute(
                _SELECT_QUOTES_SQL,
                (symbol, start.isoformat(), end.isoformat()),
            )
            rows = await cursor.fetchall()
        return [_row_to_quote(tuple(row)) for row in rows]

    async def _ensure_stock(self, conn: aiosqlite.Connection, symbol: str) -> None:
        """满足外键约束：行情入库前确保 stocks 存在占位记录。"""
        now = datetime.now(UTC).isoformat()
        await conn.execute(
            """
            INSERT OR IGNORE INTO stocks (symbol, name, market, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (symbol, symbol, Market.SH.value, now),
        )


def _quote_to_params(quote: Quote) -> tuple[object, ...]:
    return (
        quote.symbol,
        quote.trade_date.isoformat(),
        float(quote.open),
        float(quote.high),
        float(quote.low),
        float(quote.close),
        quote.volume,
        float(quote.amount) if quote.amount is not None else None,
        float(quote.adj_factor) if quote.adj_factor is not None else None,
    )


def _row_to_quote(row: tuple[object, ...]) -> Quote:
    (
        symbol,
        trade_date_str,
        open_p,
        high_p,
        low_p,
        close_p,
        volume,
        amount,
        adj_factor,
    ) = row
    return Quote(
        symbol=str(symbol),
        trade_date=date.fromisoformat(str(trade_date_str)),
        open=Decimal(str(open_p)),
        high=Decimal(str(high_p)),
        low=Decimal(str(low_p)),
        close=Decimal(str(close_p)),
        volume=int(str(volume)),
        amount=Decimal(str(amount)) if amount is not None else None,
        adj_factor=Decimal(str(adj_factor)) if adj_factor is not None else None,
    )
