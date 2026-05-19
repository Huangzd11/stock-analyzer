"""行情数据源端口。"""

from datetime import date
from typing import Protocol, runtime_checkable

from stock_analyzer.domain.models import Quote, Stock


@runtime_checkable
class IQuoteSource(Protocol):
    """外部行情数据源适配器接口。"""

    async def fetch_daily(self, symbol: str, start: date, end: date) -> list[Quote]:
        """拉取日 K 行情。"""
        ...

    async def fetch_stock_info(self, symbol: str) -> Stock:
        """拉取股票基础信息。"""
        ...
