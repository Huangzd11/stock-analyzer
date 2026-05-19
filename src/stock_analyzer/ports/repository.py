"""行情仓储端口。"""

from datetime import date
from typing import Protocol, runtime_checkable

from stock_analyzer.domain.models import Quote


@runtime_checkable
class IQuoteRepository(Protocol):
    """日 K 行情持久化接口。"""

    async def upsert_quotes(self, quotes: list[Quote]) -> int:
        """批量写入或更新行情，返回处理条数。"""
        ...

    async def get_quotes(self, symbol: str, start: date, end: date) -> list[Quote]:
        """按股票代码与日期区间查询（含起止日）。"""
        ...
