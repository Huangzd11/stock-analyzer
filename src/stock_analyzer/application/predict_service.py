"""走势预测用例服务。"""

from datetime import date

from stock_analyzer.domain.forecast.base import ForecastResult
from stock_analyzer.domain.forecast.registry import ForecastRegistry
from stock_analyzer.ports.repository import IQuoteRepository


class PredictService:
    """从仓储读取行情并执行预测策略。"""

    def __init__(
        self,
        repository: IQuoteRepository,
        registry: ForecastRegistry,
    ) -> None:
        self._repository = repository
        self._registry = registry

    async def predict(
        self,
        symbol: str,
        start: date,
        end: date,
        strategy_name: str,
        horizon_days: int = 30,
    ) -> ForecastResult:
        quotes = await self._repository.get_quotes(symbol, start, end)
        if not quotes:
            msg = f"无行情数据: {symbol}"
            raise ValueError(msg)
        strategy = self._registry.get(strategy_name)
        return strategy.predict(quotes, horizon_days)
