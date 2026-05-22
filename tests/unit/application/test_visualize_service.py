"""可视化服务单元测试。"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from stock_analyzer.application.visualize_service import VisualizeService
from stock_analyzer.domain.models import Quote


@pytest.mark.asyncio
async def test_render_chart_refresh_calls_crawl(tmp_path: Path) -> None:
    repo = AsyncMock()
    repo.get_quotes.return_value = [
        Quote(
            symbol="600519",
            trade_date=date(2024, 6, 1),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=1000,
        )
    ]
    crawl = AsyncMock()
    builder = MagicMock()
    builder.build_candlestick.return_value = tmp_path / "out.html"

    svc = VisualizeService(repo, chart_builder=builder)
    await svc.render_chart(
        "600519",
        date(2024, 1, 1),
        date(2024, 6, 1),
        tmp_path / "out.html",
        refresh=True,
        crawl_service=crawl,
    )
    crawl.crawl_daily.assert_awaited_once_with("600519", date(2024, 1, 1), date(2024, 6, 1))
    builder.build_candlestick.assert_called_once()
