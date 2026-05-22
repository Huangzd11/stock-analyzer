"""股票前景/走势评分单元测试。"""

from datetime import date

import pytest

from stock_analyzer.domain.analysis import AnalysisResult
from stock_analyzer.domain.forecast.base import ForecastPoint, ForecastResult, TrendDirection
from stock_analyzer.domain.stock_screener import OutlookScore, score_outlook


def _analysis(
    *,
    ma_20: float = 100.0,
    close_proxy: float = 105.0,
    macd_hist: float = 0.5,
    rsi: float = 55.0,
    return_30d: float | None = 0.05,
) -> AnalysisResult:
    """构造分析结果；用 ma 与 summary 表达强弱。"""
    return AnalysisResult(
        symbol="600519",
        as_of=date(2024, 3, 1),
        indicators={
            "ma_20": ma_20,
            "macd": {"dif": 1.0, "dea": 0.5, "hist": macd_hist},
            "rsi_14": rsi,
        },
        summary={
            "return_30d": return_30d,
            "volatility_30d": 0.02,
            "max_drawdown_90d": -0.05,
            "last_close": close_proxy,
        },
    )


def _forecast(trend: TrendDirection = TrendDirection.UP) -> ForecastResult:
    return ForecastResult(
        symbol="600519",
        strategy="ma_trend",
        horizon_days=5,
        points=[
            ForecastPoint(date=date(2024, 3, 2), value=100),
            ForecastPoint(date=date(2024, 3, 3), value=102),
        ],
        trend=trend,
    )


def test_score_outlook_high_for_bullish_signals() -> None:
    result = score_outlook(_analysis(), _forecast(TrendDirection.UP))
    assert result.score >= 70
    assert result.trend == TrendDirection.UP
    assert result.passed is True


def test_score_outlook_low_for_bearish_signals() -> None:
    analysis = _analysis(
        ma_20=110.0,
        close_proxy=95.0,
        macd_hist=-0.3,
        rsi=30.0,
        return_30d=-0.1,
    )
    result = score_outlook(analysis, _forecast(TrendDirection.DOWN))
    assert result.score < 50
    assert result.passed is False


@pytest.mark.parametrize(
    ("trend", "expected_min"),
    [
        (TrendDirection.UP, 30),
        (TrendDirection.SIDEWAYS, 10),
        (TrendDirection.DOWN, 0),
    ],
)
def test_score_outlook_trend_component(
    trend: TrendDirection,
    expected_min: float,
) -> None:
    result = score_outlook(_analysis(), _forecast(trend))
    assert result.score >= expected_min
