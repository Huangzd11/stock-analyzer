"""REST API 路由。"""

import asyncio
from datetime import date, timedelta
from pathlib import Path
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from stock_analyzer.application.analysis_service import AnalysisService
from stock_analyzer.application.crawl_service import CrawlRequest
from stock_analyzer.application.predict_service import PredictService
from stock_analyzer.application.realtime_scheduler import RealtimeScheduler
from stock_analyzer.application.watchlist_store import WatchlistStore
from stock_analyzer.domain.analysis import AnalysisResult
from stock_analyzer.domain.forecast.base import ForecastResult
from stock_analyzer.infrastructure.persistence.sqlite_repository import SqliteQuoteRepository
from stock_analyzer.interface.api.schemas import (
    ChartRequestBody,
    CrawlRequestBody,
    RealtimeStartBody,
    WatchlistSymbol,
    WatchlistUpdate,
)
from stock_analyzer.interface.deps import (
    build_forecast_registry,
    build_repository,
    create_crawl_service,
    create_predict_service,
    get_analysis_service,
    get_predict_service,
    get_settings,
    get_visualize_service,
    init_repository,
)

router = APIRouter(prefix="/api/v1")


def _parse_date(value: str | None, default: date) -> date:
    if value is None:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"日期格式无效: {value}") from exc


def get_scheduler(request: Request) -> RealtimeScheduler:
    return cast(RealtimeScheduler, request.app.state.scheduler)


def get_watchlist(request: Request) -> WatchlistStore:
    return cast(WatchlistStore, request.app.state.watchlist)


async def get_repository() -> SqliteQuoteRepository:
    repo = build_repository()
    await init_repository(repo)
    return repo


@router.get("/strategies")
async def list_strategies() -> dict[str, list[str]]:
    registry = build_forecast_registry(get_settings())
    return {"all": registry.list_names(), "baseline": registry.list_baseline_names()}


@router.get("/watchlist")
async def get_watchlist_symbols(
    store: WatchlistStore = Depends(get_watchlist),
) -> dict[str, list[str]]:
    return {"symbols": store.list_symbols()}


@router.put("/watchlist")
async def update_watchlist(
    body: WatchlistUpdate,
    store: WatchlistStore = Depends(get_watchlist),
) -> dict[str, list[str]]:
    try:
        return {"symbols": store.set_symbols(body.symbols)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/watchlist")
async def add_watchlist_symbol(
    body: WatchlistSymbol,
    store: WatchlistStore = Depends(get_watchlist),
) -> dict[str, list[str]]:
    try:
        return {"symbols": store.add_symbol(body.symbol)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/watchlist/{symbol}")
async def remove_watchlist_symbol(
    symbol: str,
    store: WatchlistStore = Depends(get_watchlist),
) -> dict[str, list[str]]:
    return {"symbols": store.remove_symbol(symbol)}


@router.post("/crawl")
async def crawl_symbols(body: CrawlRequestBody) -> dict[str, object]:
    end_date = _parse_date(body.end, date.today())
    start_date = _parse_date(body.start, end_date - timedelta(days=90))
    service = await create_crawl_service()
    batch = [CrawlRequest(symbol=s, start=start_date, end=end_date) for s in body.symbols]
    results = await service.crawl_batch(batch)
    return {
        "results": [
            {"symbol": r.symbol, "fetched": r.fetched_count, "persisted": r.persisted_count}
            for r in results
        ]
    }


@router.get("/realtime/status")
async def realtime_status(
    scheduler: RealtimeScheduler = Depends(get_scheduler),
) -> dict[str, object]:
    return scheduler.status_dict()


@router.post("/realtime/start")
async def realtime_start(
    body: RealtimeStartBody,
    scheduler: RealtimeScheduler = Depends(get_scheduler),
    store: WatchlistStore = Depends(get_watchlist),
) -> dict[str, object]:
    symbols = body.symbols or store.list_symbols()
    if not symbols:
        raise HTTPException(status_code=400, detail="请先添加自选股")
    try:
        await scheduler.start(symbols, body.interval_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return scheduler.status_dict()


@router.post("/realtime/stop")
async def realtime_stop(scheduler: RealtimeScheduler = Depends(get_scheduler)) -> dict[str, object]:
    await scheduler.stop()
    return scheduler.status_dict()


@router.post("/realtime/run-once")
async def realtime_run_once(
    body: RealtimeStartBody,
    scheduler: RealtimeScheduler = Depends(get_scheduler),
    store: WatchlistStore = Depends(get_watchlist),
) -> dict[str, object]:
    symbols = body.symbols or store.list_symbols()
    if not symbols:
        raise HTTPException(status_code=400, detail="请先添加自选股")
    try:
        summary = await scheduler.run_once(symbols)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "run_at": summary.run_at.isoformat(),
        "success_count": summary.success_count,
        "error_count": summary.error_count,
        "results": summary.results,
    }


@router.get("/quotes/{symbol}")
async def get_quotes(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    repo: SqliteQuoteRepository = Depends(get_repository),
) -> dict[str, object]:
    end_date = _parse_date(end, date.today())
    start_date = _parse_date(start, end_date - timedelta(days=90))
    quotes = await repo.get_quotes(symbol, start_date, end_date)
    return {
        "symbol": symbol,
        "count": len(quotes),
        "quotes": [
            {"trade_date": q.trade_date.isoformat(), "close": str(q.close), "volume": q.volume}
            for q in quotes
        ],
    }


@router.get("/analysis/{symbol}", response_model=AnalysisResult)
async def get_analysis(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResult:
    end_date = _parse_date(end, date.today())
    start_date = _parse_date(start, end_date - timedelta(days=90))
    try:
        return await service.analyze(symbol, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/forecast/{symbol}", response_model=ForecastResult)
async def get_forecast(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    strategy: str = "ma_trend",
    horizon_days: int = 30,
    service: PredictService = Depends(get_predict_service),
) -> ForecastResult:
    end_date = _parse_date(end, date.today())
    start_date = _parse_date(start, end_date - timedelta(days=120))
    try:
        return await service.predict(symbol, start_date, end_date, strategy, horizon_days)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/chart")
async def create_chart(body: ChartRequestBody) -> FileResponse:
    end_date = min(_parse_date(body.end, date.today()), date.today())
    start_date = _parse_date(body.start, end_date - timedelta(days=120))
    output_path = Path("./output/web") / f"{body.symbol}.html"
    crawl_svc = await create_crawl_service() if body.refresh else None
    forecast = None
    if body.strategy:
        predict_svc = await create_predict_service()
        forecast = await predict_svc.predict(
            body.symbol,
            start_date,
            end_date,
            body.strategy,
            body.horizon_days,
        )
    viz = await get_visualize_service()
    path = await viz.render_chart(
        body.symbol,
        start_date,
        end_date,
        output_path,
        forecast=forecast,
        refresh=body.refresh,
        crawl_service=crawl_svc,
    )
    return FileResponse(path, media_type="text/html", filename=path.name)


@router.websocket("/ws/realtime")
async def realtime_ws(websocket: WebSocket) -> None:
    """WebSocket 推送实时爬取状态（每 2 秒）。"""
    scheduler: RealtimeScheduler = websocket.app.state.scheduler
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(scheduler.status_dict())
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
