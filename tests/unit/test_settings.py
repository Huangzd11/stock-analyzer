"""配置加载测试。"""

import pytest

from stock_analyzer.config import Settings


def test_settings_loads_defaults() -> None:
    settings = Settings()
    assert settings.crawl_max_qps == 2.0
    assert settings.crawl_burst == 5
    assert settings.crawl_request_timeout == 30.0
    assert settings.http_proxy is None
    assert "sqlite" in settings.database_url


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRAWL_MAX_QPS", "10.5")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.local:8080")
    monkeypatch.setenv("CRAWL_REQUEST_TIMEOUT", "60")
    settings = Settings()
    assert settings.crawl_max_qps == 10.5
    assert settings.log_level == "DEBUG"
    assert settings.http_proxy == "http://proxy.local:8080"
    assert settings.crawl_request_timeout == 60.0
