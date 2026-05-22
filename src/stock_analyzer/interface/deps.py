"""接口层依赖装配：从配置构建服务实例。"""

from stock_analyzer.application.analysis_service import AnalysisService
from stock_analyzer.application.crawl_service import CrawlService
from stock_analyzer.application.predict_service import PredictService
from stock_analyzer.application.visualize_service import VisualizeService
from stock_analyzer.application.watchlist_auto_service import WatchlistAutoService
from stock_analyzer.application.watchlist_store import WatchlistStore
from stock_analyzer.config.database import sqlite_path_from_database_url
from stock_analyzer.config.settings import Settings
from stock_analyzer.domain.forecast.registry import (
    ForecastRegistry,
    create_baseline_registry,
    create_full_registry,
)
from stock_analyzer.infrastructure.concurrency.token_bucket import TokenBucket
from stock_analyzer.infrastructure.persistence.sqlite_repository import SqliteQuoteRepository
from stock_analyzer.infrastructure.sources.akshare_source import AkShareSource
from stock_analyzer.infrastructure.visualization.chart_builder import ChartBuilder


def get_settings() -> Settings:
    return Settings()


def build_repository(settings: Settings | None = None) -> SqliteQuoteRepository:
    cfg = settings or get_settings()
    db_path = sqlite_path_from_database_url(cfg.database_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteQuoteRepository(db_path)


async def init_repository(repo: SqliteQuoteRepository) -> None:
    await repo.initialize()


async def create_crawl_service(settings: Settings | None = None) -> CrawlService:
    cfg = settings or get_settings()
    repo = build_repository(cfg)
    await init_repository(repo)
    limiter = TokenBucket(rate=cfg.crawl_max_qps, capacity=cfg.crawl_burst)
    source = AkShareSource(
        request_timeout=cfg.crawl_request_timeout,
        http_proxy=cfg.http_proxy,
        https_proxy=cfg.https_proxy,
    )
    return CrawlService(source, repo, limiter)


async def create_analysis_service(settings: Settings | None = None) -> AnalysisService:
    repo = build_repository(settings)
    await init_repository(repo)
    return AnalysisService(repo)


def build_forecast_registry(settings: Settings | None = None) -> ForecastRegistry:
    """按配置构建预测策略注册表。"""
    cfg = settings or get_settings()
    if cfg.enable_ml_strategies:
        return create_full_registry(cfg)
    return create_baseline_registry()


async def create_predict_service(
    settings: Settings | None = None,
    registry: ForecastRegistry | None = None,
) -> PredictService:
    cfg = settings or get_settings()
    repo = build_repository(cfg)
    await init_repository(repo)
    return PredictService(repo, registry or build_forecast_registry(cfg))


async def create_visualize_service(settings: Settings | None = None) -> VisualizeService:
    repo = build_repository(settings)
    await init_repository(repo)
    return VisualizeService(repo, ChartBuilder())


async def get_analysis_service() -> AnalysisService:
    """FastAPI 依赖：技术分析服务。"""
    return await create_analysis_service()


async def get_predict_service() -> PredictService:
    """FastAPI 依赖：预测服务。"""
    return await create_predict_service()


async def get_visualize_service() -> VisualizeService:
    """FastAPI 依赖：可视化服务。"""
    return await create_visualize_service()


def parse_watchlist_candidates(raw: str) -> list[str]:
    """解析逗号分隔的候选股票代码。"""
    return [s.strip() for s in raw.split(",") if s.strip()]


async def create_watchlist_auto_service(
    watchlist: WatchlistStore,
    settings: Settings | None = None,
) -> WatchlistAutoService:
    cfg = settings or get_settings()
    repo = build_repository(cfg)
    await init_repository(repo)
    limiter = TokenBucket(rate=cfg.crawl_max_qps, capacity=cfg.crawl_burst)
    source = AkShareSource(
        request_timeout=cfg.crawl_request_timeout,
        http_proxy=cfg.http_proxy,
        https_proxy=cfg.https_proxy,
    )
    crawl = CrawlService(source, repo, limiter)
    analysis = AnalysisService(repo)
    predict = PredictService(repo, build_forecast_registry(cfg))
    return WatchlistAutoService(
        watchlist=watchlist,
        analysis=analysis,
        predict=predict,
        crawl=crawl,
        min_score=cfg.watchlist_auto_min_score,
        max_add=cfg.watchlist_auto_max_add,
    )
