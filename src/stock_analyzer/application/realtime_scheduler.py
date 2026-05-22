"""实时爬取调度：后台周期拉取自选股行情。"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from stock_analyzer.application.crawl_service import CrawlResult, CrawlService


@dataclass
class RealtimeRunSummary:
    """单次调度执行摘要。"""

    run_at: datetime
    results: list[dict[str, Any]] = field(default_factory=list)
    success_count: int = 0
    error_count: int = 0


class RealtimeScheduler:
    """后台周期爬取调度器。"""

    def __init__(
        self,
        crawl_service_factory: Callable[[], Awaitable[CrawlService]],
        incremental_days: int = 7,
    ) -> None:
        self._crawl_service_factory = crawl_service_factory
        self._incremental_days = incremental_days
        self._symbols: list[str] = []
        self._interval_seconds = 60
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._last_summary: RealtimeRunSummary | None = None
        self._lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def symbols(self) -> list[str]:
        return list(self._symbols)

    @property
    def interval_seconds(self) -> int:
        return self._interval_seconds

    @property
    def last_summary(self) -> RealtimeRunSummary | None:
        return self._last_summary

    async def start(self, symbols: list[str], interval_seconds: int) -> None:
        """启动实时爬取循环。"""
        if interval_seconds < 10:
            msg = "interval_seconds 不能小于 10 秒"
            raise ValueError(msg)
        if not symbols:
            msg = "自选股列表不能为空"
            raise ValueError(msg)
        async with self._lock:
            if self._running:
                await self.stop()
            self._symbols = list(symbols)
            self._interval_seconds = interval_seconds
            self._running = True
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """停止实时爬取。"""
        async with self._lock:
            self._running = False
            if self._task is not None:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None

    async def run_once(self, symbols: list[str] | None = None) -> RealtimeRunSummary:
        """立即执行一轮爬取（供手动触发）。"""
        target = symbols if symbols is not None else self._symbols
        if not target:
            msg = "没有可爬取的股票代码"
            raise ValueError(msg)
        summary = await self._execute_round(target)
        self._last_summary = summary
        return summary

    async def _run_loop(self) -> None:
        while self._running:
            try:
                summary = await self._execute_round(self._symbols)
                self._last_summary = summary
            except Exception as exc:  # noqa: BLE001 — 调度循环需吞掉单次失败
                self._last_summary = RealtimeRunSummary(
                    run_at=datetime.now(UTC),
                    results=[{"error": str(exc)}],
                    error_count=1,
                )
            await asyncio.sleep(self._interval_seconds)

    async def _execute_round(self, symbols: list[str]) -> RealtimeRunSummary:
        service = await self._crawl_service_factory()
        today = date.today()
        start = today - timedelta(days=self._incremental_days)
        results: list[dict[str, Any]] = []
        success = 0
        errors = 0
        for symbol in symbols:
            try:
                crawl_result: CrawlResult = await service.crawl_daily(symbol, start, today)
                results.append(
                    {
                        "symbol": crawl_result.symbol,
                        "fetched": crawl_result.fetched_count,
                        "persisted": crawl_result.persisted_count,
                        "status": "ok",
                    }
                )
                success += 1
            except Exception as exc:  # noqa: BLE001
                results.append({"symbol": symbol, "status": "error", "message": str(exc)})
                errors += 1
        return RealtimeRunSummary(
            run_at=datetime.now(UTC),
            results=results,
            success_count=success,
            error_count=errors,
        )

    def status_dict(self) -> dict[str, Any]:
        """供 API / WebSocket 返回的状态快照。"""
        summary = self._last_summary
        return {
            "running": self._running,
            "symbols": self._symbols,
            "interval_seconds": self._interval_seconds,
            "last_run_at": summary.run_at.isoformat() if summary else None,
            "last_results": summary.results if summary else [],
            "success_count": summary.success_count if summary else 0,
            "error_count": summary.error_count if summary else 0,
        }
