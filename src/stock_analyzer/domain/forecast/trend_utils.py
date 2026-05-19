"""预测策略共享工具函数。"""

from datetime import date, timedelta
from decimal import Decimal

import numpy as np

from stock_analyzer.domain.forecast.base import ForecastPoint, TrendDirection
from stock_analyzer.domain.models import Quote


def sorted_closes(quotes: list[Quote]) -> tuple[list[date], list[float]]:
    """按交易日排序后返回日期与收盘价序列。"""
    ordered = sorted(quotes, key=lambda q: q.trade_date)
    dates = [q.trade_date for q in ordered]
    closes = [float(q.close) for q in ordered]
    return dates, closes


def future_dates(last_date: date, horizon_days: int) -> list[date]:
    """生成未来 horizon_days 个日历日（简化，不含交易日历）。"""
    return [last_date + timedelta(days=offset) for offset in range(1, horizon_days + 1)]


def infer_trend(values: list[float]) -> TrendDirection:
    """根据预测序列首尾变化推断趋势。"""
    if len(values) < 2:
        return TrendDirection.SIDEWAYS
    change = values[-1] - values[0]
    threshold = max(abs(values[0]) * 0.01, 1e-6)
    if change > threshold:
        return TrendDirection.UP
    if change < -threshold:
        return TrendDirection.DOWN
    return TrendDirection.SIDEWAYS


def build_forecast_points(
    dates: list[date],
    values: list[float],
    residual_std: float,
) -> list[ForecastPoint]:
    """构建带对称置信区间的预测点。"""
    points: list[ForecastPoint] = []
    for d, v in zip(dates, values, strict=True):
        margin = Decimal(str(residual_std * 1.96))
        val = Decimal(str(round(v, 4)))
        points.append(
            ForecastPoint(
                date=d,
                value=val,
                lower=val - margin,
                upper=val + margin,
            )
        )
    return points


def residual_std(closes: list[float], fitted: list[float]) -> float:
    """计算残差标准差，用于置信区间。"""
    if len(closes) != len(fitted) or len(closes) < 2:
        return float(np.std(closes)) if closes else 0.0
    errors = np.array(closes) - np.array(fitted)
    return float(np.std(errors))
