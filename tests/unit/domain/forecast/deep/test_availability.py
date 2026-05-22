"""ML 依赖检测测试。"""

import builtins

import pytest

from stock_analyzer.domain.forecast.deep import create_lstm_forecast
from stock_analyzer.domain.forecast.deep.availability import (
    MlDependencyError,
    is_ml_available,
    require_ml,
)


def test_lstm_forecast_requires_ml_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    """未安装 torch 时应给出清晰安装提示。"""
    real_import = builtins.__import__

    def _mock_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "torch" or name.startswith("torch."):
            raise ImportError("No module named 'torch'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _mock_import)
    monkeypatch.setattr(
        "stock_analyzer.domain.forecast.deep.availability.is_ml_available",
        lambda: False,
    )

    with pytest.raises(MlDependencyError, match=r"\[ml\]"):
        require_ml("lstm")

    with pytest.raises(MlDependencyError, match="lstm"):
        create_lstm_forecast()


def test_is_ml_available_returns_bool() -> None:
    assert isinstance(is_ml_available(), bool)
