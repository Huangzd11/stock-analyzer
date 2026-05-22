"""ML 可选依赖检测。"""

_ML_INSTALL_HINT = "请安装 ML 可选依赖: pip install -e '.[ml]'"


class MlDependencyError(ImportError):
    """未安装 PyTorch 等 ML 依赖时抛出。"""

    def __init__(self, strategy: str = "lstm") -> None:
        msg = f"策略 '{strategy}' 需要深度学习依赖。{_ML_INSTALL_HINT}"
        super().__init__(msg)
        self.strategy = strategy


def is_ml_available() -> bool:
    """检测 PyTorch 是否可用。"""
    try:
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


def require_ml(strategy: str = "lstm") -> None:
    """未安装 ML 依赖时抛出明确错误。"""
    if not is_ml_available():
        raise MlDependencyError(strategy)
