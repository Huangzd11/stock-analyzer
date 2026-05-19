"""配置加载测试。"""

import pytest

from stock_analyzer.config import Settings


def test_settings_loads_defaults() -> None:
    settings = Settings()
    assert settings.crawl_max_qps == 2.0
    assert settings.crawl_burst == 5
    assert "sqlite" in settings.database_url


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRAWL_MAX_QPS", "10.5")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    settings = Settings()
    assert settings.crawl_max_qps == 10.5
    assert settings.log_level == "DEBUG"
