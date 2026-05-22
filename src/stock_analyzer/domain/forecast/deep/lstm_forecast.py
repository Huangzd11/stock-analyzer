"""LSTM 走势预测（阶段 B 强化版：多特征 + 验证早停）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from stock_analyzer.domain.forecast.base import ForecastMetadata, ForecastResult
from stock_analyzer.domain.forecast.deep.availability import require_ml
from stock_analyzer.domain.forecast.deep.lstm_features import (
    append_feature_row,
    build_feature_matrix,
    min_history_for_lookback,
)
from stock_analyzer.domain.forecast.trend_utils import (
    build_forecast_points,
    future_dates,
    infer_trend,
    sorted_closes,
)
from stock_analyzer.domain.models import Quote

_MODEL_VERSION = "lstm-v2"
_DEFAULT_LOOKBACK = 30
_DEFAULT_MAX_EPOCHS = 100
_DEFAULT_HIDDEN = 64
_DEFAULT_PATIENCE = 10
_VAL_RATIO = 0.2
_FEATURE_DIM = 4


@dataclass
class _TrainArtifacts:
    close_mean: float
    close_std: float
    vol_mean: float
    vol_std: float
    hl_mean: float
    hl_std: float
    val_mae: float
    val_rmse: float


class LstmForecast:
    """多特征双层 LSTM：验证集早停 + Huber 损失，提升预测稳定性。"""

    def __init__(
        self,
        lookback: int = _DEFAULT_LOOKBACK,
        max_epochs: int = _DEFAULT_MAX_EPOCHS,
        hidden_size: int = _DEFAULT_HIDDEN,
        patience: int = _DEFAULT_PATIENCE,
        num_layers: int = 2,
        dropout: float = 0.2,
    ) -> None:
        if lookback < 10:
            msg = f"lookback 必须 >= 10，当前为 {lookback}"
            raise ValueError(msg)
        self._lookback = lookback
        self._max_epochs = max_epochs
        self._hidden_size = hidden_size
        self._patience = patience
        self._num_layers = num_layers
        self._dropout = dropout
        self._min_history = min_history_for_lookback(lookback)

    @property
    def name(self) -> str:
        return "lstm"

    def predict(self, quotes: list[Quote], horizon_days: int) -> ForecastResult:
        require_ml("lstm")
        if horizon_days < 1:
            msg = f"horizon_days 必须 >= 1，当前为 {horizon_days}"
            raise ValueError(msg)
        if len(quotes) < self._min_history:
            msg = f"LSTM 至少需要 {self._min_history} 条历史行情"
            raise ValueError(msg)

        dates, _ = sorted_closes(quotes)
        symbol = quotes[0].symbol
        artifacts, model = self._train_model(quotes)
        forecast_values = self._forecast_horizon(model, quotes, artifacts, horizon_days)
        points = build_forecast_points(
            future_dates(dates[-1], horizon_days),
            forecast_values,
            artifacts.val_rmse,
        )

        return ForecastResult(
            symbol=symbol,
            strategy=self.name,
            horizon_days=horizon_days,
            points=points,
            trend=infer_trend(forecast_values),
            metadata=ForecastMetadata(
                model_version=_MODEL_VERSION,
                training_cutoff=dates[-1],
                mae=artifacts.val_mae,
                rmse=artifacts.val_rmse,
                explainability="low",
            ),
        )

    def _build_sequences(self, features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """滑动窗口：(N, lookback, F) -> 下一日归一化收盘价（特征第 0 维）。"""
        xs: list[np.ndarray] = []
        ys: list[float] = []
        for i in range(len(features) - self._lookback):
            xs.append(features[i : i + self._lookback])
            ys.append(float(features[i + self._lookback, 0]))
        return np.array(xs, dtype=np.float32), np.array(ys, dtype=np.float32)

    def _train_model(self, quotes: list[Quote]) -> tuple[_TrainArtifacts, Any]:
        import torch
        import torch.nn as nn

        features, closes = build_feature_matrix(quotes)
        close_mean = float(closes.mean())
        close_std = float(closes.std()) or 1.0

        x_all, y_all = self._build_sequences(features)
        split = max(int(len(x_all) * (1 - _VAL_RATIO)), 1)
        x_train, y_train = x_all[:split], y_all[:split]
        x_val, y_val = x_all[split:], y_all[split:]
        if len(x_val) == 0:
            x_val, y_val = x_train[-8:], y_train[-8:]

        x_train_t = torch.from_numpy(x_train)
        y_train_t = torch.from_numpy(y_train).unsqueeze(-1)
        x_val_t = torch.from_numpy(x_val)
        y_val_t = torch.from_numpy(y_val).unsqueeze(-1)

        lstm_dropout = self._dropout if self._num_layers > 1 else 0.0

        class _LstmNet(nn.Module):  # type: ignore[misc]
            def __init__(self) -> None:
                super().__init__()
                self.lstm = nn.LSTM(
                    _FEATURE_DIM,
                    hidden_size,
                    num_layers=num_layers,
                    batch_first=True,
                    dropout=lstm_dropout,
                )
                self.drop = nn.Dropout(dropout)
                self.fc = nn.Linear(hidden_size, 1)

            def forward(self, inputs: torch.Tensor) -> torch.Tensor:
                out, _ = self.lstm(inputs)
                out = self.drop(out[:, -1, :])
                return self.fc(out)

        hidden_size = self._hidden_size
        num_layers = self._num_layers
        dropout = self._dropout

        model = _LstmNet()
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        loss_fn = nn.HuberLoss(delta=1.0)
        best_state: dict[str, Any] | None = None
        best_val = float("inf")
        stale = 0

        for _ in range(self._max_epochs):
            model.train()
            optimizer.zero_grad()
            loss = loss_fn(model(x_train_t), y_train_t)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            model.eval()
            with torch.no_grad():
                val_loss = float(loss_fn(model(x_val_t), y_val_t).item())
            if val_loss < best_val:
                best_val = val_loss
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                stale = 0
            else:
                stale += 1
                if stale >= self._patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state)
        model.eval()

        with torch.no_grad():
            val_preds = model(x_val_t).squeeze(-1).numpy()
        val_mae_norm = float(np.mean(np.abs(val_preds - y_val)))
        val_rmse_norm = float(np.sqrt(np.mean((val_preds - y_val) ** 2)))

        ordered = sorted(quotes, key=lambda q: q.trade_date)
        vol_log = np.log1p([float(q.volume) for q in ordered])
        hl = [
            (float(q.high) - float(q.low)) / max(float(q.close), 1e-8) for q in ordered
        ]
        artifacts = _TrainArtifacts(
            close_mean=close_mean,
            close_std=close_std,
            vol_mean=float(vol_log.mean()),
            vol_std=float(vol_log.std()) or 1.0,
            hl_mean=float(np.mean(hl)),
            hl_std=float(np.std(hl)) or 1.0,
            val_mae=val_mae_norm * close_std,
            val_rmse=val_rmse_norm * close_std,
        )
        return artifacts, model

    def _forecast_horizon(
        self,
        model: Any,
        quotes: list[Quote],
        artifacts: _TrainArtifacts,
        horizon_days: int,
    ) -> list[float]:
        """自回归多步预测（反归一化收盘价）。"""
        import torch

        features, closes = build_feature_matrix(quotes)
        ordered = sorted(quotes, key=lambda q: q.trade_date)
        last_q = ordered[-1]
        features_work = features.copy()
        closes_work = closes.copy()

        last_volume = float(last_q.volume)
        last_high = float(last_q.high)
        last_low = float(last_q.low)

        preds: list[float] = []
        model.eval()
        for _ in range(horizon_days):
            window = features_work[-self._lookback :]
            x = torch.from_numpy(window).unsqueeze(0)
            with torch.no_grad():
                next_norm = float(model(x).item())
            next_close = next_norm * artifacts.close_std + artifacts.close_mean
            preds.append(next_close)

            features_work, closes_work = append_feature_row(
                features_work,
                closes_work,
                next_close,
                vol_mean=artifacts.vol_mean,
                vol_std=artifacts.vol_std,
                hl_mean=artifacts.hl_mean,
                hl_std=artifacts.hl_std,
                volume=last_volume,
                high=last_high,
                low=last_low,
            )

        return preds
