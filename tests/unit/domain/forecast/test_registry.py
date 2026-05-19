"""预测策略注册表测试。"""

from stock_analyzer.domain.forecast import create_baseline_registry


def test_forecast_registry_lists_baseline_only() -> None:
    registry = create_baseline_registry()
    assert registry.list_baseline_names() == ["linear_trend", "ma_trend"]
    assert registry.list_names() == ["linear_trend", "ma_trend"]


def test_forecast_registry_get_strategy() -> None:
    registry = create_baseline_registry()
    strategy = registry.get("ma_trend")
    assert strategy.name == "ma_trend"
