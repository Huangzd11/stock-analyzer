"""可视化用例服务。"""

from datetime import date
from pathlib import Path

from stock_analyzer.domain.forecast.base import ForecastResult
from stock_analyzer.infrastructure.visualization.chart_builder import ChartBuilder
from stock_analyzer.ports.repository import IQuoteRepository


class VisualizeService:
    """从仓储读取行情并生成图表文件。"""

    def __init__(
        self,
        repository: IQuoteRepository,
        chart_builder: ChartBuilder | None = None,
    ) -> None:
        self._repository = repository
        self._chart_builder = chart_builder or ChartBuilder()

    async def render_chart(
        self,
        symbol: str,
        start: date,
        end: date,
        output_path: Path,
        ma_period: int = 20,
        forecast: ForecastResult | None = None,
    ) -> Path:
        quotes = await self._repository.get_quotes(symbol, start, end)
        if not quotes:
            msg = f"无行情数据: {symbol}"
            raise ValueError(msg)
        return self._chart_builder.build_candlestick(
            quotes,
            output_path,
            ma_period=ma_period,
            forecast=forecast,
        )
