"""LSTM 多特征序列构建。"""

from __future__ import annotations

import numpy as np

from stock_analyzer.domain.models import Quote

# 特征：归一化收盘价、对数收益、归一化成交量、振幅占比
FEATURE_DIM = 4
_MIN_TRAIN_WINDOWS = 30


def min_history_for_lookback(lookback: int) -> int:
    """训练 + 验证所需的最少历史 K 线条数。"""
    return lookback + _MIN_TRAIN_WINDOWS + lookback


def build_feature_matrix(quotes: list[Quote]) -> tuple[np.ndarray, np.ndarray]:
    """从行情构建 (T, FEATURE_DIM) 特征矩阵与收盘价序列。"""
    ordered = sorted(quotes, key=lambda q: q.trade_date)
    closes = np.array([float(q.close) for q in ordered], dtype=np.float64)
    volumes = np.array([float(q.volume) for q in ordered], dtype=np.float64)
    highs = np.array([float(q.high) for q in ordered], dtype=np.float64)
    lows = np.array([float(q.low) for q in ordered], dtype=np.float64)

    close_mean = closes.mean()
    close_std = closes.std() or 1.0
    close_norm = (closes - close_mean) / close_std

    log_ret = np.zeros_like(closes)
    log_ret[1:] = np.log(np.maximum(closes[1:] / closes[:-1], 1e-8))

    vol_log = np.log1p(volumes)
    vol_std = vol_log.std() or 1.0
    vol_norm = (vol_log - vol_log.mean()) / vol_std

    hl_range = (highs - lows) / np.maximum(closes, 1e-8)
    hl_mean = hl_range.mean()
    hl_std = hl_range.std() or 1.0
    hl_norm = (hl_range - hl_mean) / hl_std

    features = np.column_stack([close_norm, log_ret, vol_norm, hl_norm])
    return features.astype(np.float32), closes


def append_feature_row(
    features: np.ndarray,
    closes: np.ndarray,
    new_close: float,
    *,
    vol_mean: float,
    vol_std: float,
    hl_mean: float,
    hl_std: float,
    volume: float,
    high: float,
    low: float,
) -> tuple[np.ndarray, np.ndarray]:
    """自回归预测时追加一行特征。"""
    closes_new = np.append(closes, new_close).astype(np.float64)
    close_mean = closes_new.mean()
    close_std = closes_new.std() or 1.0
    close_norm_last = float((new_close - close_mean) / close_std)

    prev_close = float(closes[-1]) if len(closes) else new_close
    log_r = float(np.log(max(new_close / prev_close, 1e-8)))
    vol_norm = float((np.log1p(volume) - vol_mean) / vol_std)
    hl_norm = float(((high - low) / max(new_close, 1e-8) - hl_mean) / hl_std)

    new_row = np.array([close_norm_last, log_r, vol_norm, hl_norm], dtype=np.float32)
    return np.vstack([features, new_row]), closes_new
