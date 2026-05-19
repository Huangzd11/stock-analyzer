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
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=ma_values,
                mode="lines",
                name=f"MA{ma_period}",
                line={"color": "orange"},
            ),
            row=1,
            col=1,
        )
        if forecast is not None:
            forecast_dates = [p.date.isoformat() for p in forecast.points]
            forecast_values = [float(p.value) for p in forecast.points]
            fig.add_trace(
                go.Scatter(
                    x=forecast_dates,
                    y=forecast_values,
                    mode="lines+markers",
                    name=f"预测({forecast.strategy})",
                    line={"color": "purple", "dash": "dot"},
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
        fig.update_layout(
            title=f"{ordered[0].symbol} 行情图",
            xaxis_rangeslider_visible=False,
            template="plotly_white",
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_path))
        return output_path
