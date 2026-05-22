"""股票前景与走势评分（纯函数，供自动加自选等用例复用）。"""

from dataclasses import dataclass

from stock_analyzer.domain.analysis import AnalysisResult
from stock_analyzer.domain.forecast.base import ForecastResult, TrendDirection

# 各维度满分权重（总分 100）
_WEIGHT_TREND = 35.0
_WEIGHT_ABOVE_MA = 25.0
_WEIGHT_MACD = 15.0
_WEIGHT_RETURN = 15.0
_WEIGHT_RSI = 10.0

_DEFAULT_PASS_SCORE = 55.0
_RSI_LOW = 40.0
_RSI_HIGH = 75.0


@dataclass(frozen=True)
class OutlookScore:
    """单只股票的综合评分。"""

    symbol: str
    score: float
    trend: TrendDirection
    passed: bool
    reasons: list[str]


def score_outlook(
    analysis: AnalysisResult,
    forecast: ForecastResult,
    *,
    pass_threshold: float = _DEFAULT_PASS_SCORE,
) -> OutlookScore:
    """根据技术分析与预测走势计算前景得分。"""
    score = 0.0
    reasons: list[str] = []

    trend = forecast.trend
    if trend == TrendDirection.UP:
        score += _WEIGHT_TREND
        reasons.append("预测趋势向上")
    elif trend == TrendDirection.SIDEWAYS:
        score += _WEIGHT_TREND * 0.4
        reasons.append("预测趋势震荡")
    else:
        reasons.append("预测趋势向下")

    ma_key = next((k for k in analysis.indicators if k.startswith("ma_")), None)
    ma_val = float(analysis.indicators[ma_key]) if ma_key else 0.0
    last_close = analysis.summary.get("last_close")
    if last_close is not None and ma_val > 0 and float(last_close) >= ma_val:
        score += _WEIGHT_ABOVE_MA
        reasons.append("收盘价站上均线")

    macd = analysis.indicators.get("macd")
    if isinstance(macd, dict) and macd.get("hist") is not None and float(macd["hist"]) > 0:
        score += _WEIGHT_MACD
        reasons.append("MACD 柱状为正")

    ret = analysis.summary.get("return_30d")
    if ret is not None and float(ret) > 0:
        score += _WEIGHT_RETURN
        reasons.append("近 30 日收益为正")

    rsi_key = next((k for k in analysis.indicators if k.startswith("rsi_")), None)
    if rsi_key:
        rsi = float(analysis.indicators[rsi_key])
        if _RSI_LOW <= rsi <= _RSI_HIGH:
            score += _WEIGHT_RSI
            reasons.append("RSI 处于健康区间")

    rounded = round(score, 2)
    return OutlookScore(
        symbol=analysis.symbol,
        score=rounded,
        trend=trend,
        passed=rounded >= pass_threshold,
        reasons=reasons,
    )
