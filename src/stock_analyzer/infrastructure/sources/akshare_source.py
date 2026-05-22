"""AkShare 数据源适配器：多源回退 + 可配置代理/超时。"""



import asyncio

import os

from contextlib import contextmanager

from datetime import date, datetime

from decimal import Decimal

from typing import Iterator



import pandas as pd

import requests



from stock_analyzer.domain.models import Market, Quote, Stock



_COL_DATE = "日期"

_COL_OPEN = "开盘"

_COL_HIGH = "最高"

_COL_LOW = "最低"

_COL_CLOSE = "收盘"

_COL_VOLUME = "成交量"

_COL_AMOUNT = "成交额"



# 腾讯源列名

_TX_DATE = "date"

_TX_OPEN = "open"

_TX_HIGH = "high"

_TX_LOW = "low"

_TX_CLOSE = "close"

_TX_AMOUNT = "amount"



# 新浪源列名（英文）

_SINA_OPEN = "open"

_SINA_HIGH = "high"

_SINA_LOW = "low"

_SINA_CLOSE = "close"

_SINA_VOLUME = "volume"

_SINA_AMOUNT = "amount"





class QuoteSourceError(Exception):

    """行情数据源不可用。"""





def infer_market(symbol: str) -> Market:

    """根据 A 股代码前缀推断市场。"""

    if symbol.startswith(("60", "68")):

        return Market.SH

    if symbol.startswith(("00", "30")):

        return Market.SZ

    if symbol.startswith(("8", "4")):

        return Market.BJ

    return Market.SH





def symbol_to_prefixed(symbol: str) -> str:

    """6 位代码 → 带市场前缀代码（如 sh600519）。"""

    market = infer_market(symbol)

    prefix = market.value.lower()

    return f"{prefix}{symbol}"





class AkShareSource:

    """通过 AkShare 拉取 A 股行情，东方财富失败时自动回退腾讯/新浪。"""



    def __init__(

        self,

        request_timeout: float = 30.0,

        http_proxy: str | None = None,

        https_proxy: str | None = None,

    ) -> None:

        self._request_timeout = request_timeout

        self._http_proxy = http_proxy

        self._https_proxy = https_proxy or http_proxy



    async def fetch_daily(self, symbol: str, start: date, end: date) -> list[Quote]:

        if start > end:

            msg = f"start ({start}) 不能晚于 end ({end})"

            raise ValueError(msg)

        return await asyncio.to_thread(self._fetch_daily_sync, symbol, start, end)



    async def fetch_stock_info(self, symbol: str) -> Stock:

        return await asyncio.to_thread(self._fetch_stock_info_sync, symbol)



    def _fetch_daily_sync(self, symbol: str, start: date, end: date) -> list[Quote]:

        errors: list[str] = []

        with self._proxy_env():

            for name, fetcher in (

                ("东方财富", self._fetch_em_sync),

                ("腾讯证券", self._fetch_tx_sync),

                ("新浪财经", self._fetch_sina_sync),

            ):

                try:

                    df = fetcher(symbol, start, end)

                    if df is not None and not df.empty:

                        return self._dataframe_to_quotes(symbol, df, name)

                except (requests.RequestException, OSError, ValueError) as exc:

                    errors.append(f"{name}: {exc}")

        detail = "; ".join(errors) if errors else "未知错误"

        msg = f"所有数据源均不可用，请检查网络或代理配置。详情: {detail}"

        raise QuoteSourceError(msg)



    def _fetch_em_sync(self, symbol: str, start: date, end: date) -> pd.DataFrame:

        import akshare as ak



        return ak.stock_zh_a_hist(

            symbol=symbol,

            period="daily",

            start_date=start.strftime("%Y%m%d"),

            end_date=end.strftime("%Y%m%d"),

            adjust="",

            timeout=self._request_timeout,

        )



    def _fetch_tx_sync(self, symbol: str, start: date, end: date) -> pd.DataFrame:

        import akshare as ak



        return ak.stock_zh_a_hist_tx(

            symbol=symbol_to_prefixed(symbol),

            start_date=start.strftime("%Y-%m-%d"),

            end_date=end.strftime("%Y-%m-%d"),

            adjust="",

            timeout=self._request_timeout,

        )



    def _fetch_sina_sync(self, symbol: str, start: date, end: date) -> pd.DataFrame:

        import akshare as ak



        return ak.stock_zh_a_daily(

            symbol=symbol_to_prefixed(symbol),

            start_date=start.strftime("%Y%m%d"),

            end_date=end.strftime("%Y%m%d"),

            adjust="",

        )



    def _dataframe_to_quotes(self, symbol: str, df: pd.DataFrame, source: str) -> list[Quote]:

        if source == "东方财富":

            return [_row_em_to_quote(symbol, row) for _, row in df.iterrows()]

        if source == "腾讯证券":

            return [_row_tx_to_quote(symbol, row) for _, row in df.iterrows()]

        return [_row_sina_to_quote(symbol, row) for _, row in df.iterrows()]



    def _fetch_stock_info_sync(self, symbol: str) -> Stock:

        import akshare as ak



        name = symbol

        with self._proxy_env():

            try:

                info_df = ak.stock_individual_info_em(symbol=symbol)

                if not info_df.empty:

                    name_row = info_df.loc[info_df["item"] == "股票简称", "value"]

                    if not name_row.empty:

                        name = str(name_row.iloc[0])

            except Exception:

                pass

        return Stock(symbol=symbol, name=name, market=infer_market(symbol))



    @contextmanager

    def _proxy_env(self) -> Iterator[None]:

        """临时注入 HTTP(S) 代理环境变量，供 requests/akshare 使用。"""

        keys = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy")

        backup: dict[str, str | None] = {k: os.environ.get(k) for k in keys}

        try:

            if self._http_proxy:

                os.environ["HTTP_PROXY"] = self._http_proxy

                os.environ["http_proxy"] = self._http_proxy

            if self._https_proxy:

                os.environ["HTTPS_PROXY"] = self._https_proxy

                os.environ["https_proxy"] = self._https_proxy

            yield

        finally:

            for key, old in backup.items():

                if old is None:

                    os.environ.pop(key, None)

                else:

                    os.environ[key] = old





def _row_em_to_quote(symbol: str, row: pd.Series) -> Quote:

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





def _row_tx_to_quote(symbol: str, row: pd.Series) -> Quote:

    trade_date = _parse_trade_date(row[_TX_DATE])

    amount_raw = row.get(_TX_AMOUNT)

    return Quote(

        symbol=symbol,

        trade_date=trade_date,

        open=Decimal(str(row[_TX_OPEN])),

        high=Decimal(str(row[_TX_HIGH])),

        low=Decimal(str(row[_TX_LOW])),

        close=Decimal(str(row[_TX_CLOSE])),

        volume=0,

        amount=Decimal(str(amount_raw)) if pd.notna(amount_raw) else None,

    )





def _row_sina_to_quote(symbol: str, row: pd.Series) -> Quote:

    trade_date = _parse_trade_date(row.name)

    amount_raw = row.get(_SINA_AMOUNT)

    return Quote(

        symbol=symbol,

        trade_date=trade_date,

        open=Decimal(str(row[_SINA_OPEN])),

        high=Decimal(str(row[_SINA_HIGH])),

        low=Decimal(str(row[_SINA_LOW])),

        close=Decimal(str(row[_SINA_CLOSE])),

        volume=int(row[_SINA_VOLUME]),

        amount=Decimal(str(amount_raw)) if pd.notna(amount_raw) else None,

    )





def _parse_trade_date(value: object) -> date:

    if isinstance(value, date):

        return value

    if isinstance(value, datetime):

        return value.date()

    return date.fromisoformat(str(value)[:10])


