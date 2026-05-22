"""应用配置：从环境变量与 .env 加载。"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置项。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/stock_analyzer.db",
        description="数据库连接 URL",
    )
    crawl_max_qps: float = Field(default=2.0, ge=0.1, description="爬取全局限流 QPS")
    crawl_burst: int = Field(default=5, ge=1, description="令牌桶突发容量")
    crawl_request_timeout: float = Field(
        default=30.0,
        ge=5.0,
        description="爬取 HTTP 请求超时（秒）",
    )
    http_proxy: str | None = Field(default=None, description="HTTP 代理，如 http://127.0.0.1:7890")
    https_proxy: str | None = Field(
        default=None,
        description="HTTPS 代理，未设置时沿用 http_proxy",
    )
    log_level: str = Field(default="INFO", description="日志级别")
    enable_ml_strategies: bool = Field(
        default=False,
        description="启用深度学习预测策略（需 pip install .[ml]）",
    )
    lstm_lookback: int = Field(default=30, ge=10, le=120, description="LSTM 回看窗口")
    lstm_max_epochs: int = Field(default=100, ge=10, le=500, description="LSTM 最大训练轮次")
    lstm_hidden_size: int = Field(default=64, ge=16, le=256, description="LSTM 隐层大小")
    lstm_patience: int = Field(default=10, ge=3, le=50, description="LSTM 早停耐心值")
    watchlist_path: str = Field(
        default="./data/watchlist.json",
        description="自选股列表 JSON 文件路径",
    )
    realtime_interval_seconds: int = Field(
        default=60,
        ge=10,
        le=3600,
        description="实时爬取默认间隔（秒）",
    )
    realtime_incremental_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="实时爬取增量回溯天数",
    )
