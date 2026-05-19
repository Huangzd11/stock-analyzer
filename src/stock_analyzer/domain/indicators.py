"""技术指标纯函数：无 I/O，便于单测。"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MacdResult:
    """MACD 指标结果。"""

    dif: list[float | None]
    dea: list[float | None]
    hist: list[float | None]


def _validate_period(period: int, name: str = "period") -> None:
    if period < 1:
        msg = f"{name} 必须 >= 1，当前为 {period}"
        raise ValueError(msg)


def _to_array(prices: Sequence[float]) -> np.ndarray:
    return np.asarray(prices, dtype=np.float64)


def _nan_list(length: int) -> list[float | None]:
    return [None] * length


def _ema_series(values: np.ndarray, period: int) -> np.ndarray:
    """指数移动平均；前 period-1 为 nan，首个 EMA 为前 period 项 SMA。"""
    n = len(values)
    ema = np.full(n, np.nan)
    if n < period:
        return ema
    alpha = 2.0 / (period + 1)
    ema[period - 1] = float(np.mean(values[:period]))
    for i in range(period, n):
        ema[i] = alpha * values[i] + (1.0 - alpha) * ema[i - 1]
    return ema


def _array_to_optional_list(arr: np.ndarray) -> list[float | None]:
    return [None if np.isnan(v) else float(v) for v in arr]


def calc_ma(prices: Sequence[float], period: int) -> list[float | None]:
    """简单移动平均（SMA）。不足 period 的位置返回 None。"""
    _validate_period(period)
    n = len(prices)
    if n == 0:
        return []
    arr = _to_array(prices)
    result = _nan_list(n)
    for i in range(period - 1, n):
        result[i] = float(np.mean(arr[i - period + 1 : i + 1]))
    return result


def calc_macd(
    prices: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> MacdResult:
    """MACD：DIF = EMA(fast) - EMA(slow)，DEA = EMA(DIF, signal)，HIST = DIF - DEA。"""
    _validate_period(fast, "fast")
    _validate_period(slow, "slow")
    _validate_period(signal, "signal")
    if fast >= slow:
        msg = f"fast ({fast}) 必须小于 slow ({slow})"
        raise ValueError(msg)

    n = len(prices)
    if n == 0:
        empty: list[float | None] = []
        return MacdResult(dif=empty, dea=empty, hist=empty)

    arr = _to_array(prices)
    ema_fast = _ema_series(arr, fast)
    ema_slow = _ema_series(arr, slow)
    dif_arr = ema_fast - ema_slow

    # DEA 对 DIF 序列做 EMA（忽略 nan，从首个有效 DIF 起算）
    dea_arr = np.full(n, np.nan)
    valid_mask = ~np.isnan(dif_arr)
    if np.any(valid_mask):
        valid_dif = dif_arr[valid_mask]
        dea_valid = _ema_series(valid_dif, signal)
        dea_arr[valid_mask] = dea_valid

    hist_arr = dif_arr - dea_arr
    return MacdResult(
        dif=_array_to_optional_list(dif_arr),
        dea=_array_to_optional_list(dea_arr),
        hist=_array_to_optional_list(hist_arr),
    )


def calc_rsi(prices: Sequence[float], period: int = 14) -> list[float | None]:
    """相对强弱指数（RSI），Wilder 平滑。有效值范围 [0, 100]。"""
    _validate_period(period)
    n = len(prices)
    if n == 0:
        return []
    if n == 1:
        return [None]

    arr = _to_array(prices)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    result = _nan_list(n)
    if n <= period:
        return result

    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    result[period] = _rsi_from_averages(avg_gain, avg_loss)

    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        result[i] = _rsi_from_averages(avg_gain, avg_loss)

    return result


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))
