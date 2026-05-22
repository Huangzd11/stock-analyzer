"""FastAPI 应用入口：API + Web 控制台。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from stock_analyzer.application.realtime_scheduler import RealtimeScheduler
from stock_analyzer.application.watchlist_store import WatchlistStore
from stock_analyzer.config.settings import Settings
from stock_analyzer.interface.api.routes import router as api_router
from stock_analyzer.interface.deps import create_crawl_service, get_settings

STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：初始化调度器与自选股存储。"""
    settings: Settings = app.state.settings
    watchlist_path = Path(settings.watchlist_path)
    app.state.watchlist = WatchlistStore(watchlist_path)
    app.state.scheduler = RealtimeScheduler(
        crawl_service_factory=create_crawl_service,
        incremental_days=settings.realtime_incremental_days,
    )
    yield
    await app.state.scheduler.stop()


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()
    application = FastAPI(
        title="Stock Analyzer",
        version="0.2.0",
        description="A 股实时爬取、分析与预测 Web 平台（学习研究用途）",
        lifespan=lifespan,
    )
    application.state.settings = cfg
    application.include_router(api_router)
    if STATIC_DIR.is_dir():
        application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @application.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
