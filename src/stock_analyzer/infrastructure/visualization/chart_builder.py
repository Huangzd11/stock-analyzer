"""Plotly 图表构建器。"""

from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from stock_analyzer.domain.forecast.base import ForecastResult
from stock_analyzer.domain.indicators import calc_ma
from stock_analyzer.domain.models import Quote


class ChartBuilder:
    """生成 K 线 + 均线 + 成交量 HTML 图表。"""

    def build_candlestick(
        self,
        quotes: list[Quote],
        output_path: Path,
        ma_period: int = 20,
        forecast: ForecastResult | None = None,
    ) -> Path:
        if not quotes:
            msg = "行情数据为空，无法绘图"
            raise ValueError(msg)

        ordered = sorted(quotes, key=lambda q: q.trade_date)
        dates = [q.trade_date.isoformat() for q in ordered]
        closes = [float(q.close) for q in ordered]
        ma_values = calc_ma(closes, ma_period)
        ma_dates = [d for d, v in zip(dates, ma_values, strict=True) if v is not None]
        ma_y = [v for v in ma_values if v is not None]

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=("K 线与均线", "成交量"),
        )
        fig.add_trace(
            go.Candlestick(
                x=dates,
                open=[float(q.open) for q in ordered],
                high=[float(q.high) for q in ordered],
                low=[float(q.low) for q in ordered],
                close=closes,
                name="K线",
            ),
            row=1,
            col=1,
        )
        if ma_dates:
            fig.add_trace(
                go.Scatter(
                    x=ma_dates,
                    y=ma_y,
                    mode="lines",
                    name=f"MA{ma_period}",
                    line={"color": "orange", "width": 1.5},
                    connectgaps=False,
                ),
                row=1,
                col=1,
            )
        forecast_dates: list[str] = []
        if forecast is not None:
            forecast_dates = [p.date.isoformat() for p in forecast.points]
            forecast_values = [float(p.value) for p in forecast.points]
            fig.add_trace(
                go.Scatter(
                    x=forecast_dates,
                    y=forecast_values,
                    mode="lines+markers",
                    name=f"预测({forecast.strategy})",
                    line={"color": "purple", "dash": "dot", "width": 2},
                    connectgaps=False,
                ),
                row=1,
                col=1,
            )
        fig.add_trace(
            go.Bar(
                x=dates,
                y=[q.volume for q in ordered],
                name="成交量",
                marker_color="steelblue",
            ),
            row=2,
            col=1,
        )
        last_hist = dates[-1]
        x_end_price = forecast_dates[-1] if forecast_dates else last_hist
        fig.update_layout(
            title=f"{ordered[0].symbol} 行情图（{dates[0]} ~ {last_hist}）",
            xaxis_rangeslider_visible=False,
            template="plotly_white",
        )
        # 价格区可含预测；成交量仅展示历史 K 线区间，避免拉到未来空白
        fig.update_xaxes(range=[dates[0], x_end_price], row=1, col=1)
        fig.update_xaxes(range=[dates[0], last_hist], row=2, col=1)
        fig.update_xaxes(
            rangebreaks=[{"pattern": "day of week", "bounds": ["sat", "mon"]}],
            row=1,
            col=1,
        )
        fig.update_xaxes(
            rangebreaks=[{"pattern": "day of week", "bounds": ["sat", "mon"]}],
            row=2,
            col=1,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_path))
        return output_path
