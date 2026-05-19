"""包导入与版本测试。"""

import stock_analyzer
from stock_analyzer import __version__


def test_package_importable() -> None:
    assert stock_analyzer.__version__ == __version__
    assert __version__ == "0.1.0"
