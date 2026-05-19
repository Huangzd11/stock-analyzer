"""FastAPI 应用入口。"""

from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query

from stock_analyzer.application.analysis_service import AnalysisService
from stock_analyzer.application.predict_service import PredictService
from stock_analyzer.domain.analysis import AnalysisResult
from stock_analyzer.domain.forecast.base import ForecastResult
from stock_analyzer.interface.deps import create_analysis_service, create_predict_service

app = FastAPI(
    title="Stock Analyzer API",
    version="0.1.0",
    description="A 股数据分析 API（学习研究用途）",
)


async def get_analysis_service() -> AnalysisService:
    return await create_analysis_service()


async def get_predict_service() -> PredictService:
    return await create_predict_service()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/analysis/{symbol}", response_model=AnalysisResult)
async def get_analysis(
    symbol: str,
    start: date = Query(..., description="开始日期"),
    end: date = Query(..., description="结束日期"),
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResult:
    try:
        return await service.analyze(symbol, start, end)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/forecast/{symbol}", response_model=ForecastResult)
async def get_forecast(
    symbol: str,
    start: date = Query(...),
    end: date = Query(...),
    strategy: str = Query("ma_trend", description="预测策略"),
    horizon_days: int = Query(30, ge=1, le=365),
    service: PredictService = Depends(get_predict_service),
) -> ForecastResult:
    try:
        return await service.predict(symbol, start, end, strategy, horizon_days)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
