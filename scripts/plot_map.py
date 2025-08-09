import pandas as pd
import plotly.express as px
import numpy as np
import plotly.graph_objects as go
from IPython.display import display
import ipywidgets as widgets


def plot_interactive_map(df, ts_df, le_long, parameter, title, y_range=None):
    fig = px.choropleth_map(
        df,
        geojson=df.geometry.__geo_interface__,
        locations=df.index,
        color=parameter,
        hover_name="region_en",
        center={"lat": 48.0, "lon": 67.0},
        zoom=3.0,
        opacity=0.75,
        color_continuous_scale="YlGn",
        labels={parameter: "Scale"},
    )

    fig.update_traces(customdata=np.stack([df["region_en"]], axis=-1))

    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0}, title=title)

    fig_map = go.FigureWidget(fig)

    spark = go.FigureWidget(
        go.Figure(
            data=[
                go.Scatter(
                    x=[],
                    y=[],
                    mode="lines",
                    line={"width": 0},
                    hoverinfo="skip",
                    showlegend=False,
                    name="upper_ci",
                ),
                go.Scatter(
                    x=[],
                    y=[],
                    mode="lines",
                    line={"width": 0},
                    fill="tonexty",
                    fillcolor="rgba(128,128,128,0.25)",
                    hoverinfo="skip",
                    showlegend=False,
                    name="lower_ci",
                ),
                go.Scatter(
                    x=[],
                    y=[],
                    mode="lines",
                    line={"width": 2},
                    showlegend=False,
                    name=parameter,
                ),
            ],
            layout=go.Layout(
                title="Кликни на регион",
                margin=dict(l=30, r=10, t=40, b=30),
                xaxis=dict(title="", showgrid=False, tickformat="%Y-%m", tickangle=0),
                yaxis=dict(title="", showgrid=True, zeroline=False),
                height=300,
                width=520,
            ),
        )
    )

    def _season_color(month: int) -> str:
        if month in (12, 1, 2):
            return "rgba(0,0,255,0.10)"
        if month in (3, 4, 5):
            return "rgba(0,128,0,0.10)"
        if month in (6, 7, 8):
            return "rgba(255,0,0,0.10)"
        return "rgba(255,215,0,0.10)"

    def _monthly_bands(x_start="2017-01-01", x_end="2021-05-31"):
        x0 = pd.Timestamp(x_start).normalize()
        x_end = pd.Timestamp(x_end).normalize()
        shapes = []
        cur = x0
        while cur <= x_end:
            nxt = (cur + pd.offsets.MonthEnd(1)).normalize()
            shapes.append(
                dict(
                    type="rect",
                    xref="x",
                    x0=cur,
                    x1=nxt,
                    yref="paper",
                    y0=0,
                    y1=1,
                    line={"width": 0},
                    layer="below",
                    fillcolor=_season_color(cur.month),
                )
            )
            cur = (cur + pd.offsets.MonthBegin(1)).normalize()
        return shapes

    spark.update_layout(shapes=_monthly_bands("2017-01-01", "2021-05-31"))

    spark.update_xaxes(
        type="date",
        dtick="M1",
        tickformat="%Y.%m",
        range=[pd.Timestamp("2017-01-01"), pd.Timestamp("2021-05-31")],
        tickangle=90,
        showline=True,
        linewidth=1,
        linecolor="black",
        showgrid=False,
        tickfont=dict(size=6),
    )

    spark.update_yaxes(showline=True, linewidth=1, linecolor="black", showgrid=False)

    if y_range is not None:
        spark.update_yaxes(range=y_range)

    spark.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    spark.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(size=10, color="blue"),
            name="Зима",
        )
    )
    spark.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(size=10, color="green"),
            name="Весна",
        )
    )
    spark.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(size=10, color="red"),
            name="Лето",
        )
    )
    spark.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(size=10, color="yellow"),
            name="Осень",
        )
    )

    spark.update_layout(
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            bordercolor="black",
            borderwidth=0.5,
            font=dict(size=10),
        )
    )

    def _compute_ci(series_y: pd.Series, window: int = 3):
        m = series_y.rolling(window=window, min_periods=2, center=True).mean()
        s = series_y.rolling(window=window, min_periods=2, center=True).std(ddof=1)
        ci_up = m + 1.96 * (s.fillna(0))
        ci_lo = m - 1.96 * (s.fillna(0))
        ci_up = ci_up.fillna(series_y + 0.05)
        ci_lo = ci_lo.fillna(series_y - 0.05)
        return ci_lo, ci_up

    table_fig = go.FigureWidget(
        go.Figure(
            data=[
                go.Table(
                    header=dict(
                        values=["<b>Year</b>", "<b>Life Expectancy</b>"],
                        fill_color="white",
                        align="left",
                    ),
                    cells=dict(values=[[], []], align="left"),
                )
            ],
            layout=go.Layout(
                title="Life Expectancy",
                height=220,
                width=520,
                margin=dict(l=20, r=10, t=40, b=10),
            ),
        )
    )

    def _update_le_table(region_en: str):
        sub = le_long[le_long["region_en"] == region_en].copy()
        years = list(range(2017, 2022))
        m = {int(r["year"]): r["life_expectancy"] for _, r in sub.iterrows()}
        vals = [m.get(y, None) for y in years]
        vals_fmt = [
            ("—" if (v is None or pd.isna(v)) else f"{float(v):.1f}") for v in vals
        ]

        with table_fig.batch_update():
            table_fig.data[0].cells.values = [years, vals_fmt]
            table_fig.layout.title = f"Life Expectancy"

    def _on_click(trace, points, state):
        if not points.point_inds:
            return
        idx = points.point_inds[0]

        region_en = trace.customdata[idx][0]
        if region_en not in ts_df or region_en is None:
            return

        series = ts_df[region_en].copy()
        series = series.sort_values("date")
        x_vals = pd.to_datetime(series["date"]).dt.to_pydatetime()
        y_vals = series[parameter].astype(float)

        if {"ci_lower", "ci_upper"}.issubset(series.columns):
            ci_lo = series["ci_lower"].astype(float)
            ci_up = series["ci_upper"].astype(float)
        else:
            ci_lo, ci_up = _compute_ci(y_vals, window=3)

        with spark.batch_update():
            spark.data[0].x = x_vals
            spark.data[0].y = ci_up

            spark.data[1].x = x_vals
            spark.data[1].y = ci_lo

            spark.data[2].x = x_vals
            spark.data[2].y = y_vals

            spark.update_xaxes(
                type="date",
                dtick="M1",
                tickformat="%Y.%m",
                tickangle=90,
                showline=True,
                linewidth=1,
                linecolor="black",
                showgrid=False,
                tickfont=dict(size=6),
                range=[pd.Timestamp("2017-01-01"), pd.Timestamp("2021-05-31")],
            )

            spark.layout.title = f"{region_en}"
            if y_range is not None:
                spark.layout.yaxis.range = list(y_range)
            elif len(series) and y_vals.notna().any():
                ymin = max(y_vals.min() - 0.1, 0)
                ymax = min(y_vals.max() + 0.1, 4)
                spark.layout.yaxis.range = [ymin, ymax]

        _update_le_table(region_en)

    fig_map.data[0].on_click(_on_click)

    right = widgets.VBox([spark, table_fig])
    box = widgets.HBox([fig_map, right])
    display(box)
