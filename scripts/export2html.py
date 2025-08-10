import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

# ---------- config ----------
DATA_DIR = Path("data")
CSV_SURVEY = DATA_DIR / "survey_random.csv"
CSV_LE = DATA_DIR / "LE_2017_2021.csv"
GEOJSON_PATH = Path(
    "geoBoundaries-KAZ-ADM1-all/geoBoundaries-KAZ-ADM1_simplified.geojson"
)
OUT_HTML = Path("docs/interactive_maps_all.html")
OUT_HTML.parent.mkdir(parents=True, exist_ok=True)

# ---------- load data once ----------
df_base = pd.read_csv(CSV_SURVEY)
gdf = gpd.read_file(GEOJSON_PATH)

name_map = {
    "г.Нур-Султан": "Astana",
    "г.Шымкент": "Shymkent",
    "г.Алматы": "Almaty",
    "Алматинская": "Almaty Region",
    "Жамбылская": "Jambyl Region",
    "Западно-Казахстанская": "West Kazakhstan Region",
    "Туркестанская": "Turkistan Region",
    "Южно-Казахстанская": "South Kazakhstan Region",
    "Северо-Казахстанская": "North Kazakhstan Region",
    "Костанайская": "Kostanay Region",
    "Мангистауская": "Mangystau Region",
    "Актюбинская": "Aktobe Region",
    "Акмолинская": "Akmola Region",
    "Атырауская": "Atyrau Region",
    "Восточно-Казахстанская": "East Kazakhstan Region",
    "Павлодарская": "Pavlodar Region",
    "Кызылординская": "Kyzylorda Region",
    "Карагандинская": "Karaganda Region",
}

le_long = (
    pd.read_csv(CSV_LE)
    .melt(
        id_vars=["Region"],
        value_vars=["2017", "2018", "2019", "2020", "2021"],
        var_name="year",
        value_name="life_expectancy",
    )
    .rename(columns={"Region": "region_en"})
)
le_long["year"] = le_long["year"].astype(int)
YEARS = [2017, 2018, 2019, 2020, 2021]


# ---------- helpers ----------
def rolling_ci(series: pd.Series, win: int = 3):
    m = series.rolling(window=win, min_periods=2, center=True).mean()
    s = series.rolling(window=win, min_periods=2, center=True).std(ddof=1)
    up = (m + 1.96 * s.fillna(0)).fillna(series + 0.05)
    lo = (m - 1.96 * s.fillna(0)).fillna(series - 0.05)
    return lo, up


def to_iso(s: pd.Series) -> list[str]:
    return pd.to_datetime(s).dt.strftime("%Y-%m-%dT%H:%M:%S").tolist()


def life_exp_dict(le_df: pd.DataFrame):
    out = {}
    for reg, sub in le_df.groupby("region_en"):
        arr = []
        m = {int(r["year"]): r["life_expectancy"] for _, r in sub.iterrows()}
        for y in YEARS:
            v = m.get(y, None)
            arr.append(None if (v is None or pd.isna(v)) else float(v))
        out[reg] = arr
    return out


LIFE_EXP_ALL = life_exp_dict(le_long)

CENTER = {"lat": 48.0, "lon": 67.0}
ZOOM = 3.5
geojson_fixed = json.loads(gdf.to_json())


def build_one_dashboard(
    df_in: pd.DataFrame,
    *,
    score_col: str,
    question_col: str,
    mapping: dict,
    title: str,
    y_range: list[float],
    slug: str,
):
    df = df_in.copy()
    df[score_col] = df[question_col].map(mapping)

    # aggregate for map
    df_score = (
        df[[score_col, "Область"]]
        .groupby("Область", as_index=False)
        .mean()
        .sort_values(score_col)
    )
    df_score["region_en"] = df_score["Область"].map(name_map)
    merged = gdf.merge(df_score, left_on="shapeName", right_on="region_en", how="left")

    # time series
    df["date"] = pd.to_datetime(dict(year=df["Год"], month=df["Месяц"], day=1))
    ts = (
        df.groupby(["Область", "date"], as_index=False)[score_col]
        .mean()
        .sort_values(["Область", "date"])
    )
    ts["region_en"] = ts["Область"].map(name_map)

    ts_dict = {}
    for reg, sub in ts.groupby("region_en", dropna=False):
        if pd.isna(reg):
            continue
        sub = sub.sort_values("date")
        dates = to_iso(sub["date"])
        vals = sub[score_col].astype(float)
        lo, up = rolling_ci(vals, 3)
        ts_dict[reg] = {
            "dates": dates,
            "values": [None if pd.isna(x) else float(x) for x in vals.tolist()],
            "ci_lower": [None if pd.isna(x) else float(x) for x in lo.tolist()],
            "ci_upper": [None if pd.isna(x) else float(x) for x in up.tolist()],
        }

    shape_to_en = merged.set_index("shapeName")["region_en"].to_dict()

    # ---------- MAP ----------
    map_fig = px.choropleth_mapbox(
        merged,
        geojson=geojson_fixed,
        locations="shapeName",
        featureidkey="properties.shapeName",
        color=score_col,
        hover_name="region_en",
        color_continuous_scale="YlGn",
        mapbox_style="carto-positron",
        center=CENTER,
        zoom=ZOOM,
        opacity=0.75,
    )
    map_fig.update_traces(marker_line_width=0.5, marker_line_color="white")
    map_fig.update_layout(margin=dict(r=0, t=40, l=0, b=0), title=title)

    # ---------- SPARK ----------
    spark_fig = go.Figure(
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
                name=score_col,
            ),
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color="blue"),
                name="Зима",
            ),
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color="green"),
                name="Весна",
            ),
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color="red"),
                name="Лето",
            ),
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color="yellow"),
                name="Осень",
            ),
        ],
        layout=go.Layout(
            title="Кликни на регион",
            margin=dict(l=30, r=10, t=40, b=30),
            xaxis=dict(
                title="",
                showgrid=False,
                tickformat="%Y.%m",
                dtick="M1",
                tickangle=90,
                showline=True,
                linewidth=1,
                linecolor="black",
                tickfont=dict(size=7),
            ),
            yaxis=dict(
                title="",
                showgrid=False,
                zeroline=False,
                showline=True,
                linewidth=1,
                linecolor="black",
                range=y_range,
            ),
            height=300,
            width=520,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                bordercolor="black",
                borderwidth=0.5,
                font=dict(size=10),
            ),
            shapes=[],
        ),
    )

    # ---------- TABLE ----------
    table_fig = go.Figure(
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

    return {
        "slug": slug,
        "map_spec": pio.to_json(map_fig, validate=False),
        "spark_spec": pio.to_json(spark_fig, validate=False),
        "table_spec": pio.to_json(table_fig, validate=False),
        "ts_data": json.dumps(ts_dict, ensure_ascii=False),
        "life_exp": json.dumps(LIFE_EXP_ALL, ensure_ascii=False),
        "years": json.dumps(YEARS),
        "shape_to_en": json.dumps(shape_to_en, ensure_ascii=False),
        "y_range": json.dumps(y_range),
    }


# ---------- build 4 dashboards ----------
dashboards = [
    build_one_dashboard(
        df_base,
        score_col="eco_score",
        question_col="q8. Оцените, пожалуйста, экологическую ситуацию в Вашем населенном пункте",
        mapping={"Плохая": 0, "Удовлетворительная": 1, "Хорошая": 2},
        title="Kazakhstan: Ecology Score by Region (2017–2021)",
        y_range=[0.0, 2.0],
        slug="eco",
    ),
    build_one_dashboard(
        df_base,
        score_col="health_score",
        question_col="q10a. В целом как бы Вы оценили свое здоровье в настоящее время?",
        mapping={
            "Ужасное": 0,
            "Плохое": 1,
            "Удовлетворительное": 2,
            "Хорошее": 3,
            "Прекрасное": 4,
        },
        title="Kazakhstan: Health Score by Region (2017–2021)",
        y_range=[0.0, 4.0],
        slug="health",
    ),
    build_one_dashboard(
        df_base,
        score_col="gov_med_score",
        question_col="q9.1. Оцените, пожалуйста, качество медицинских услуг в государственных медицинских учреждениях (поликлиники, больницы) в Казахстане",
        mapping={"Плохое": 1, "Удовлетворительное": 2, "Хорошее": 3},
        title="Kazakhstan: Government Medicine Score by Region (2017–2021)",
        y_range=[1.0, 3.0],
        slug="govmed",
    ),
    build_one_dashboard(
        df_base,
        score_col="priv_med_score",
        question_col="q9.2. Оцените, пожалуйста, качество медицинских услуг в  частных клиниках в Казахстане",
        mapping={"Плохое": 1, "Удовлетворительное": 2, "Хорошее": 3},
        title="Kazakhstan: Private Medicine Score by Region (2017–2021)",
        y_range=[1.0, 3.0],
        slug="privmed",
    ),
]


# ---------- HTML (layout 1×4) ----------
def block_html(slug: str) -> str:
    return f"""
  <section class="dash">
    <div class="map" id="mapDiv_{slug}"></div>
    <div class="right">
      <div id="sparkDiv_{slug}"></div>
      <div id="tableDiv_{slug}"></div>
    </div>
  </section>
"""


dash_html = "\n".join(block_html(d["slug"]) for d in dashboards)

js_array_items = []
for d in dashboards:
    js_obj = (
        "{"
        f"slug: {json.dumps(d['slug'])}, "
        f"MAP_SPEC: {d['map_spec']}, "
        f"SPARK_SPEC: {d['spark_spec']}, "
        f"TABLE_SPEC: {d['table_spec']}, "
        f"TS_DATA: {d['ts_data']}, "
        f"LIFE_EXP: {d['life_exp']}, "
        f"YEARS: {d['years']}, "
        f"SHAPE_TO_EN: {d['shape_to_en']}, "
        f"YRANGE: {d['y_range']}"
        "}"
    )
    js_array_items.append(js_obj)
dash_js_literal = ",\n  ".join(js_array_items)

page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Interactive Maps (4 Dashboards)</title>
<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
<style>
  body {{ margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background:#fafafa; }}
  /* 1 колонка, 4 строки */
  .grid {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
    padding: 12px;
  }}
  .dash {{ display:flex; gap:10px; padding:10px; background:#fff; border-radius:12px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .map {{ flex:1; min-height:600px; }}
  .right {{ width:560px; display:flex; flex-direction:column; gap:8px; }}
  .title {{ padding: 8px 14px; font-weight:600; color:#333; }}
</style>
</head>
<body>

<div class="title">Kazakhstan: Four Interactive Dashboards (2017–2021)</div>
<div class="grid">
{dash_html}
</div>

<script>
function parseMaybe(x) {{
  if (typeof x === 'string') {{ try {{ return JSON.parse(x); }} catch (e) {{ return null; }} }}
  return x;
}}
function seasonColor(m) {{
  if (m===12 || m===1 || m===2) return "rgba(0,0,255,0.10)";
  if (m===3 || m===4 || m===5) return "rgba(0,128,0,0.10)";
  if (m===6 || m===7 || m===8) return "rgba(255,0,0,0.10)";
  return "rgba(255,215,0,0.10)";
}}
function monthlyBands(xStart, xEnd) {{
  const shapes = [];
  let cur = new Date(xStart), end = new Date(xEnd);
  while (cur <= end) {{
    const m = cur.getMonth()+1;
    const x0 = new Date(cur.getFullYear(), cur.getMonth(), 1).toISOString().slice(0,10);
    const x1 = new Date(cur.getFullYear(), cur.getMonth()+1, 1).toISOString().slice(0,10);
    shapes.push({{ type:"rect", xref:"x", x0, x1, yref:"paper", y0:0, y1:1, line:{{width:0}}, layer:"below", fillcolor:seasonColor(m) }});
    cur = new Date(cur.getFullYear(), cur.getMonth()+1, 1);
  }}
  return shapes;
}}
function fmtVal(v) {{ return (v==null || Number.isNaN(v)) ? "—" : Number(v).toFixed(1); }}

const DASHES = [
  {dash_js_literal}
];

document.addEventListener('DOMContentLoaded', () => {{
  for (const D_raw of DASHES) {{
    const D = {{}};
    D.slug = D_raw.slug;
    D.MAP_SPEC   = parseMaybe(D_raw.MAP_SPEC);
    D.SPARK_SPEC = parseMaybe(D_raw.SPARK_SPEC);
    D.TABLE_SPEC = parseMaybe(D_raw.TABLE_SPEC);
    D.TS_DATA    = parseMaybe(D_raw.TS_DATA);
    D.LIFE_EXP   = parseMaybe(D_raw.LIFE_EXP);
    D.YEARS      = parseMaybe(D_raw.YEARS);
    D.SHAPE_TO_EN= parseMaybe(D_raw.SHAPE_TO_EN);
    D.YRANGE     = parseMaybe(D_raw.YRANGE);

    Plotly.newPlot("mapDiv_"+D.slug,   D.MAP_SPEC.data,   D.MAP_SPEC.layout,   {{responsive:true}});
    Plotly.newPlot("sparkDiv_"+D.slug, D.SPARK_SPEC.data, D.SPARK_SPEC.layout, {{displayModeBar:false, responsive:true}});
    Plotly.newPlot("tableDiv_"+D.slug, D.TABLE_SPEC.data, D.TABLE_SPEC.layout, {{displayModeBar:false, responsive:true}});

    Plotly.relayout("sparkDiv_"+D.slug, {{
      "shapes": monthlyBands("2017-01-01","2021-05-31"),
      "yaxis.range": D.YRANGE
    }});

    document.getElementById("mapDiv_"+D.slug).on("plotly_click", function(evt) {{
      if (!evt.points || !evt.points.length) return;
      const shapeName = evt.points[0].location;
      const regionEn  = (D.SHAPE_TO_EN && D.SHAPE_TO_EN[shapeName]) ? D.SHAPE_TO_EN[shapeName] : shapeName;
      if (!D.TS_DATA || !(regionEn in D.TS_DATA)) return;

      const ts = D.TS_DATA[regionEn];
      Plotly.update("sparkDiv_"+D.slug,
        {{ x:[ts.dates, ts.dates, ts.dates], y:[ts.ci_upper, ts.ci_lower, ts.values] }},
        {{}}, [0,1,2]
      );
      Plotly.relayout("sparkDiv_"+D.slug, {{"yaxis.range": D.YRANGE, "title.text": regionEn}});

      const le = (D.LIFE_EXP && (regionEn in D.LIFE_EXP)) ? D.LIFE_EXP[regionEn] : new Array(D.YEARS.length).fill(null);
      Plotly.restyle("tableDiv_"+D.slug, {{"cells.values": [[D.YEARS, le.map(fmtVal)]]}}, [0]);
    }});
  }}
}});
</script>
</body>
</html>
"""

OUT_HTML.write_text(page, encoding="utf-8")
print(f"Saved: {OUT_HTML.resolve()}")
