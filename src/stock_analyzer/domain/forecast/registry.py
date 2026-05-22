"""预测策略注册表：阶段 A 仅注册可解释基线。"""

from stock_analyzer.domain.forecast.base import ForecastStrategy
from stock_analyzer.domain.forecast.linear_trend import LinearTrendForecast
from stock_analyzer.domain.forecast.moving_average import MovingAverageForecast

_BASELINE_STRATEGY_NAMES = ("ma_trend", "linear_trend")


class ForecastRegistry:
    """策略名 → 实现实例。"""

    def __init__(self) -> None:
        self._strategies: dict[str, ForecastStrategy] = {}

    def register(self, strategy: ForecastStrategy) -> None:
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> ForecastStrategy:
        if name not in self._strategies:
            msg = f"未知预测策略: {name}，可用: {self.list_names()}"
            raise KeyError(msg)
        return self._strategies[name]

    def list_names(self) -> list[str]:
        return sorted(self._strategies.keys())

    def list_baseline_names(self) -> list[str]:
        """返回已注册的基线策略名（MVP 应仅含阶段 A）。"""
        return [n for n in self.list_names() if n in _BASELINE_STRATEGY_NAMES]


def create_baseline_registry() -> ForecastRegistry:
    """创建并注册阶段 A 基线策略。"""
    registry = ForecastRegistry()
    registry.register(MovingAverageForecast())
    registry.register(LinearTrendForecast())
    return registry


def create_full_registry(settings: object | None = None) -> ForecastRegistry:
    """创建基线 + 深度学习策略注册表（需已安装 .[ml]）。"""
    registry = create_baseline_registry()
    from stock_analyzer.domain.forecast.deep import register_deep_strategies

    register_deep_strategies(registry, settings)
    return registry
