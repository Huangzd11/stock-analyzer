"""技术分析用例服务。"""

from datetime import date

import numpy as np

from stock_analyzer.domain.analysis import AnalysisResult
from stock_analyzer.domain.indicators import calc_ma, calc_macd, calc_rsi
from stock_analyzer.domain.models import Quote
from stock_analyzer.ports.repository import IQuoteRepository

_DEFAULT_MA_PERIOD = 20
_DEFAULT_RSI_PERIOD = 14


class AnalysisService:
    """从仓储读取行情并计算技术指标。"""

    def __init__(self, repository: IQuoteRepository) -> None:
        self._repository = repository

    async def analyze(
        self,
        symbol: str,
        start: date,
        end: date,
        ma_period: int = _DEFAULT_MA_PERIOD,
    ) -> AnalysisResult:
        quotes = await self._repository.get_quotes(symbol, start, end)
        if not quotes:
            msg = f"无行情数据: {symbol}"
            raise ValueError(msg)
        return self._build_result(symbol, quotes, ma_period)

    def _build_result(
        self,
        symbol: str,
        quotes: list[Quote],
        ma_period: int,
    ) -> AnalysisResult:
        ordered = sorted(quotes, key=lambda q: q.trade_date)
        closes = [float(q.close) for q in ordered]
        as_of = ordered[-1].trade_date

        ma = calc_ma(closes, ma_period)
        macd = calc_macd(closes)
        rsi = calc_rsi(closes, _DEFAULT_RSI_PERIOD)

        indicators: dict[str, float | dict[str, float | None]] = {
            f"ma_{ma_period}": _last_valid(ma),
            "macd": {
                "dif": _last_valid(macd.dif),
                "dea": _last_valid(macd.dea),
                "hist": _last_valid(macd.hist),
            },
            f"rsi_{_DEFAULT_RSI_PERIOD}": _last_valid(rsi),
        }
        summary = _compute_summary(ordered, closes)
        return AnalysisResult(
            symbol=symbol,
            as_of=as_of,
            indicators=indicators,
            summary=summary,
        )


def _last_valid(values: list[float | None]) -> float:
    for v in reversed(values):
        if v is not None:
            return v
    return 0.0


def _compute_summary(quotes: list[Quote], closes: list[float]) -> dict[str, float | None]:
    """计算收益、波动率、最大回撤等摘要。"""
    summary: dict[str, float | None] = {
        "return_30d": None,
        "volatility_30d": None,
        "max_drawdown_90d": None,
    }
    if len(closes) >= 2:
        returns = np.diff(closes) / np.array(closes[:-1])
        if len(returns) >= 30:
            recent = returns[-30:]
            summary["return_30d"] = float(closes[-1] / closes[-31] - 1)
            summary["volatility_30d"] = float(np.std(recent))
        lookback = min(90, len(closes))
        summary["max_drawdown_90d"] = _max_drawdown(closes[-lookback:])
    return summary


def _max_drawdown(closes: list[float]) -> float:
    peak = closes[0]
    max_dd = 0.0
    for price in closes:
        if price > peak:
            peak = price
        dd = (price - peak) / peak
        if dd < max_dd:
            max_dd = dd
    return max_dd
