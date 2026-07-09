"""
Task 6: Streamlit Dashboard
Multi-page interactive dashboard with:
- KPI cards
- EDA charts (interactive Plotly)
- Geospatial maps (embedded iframes)
- Advanced analysis outputs
Filterable by date range, vehicle type, and pickup zone.
"""

import os, warnings
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")
st.set_page_config(
    page_title="Uber NCR Analytics Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE   = os.path.dirname(os.path.abspath(__file__))
DATA   = os.path.join(BASE, "data", "cleaned_uber_data.csv")
OUTDIR = os.path.join(BASE, "output")

# ── Dark theme overrides ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background-color: #0d1117; }
[data-testid="stSidebar"] { background: #161b22; }
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
.metric-card {
    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
    border: 1px solid #374151;
    border-radius: 12px;
    padding: 20px 24px;
    margin: 8px 0;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
}
.metric-value { font-size: 2.4rem; font-weight: 700; margin: 0; }
.metric-label { font-size: 0.85rem; color: #9ca3af; margin: 0; letter-spacing: 0.05em; text-transform: uppercase; }
.metric-delta { font-size: 0.9rem; margin-top: 4px; }
h1, h2, h3 { color: #f0f6fc !important; }
.stTabs [data-baseweb="tab"] { color: #8b949e; font-weight: 500; }
.stTabs [aria-selected="true"] { color: #e94560 !important; border-bottom: 2px solid #e94560; }
</style>
""", unsafe_allow_html=True)

COLORS = {
    "primary":    "#e94560",
    "secondary":  "#0f3460",
    "gold":       "#f5a623",
    "teal":       "#4ecdc4",
    "background": "#0d1117",
    "surface":    "#161b22",
}
PLOTLY_TEMPLATE = dict(
    layout=go.Layout(
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["surface"],
        font=dict(color="#c9d1d9", family="Inter"),
        colorway=[COLORS["primary"], COLORS["gold"], COLORS["teal"],
                  COLORS["secondary"], "#45b7d1", "#96ceb4"],
        xaxis=dict(gridcolor="#21262d", linecolor="#30363d"),
        yaxis=dict(gridcolor="#21262d", linecolor="#30363d"),
    )
)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading dataset …")
def load_data():
    d = pd.read_csv(DATA, low_memory=False)
    d["Date"]        = pd.to_datetime(d["Date"], errors="coerce")
    d["hour_of_day"] = pd.to_numeric(d["hour_of_day"], errors="coerce")
    d["Booking Value"]  = pd.to_numeric(d["Booking Value"],  errors="coerce")
    d["Ride Distance"]  = pd.to_numeric(d["Ride Distance"],  errors="coerce")
    d["Driver Ratings"] = pd.to_numeric(d["Driver Ratings"], errors="coerce")
    d["Customer Rating"]= pd.to_numeric(d["Customer Rating"],errors="coerce")
    d["Avg VTAT"]       = pd.to_numeric(d["Avg VTAT"],       errors="coerce")
    d["pickup_lat"]  = pd.to_numeric(d["pickup_lat"],  errors="coerce")
    d["pickup_lon"]  = pd.to_numeric(d["pickup_lon"],  errors="coerce")
    d["drop_lat"]    = pd.to_numeric(d["drop_lat"],    errors="coerce")
    d["drop_lon"]    = pd.to_numeric(d["drop_lon"],    errors="coerce")
    return d

df = load_data()

# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/58/Uber_logo_2018.svg/200px-Uber_logo_2018.svg.png",
             width=90)
    st.markdown("## 🎛 Filters")

    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()
    date_range = st.date_input("Date Range", value=(min_date, max_date),
                                min_value=min_date, max_value=max_date)

    vehicles = ["All"] + sorted(df["Vehicle Type"].dropna().unique().tolist())
    sel_vehicle = st.selectbox("Vehicle Type", vehicles)

    zones = ["All"] + sorted(df["Pickup Location"].dropna().unique().tolist())
    sel_zone = st.selectbox("Pickup Zone", zones)

    st.markdown("---")
    st.markdown("**Data info**")
    st.caption(f"📅 {min_date} – {max_date}")
    st.caption(f"📊 {len(df):,} total bookings")

# Apply filters
mask = pd.Series([True] * len(df))
if len(date_range) == 2:
    mask &= (df["Date"].dt.date >= date_range[0]) & (df["Date"].dt.date <= date_range[1])
if sel_vehicle != "All":
    mask &= df["Vehicle Type"] == sel_vehicle
if sel_zone != "All":
    mask &= df["Pickup Location"] == sel_zone

fdf = df[mask].copy()

# ── KPI calculation ────────────────────────────────────────────────────────────
total       = len(fdf)
n_completed = (fdf["Booking Status"] == "Completed").sum()
n_cancelled = fdf["Booking Status"].str.contains("Cancel", case=False, na=False).sum()
n_cust_can  = (fdf["Cancelled Rides by Customer"].fillna(0) > 0).sum() if "Cancelled Rides by Customer" in fdf.columns else 0
n_drv_can   = (fdf["Cancelled Rides by Driver"].fillna(0) > 0).sum()   if "Cancelled Rides by Driver"   in fdf.columns else 0
avg_fare    = fdf["Booking Value"].mean()
avg_dist    = fdf["Ride Distance"].mean()
avg_rating  = fdf["Driver Ratings"].mean()

success_rate  = n_completed / total if total else 0
cancel_rate   = n_cancelled / total  if total else 0
cust_rate     = n_cust_can  / total  if total else 0
drv_rate      = n_drv_can   / total  if total else 0

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='font-size:2rem; margin-bottom:0;'>
  🚗 Uber NCR Analytics Dashboard
</h1>
<p style='color:#8b949e; margin-top:4px;'>
  End-to-end ride-booking intelligence for the National Capital Region
</p>
""", unsafe_allow_html=True)

# ── Tab navigation ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Overview & KPIs",
    "📈 EDA Charts",
    "🗺 Geospatial Maps",
    "🤖 Advanced Analysis",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — KPI Cards + summary charts
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Key Performance Indicators")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    def kpi(col, label, value, delta="", color="#e94560"):
        col.markdown(f"""
        <div class="metric-card">
          <p class="metric-label">{label}</p>
          <p class="metric-value" style="color:{color}">{value}</p>
          <p class="metric-delta" style="color:#6b7280">{delta}</p>
        </div>""", unsafe_allow_html=True)

    kpi(c1, "Total Bookings",       f"{total:,}",                  color="#f0f6fc")
    kpi(c2, "Success Rate",         f"{success_rate:.1%}",         f"bench 65.96%", color="#4ecdc4")
    kpi(c3, "Cancellation Rate",    f"{cancel_rate:.1%}",          f"bench 25.00%", color=COLORS["primary"])
    kpi(c4, "Cust. Cancellations",  f"{cust_rate:.1%}",            f"bench 19.15%", color=COLORS["gold"])
    kpi(c5, "Driver Cancellations", f"{drv_rate:.1%}",             f"bench 7.45%",  color="#45b7d1")
    kpi(c6, "Avg Fare",             f"₹{avg_fare:.0f}",            f"avg dist {avg_dist:.1f} km", color="#96ceb4")

    st.markdown("---")

    col_l, col_r = st.columns(2)
    with col_l:
        # Booking status donut
        status_counts = fdf["Booking Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig_donut = px.pie(status_counts, names="Status", values="Count", hole=0.55,
                           title="Booking Status Breakdown",
                           color_discrete_sequence=[COLORS["teal"], COLORS["primary"],
                                                    COLORS["gold"], COLORS["secondary"], "#8b949e"])
        fig_donut.update_layout(**PLOTLY_TEMPLATE["layout"].to_plotly_json())
        fig_donut.update_traces(textfont_color="white")
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_r:
        # Vehicle type booking volume
        veh_counts = fdf["Vehicle Type"].value_counts().reset_index()
        veh_counts.columns = ["Vehicle", "Bookings"]
        fig_veh = px.bar(veh_counts, x="Bookings", y="Vehicle", orientation="h",
                          title="Bookings by Vehicle Type",
                          color="Bookings", color_continuous_scale="YlOrRd")
        fig_veh.update_layout(**PLOTLY_TEMPLATE["layout"].to_plotly_json())
        st.plotly_chart(fig_veh, use_container_width=True)

    # Daily trend
    daily = fdf.groupby("Date").agg(
        bookings=("Booking ID", "count"),
        cancellations=("Booking Status", lambda s: s.str.contains("Cancel", case=False, na=False).mean() * 100)
    ).reset_index()
    fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
    fig_trend.add_trace(go.Bar(x=daily["Date"], y=daily["bookings"], name="Bookings",
                                marker_color=COLORS["secondary"], opacity=0.8), secondary_y=False)
    fig_trend.add_trace(go.Scatter(x=daily["Date"], y=daily["cancellations"], name="Cancel Rate %",
                                    line=dict(color=COLORS["primary"], width=2), mode="lines"),
                         secondary_y=True)
    fig_trend.update_layout(title="Daily Bookings & Cancellation Rate",
                              **PLOTLY_TEMPLATE["layout"].to_plotly_json())
    fig_trend.update_yaxes(title_text="Bookings", secondary_y=False)
    fig_trend.update_yaxes(title_text="Cancellation Rate (%)", secondary_y=True)
    st.plotly_chart(fig_trend, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — EDA Charts
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Exploratory Data Analysis")

    col1, col2 = st.columns(2)
    with col1:
        # Hourly volume
        hourly = fdf.groupby("hour_of_day").size().reset_index(name="Rides")
        fig_h = px.bar(hourly, x="hour_of_day", y="Rides", title="Ride Volume by Hour",
                        color="Rides", color_continuous_scale="YlOrRd")
        fig_h.update_layout(**PLOTLY_TEMPLATE["layout"].to_plotly_json())
        st.plotly_chart(fig_h, use_container_width=True)

    with col2:
        # Cancellation by hour
        hcan = fdf.groupby("hour_of_day").apply(
            lambda g: g["Booking Status"].str.contains("Cancel", case=False, na=False).mean() * 100
        ).reset_index(name="Cancel Rate %")
        fig_hc = px.line(hcan, x="hour_of_day", y="Cancel Rate %",
                          title="Cancellation Rate by Hour",
                          markers=True, color_discrete_sequence=[COLORS["primary"]])
        fig_hc.update_layout(**PLOTLY_TEMPLATE["layout"].to_plotly_json())
        st.plotly_chart(fig_hc, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        # Fare distribution
        fig_fare = px.box(fdf[fdf["Booking Value"].notna()],
                           x="Vehicle Type", y="Booking Value",
                           title="Booking Value by Vehicle Type",
                           color="Vehicle Type",
                           color_discrete_sequence=[COLORS["primary"], COLORS["gold"],
                                                    COLORS["teal"], COLORS["secondary"],
                                                    "#45b7d1", "#96ceb4"])
        fig_fare.update_layout(**PLOTLY_TEMPLATE["layout"].to_plotly_json())
        st.plotly_chart(fig_fare, use_container_width=True)

    with col4:
        # Payment method
        pay = fdf["Payment Method"].dropna()
        pay = pay[pay.str.lower() != "null"].value_counts().reset_index()
        pay.columns = ["Method", "Count"]
        fig_pay = px.pie(pay, names="Method", values="Count", hole=0.45,
                          title="Payment Method Distribution",
                          color_discrete_sequence=[COLORS["primary"], COLORS["gold"],
                                                   COLORS["teal"], COLORS["secondary"], "#45b7d1"])
        fig_pay.update_layout(**PLOTLY_TEMPLATE["layout"].to_plotly_json())
        st.plotly_chart(fig_pay, use_container_width=True)

    # Rating scatter
    rat = fdf[["Driver Ratings", "Customer Rating"]].dropna()
    rat = rat[(rat["Driver Ratings"] > 0) & (rat["Customer Rating"] > 0)]
    if len(rat) > 0:
        fig_rat = px.density_heatmap(rat, x="Driver Ratings", y="Customer Rating",
                                      nbinsx=20, nbinsy=20,
                                      title="Driver vs Customer Rating Density",
                                      color_continuous_scale="YlOrRd")
        fig_rat.update_layout(**PLOTLY_TEMPLATE["layout"].to_plotly_json())
        st.plotly_chart(fig_rat, use_container_width=True)

    # Cancellation reasons
    col5, col6 = st.columns(2)
    with col5:
        cr = fdf["Reason for cancelling by Customer"].dropna()
        cr = cr[cr.str.lower() != "null"].value_counts().head(8).reset_index()
        cr.columns = ["Reason", "Count"]
        fig_cr = px.bar(cr, x="Count", y="Reason", orientation="h",
                         title="Customer Cancellation Reasons",
                         color="Count", color_continuous_scale="Reds")
        fig_cr.update_layout(**PLOTLY_TEMPLATE["layout"].to_plotly_json())
        st.plotly_chart(fig_cr, use_container_width=True)

    with col6:
        dr = fdf["Driver Cancellation Reason"].dropna()
        dr = dr[dr.str.lower() != "null"].value_counts().head(8).reset_index()
        dr.columns = ["Reason", "Count"]
        fig_dr = px.bar(dr, x="Count", y="Reason", orientation="h",
                         title="Driver Cancellation Reasons",
                         color="Count", color_continuous_scale="Blues")
        fig_dr.update_layout(**PLOTLY_TEMPLATE["layout"].to_plotly_json())
        st.plotly_chart(fig_dr, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Geospatial Maps
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Geospatial Analysis")

    geo_files = {
        "🔥 Pickup Heatmap":          "geo/pickup_heatmap.html",
        "⬡ H3 Demand Hex Grid":       "geo/h3_demand_hex.html",
        "🚫 H3 Cancellation Rate":    "geo/cancellation_rate_hex.html",
        "↔ OD Flow Map (Top 15)":    "geo/od_flow_map.html",
        "⏰ Hourly Demand Animation":  "geo/demand_animation.html",
    }

    sel_map = st.selectbox("Select Map", list(geo_files.keys()))
    map_path = os.path.join(OUTDIR, geo_files[sel_map])

    if os.path.exists(map_path):
        with open(map_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=620, scrolling=False)
    else:
        st.warning(f"Map not yet generated. Run `python scripts/04_geospatial.py` first.\n\nExpected: `{map_path}`")

    # Pickup scatter on Plotly mapbox
    st.markdown("#### Interactive Pickup Density (Live Filter)")
    geo_fdf = fdf.dropna(subset=["pickup_lat","pickup_lon"])
    if len(geo_fdf) > 0:
        sample = geo_fdf.sample(min(5000, len(geo_fdf)), random_state=42)
        fig_scatter = px.scatter_mapbox(
            sample, lat="pickup_lat", lon="pickup_lon",
            color="Vehicle Type", hover_name="Pickup Location",
            hover_data={"Booking Value": True, "Ride Distance": True},
            zoom=10, center=dict(lat=28.6, lon=77.1),
            mapbox_style="carto-darkmatter",
            title="Pickup Locations (sampled 5k)",
            height=500, template="plotly_dark",
            opacity=0.7,
        )
        fig_scatter.update_layout(paper_bgcolor=COLORS["background"])
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Geocoded coordinates not available. Run `02_geocoding.py` first.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Advanced Analysis
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### Advanced Analysis")

    st.markdown("#### 🔴 DBSCAN Hotspot Clusters")
    cluster_path = os.path.join(BASE, "hotspot_clusters.csv")
    if os.path.exists(cluster_path):
        clusters = pd.read_csv(cluster_path)
        col_a, col_b = st.columns([2, 1])
        with col_a:
            fig_cl = px.scatter_mapbox(
                clusters[clusters["cluster"] != -1],
                lat="centroid_lat", lon="centroid_lon",
                size="count", color="count",
                color_continuous_scale="YlOrRd", size_max=30,
                hover_data={"count": True},
                zoom=10, center=dict(lat=28.6, lon=77.1),
                mapbox_style="carto-darkmatter",
                title="DBSCAN Cluster Centroids (sized by rides)",
                height=480, template="plotly_dark",
            )
            fig_cl.update_layout(paper_bgcolor=COLORS["background"])
            st.plotly_chart(fig_cl, use_container_width=True)
        with col_b:
            st.dataframe(clusters.sort_values("count", ascending=False).head(15), use_container_width=True)
    else:
        st.info("Run `python scripts/05_advanced.py` to generate cluster data.")

    st.markdown("#### 📈 Demand Forecast (Prophet)")
    forecast_path = os.path.join(BASE, "forecast_results.csv")
    if os.path.exists(forecast_path):
        fc = pd.read_csv(forecast_path)
        fc["ds"] = pd.to_datetime(fc["ds"])
        zones_fc = fc["zone"].unique().tolist()
        sel_fc_zone = st.selectbox("Select Zone for Forecast", zones_fc)
        zone_fc = fc[fc["zone"] == sel_fc_zone]
        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(x=zone_fc["ds"], y=zone_fc["yhat_upper"],
                                     fill=None, mode="lines",
                                     line=dict(color="rgba(245,166,35,0.3)"), name="Upper"))
        fig_fc.add_trace(go.Scatter(x=zone_fc["ds"], y=zone_fc["yhat_lower"],
                                     fill="tonexty", mode="lines",
                                     line=dict(color="rgba(245,166,35,0.3)"), name="Lower",
                                     fillcolor="rgba(245,166,35,0.15)"))
        fig_fc.add_trace(go.Scatter(x=zone_fc["ds"], y=zone_fc["yhat"],
                                     mode="lines", name="Forecast",
                                     line=dict(color=COLORS["gold"], width=2)))
        fig_fc.update_layout(title=f"30-Day Demand Forecast — {sel_fc_zone}",
                              xaxis_title="Date", yaxis_title="Predicted Daily Rides",
                              **PLOTLY_TEMPLATE["layout"].to_plotly_json())
        st.plotly_chart(fig_fc, use_container_width=True)
    else:
        st.info("Run `python scripts/05_advanced.py` to generate forecast data.")

    st.markdown("#### ⚠ Anomaly Detection (Isolation Forest)")
    if "anomaly_flag" in fdf.columns:
        anom = fdf[fdf["anomaly_flag"] == -1]
        st.metric("Anomalous Bookings", f"{len(anom):,}", f"{len(anom)/len(fdf):.1%} of filtered data")
        fig_anom = px.scatter(
            anom.dropna(subset=["Booking Value","Ride Distance"]),
            x="Ride Distance", y="Booking Value",
            color="Vehicle Type", hover_name="Pickup Location",
            title="Anomalous Bookings (Isolation Forest)", opacity=0.7,
            color_discrete_sequence=[COLORS["primary"], COLORS["gold"], COLORS["teal"],
                                      COLORS["secondary"], "#45b7d1"],
        )
        fig_anom.update_layout(**PLOTLY_TEMPLATE["layout"].to_plotly_json())
        st.plotly_chart(fig_anom, use_container_width=True)
    else:
        st.info("Run `python scripts/05_advanced.py` to add anomaly flags.")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center; color:#6b7280; font-size:0.8rem;'>
  Uber NCR Analytics Dashboard · Built with Streamlit + Plotly · Data: ncr_ride_bookings.csv
</div>
""", unsafe_allow_html=True)
