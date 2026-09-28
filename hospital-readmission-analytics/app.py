"""
app.py — Hospital Readmission & Length-of-Stay Analytics (Streamlit)
-------------------------------------------------------------------
An interactive dashboard on 99,343 real, cleaned hospital encounters.
Reads data/processed/analytics_encounters.csv (produced by the SQL layer).

Run locally:   streamlit run app.py
"""

from pathlib import Path
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

# --- Inject CSS: background, KPI cards, section headers, font ---------------
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
  .stApp {{ background:{BG}; }}
  html, body, [class*="css"] {{ font-family:'IBM Plex Sans', sans-serif; color:{INK}; }}
  .block-container {{ padding-top:1.6rem; padding-bottom:2rem; max-width:1360px; }}
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
  .sec {{ display:flex; align-items:center; gap:12px; margin:22px 0 4px; }}
  .sec h2 {{ font-size:14px; font-weight:600; margin:0; color:{INK};
             white-space:nowrap; letter-spacing:.02em; }}
  .sec .rule {{ flex:1; height:1px; background:{LINE}; }}
  .insight {{ font-size:12.5px; color:{INK}; background:{'#26313f' if DARK else '#FBF4EC'};
              border-left:3px solid #E0A100; padding:8px 11px; border-radius:0 6px 6px 0;
              margin-top:6px; }}
  [data-testid="stSidebar"] {{ background:{PANEL}; }}
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

def base_layout(h=250, left=46, legend=False):
    return go.Layout(
        height=h, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", size=12, color=INK),
        margin=dict(t=8, r=14, b=36, l=left), showlegend=legend, bargap=.28,
        xaxis=dict(showgrid=False, zeroline=False, linecolor=LINE, tickfont=dict(size=11)),
        yaxis=dict(gridcolor=LINE, zeroline=False, tickfont=dict(size=11)))

def rate_bar(frame, col, order=None, min_n=0, horizontal=False, label_map=None, h=250):
    d = rate_table(frame, col, order, min_n)
    labels = [label_map.get(x, x) if label_map else x for x in d[col].astype(str)]
    colors = [risk_color(v) for v in d["rate"]]
    if horizontal:
        tr = go.Bar(y=labels, x=d["rate"], orientation="h", marker_color=colors,
                    text=[f"{v}%" for v in d["rate"]], textposition="auto",
                    customdata=d["n"],
                    hovertemplate="%{y}<br>%{x}% readmitted<br>n=%{customdata:,}<extra></extra>")
        lay = base_layout(h, left=150); lay.xaxis.ticksuffix = "%"
    else:
        tr = go.Bar(x=labels, y=d["rate"], marker_color=colors,
                    text=[f"{v}%" for v in d["rate"]], textposition="outside",
                    customdata=d["n"],
                    hovertemplate="%{x}<br>%{y}% readmitted<br>n=%{customdata:,}<extra></extra>")
        lay = base_layout(h); lay.yaxis.ticksuffix = "%"; lay.yaxis.rangemode="tozero"
    return go.Figure(tr, lay)

def rate_line(frame, col, order=None, h=250):
    d = rate_table(frame, col, order)
    tr = go.Scatter(x=d[col].astype(str), y=d["rate"], mode="lines+markers",
                    line=dict(color=TEAL, width=3, shape="spline"),
                    marker=dict(color=TEAL, size=7), fill="tozeroy",
                    fillcolor="rgba(14,124,134,.10)", customdata=d["n"],
                    hovertemplate="%{x}<br>%{y}% readmitted<br>n=%{customdata:,}<extra></extra>")
    lay = base_layout(h); lay.yaxis.ticksuffix = "%"; lay.yaxis.rangemode="tozero"
    return go.Figure(tr, lay)

def vol_bar(frame, col, order=None, horizontal=False, top=None, h=250):
    g = frame.groupby(col, observed=True).size().reset_index(name="n")
    if order:
        g[col] = pd.Categorical(g[col], categories=order, ordered=True)
        g = g.sort_values(col)
    else:
        g = g.sort_values("n", ascending=True)
    if top:
        g = g.tail(top)
    if horizontal:
        tr = go.Bar(y=g[col].astype(str), x=g["n"], orientation="h", marker_color=TEAL,
                    hovertemplate="%{y}<br>%{x:,} encounters<extra></extra>")
        lay = base_layout(h, left=165)
    else:
        tr = go.Bar(x=g[col].astype(str), y=g["n"], marker_color=TEAL,
                    hovertemplate="%{x}<br>%{y:,} encounters<extra></extra>")
        lay = base_layout(h)
    return go.Figure(tr, lay)

def donut(frame, h=250):
    comp = frame["readmitted_raw"].value_counts()
    vals = [int(comp.get("<30",0)), int(comp.get(">30",0)), int(comp.get("NO",0))]
    rate = round(100*frame["is_readmitted_30d"].mean(), 1)
    tr = go.Pie(labels=["Within 30 days","After 30 days","Not readmitted"], values=vals,
                hole=.62, sort=False, marker=dict(colors=["#C0392B","#E0A100","#CDD7DD"]),
                textinfo="percent",
                hovertemplate="%{label}<br>%{value:,} (%{percent})<extra></extra>")
    lay = base_layout(h, legend=True)
    lay.margin = dict(t=8,r=8,b=8,l=8)
    lay.legend = dict(orientation="h", y=-.06, font=dict(size=10))
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
# SIDEBAR FILTERS  (all stack together; empty = no filter)
# ===========================================================================
st.sidebar.header("Filters")
def ms(label, col, fmt=None):
    opts = sorted([x for x in df[col].dropna().unique()])
    return st.sidebar.multiselect(label, opts, default=[])

f = df.copy()
sel_adm = st.sidebar.multiselect("Admission type",
            sorted(df["admission_type"].dropna().unique()), default=[])
sel_age = st.sidebar.multiselect("Age band",
            [a for a in AGE_ORDER if a in df["age_band"].unique()], default=[])
sel_gender = st.sidebar.multiselect("Gender",
            sorted(df["gender"].dropna().unique()), default=[])
sel_a1c = st.sidebar.multiselect("A1C test result",
            sorted(df["a1c_result"].dropna().unique()), default=[])
sel_change = st.sidebar.multiselect("Medication changed",
            sorted(df["med_changed"].dropna().unique()), default=[])
los_min, los_max = int(df["length_of_stay"].min()), int(df["length_of_stay"].max())
sel_los = st.sidebar.slider("Length of stay (days)", los_min, los_max, (los_min, los_max))

if sel_adm:    f = f[f["admission_type"].isin(sel_adm)]
if sel_age:    f = f[f["age_band"].isin(sel_age)]
if sel_gender: f = f[f["gender"].isin(sel_gender)]
if sel_a1c:    f = f[f["a1c_result"].isin(sel_a1c)]
if sel_change: f = f[f["med_changed"].isin(sel_change)]
f = f[f["length_of_stay"].between(sel_los[0], sel_los[1])]

st.sidebar.markdown(f"**{len(f):,}** of {len(df):,} encounters selected")
if len(f) == 0:
    st.warning("No encounters match these filters. Widen your selection.")
    st.stop()

# ===========================================================================
# KPI ROW
# ===========================================================================
def kpi(lab, val, hero=False):
    return f'<div class="kpi {"hero" if hero else ""}"><div class="lab">{lab}</div><div class="val">{val}</div></div>'

kpis = "".join([
    kpi("30-day readmission rate", f"{100*f['is_readmitted_30d'].mean():.1f}%", hero=True),
    kpi("Total encounters", f"{len(f):,}"),
    kpi("Readmissions (&lt;30d)", f"{int(f['is_readmitted_30d'].sum()):,}"),
    kpi("Avg length of stay", f"{f['length_of_stay'].mean():.1f} d"),
    kpi("Unique patients", f"{f['patient_nbr'].nunique():,}"),
    kpi("Avg medications", f"{f['num_medications'].mean():.1f}"),
])
st.markdown(f'<div class="kpi-row">{kpis}</div>', unsafe_allow_html=True)


def section(title, note=""):
    n = f'<span style="color:{INK_SOFT};font-size:12px;margin-left:auto">{note}</span>' if note else ""
    st.markdown(f'<div class="sec"><h2>{title}</h2><div class="rule"></div>{n}</div>',
                unsafe_allow_html=True)

PC = dict(use_container_width=True, config={"displayModeBar": False})

# --- Section 1: Readmission drivers ----------------------------------------
section("Readmission drivers", "30-day readmission rate by patient factor")
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    st.markdown("**Readmission rate by prior inpatient visits**")
    d = rate_table(f, "prior_band", ["0","1-2","3-5","6+"])
    st.plotly_chart(rate_bar(f, "prior_band", ["0","1-2","3-5","6+"],
                    label_map={"0":"0 prior","1-2":"1-2 prior","3-5":"3-5 prior","6+":"6+ prior"},
                    h=330), **PC)
    if len(d) >= 2 and d["rate"].iloc[0] > 0:
        hi, lo = d["rate"].iloc[-1], d["rate"].iloc[0]
        st.markdown(f'<div class="insight">Patients with <b>6+ prior admissions</b> are readmitted '
                    f'<b>{hi/lo:.1f}×</b> as often as those with none ({hi}% vs {lo}%).</div>',
                    unsafe_allow_html=True)
with c2:
    st.markdown("**By age band**")
    st.plotly_chart(rate_bar(f, "age_band", AGE_ORDER, h=330), **PC)
with c3:
    st.markdown("**By number of diagnoses**")
    fr = f.copy(); fr["ndx"] = fr["number_diagnoses"].clip(upper=9)
    st.plotly_chart(rate_line(fr, "ndx", order=sorted(fr["ndx"].unique()), h=330), **PC)

# --- Section 2: Clinical factors -------------------------------------------
section("Clinical factors")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("**By medication count**")
    st.plotly_chart(rate_bar(f, "med_band", ["1-10","11-20","21-30","31+"]), **PC)
with c2:
    st.markdown("**By A1C test result**")
    st.plotly_chart(rate_bar(f, "a1c_result", min_n=50), **PC)
with c3:
    st.markdown("**By medication change**")
    st.plotly_chart(rate_bar(f, "med_changed",
                    label_map={"Ch":"Changed","No":"No change"}), **PC)
with c4:
    st.markdown("**By discharge disposition**")
    st.plotly_chart(rate_bar(f, "discharge_disposition", min_n=400, horizontal=True), **PC)

# --- Section 3: Length of stay ---------------------------------------------
section("Length of stay")
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    st.markdown("**Length of stay distribution**")
    los = f["length_of_stay"].clip(1,14).value_counts().reindex(range(1,15)).fillna(0)
    fig = go.Figure(go.Bar(x=[str(i) for i in range(1,15)], y=los.values, marker_color=TEAL,
                    hovertemplate="%{x} days<br>%{y:,} encounters<extra></extra>"),
                    base_layout(300))
    st.plotly_chart(fig, **PC)
with c2:
    st.markdown("**Readmission rate by length of stay**")
    st.plotly_chart(rate_line(f, "los_band", ["1-2","3-4","5-7","8-14"], h=300), **PC)
with c3:
    st.markdown("**Readmission mix**")
    st.plotly_chart(donut(f, h=300), **PC)

# --- Section 4: Population served ------------------------------------------
section("Population served")
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    st.markdown("**Encounter volume by age**")
    st.plotly_chart(vol_bar(f, "age_band", AGE_ORDER), **PC)
with c2:
    st.markdown("**Readmission rate by gender**")
    st.plotly_chart(rate_bar(f, "gender", min_n=50), **PC)
with c3:
    st.markdown("**Top admitting specialties by volume**")
    st.plotly_chart(vol_bar(f.dropna(subset=["medical_specialty"]),
                    "medical_specialty", horizontal=True, top=8), **PC)

st.caption("Source: Diabetes 130-US Hospitals dataset (UCI ML Repository), de-identified, "
           "1999–2008. Encounters ending in death or hospice are excluded from readmission "
           "analysis. Built with Python, SQL, and Plotly.")
