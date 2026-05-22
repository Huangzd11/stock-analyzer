"""阶段 B：深度学习预测策略（需安装 .[ml] 可选依赖）。"""

from stock_analyzer.domain.forecast.base import ForecastStrategy
from stock_analyzer.domain.forecast.deep.availability import (
    MlDependencyError,
    is_ml_available,
    require_ml,
)
from stock_analyzer.domain.forecast.registry import ForecastRegistry


def create_lstm_forecast(settings: object | None = None) -> ForecastStrategy:
    """创建 LSTM 策略；未安装 torch 时抛出 MlDependencyError。"""
    require_ml("lstm")
    from stock_analyzer.config.settings import Settings
    from stock_analyzer.domain.forecast.deep.lstm_forecast import LstmForecast

    cfg = settings if isinstance(settings, Settings) else Settings()
    return LstmForecast(
        lookback=cfg.lstm_lookback,
        max_epochs=cfg.lstm_max_epochs,
        hidden_size=cfg.lstm_hidden_size,
        patience=cfg.lstm_patience,
    )


def register_deep_strategies(
    registry: ForecastRegistry,
    settings: object | None = None,
) -> None:
    """向注册表添加深度学习策略。"""
    registry.register(create_lstm_forecast(settings))


__all__ = [
    "MlDependencyError",
    "create_lstm_forecast",
    "is_ml_available",
    "register_deep_strategies",
    "require_ml",
]
