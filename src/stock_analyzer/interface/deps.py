"""接口层依赖装配：从配置构建服务实例。"""

from stock_analyzer.application.analysis_service import AnalysisService
from stock_analyzer.application.crawl_service import CrawlService
from stock_analyzer.application.predict_service import PredictService
from stock_analyzer.application.visualize_service import VisualizeService
from stock_analyzer.config.database import sqlite_path_from_database_url
from stock_analyzer.config.settings import Settings
from stock_analyzer.domain.forecast.registry import ForecastRegistry, create_baseline_registry
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
    return CrawlService(AkShareSource(), repo, limiter)


async def create_analysis_service(settings: Settings | None = None) -> AnalysisService:
    repo = build_repository(settings)
    await init_repository(repo)
    return AnalysisService(repo)


async def create_predict_service(
    settings: Settings | None = None,
    registry: ForecastRegistry | None = None,
) -> PredictService:
    repo = build_repository(settings)
    await init_repository(repo)
    return PredictService(repo, registry or create_baseline_registry())


async def create_visualize_service(settings: Settings | None = None) -> VisualizeService:
    repo = build_repository(settings)
    await init_repository(repo)
    return VisualizeService(repo, ChartBuilder())
