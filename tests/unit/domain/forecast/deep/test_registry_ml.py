"""含 ML 策略的注册表测试。"""

import pytest

from stock_analyzer.domain.forecast.registry import create_baseline_registry, create_full_registry

torch = pytest.importorskip("torch")


@pytest.mark.ml
def test_full_registry_includes_lstm() -> None:
    registry = create_full_registry()
    names = registry.list_names()
    assert "lstm" in names
    assert "ma_trend" in names


def test_baseline_registry_excludes_lstm() -> None:
    registry = create_baseline_registry()
    assert "lstm" not in registry.list_names()
