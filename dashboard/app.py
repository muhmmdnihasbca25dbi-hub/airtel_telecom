"""Network Usage dashboard - Airtel Telecom Analytics, Domain C.

Run:  streamlit run app.py
Put the .streamlit/config.toml file next to this app (light theme, upload size).
First screen asks for the project's SQLite database (.db). The dashboard is
built only after the file is uploaded.
"""
import sqlite3
import tempfile

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================ 1. SETTINGS
T3_P_VALUE = None  # paste the one-tailed p-value from Step 4 T3, e.g. 0.0004
OFFER_START, OFFER_END = "2025-05-01", "2025-06-30"

INK = "#111827"  # all chart text is this near-black
NAVY, GOLD, SLATE = "#14213D", "#C8A24A", "#8D99AE"
GROUP_COLORS = {"A": SLATE, "B": NAVY}

REQUIRED_OBJECTS = {"customer_features", "usage_daily", "v_usage_month"}
PROVENANCE = ("Data provenance: circle and plan structures are real; "
              "subscriber-level records are synthetic.")

# Visual heights in pixels. Every visual has an explicit height.
# The height includes the HTML panel title (TITLE_H) drawn above each chart.
HERO_ROW_H, BOTTOM_ROW_H, DETAIL_TABLE_H = 260, 310, 190
TITLE_H = 46  # must match .panel-title height in the CSS

st.set_page_config(page_title="Network Usage Dashboard", layout="wide",
                   initial_sidebar_state="expanded")

CSS = """
<style>
.stApp {background:#F6F7FA;}
[data-testid="stHeader"] {display:none;}
.block-container {padding:0.9rem 1.4rem 0.2rem 1.4rem; max-width:100%;}
[data-testid="stVerticalBlock"] {gap:0.55rem;}

/* text is always dark, even when the browser is in dark mode */
.stApp, .stApp p, .stApp label, .stApp li {color:#111827;}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {color:#374151 !important;}
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] * {color:#111827 !important; font-weight:600;}

/* sidebar */
[data-testid="stSidebar"] {background:#EAEEF4; border-right:1px solid #D9DEE7;
    min-width:230px !important; max-width:230px !important;}
[data-testid="stSidebar"] h3 {color:#14213D !important; font-size:1.05rem;}
[data-testid="stSidebar"] button {background:#14213D; border:0;}
[data-testid="stSidebar"] button, [data-testid="stSidebar"] button * {color:#FFFFFF !important;}

/* inputs: select box and its option list, light on dark text */
div[data-baseweb="select"] > div {background:#FFFFFF !important; border:1px solid #CBD2DE !important;}
div[data-baseweb="select"] div, div[data-baseweb="select"] span,
div[data-baseweb="select"] input {color:#111827 !important; -webkit-text-fill-color:#111827 !important;}
div[data-baseweb="select"] svg {fill:#111827 !important;}
div[data-baseweb="popover"], div[data-baseweb="popover"] ul,
ul[role="listbox"] {background:#FFFFFF !important;}
li[role="option"] {background:#FFFFFF !important;}
li[role="option"] * {background:transparent !important; color:#111827 !important;}
li[role="option"]:hover, li[role="option"][aria-selected="true"] {background:#E8ECF3 !important;}
[data-testid="stFileUploaderDropzone"] {background:#FFFFFF !important; border:1px dashed #9CA3AF;}
[data-testid="stFileUploaderDropzone"] * {color:#111827 !important;}
[data-testid="stFileUploaderDropzone"] button {background:#14213D; border:0;}
[data-testid="stFileUploaderDropzone"] button * {color:#FFFFFF !important;}

/* tabs */
button[data-baseweb="tab"] {font-weight:600; color:#4B5563;}
button[data-baseweb="tab"][aria-selected="true"], button[data-baseweb="tab"][aria-selected="true"] * {color:#14213D !important;}
[data-baseweb="tab-highlight"] {background-color:#C8A24A !important; height:3px;}
[data-baseweb="tab-border"] {background-color:#D9DEE7 !important;}

/* header */
.app-head {border-bottom:2px solid #C8A24A; padding-bottom:5px;}
.app-row {display:flex; align-items:baseline; gap:12px;}
.app-title {font-size:1.5rem; font-weight:700; color:#14213D; line-height:1.25;}
.app-sub {font-size:0.78rem; color:#4B5563; letter-spacing:0.03em;}
.app-chip {margin-left:auto; font-size:0.74rem; color:#14213D; background:#E8ECF3;
    border-radius:12px; padding:2px 12px;}
.app-reader {font-size:0.85rem; color:#374151; margin-top:2px;}

/* cards and chart panels share one look */
.card {box-sizing:border-box; background:#FFFFFF; border:1px solid #E5E8EF; border-left:4px solid #C8A24A;
    border-radius:10px; padding:8px 14px; height:88px; overflow:hidden;
    box-shadow:0 2px 8px rgba(20,33,61,0.07);}
.card-title {font-size:0.66rem; text-transform:uppercase; letter-spacing:0.05em; color:#4B5563; font-weight:600;}
.card-value {font-size:1.35rem; font-weight:700; color:#14213D; line-height:1.3;}
.card-note {font-size:0.7rem; color:#4B5563; line-height:1.25;}
.tag {background:#14213D; color:#FFFFFF; border-radius:4px; font-size:0.56rem; padding:1px 6px; margin-left:8px;}

/* chart title is HTML above the chart, so every plot area lines up */
.panel-title {box-sizing:border-box; height:46px; overflow:hidden; background:#FFFFFF;
    border:1px solid #E5E8EF; border-bottom:0; border-radius:10px 10px 0 0;
    padding:8px 14px 0 14px; font-size:13px; font-weight:700; line-height:1.3; color:#111827;
    box-shadow:0 -2px 8px rgba(20,33,61,0.04);}
[data-testid="stPlotlyChart"] {background:#FFFFFF; border:1px solid #E5E8EF; border-top:0;
    border-radius:0 0 10px 10px; box-shadow:0 2px 8px rgba(20,33,61,0.07);
    overflow:hidden; margin-top:-0.55rem;}

/* label above the month selector, sized so the selector lines up with the cards */
.sel-label {height:40px; display:flex; align-items:flex-end; padding-bottom:4px;
    font-size:0.85rem; font-weight:600; color:#111827;}
</style>
"""

# ============================================================ 2. SQL
# Ids in comments are the requirement ids in the Step 3 PDF.
FILTER = ("(:conn = 'All' OR c.connection_type = :conn) "
          "AND (:grp = 'All' OR c.ab_group = :grp)")
FROM_DAYS = "FROM usage_daily u JOIN customer_features c ON c.customer_id = u.customer_id"
FROM_MONTHS = "FROM v_usage_month m JOIN customer_features c ON c.customer_id = m.customer_id"
IN_MONTH = "strftime('%Y-%m', u.usage_date) = :month"

# Sidebar and selector options
Q_CONNECTIONS = "SELECT DISTINCT connection_type FROM customer_features ORDER BY 1"
Q_GROUPS = "SELECT DISTINCT ab_group FROM customer_features ORDER BY 1"
Q_MONTHS = "SELECT DISTINCT month FROM v_usage_month ORDER BY 1"  # D5

# ---- Overview
Q_TOTAL_DAYS = "SELECT COUNT(*) AS usage_days FROM usage_daily"  # D2 (fixed)

Q_OFFER_LIFT = """
WITH p AS (SELECT c.ab_group, u.customer_id,
                  CASE WHEN u.usage_date >= '2025-05-01' THEN 'during' ELSE 'before' END AS per,
                  AVG(u.data_mb) AS m
           FROM usage_daily u
           JOIN customer_features c ON c.customer_id = u.customer_id
           GROUP BY u.customer_id, per),
g AS (SELECT per, ab_group, AVG(m) AS avg_mb FROM p GROUP BY per, ab_group)
SELECT ROUND(MAX(CASE WHEN per = 'during' AND ab_group = 'B' THEN avg_mb END)
           - MAX(CASE WHEN per = 'during' AND ab_group = 'A' THEN avg_mb END), 2) AS lift_mb,
       ROUND(MAX(CASE WHEN per = 'during' AND ab_group = 'B' THEN avg_mb END), 2) AS b_mb,
       ROUND(MAX(CASE WHEN per = 'during' AND ab_group = 'A' THEN avg_mb END), 2) AS a_mb
FROM g
"""  # N4 (fixed)

Q_PER_DAY = f"""
SELECT ROUND(AVG(c.mb_per_active_day), 2)   AS per_active_day,
       ROUND(AVG(c.mb_per_observed_day), 2) AS per_observed_day
FROM customer_features c WHERE {FILTER}
"""  # D3

Q_MONTHLY_GROUP = f"""
SELECT strftime('%Y-%m', u.usage_date) AS m, c.ab_group,
       COUNT(*) AS usage_days, ROUND(AVG(u.data_mb), 2) AS avg_mb
{FROM_DAYS} WHERE {FILTER}
GROUP BY m, c.ab_group ORDER BY m, c.ab_group
"""  # N3

Q_MONTHLY_SUBS = f"""
SELECT m.month, COUNT(DISTINCT m.customer_id) AS active_subs
{FROM_MONTHS} WHERE {FILTER}
GROUP BY m.month ORDER BY m.month
"""  # D5

Q_ALLOWANCE = f"""
SELECT c.plan_name, c.monthly_gb, COUNT(*) AS subs,
       ROUND(AVG(c.total_data_mb/1024.0/6), 2) AS actual_gb_per_month,
       ROUND(100.0 * AVG((c.total_data_mb/1024.0/6) / c.monthly_gb), 1) AS pct_of_allowance
FROM customer_features c
WHERE c.usage_days > 0 AND {FILTER}
GROUP BY c.plan_name, c.monthly_gb ORDER BY c.monthly_gb
"""  # E4

Q_BASE_ALLOWANCE = """
SELECT ROUND(100.0 * AVG((total_data_mb/1024.0/6) / monthly_gb), 1) AS pct_of_allowance
FROM customer_features WHERE usage_days > 0
"""  # E5 (whole base, no filters, used as the reference line)

# ---- Month detail
Q_MONTH_SUBS = f"""
SELECT COUNT(DISTINCT m.customer_id) AS active_subs
{FROM_MONTHS} WHERE m.month = :month AND {FILTER}
"""  # D5

Q_MONTH_TB = f"""
SELECT ROUND(SUM(m.total_mb)/1024/1024, 1) AS total_tb
{FROM_MONTHS} WHERE m.month = :month AND {FILTER}
"""  # D1

Q_MONTH_PER_DAY = f"""
SELECT ROUND(AVG(u.data_mb), 2) AS mb_per_usage_day, COUNT(*) AS usage_days
{FROM_DAYS} WHERE {IN_MONTH} AND {FILTER}
"""  # N3 / D2

Q_DAILY_TB = f"""
SELECT u.usage_date,
       ROUND(SUM(u.data_mb)/1024.0/1024.0, 2) AS tb_carried,
       ROUND(AVG(SUM(u.data_mb)/1024.0/1024.0) OVER (), 2) AS avg_tb
{FROM_DAYS} WHERE {IN_MONTH} AND {FILTER}
GROUP BY u.usage_date ORDER BY u.usage_date
"""  # not in PDF, built from D1

Q_MONTH_GROUPS = f"""
SELECT c.ab_group, COUNT(*) AS usage_days, ROUND(AVG(u.data_mb), 2) AS mb_per_usage_day
{FROM_DAYS} WHERE {IN_MONTH} AND {FILTER}
GROUP BY c.ab_group ORDER BY c.ab_group
"""  # N3

Q_MONTH_DEVICES = f"""
SELECT c.device_type, COUNT(*) AS usage_days,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_days,
       ROUND(AVG(u.data_mb), 2) AS mb_per_usage_day
{FROM_DAYS} WHERE {IN_MONTH} AND {FILTER}
GROUP BY c.device_type ORDER BY usage_days DESC
"""  # not in PDF, built from E3 and N3


# ============================================================ 3. HELPERS
STRETCH = tuple(int(p) for p in st.__version__.split(".")[:2]) >= (1, 50)


@st.cache_data(show_spinner=False)
def run(db_path, sql, params):
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def q(sql, **extra):
    """Run a query with the current sidebar filters (and any extra values)."""
    params = {"conn": st.session_state.get("conn", "All"),
              "grp": st.session_state.get("grp", "All"), **extra}
    return run(st.session_state["db_path"], sql, params)


def month_short(m):
    return pd.to_datetime(m + "-01").strftime("%b")


def month_long(m):
    return pd.to_datetime(m + "-01").strftime("%B %Y")


def html(markup):
    """st.html keeps exact heights; older Streamlit versions fall back to markdown."""
    if hasattr(st, "html"):
        st.html(markup)
    else:
        st.markdown(markup, unsafe_allow_html=True)


def show(fig):
    config = {"displayModeBar": False}
    if STRETCH:
        st.plotly_chart(fig, width="stretch", theme=None, config=config)
    else:
        st.plotly_chart(fig, use_container_width=True, theme=None, config=config)


def card(title, value, note, tag=""):
    badge = f'<span class="tag">{tag}</span>' if tag else ""
    html(f'<div class="card"><div class="card-title">{title}{badge}</div>'
         f'<div class="card-value">{value}</div><div class="card-note">{note}</div></div>')


def panel_title(text):
    """Chart title as HTML above the chart, with a fixed height."""
    html(f'<div class="panel-title">{text}</div>')


def style(fig, title, height, wrap_at, x_title=None, y_title=None):
    """Same look for every chart: finding as title (HTML), labelled axes and legend.
    wrap_at is kept for compatibility; CSS wraps the title text now."""
    panel_title(title)
    fig.update_layout(
        title=None, height=height - TITLE_H, margin=dict(l=55, r=15, t=40, b=50),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Segoe UI, Arial", size=10, color=INK),
        xaxis_title=x_title, yaxis_title=y_title,
        hoverlabel=dict(bgcolor="white", font=dict(color=INK, size=11)),
        legend=dict(orientation="h", x=0, xanchor="left", y=1.02, yanchor="bottom",
                    font=dict(size=10, color=INK)))
    fig.update_xaxes(showgrid=False, linecolor="#9CA3AF", tickfont=dict(color=INK),
                     title_font=dict(size=11, color=INK))
    fig.update_yaxes(gridcolor="#E5E7EB", zeroline=False, tickfont=dict(color=INK),
                     title_font=dict(size=11, color=INK))


def table(df, title, height, wrap_at, formats, row_h=24, font=11):
    """Table drawn with Plotly so it has an explicit height and no scrollbar."""
    panel_title(title)
    row_fill = ["#FFFFFF" if i % 2 == 0 else "#F1F3F8" for i in range(len(df))]
    fig = go.Figure(go.Table(
        header=dict(values=list(df.columns), fill_color=NAVY, align="left", height=row_h + 2,
                    font=dict(color="white", size=font)),
        cells=dict(values=[df[c] for c in df.columns], format=formats, align="left",
                   height=row_h, fill_color=[row_fill] * len(df.columns),
                   font=dict(color=INK, size=font))))
    fig.update_layout(height=height - TITLE_H, margin=dict(l=10, r=10, t=5, b=5),
                      paper_bgcolor="white")
    return fig


# ============================================================ 4. UPLOAD SCREEN
def check_database(path):
    """Return an error message, or None when the file has the tables we need."""
    try:
        conn = sqlite3.connect(path)
        found = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}
        conn.close()
    except sqlite3.DatabaseError:
        return "This is not a valid SQLite database file."
    missing = REQUIRED_OBJECTS - found
    return f"The database is missing: {', '.join(sorted(missing))}." if missing else None


def upload_page():
    st.markdown("<style>[data-testid='stSidebar']{display:none;}</style>",
                unsafe_allow_html=True)
    _, middle, _ = st.columns([1, 2, 1])
    with middle:
        st.markdown("<br><br>", unsafe_allow_html=True)
        html('<div class="app-head"><div class="app-row">'
             '<span class="app-title">Network Usage Dashboard</span>'
             '<span class="app-sub">Airtel Telecom Analytics</span></div>'
             '<div class="app-reader">Upload the Airtel telecom SQLite database (.db) '
             'to generate the dashboard.</div></div>')
        file = st.file_uploader("Upload database file", type=["db", "sqlite", "sqlite3"])
        if file is None:
            return
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            tmp.write(file.getvalue())
        error = check_database(tmp.name)
        if error:
            st.error(error)
            return
        st.session_state["db_path"] = tmp.name
        st.session_state["file_name"] = file.name
        st.rerun()


# ============================================================ 5. SIDEBAR AND HEADER
def sidebar():
    st.sidebar.markdown("### Filters")
    st.sidebar.selectbox("Connection type", ["All"] + q(Q_CONNECTIONS).iloc[:, 0].tolist(), key="conn")
    st.sidebar.selectbox("Experiment group", ["All"] + q(Q_GROUPS).iloc[:, 0].tolist(), key="grp")
    st.sidebar.caption("Filters apply to every card and chart except the two cards "
                       "marked FIXED. On Month detail, the selected month applies too.")
    st.sidebar.caption(f"File: {st.session_state['file_name']}")
    if st.sidebar.button("Upload a different file"):
        st.session_state.clear()
        st.rerun()


def header():
    chip = (f"Connection: {st.session_state['conn']} &nbsp;|&nbsp; "
            f"Group: {st.session_state['grp']}")
    html('<div class="app-head"><div class="app-row">'
         '<span class="app-title">Network Usage Dashboard</span>'
         '<span class="app-sub">Airtel Telecom Analytics &middot; Domain C</span>'
         f'<span class="app-chip">{chip}</span></div>'
         '<div class="app-reader">For the <b>Network Capacity Planner</b>: deciding how much '
         'data the network must carry and whether plans fit subscriber usage.</div></div>')


# ============================================================ 6. OVERVIEW TAB
def overview_cards():
    total = q(Q_TOTAL_DAYS).iloc[0, 0]
    lift = q(Q_OFFER_LIFT).iloc[0]
    day = q(Q_PER_DAY).iloc[0]
    p_text = (f"One-tailed p = {T3_P_VALUE}" if T3_P_VALUE is not None
              else "One-tailed p-value: set T3_P_VALUE in app.py")
    c1, c2, c3 = st.columns(3)
    with c1:
        card("Usage days recorded, Jan-Jun 2025", f"{total:,}",
             "All subscribers, before filters. One usage day = one subscriber on one day with usage.",
             "FIXED")
    with c2:
        card("Offer effect on data use (Step 4 T3)", f"{lift['lift_mb']:+,.2f} MB",
             f"Group B {lift['b_mb']:,.0f} vs group A {lift['a_mb']:,.0f} MB per subscriber, "
             f"May-Jun. {p_text}", "FIXED")
    with c3:
        card("Data per active day", f"{day['per_active_day']:,.0f} MB",
             f"Per day with usage. Per calendar day it is {day['per_observed_day']:,.0f} MB, "
             "a different measure.")


def overview_hero():
    df = q(Q_MONTHLY_GROUP)
    df["month"] = pd.to_datetime(df["m"] + "-01")
    fig = go.Figure()
    for group, part in df.groupby("ab_group"):
        fig.add_trace(go.Scatter(
            x=part["month"], y=part["avg_mb"], mode="lines+markers", name=f"Group {group}",
            line=dict(color=GROUP_COLORS[group], width=3), customdata=part["usage_days"],
            hovertemplate="%{x|%B}: %{y:,.0f} MB per usage day<br>"
                          "%{customdata:,} usage days<extra>Group " + group + "</extra>"))
    fig.add_vrect(x0=OFFER_START, x1=OFFER_END, fillcolor=GOLD, opacity=0.15, line_width=0,
                  annotation_text="Offer period (1 May-30 Jun)", annotation_position="top left",
                  annotation_font_size=9, annotation_font_color=INK)
    may = df[df["m"] == "2025-05"].set_index("ab_group")["avg_mb"]
    if len(may) == 2:
        title = f"May: group B used {may['B']:,.0f} MB per usage day, group A {may['A']:,.0f} MB"
    else:
        title = f"May: group {may.index[0]} used {may.iloc[0]:,.0f} MB per usage day"
    style(fig, title, HERO_ROW_H, 70, "Month (2025)", "Data per usage day (MB)")
    fig.update_xaxes(tickformat="%b", dtick="M1")
    fig.update_yaxes(range=[0, df["avg_mb"].max() * 1.25])
    show(fig)


def overview_subscribers():
    df = q(Q_MONTHLY_SUBS)
    fig = go.Figure(go.Bar(
        x=df["month"].map(month_short), y=df["active_subs"], name="Subscribers who used the network",
        marker_color=NAVY, text=df["active_subs"], texttemplate="%{text:,}",
        textposition="outside", textfont=dict(size=9, color=INK), cliponaxis=False))
    first, last = df["active_subs"].iloc[0], df["active_subs"].iloc[-1]
    verb = "fell" if last < first else "rose"
    style(fig, f"Active subscribers {verb} from {first:,} (Jan) to {last:,} (Jun)",
          HERO_ROW_H, 34, "Month (2025)", "Subscribers (count)")
    fig.update_yaxes(range=[0, df["active_subs"].max() * 1.2])
    show(fig)


def overview_table():
    subs = q(Q_MONTHLY_SUBS).set_index("month")
    rates = q(Q_MONTHLY_GROUP)
    wide = rates.pivot(index="m", columns="ab_group", values="avg_mb")
    out = subs.join(wide).reset_index()
    peak = rates.loc[rates["avg_mb"].idxmax()]
    out["month"] = out["month"].map(month_short)
    out = out.rename(columns={"month": "Month", "active_subs": "Subscribers",
                              "A": "Group A MB/day", "B": "Group B MB/day"})
    formats = [None, ","] + [",.0f"] * (len(out.columns) - 2)
    title = f"Data per usage day peaks in {month_short(peak['m'])} at {peak['avg_mb']:,.0f} MB"
    show(table(out, title, HERO_ROW_H, 34, formats))


def overview_allowance():
    """Horizontal bars: one row per plan, reference line = base allowance usage."""
    df = q(Q_ALLOWANCE)
    base = q(Q_BASE_ALLOWANCE).iloc[0, 0]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["plan_name"], x=df["pct_of_allowance"], orientation="h",
        name="Share of allowance used by the plan's subscribers", marker_color=NAVY,
        text=[f"{p:.1f}%  (n={n:,})" for p, n in zip(df["pct_of_allowance"], df["subs"])],
        textposition="outside", textfont=dict(size=9, color=INK), cliponaxis=False))
    fig.add_shape(type="line", xref="x", yref="paper", x0=base, x1=base, y0=0, y1=1,
                  line=dict(color=GOLD, width=2, dash="dash"))
    fig.add_trace(go.Scatter(  # legend entry for the reference line
        x=[None], y=[None], mode="lines",
        name=f"Reference line: base allowance usage, all subscribers ({base:.1f}%)",
        line=dict(color=GOLD, width=2, dash="dash")))
    title = (f"Every plan uses {df['pct_of_allowance'].min():.1f}% to "
             f"{df['pct_of_allowance'].max():.1f}% of its data allowance; the base uses {base:.1f}%")
    style(fig, title, BOTTOM_ROW_H, 130, "Share of monthly data allowance used (%)",
          f"Plan (all {len(df)} shown)")
    fig.update_layout(bargap=0.3)
    fig.update_yaxes(autorange="reversed", automargin=True, tickfont=dict(size=9, color=INK))
    fig.update_xaxes(range=[0, df["pct_of_allowance"].max() * 1.3])
    show(fig)


def overview():
    overview_cards()
    left, middle, right = st.columns([2, 1, 1])
    with left:
        overview_hero()
    with middle:
        overview_subscribers()
    with right:
        overview_table()
    overview_allowance()
    st.caption(PROVENANCE)


# ============================================================ 7. MONTH DETAIL TAB
def detail_cards():
    months = q(Q_MONTHS)["month"].tolist()
    # Month picker: a horizontal radio row (no dropdown, so no popup styling issues)
    month = st.radio("Select month", months, format_func=month_long,
                     key="month", horizontal=True)
    c1, c2, c3 = st.columns(3)
    subs = q(Q_MONTH_SUBS, month=month).iloc[0, 0]
    tb = q(Q_MONTH_TB, month=month).iloc[0, 0]
    day = q(Q_MONTH_PER_DAY, month=month).iloc[0]
    with c1:
        card("Subscribers who used the network", f"{subs:,}",
             f"At least one usage day in {month_long(month)}.")
    with c2:
        card("Total data carried", f"{tb:,.1f} TB",
             "All subscribers' MB summed, then divided by 1,024 twice (MB to GB to TB).")
    with c3:
        card("Data per usage day", f"{day['mb_per_usage_day']:,.0f} MB",
             f"Average over {int(day['usage_days']):,} usage days in {month_long(month)}.")
    return month


def detail_daily(month):
    df = q(Q_DAILY_TB, month=month)
    df["day"] = pd.to_datetime(df["usage_date"])
    avg = df["avg_tb"].iloc[0]
    peak = df.loc[df["tb_carried"].idxmax()]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["day"], y=df["tb_carried"], mode="lines+markers", name="Data carried per day (TB)",
        line=dict(color=NAVY, width=2.5), marker=dict(size=4),
        hovertemplate="%{x|%d %b}: %{y:.2f} TB<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=[df["day"].iloc[0], df["day"].iloc[-1]], y=[avg, avg], mode="lines",
        name=f"Reference line: average day in the month ({avg:.2f} TB)",
        line=dict(color=GOLD, width=2, dash="dash")))
    title = f"Busiest day, {peak['day']:%d %b}, carried {peak['tb_carried']:.2f} TB against a {avg:.2f} TB average"
    style(fig, title, HERO_ROW_H, 70, f"Day of {month_long(month)}", "Data carried (TB)")
    fig.update_xaxes(tickformat="%d")
    show(fig)


def detail_groups(month):
    df = q(Q_MONTH_GROUPS, month=month)
    fig = go.Figure()
    for _, row in df.iterrows():
        group = row["ab_group"]
        fig.add_trace(go.Bar(
            x=[f"Group {group}"], y=[row["mb_per_usage_day"]], name=f"Group {group}",
            marker_color=GROUP_COLORS[group], textposition="outside",
            textfont=dict(size=9, color=INK), cliponaxis=False,
            text=[f"{row['mb_per_usage_day']:,.0f} MB<br>{int(row['usage_days']):,} usage days"]))
    mb = df.set_index("ab_group")["mb_per_usage_day"]
    if len(mb) == 2:
        title = f"Group B used {mb['B']:,.0f} MB per usage day vs {mb['A']:,.0f} MB for group A"
    else:
        title = f"Group {mb.index[0]} used {mb.iloc[0]:,.0f} MB per usage day in {month_short(month)}"
    style(fig, title, HERO_ROW_H, 34, "Experiment group", "Data per usage day (MB)")
    fig.update_layout(bargap=0.4)
    fig.update_yaxes(range=[0, mb.max() * 1.5])
    show(fig)


def detail_devices_pie(month):
    df = q(Q_MONTH_DEVICES, month=month)
    top = df.loc[df["usage_days"].idxmax()]
    fig = go.Figure(go.Pie(
        labels=df["device_type"], values=df["usage_days"], hole=0.45, sort=False,
        marker=dict(colors=[NAVY, GOLD, SLATE][:len(df)]), textinfo="percent",
        textposition="outside", automargin=True, textfont=dict(size=11, color=INK),
        hovertemplate="%{label}: %{value:,} usage days (%{percent})<extra></extra>"))
    title = f"{top['device_type']} is {top['pct_days']:.0f}% of usage days in {month_short(month)}"
    style(fig, title, HERO_ROW_H, 34)
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=30),
                      legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.02, yanchor="top"))
    show(fig)


def detail_devices_table(month):
    df = q(Q_MONTH_DEVICES, month=month)
    top = df.loc[df["mb_per_usage_day"].idxmax()]
    out = df.rename(columns={"device_type": "Device type", "usage_days": "Usage days",
                             "pct_days": "Share of usage days (%)",
                             "mb_per_usage_day": "Data per usage day (MB)"})
    title = f"{top['device_type']} subscribers use the most data per usage day: {top['mb_per_usage_day']:,.0f} MB"
    show(table(out, title, DETAIL_TABLE_H, 130, [None, ",", ".1f", ",.0f"], row_h=32, font=12))


def detail():
    month = detail_cards()
    left, middle, right = st.columns([2, 1, 1])
    with left:
        detail_daily(month)
    with middle:
        detail_groups(month)
    with right:
        detail_devices_pie(month)
    detail_devices_table(month)
    st.caption(PROVENANCE)


# ============================================================ 8. APP
st.markdown(CSS, unsafe_allow_html=True)

if "db_path" not in st.session_state:
    upload_page()
else:
    sidebar()
    header()
    overview_tab, detail_tab = st.tabs(["Overview", "Month detail"])
    with overview_tab:
        overview()
    with detail_tab:
        detail()