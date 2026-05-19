"""CLI 接口测试。"""

from datetime import date
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stock_analyzer.application.crawl_service import CrawlResult
from stock_analyzer.interface.cli.main import app

runner = CliRunner()


@patch("stock_analyzer.interface.cli.main.create_crawl_service", new_callable=AsyncMock)
def test_cli_crawl_invokes_service(mock_create: AsyncMock) -> None:
    mock_service = AsyncMock()
    mock_service.crawl_daily.return_value = CrawlResult(
        symbol="600519",
        fetched_count=10,
        persisted_count=10,
    )
    mock_create.return_value = mock_service

    result = runner.invoke(
        app,
        [
            "crawl",
            "--symbols",
            "600519",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-31",
        ],
    )

    assert result.exit_code == 0, result.stdout
    mock_create.assert_awaited_once()
    mock_service.crawl_daily.assert_awaited_once_with(
        "600519",
        date(2024, 1, 1),
        date(2024, 1, 31),
    )
    assert "600519" in result.stdout


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "crawl" in result.stdout
