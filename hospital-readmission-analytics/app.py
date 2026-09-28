"""
app.py — Hospital Readmission & Length-of-Stay Analytics (Streamlit)
-------------------------------------------------------------------
An interactive dashboard on 99,343 real, cleaned hospital encounters.
Reads data/processed/analytics_encounters.csv (produced by the SQL layer).

Run locally:   streamlit run app.py
"""

from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ===========================================================================
# THEME  — to change the background, swap BG for one of the options below:
#   Clinical Mist "#E9EEF2" | Command-Center Dark "#0F172A" | Teal Tint "#E8F3F2"
#   Neutral Graphite "#EDEFF2" | Warm Greige "#F1EEEA"
# For the dark option, also set DARK = True.
# ===========================================================================
BG = "#E9EEF2"
DARK = False

PANEL   = "#1E293B" if DARK else "#FFFFFF"
INK     = "#E8EEF3" if DARK else "#132430"
INK_SOFT= "#93A4B3" if DARK else "#5D6D79"
LINE    = "#334155" if DARK else "#DBE3EA"
TEAL    = "#2AA5B0" if DARK else "#0E7C86"

st.set_page_config(page_title="Hospital Readmission Analytics",
                   page_icon="🏥", layout="wide")

DATA = Path(__file__).parent / "data" / "processed" / "analytics_encounters.csv"
AGE_ORDER = ["[0-10)","[10-20)","[20-30)","[30-40)","[40-50)",
             "[50-60)","[60-70)","[70-80)","[80-90)","[90-100)"]

# --- Inject CSS -------------------------------------------------------------
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
  .stApp {{ background:{BG}; }}
  html, body, [class*="css"] {{ font-family:'IBM Plex Sans', sans-serif; color:{INK}; }}
  .block-container {{ padding-top:1.6rem; padding-bottom:2rem; max-width:1300px; }}
  h1.title {{ font-size:24px; font-weight:700; margin:0; color:{INK}; letter-spacing:-.01em; }}
  .subtitle {{ color:{INK_SOFT}; font-size:14px; margin:2px 0 4px; }}
  /* KPI cards */
  .kpi-row {{ display:flex; gap:12px; margin:14px 0 6px; flex-wrap:wrap; }}
  .kpi {{ flex:1; min-width:150px; background:{PANEL}; border:1px solid {LINE};
          border-radius:12px; padding:15px 16px 13px; }}
  .kpi .lab {{ font-size:11.5px; color:{INK_SOFT}; font-weight:500; }}
  .kpi .val {{ font-size:26px; font-weight:700; margin-top:5px; line-height:1;
               color:{INK}; font-variant-numeric:tabular-nums; }}
  .kpi.hero {{ border-color:{TEAL}; }}
  .kpi.hero::before {{ content:""; display:block; height:3px; width:32px;
               background:{TEAL}; border-radius:3px; margin-bottom:11px; }}
  .kpi.hero .val {{ color:{TEAL}; font-size:30px; }}
  /* section header */
  .sec {{ display:flex; align-items:center; gap:12px; margin:26px 0 8px; }}
  .sec h2 {{ font-size:14px; font-weight:600; margin:0; color:{INK};
             white-space:nowrap; letter-spacing:.02em; }}
  .sec .rule {{ flex:1; height:1px; background:{LINE}; }}
  .chart-title {{ font-size:14px; font-weight:600; color:{INK}; margin:2px 0 2px; }}
  .insight {{ font-size:12.5px; color:{INK}; background:{'#26313f' if DARK else '#FBF4EC'};
              border-left:3px solid #E0A100; padding:8px 11px; border-radius:0 6px 6px 0;
              margin-top:8px; }}
  [data-testid="stSidebar"] {{ background:{PANEL}; }}
  /* Bordered chart cards = visual boundaries + breathing room */
  [data-testid="stVerticalBlockBorderWrapper"] {{
     background:{PANEL}; border:1px solid {LINE} !important; border-radius:12px;
     padding:14px 16px 8px; box-shadow:0 1px 2px rgba(19,36,48,.05); }}
  /* Force readable text on Streamlit's own elements, regardless of system theme */
  [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
  [data-testid="stMarkdownContainer"] strong {{ color:{INK} !important; }}
  [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label,
  [data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 {{ color:{INK} !important; }}
  [data-baseweb="select"] > div {{ background:{PANEL} !important; border:1px solid {LINE} !important; }}
  [data-baseweb="select"] div, [data-baseweb="select"] span {{ color:{INK} !important; }}
  span[data-baseweb="tag"] {{ background:{TEAL} !important; }}
  span[data-baseweb="tag"] span {{ color:#FFFFFF !important; }}
  footer, #MainMenu {{ visibility:hidden; }}
</style>
""", unsafe_allow_html=True)


# --- Data -------------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(DATA)
    df["prior_band"] = pd.cut(df["number_inpatient"], [-1,0,2,5,999],
                              labels=["0","1-2","3-5","6+"])
    df["med_band"] = pd.cut(df["num_medications"], [-1,10,20,30,999],
                            labels=["1-10","11-20","21-30","31+"])
    df["los_band"] = pd.cut(df["length_of_stay"], [0,2,4,7,14],
                            labels=["1-2","3-4","5-7","8-14"])
    return df

df = load_data()


# --- Risk color: teal-green -> amber -> red on a fixed 5-40% scale ----------
RISK = [(31,138,112), (224,161,0), (192,57,43)]
def risk_color(v):
    t = max(0.0, min(1.0, (v-5)/(40-5)))
    a,b,tt = (RISK[0],RISK[1],t/.5) if t < .5 else (RISK[1],RISK[2],(t-.5)/.5)
    c = [round(a[i]+(b[i]-a[i])*tt) for i in range(3)]
    return f"rgb({c[0]},{c[1]},{c[2]})"

def rate_table(frame, col, order=None, min_n=0):
    g = (frame.groupby(col, observed=True)
              .agg(rate=("is_readmitted_30d","mean"), n=("is_readmitted_30d","size"))
              .reset_index())
    g["rate"] = (g["rate"]*100).round(1)
    g = g[g["n"] >= min_n]
    if order:
        g[col] = pd.Categorical(g[col], categories=order, ordered=True)
        g = g.sort_values(col)
    else:
        g = g.sort_values("rate")
    return g

def base_layout(h=300, left=48, legend=False):
    return go.Layout(
        height=h, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", size=12, color=INK),
        margin=dict(t=10, r=16, b=40, l=left), showlegend=legend, bargap=.3,
        hoverlabel=dict(bgcolor="#132430" if not DARK else "#0B1220",
                        font=dict(color="#FFFFFF", family="IBM Plex Sans", size=12)),
        xaxis=dict(showgrid=False, zeroline=False, linecolor=LINE, tickfont=dict(size=11)),
        yaxis=dict(gridcolor=LINE, zeroline=False, tickfont=dict(size=11)))

# Tooltips use customdata (rate, n, label) so they read as plain sentences and
# never double up the % sign (which happened when %{y} inherited the axis suffix).
def rate_bar(frame, col, order=None, min_n=0, horizontal=False, label_map=None,
             noun="patients", h=300):
    d = rate_table(frame, col, order, min_n)
    labels = [label_map.get(x, x) if label_map else x for x in d[col].astype(str)]
    colors = [risk_color(v) for v in d["rate"]]
    ht = ("<b>%{customdata[2]}</b><br>"
          "%{customdata[0]:.1f}% readmitted within 30 days<br>"
          "%{customdata[1]:,} encounters<extra></extra>")
    cd = np.column_stack([d["rate"].to_numpy(), d["n"].to_numpy(), np.array(labels, dtype=object)])
    if horizontal:
        tr = go.Bar(y=labels, x=d["rate"], orientation="h", marker_color=colors,
                    text=[f"{v}%" for v in d["rate"]], textposition="auto",
                    customdata=cd, hovertemplate=ht)
        lay = base_layout(h, left=150); lay.xaxis.ticksuffix = "%"
    else:
        tr = go.Bar(x=labels, y=d["rate"], marker_color=colors,
                    text=[f"{v}%" for v in d["rate"]], textposition="outside",
                    customdata=cd, hovertemplate=ht)
        lay = base_layout(h); lay.yaxis.ticksuffix = "%"; lay.yaxis.rangemode="tozero"
    return go.Figure(tr, lay)

def rate_line(frame, col, order=None, unit="", h=300):
    d = rate_table(frame, col, order)
    xl = d[col].astype(str)
    cd = np.column_stack([d["rate"].to_numpy(), d["n"].to_numpy()])
    suf = f" {unit}" if unit else ""
    ht = ("<b>%{x}" + suf + "</b><br>"
          "%{customdata[0]:.1f}% readmitted within 30 days<br>"
          "%{customdata[1]:,} encounters<extra></extra>")
    tr = go.Scatter(x=xl, y=d["rate"], mode="lines+markers",
                    line=dict(color=TEAL, width=3, shape="spline"),
                    marker=dict(color=TEAL, size=7), fill="tozeroy",
                    fillcolor="rgba(14,124,134,.10)", customdata=cd, hovertemplate=ht)
    lay = base_layout(h); lay.yaxis.ticksuffix = "%"; lay.yaxis.rangemode="tozero"
    return go.Figure(tr, lay)

def vol_bar(frame, col, order=None, horizontal=False, top=None, h=300):
    g = frame.groupby(col, observed=True).size().reset_index(name="n")
    if order:
        g[col] = pd.Categorical(g[col], categories=order, ordered=True); g = g.sort_values(col)
    else:
        g = g.sort_values("n", ascending=True)
    if top: g = g.tail(top)
    if horizontal:
        tr = go.Bar(y=g[col].astype(str), x=g["n"], orientation="h", marker_color=TEAL,
                    hovertemplate="<b>%{y}</b><br>%{x:,} encounters<extra></extra>")
        lay = base_layout(h, left=170)
    else:
        tr = go.Bar(x=g[col].astype(str), y=g["n"], marker_color=TEAL,
                    hovertemplate="<b>%{x}</b><br>%{y:,} encounters<extra></extra>")
        lay = base_layout(h)
    return go.Figure(tr, lay)

def donut(frame, h=300):
    comp = frame["readmitted_raw"].value_counts()
    vals = [int(comp.get("<30",0)), int(comp.get(">30",0)), int(comp.get("NO",0))]
    rate = round(100*frame["is_readmitted_30d"].mean(), 1)
    tr = go.Pie(labels=["Readmitted within 30 days","Readmitted after 30 days","Not readmitted"],
                values=vals, hole=.62, sort=False,
                marker=dict(colors=["#C0392B","#E0A100","#CDD7DD"]), textinfo="percent",
                hovertemplate="<b>%{label}</b><br>%{value:,} encounters (%{percent})<extra></extra>")
    lay = base_layout(h, legend=True)
    lay.margin = dict(t=10,r=10,b=10,l=10)
    lay.legend = dict(orientation="h", y=-.08, font=dict(size=10.5))
    lay.annotations = [dict(text=f"<b>{rate}%</b><br><span style='font-size:10px;color:{INK_SOFT}'>&lt;30 days</span>",
                            showarrow=False, font=dict(size=20, color=INK))]
    return go.Figure(tr, lay)


# ===========================================================================
# HEADER
# ===========================================================================
st.markdown('<h1 class="title">🏥 Hospital Readmission &amp; Length-of-Stay Analytics</h1>',
            unsafe_allow_html=True)
st.markdown('<div class="subtitle">Who returns within 30 days of discharge — and what predicts it. '
            '99,343 real de-identified encounters (130 US hospitals, 1999–2008).</div>',
            unsafe_allow_html=True)

# ===========================================================================
# SIDEBAR FILTERS
# ===========================================================================
st.sidebar.header("Filters")
st.sidebar.caption("Narrow the whole dashboard. Leave a filter empty to include everyone.")

f = df.copy()
sel_adm = st.sidebar.multiselect("Admission type",
            sorted(df["admission_type"].dropna().unique()), default=[],
            help="How the visit began — Emergency, Urgent, Elective, etc.")
sel_age = st.sidebar.multiselect("Age band",
            [a for a in AGE_ORDER if a in df["age_band"].unique()], default=[],
            help="Patient age range")
sel_gender = st.sidebar.multiselect("Gender",
            sorted(df["gender"].dropna().unique()), default=[], help="Patient gender")

if sel_adm:    f = f[f["admission_type"].isin(sel_adm)]
if sel_age:    f = f[f["age_band"].isin(sel_age)]
if sel_gender: f = f[f["gender"].isin(sel_gender)]

st.sidebar.markdown(f"**{len(f):,}** of {len(df):,} encounters selected")
if len(f) == 0:
    st.warning("No encounters match these filters. Widen your selection.")
    st.stop()

# ===========================================================================
# KPI ROW
# ===========================================================================
def kpi(lab, val, hero=False):
    return f'<div class="kpi {"hero" if hero else ""}"><div class="lab">{lab}</div><div class="val">{val}</div></div>'

st.markdown('<div class="kpi-row">' + "".join([
    kpi("30-day readmission rate", f"{100*f['is_readmitted_30d'].mean():.1f}%", hero=True),
    kpi("Total encounters", f"{len(f):,}"),
    kpi("Readmissions (&lt;30d)", f"{int(f['is_readmitted_30d'].sum()):,}"),
    kpi("Avg length of stay", f"{f['length_of_stay'].mean():.1f} d"),
    kpi("Unique patients", f"{f['patient_nbr'].nunique():,}"),
    kpi("Avg medications", f"{f['num_medications'].mean():.1f}"),
]) + '</div>', unsafe_allow_html=True)


def section(title, note=""):
    n = f'<span style="color:{INK_SOFT};font-size:12px;margin-left:auto">{note}</span>' if note else ""
    st.markdown(f'<div class="sec"><h2>{title}</h2><div class="rule"></div>{n}</div>',
                unsafe_allow_html=True)

PC = dict(use_container_width=True, config={"displayModeBar": False})

def card(container, title, fig, insight=None):
    """Render one chart inside a bordered card (a visual boundary)."""
    with container:
        with st.container(border=True):
            st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)
            st.plotly_chart(fig, **PC)
            if insight:
                st.markdown(insight, unsafe_allow_html=True)

# --- Section 1: Readmission drivers (2 per row) ----------------------------
section("Readmission drivers", "30-day readmission rate by patient factor")
a, b = st.columns(2, gap="large")
d = rate_table(f, "prior_band", ["0","1-2","3-5","6+"])
ins = None
if len(d) >= 2 and d["rate"].iloc[0] > 0:
    hi, lo = d["rate"].iloc[-1], d["rate"].iloc[0]
    ins = (f'<div class="insight">Patients with <b>6+ prior admissions</b> are readmitted '
           f'<b>{hi/lo:.1f}×</b> as often as those with none ({hi}% vs {lo}%).</div>')
card(a, "Readmission rate by prior inpatient visits",
     rate_bar(f, "prior_band", ["0","1-2","3-5","6+"],
              label_map={"0":"0 prior","1-2":"1-2 prior","3-5":"3-5 prior","6+":"6+ prior"},
              h=340), ins)
card(b, "Readmission rate by age band", rate_bar(f, "age_band", AGE_ORDER, h=340))

a, b = st.columns(2, gap="large")
fr = f.copy(); fr["ndx"] = fr["number_diagnoses"].clip(upper=9)
card(a, "Readmission rate by number of diagnoses",
     rate_line(fr, "ndx", order=sorted(fr["ndx"].unique()), unit="diagnoses", h=300))
card(b, "Readmission rate by medication count",
     rate_bar(f, "med_band", ["1-10","11-20","21-30","31+"], h=300))

# --- Section 2: Clinical factors (2 per row) -------------------------------
section("Clinical factors")
a, b = st.columns(2, gap="large")
card(a, "Readmission rate by A1C test result", rate_bar(f, "a1c_result", min_n=50, h=300))
card(b, "Readmission rate by medication change",
     rate_bar(f, "med_changed", label_map={"Ch":"Changed","No":"No change"}, h=300))

a, b = st.columns(2, gap="large")
card(a, "Readmission rate by discharge disposition",
     rate_bar(f, "discharge_disposition", min_n=400, horizontal=True, h=340))
card(b, "Readmission mix", donut(f, h=340))

# --- Section 3: Length of stay (2 per row) ---------------------------------
section("Length of stay")
a, b = st.columns(2, gap="large")
los = f["length_of_stay"].clip(1,14).value_counts().reindex(range(1,15)).fillna(0)
losfig = go.Figure(go.Bar(x=[str(i) for i in range(1,15)], y=los.values, marker_color=TEAL,
                   hovertemplate="<b>%{x} days</b><br>%{y:,} encounters<extra></extra>"),
                   base_layout(300))
card(a, "Length of stay distribution", losfig)
card(b, "Readmission rate by length of stay",
     rate_line(f, "los_band", ["1-2","3-4","5-7","8-14"], unit="days", h=300))

# --- Section 4: Population served ------------------------------------------
section("Population served")
a, b = st.columns(2, gap="large")
card(a, "Encounter volume by age", vol_bar(f, "age_band", AGE_ORDER, h=300))
card(b, "Readmission rate by gender", rate_bar(f, "gender", min_n=50, h=300))

with st.container(border=True):
    st.markdown('<div class="chart-title">Top admitting specialties by volume</div>',
                unsafe_allow_html=True)
    st.plotly_chart(vol_bar(f.dropna(subset=["medical_specialty"]),
                    "medical_specialty", horizontal=True, top=8, h=340), **PC)

st.caption("Source: Diabetes 130-US Hospitals dataset (UCI ML Repository), de-identified, "
           "1999–2008. Encounters ending in death or hospice are excluded from readmission "
           "analysis. Built with Python, SQL, and Plotly.")
