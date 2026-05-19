"""爬取编排：限流 → 拉取 → 入库。"""

import asyncio
from dataclasses import dataclass
from datetime import date

from stock_analyzer.infrastructure.concurrency.fair_queue import FairQueue, FairTask
from stock_analyzer.infrastructure.concurrency.token_bucket import TokenBucket
from stock_analyzer.ports.quote_source import IQuoteSource
from stock_analyzer.ports.rate_limiter import IRateLimiter
from stock_analyzer.ports.repository import IQuoteRepository


@dataclass(frozen=True)
class CrawlRequest:
    """单只股票爬取请求。"""

    symbol: str
    start: date
    end: date
    tenant_id: str = "default"


@dataclass(frozen=True)
class CrawlResult:
    """爬取结果摘要。"""

    symbol: str
    fetched_count: int
    persisted_count: int


class CrawlService:
    """爬取用例服务。"""

    def __init__(
        self,
        source: IQuoteSource,
        repository: IQuoteRepository,
        rate_limiter: IRateLimiter,
    ) -> None:
        self._source = source
        self._repository = repository
        self._rate_limiter = rate_limiter

    async def crawl_daily(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> CrawlResult:
        """爬取单只股票日 K 并入库。"""
        if start > end:
            msg = f"start ({start}) 不能晚于 end ({end})"
            raise ValueError(msg)
        await self._acquire_token()
        quotes = await self._source.fetch_daily(symbol, start, end)
        persisted = await self._repository.upsert_quotes(quotes)
        return CrawlResult(
            symbol=symbol,
            fetched_count=len(quotes),
            persisted_count=persisted,
        )

    async def crawl_batch(self, requests: list[CrawlRequest]) -> list[CrawlResult]:
        """按公平队列调度多只股票爬取。"""
        if not requests:
            return []
        queue: FairQueue[CrawlRequest] = FairQueue()
        for req in requests:
            queue.enqueue(FairTask(tenant_id=req.tenant_id, payload=req))
        results: list[CrawlResult] = []
        for _ in range(len(requests)):
            task = queue.dequeue()
            if task is None:
                break
            req = task.payload
            result = await self.crawl_daily(req.symbol, req.start, req.end)
            results.append(result)
        return results

    async def _acquire_token(self) -> None:
        if isinstance(self._rate_limiter, TokenBucket):
            await self._rate_limiter.acquire_async()
            return
        while not self._rate_limiter.try_acquire():
            await asyncio.sleep(0.05)
