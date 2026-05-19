"""领域实体：股票与行情 K 线。"""

import re
from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

# A 股 6 位数字代码
_SYMBOL_PATTERN = re.compile(r"^\d{6}$")


class Market(StrEnum):
    """交易市场。"""

    SH = "SH"  # 上交所
    SZ = "SZ"  # 深交所
    BJ = "BJ"  # 北交所


class Stock(BaseModel):
    """股票基础信息。"""

    symbol: str = Field(..., description="6 位股票代码")
    name: str = Field(..., min_length=1)
    market: Market
    industry: str | None = None
    list_date: date | None = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        if not _SYMBOL_PATTERN.match(value):
            msg = f"股票代码格式无效: {value}，应为 6 位数字"
            raise ValueError(msg)
        return value


class Quote(BaseModel):
    """日 K 行情。"""

    symbol: str = Field(..., description="6 位股票代码")
    trade_date: date
    open: Decimal = Field(..., gt=0)
    high: Decimal = Field(..., gt=0)
    low: Decimal = Field(..., gt=0)
    close: Decimal = Field(..., gt=0)
    volume: int = Field(..., ge=0)
    amount: Decimal | None = Field(default=None, ge=0)
    adj_factor: Decimal | None = Field(default=None, gt=0)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        if not _SYMBOL_PATTERN.match(value):
            msg = f"股票代码格式无效: {value}，应为 6 位数字"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_ohlc_consistency(self) -> "Quote":
        """校验 high/low 与 open/close 的一致性。"""
        open_p, high_p, low_p, close_p = self.open, self.high, self.low, self.close
        max_price = max(open_p, close_p)
        min_price = min(open_p, close_p)
        if high_p < max_price:
            msg = f"最高价 {high_p} 不能低于 open/close 较大值 {max_price}"
            raise ValueError(msg)
        if low_p > min_price:
            msg = f"最低价 {low_p} 不能高于 open/close 较小值 {min_price}"
            raise ValueError(msg)
        return self
