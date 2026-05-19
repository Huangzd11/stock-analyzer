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
    log_level: str = Field(default="INFO", description="日志级别")
