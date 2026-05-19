"""AkShare 数据源适配器。"""

import asyncio
from datetime import date, datetime
from decimal import Decimal

import pandas as pd

from stock_analyzer.domain.models import Market, Quote, Stock

_COL_DATE = "日期"
_COL_OPEN = "开盘"
_COL_HIGH = "最高"
_COL_LOW = "最低"
_COL_CLOSE = "收盘"
_COL_VOLUME = "成交量"
_COL_AMOUNT = "成交额"


def infer_market(symbol: str) -> Market:
    """根据 A 股代码前缀推断市场。"""
    if symbol.startswith(("60", "68")):
        return Market.SH
    if symbol.startswith(("00", "30")):
        return Market.SZ
    if symbol.startswith(("8", "4")):
        return Market.BJ
    return Market.SH


class AkShareSource:
    """通过 AkShare 拉取 A 股行情。"""

    async def fetch_daily(self, symbol: str, start: date, end: date) -> list[Quote]:
        if start > end:
            msg = f"start ({start}) 不能晚于 end ({end})"
            raise ValueError(msg)
        return await asyncio.to_thread(self._fetch_daily_sync, symbol, start, end)

    async def fetch_stock_info(self, symbol: str) -> Stock:
        return await asyncio.to_thread(self._fetch_stock_info_sync, symbol)

    def _fetch_daily_sync(self, symbol: str, start: date, end: date) -> list[Quote]:
        import akshare as ak

        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="",
        )
        if df is None or df.empty:
            return []
        return [_row_to_quote(symbol, row) for _, row in df.iterrows()]

    def _fetch_stock_info_sync(self, symbol: str) -> Stock:
        import akshare as ak

        name = symbol
        try:
            info_df = ak.stock_individual_info_em(symbol=symbol)
            if not info_df.empty:
                name_row = info_df.loc[info_df["item"] == "股票简称", "value"]
                if not name_row.empty:
                    name = str(name_row.iloc[0])
        except Exception:
            pass
        return Stock(symbol=symbol, name=name, market=infer_market(symbol))


def _row_to_quote(symbol: str, row: pd.Series) -> Quote:
    trade_date = _parse_trade_date(row[_COL_DATE])
    amount_raw = row.get(_COL_AMOUNT)
    return Quote(
        symbol=symbol,
        trade_date=trade_date,
        open=Decimal(str(row[_COL_OPEN])),
        high=Decimal(str(row[_COL_HIGH])),
        low=Decimal(str(row[_COL_LOW])),
        close=Decimal(str(row[_COL_CLOSE])),
        volume=int(row[_COL_VOLUME]),
        amount=Decimal(str(amount_raw)) if pd.notna(amount_raw) else None,
    )


def _parse_trade_date(value: object) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])
