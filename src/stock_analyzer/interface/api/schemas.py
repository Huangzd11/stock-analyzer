"""API 请求/响应模型。"""

from pydantic import BaseModel, Field


class WatchlistUpdate(BaseModel):
    symbols: list[str] = Field(..., min_length=1)


class WatchlistSymbol(BaseModel):
    symbol: str = Field(..., min_length=6, max_length=6)


class WatchlistAutoAddBody(BaseModel):
    """自动添加走势/前景较好股票到自选股。"""

    symbols: list[str] | None = Field(
        default=None,
        description="候选代码；为空时使用配置 WATCHLIST_AUTO_CANDIDATES",
    )
    max_add: int | None = Field(default=None, ge=1, le=20)
    strategy: str = Field(default="ma_trend", description="评分所用预测策略")
    min_score: float | None = Field(default=None, ge=0.0, le=100.0)


class CrawlRequestBody(BaseModel):
    symbols: list[str] = Field(..., min_length=1)
    start: str | None = None
    end: str | None = None


class RealtimeStartBody(BaseModel):
    symbols: list[str] | None = None
    interval_seconds: int = Field(default=60, ge=10, le=3600)


class AnalysisQuery(BaseModel):
    start: str | None = None
    end: str | None = None


class ForecastQuery(BaseModel):
    start: str | None = None
    end: str | None = None
    strategy: str = "ma_trend"
    horizon_days: int = Field(default=30, ge=1, le=365)


class ChartRequestBody(BaseModel):
    symbol: str
    start: str | None = None
    end: str | None = None
    strategy: str | None = None
    horizon_days: int = Field(default=30, ge=1, le=365)
    refresh: bool = Field(
        default=True,
        description="生成前是否按区间拉取最新日 K（补齐缺口）",
    )
