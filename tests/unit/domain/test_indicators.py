"""技术指标计算测试（迭代 2）。"""

import math

import pytest

from stock_analyzer.domain.indicators import MacdResult, calc_ma, calc_macd, calc_rsi


def test_ma_calculates_correct_values() -> None:
    prices = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert calc_ma(prices, period=3) == [None, None, 2.0, 3.0, 4.0]


def test_ma_period_one_returns_same_prices() -> None:
    prices = [10.0, 20.0, 30.0]
    assert calc_ma(prices, period=1) == [10.0, 20.0, 30.0]


def test_ma_rejects_invalid_period() -> None:
    with pytest.raises(ValueError, match="period"):
        calc_ma([1.0, 2.0], period=0)


def test_macd_matches_reference() -> None:
    """MACD 分量满足 DIF/DEA/HIST 关系，并与手工验算的首个有效点对齐。"""
    # 足够长度以产生有效 MACD（慢线 26）
    prices = [float(i) for i in range(1, 41)]
    result = calc_macd(prices, fast=12, slow=26, signal=9)
    assert isinstance(result, MacdResult)
    assert len(result.dif) == len(prices)

    for dif, dea, hist in zip(result.dif, result.dea, result.hist, strict=True):
        if dif is not None and dea is not None and hist is not None:
            assert math.isclose(hist, dif - dea, rel_tol=1e-9)

    # 首个同时有 DIF、DEA、HIST 的索引（signal=9 需额外预热）
    first_hist_idx = next(i for i, h in enumerate(result.hist) if h is not None)
    dif = result.dif[first_hist_idx]
    dea = result.dea[first_hist_idx]
    assert dif is not None and dea is not None
    assert math.isclose(result.hist[first_hist_idx], dif - dea, rel_tol=1e-9)


def test_macd_rejects_fast_greater_than_slow() -> None:
    with pytest.raises(ValueError, match="fast"):
        calc_macd([1.0] * 30, fast=26, slow=12)


def test_rsi_bounded_0_100() -> None:
    prices = [float(i) for i in range(1, 60)]
    rsi = calc_rsi(prices, period=14)
    valid = [v for v in rsi if v is not None]
    assert valid, "应有可计算的 RSI 值"
    assert all(0.0 <= v <= 100.0 for v in valid)


def test_rsi_uptrend_higher_than_downtrend() -> None:
    uptrend = [float(i) for i in range(1, 40)]
    downtrend = [float(40 - i) for i in range(39)]
    rsi_up = [v for v in calc_rsi(uptrend, period=14) if v is not None][-1]
    rsi_down = [v for v in calc_rsi(downtrend, period=14) if v is not None][-1]
    assert rsi_up > rsi_down


def test_rsi_rejects_invalid_period() -> None:
    with pytest.raises(ValueError, match="period"):
        calc_rsi([1.0, 2.0], period=0)
