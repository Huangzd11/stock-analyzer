"""CLI 主入口。"""

import asyncio
import json
from datetime import date, timedelta
from pathlib import Path

import typer

from stock_analyzer import __version__
from stock_analyzer.interface.deps import (
    create_analysis_service,
    create_crawl_service,
    create_predict_service,
    create_visualize_service,
)

app = typer.Typer(
    name="stock-analyzer",
    help="股票数据采集、分析、预测与可视化",
    no_args_is_help=True,
)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        msg = f"日期格式无效: {value}，请使用 YYYY-MM-DD"
        raise typer.BadParameter(msg) from exc


def _parse_symbols(value: str) -> list[str]:
    symbols = [s.strip() for s in value.split(",") if s.strip()]
    if not symbols:
        raise typer.BadParameter("至少提供一个股票代码")
    return symbols


def _echo_json(data: object) -> None:
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2, default=str))


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="显示版本号",
    ),
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command("crawl")
def crawl(
    symbols: str = typer.Option(..., "--symbols", "-s", help="股票代码，逗号分隔"),
    start: str = typer.Option(..., "--start", help="开始日期 YYYY-MM-DD"),
    end: str | None = typer.Option(None, "--end", help="结束日期，默认今天"),
) -> None:
    """爬取日 K 并写入本地数据库。"""
    start_date = _parse_date(start)
    end_date = _parse_date(end) if end else date.today()
    if start_date > end_date:
        raise typer.BadParameter("start 不能晚于 end")

    async def _run() -> None:
        service = await create_crawl_service()
        results = []
        for symbol in _parse_symbols(symbols):
            result = await service.crawl_daily(symbol, start_date, end_date)
            results.append(
                {
                    "symbol": result.symbol,
                    "fetched": result.fetched_count,
                    "persisted": result.persisted_count,
                }
            )
        _echo_json({"results": results})

    asyncio.run(_run())


@app.command("analyze")
def analyze(
    symbol: str = typer.Option(..., "--symbol", help="6 位股票代码"),
    start: str | None = typer.Option(None, "--start", help="开始日期，默认 90 天前"),
    end: str | None = typer.Option(None, "--end", help="结束日期，默认今天"),
) -> None:
    """对已入库股票做技术分析。"""
    end_date = _parse_date(end) if end else date.today()
    start_date = _parse_date(start) if start else end_date - timedelta(days=90)

    async def _run() -> None:
        service = await create_analysis_service()
        result = await service.analyze(symbol, start_date, end_date)
        _echo_json(result.model_dump(mode="json"))

    asyncio.run(_run())


@app.command("predict")
def predict(
    symbol: str = typer.Option(..., "--symbol", help="6 位股票代码"),
    strategy: str = typer.Option("ma_trend", "--strategy", help="预测策略"),
    days: int = typer.Option(30, "--days", min=1, help="预测天数"),
    start: str | None = typer.Option(None, "--start", help="历史数据开始日期"),
    end: str | None = typer.Option(None, "--end", help="历史数据结束日期"),
) -> None:
    """基于历史行情进行走势预测。"""
    end_date = _parse_date(end) if end else date.today()
    start_date = _parse_date(start) if start else end_date - timedelta(days=120)

    async def _run() -> None:
        service = await create_predict_service()
        try:
            result = await service.predict(symbol, start_date, end_date, strategy, days)
        except KeyError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        _echo_json(result.model_dump(mode="json"))

    asyncio.run(_run())


@app.command("chart")
def chart(
    symbol: str = typer.Option(..., "--symbol", help="6 位股票代码"),
    output: Path = typer.Option(
        Path("./output/chart.html"),
        "--output",
        "-o",
        help="输出 HTML 路径",
    ),
    strategy: str | None = typer.Option(
        None,
        "--strategy",
        help="可选：叠加预测策略",
    ),
    days: int = typer.Option(30, "--days", min=1, help="预测天数"),
    start: str | None = typer.Option(None, "--start"),
    end: str | None = typer.Option(None, "--end"),
) -> None:
    """生成 K 线 + 均线 (+ 可选预测) HTML 图表。"""
    end_date = _parse_date(end) if end else date.today()
    start_date = _parse_date(start) if start else end_date - timedelta(days=120)

    async def _run() -> None:
        forecast = None
        if strategy:
            predict_svc = await create_predict_service()
            forecast = await predict_svc.predict(symbol, start_date, end_date, strategy, days)
        viz = await create_visualize_service()
        path = await viz.render_chart(
            symbol,
            start_date,
            end_date,
            output,
            forecast=forecast,
        )
        _echo_json({"output": str(path.resolve())})

    asyncio.run(_run())


if __name__ == "__main__":
    app()
