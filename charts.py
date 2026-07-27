from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def price_chart(
    data: pd.DataFrame,
    asset_name: str,
    score: int,
    support: float | None = None,
    resistance: float | None = None,
    rows: int = 180,
) -> go.Figure:
    chart_data = data.tail(rows)
    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=chart_data.index,
            open=chart_data["Open"],
            high=chart_data["High"],
            low=chart_data["Low"],
            close=chart_data["Close"],
            name="Prezzo",
        )
    )
    fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data["EMA20"], mode="lines", name="EMA 20"))
    fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data["EMA50"], mode="lines", name="EMA 50"))
    fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data["EMA200"], mode="lines", name="EMA 200"))

    if support is not None:
        fig.add_hline(y=support, line_dash="dot", annotation_text="Supporto")
    if resistance is not None:
        fig.add_hline(y=resistance, line_dash="dot", annotation_text="Resistenza")

    fig.update_layout(
        title=f"{asset_name} · Struttura {score}/100",
        xaxis_title="Data",
        yaxis_title="Prezzo",
        xaxis_rangeslider_visible=False,
        height=560,
        margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(orientation="h"),
    )
    return fig


def rsi_chart(data: pd.DataFrame, asset_name: str, rows: int = 180) -> go.Figure:
    chart_data = data.tail(rows)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=chart_data.index,
            y=chart_data["RSI"],
            mode="lines",
            name="RSI 14",
        )
    )
    fig.add_hline(y=70, line_dash="dash")
    fig.add_hline(y=30, line_dash="dash")
    fig.update_layout(
        title=f"RSI · {asset_name}",
        yaxis_range=[0, 100],
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig
