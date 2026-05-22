"""实时调度器单元测试。"""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from stock_analyzer.application.crawl_service import CrawlResult
from stock_analyzer.application.realtime_scheduler import RealtimeScheduler


@pytest.mark.asyncio
async def test_scheduler_run_once_success() -> None:
    mock_service = AsyncMock()
    mock_service.crawl_daily.return_value = CrawlResult(
        symbol="600519",
        fetched_count=5,
        persisted_count=5,
    )

    async def factory() -> AsyncMock:
        return mock_service

    scheduler = RealtimeScheduler(crawl_service_factory=factory, incremental_days=3)
    summary = await scheduler.run_once(["600519"])
    assert summary.success_count == 1
    assert summary.error_count == 0
    mock_service.crawl_daily.assert_called_once()
    start_arg = mock_service.crawl_daily.call_args[0][1]
    assert isinstance(start_arg, date)


@pytest.mark.asyncio
async def test_scheduler_start_requires_interval() -> None:
    scheduler = RealtimeScheduler(crawl_service_factory=AsyncMock())
    with pytest.raises(ValueError, match="10"):
        await scheduler.start(["600519"], 5)


@pytest.mark.asyncio
async def test_scheduler_stop_clears_running() -> None:
    mock_service = AsyncMock()
    mock_service.crawl_daily.return_value = CrawlResult(
        symbol="600519",
        fetched_count=1,
        persisted_count=1,
    )

    async def factory() -> AsyncMock:
        return mock_service

    scheduler = RealtimeScheduler(crawl_service_factory=factory, incremental_days=1)
    await scheduler.start(["600519"], 60)
    assert scheduler.is_running
    await scheduler.stop()
    assert not scheduler.is_running
