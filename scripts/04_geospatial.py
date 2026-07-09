"""
Task 4: Geospatial Analysis
- Folium pickup heatmap
- H3 hexagonal binning (res 8) -- demand + cancellation rate choropleth
- OD flow map (top 15 pairs)
- Plotly animated demand scatter_mapbox by hour
Saves HTML + PNG to output/geo/
"""

import sys, os, warnings, json, math
import numpy as np
import pandas as pd
import folium
from folium.plugins import HeatMap, AntPath

# Force UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import plotly.express as px
import plotly.graph_objects as go

warnings.filterwarnings("ignore")

BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA   = os.path.join(BASE, "data", "cleaned_uber_data.csv")
OUTDIR = os.path.join(BASE, "output", "geo")
os.makedirs(OUTDIR, exist_ok=True)

# -- try import h3 -------------------------------------------------------------
try:
    import h3
    HAS_H3 = True
except ImportError:
    HAS_H3 = False
    print("  [WARN] h3 not available - hex maps skipped")

MAPBOX_STYLE = "carto-darkmatter"

# -- Load -----------------------------------------------------------------------
print("Loading cleaned dataset ...")
df = pd.read_csv(DATA, low_memory=False)
df["Date"]        = pd.to_datetime(df["Date"], errors="coerce")
df["hour_of_day"] = pd.to_numeric(df["hour_of_day"], errors="coerce")
df["pickup_lat"]  = pd.to_numeric(df["pickup_lat"], errors="coerce")
df["pickup_lon"]  = pd.to_numeric(df["pickup_lon"], errors="coerce")
df["drop_lat"]    = pd.to_numeric(df["drop_lat"], errors="coerce")
df["drop_lon"]    = pd.to_numeric(df["drop_lon"], errors="coerce")
print(f"  {len(df):,} rows loaded")

geo_df = df.dropna(subset=["pickup_lat", "pickup_lon"])
print(f"  {len(geo_df):,} rows with geocoords")

NCR_CENTER = [28.6, 77.1]

# -----------------------------------------------------------------------------
# MAP 1: Pickup density heatmap
# -----------------------------------------------------------------------------
print("\n[1/5] Building pickup heatmap ...")
m1 = folium.Map(location=NCR_CENTER, zoom_start=11,
                tiles="CartoDB dark_matter")
heat_data = geo_df[["pickup_lat", "pickup_lon"]].dropna().values.tolist()
HeatMap(heat_data, radius=10, blur=12, max_zoom=13,
        gradient={"0.3": "#0f3460", "0.6": "#e94560", "1.0": "#f5a623"}).add_to(m1)
folium.map.Marker(
    [29.1, 77.8],
    icon=folium.DivIcon(html='<div style="color:white;font-size:14px;'
                             'background:#1a1a2e;padding:5px;border-radius:4px">'
                             '🔴 Pickup Density Heatmap -- NCR</div>')
).add_to(m1)
out1 = os.path.join(OUTDIR, "pickup_heatmap.html")
m1.save(out1)
print(f"  [OK] pickup_heatmap.html")

# -----------------------------------------------------------------------------
# MAP 2 & 3: H3 hex grid -- demand + cancellation choropleth
# -----------------------------------------------------------------------------
if HAS_H3:
    print("[2/5] Building H3 hex demand map ...")
    RES = 8
    geo_df = geo_df.copy()
    geo_df["h3_cell"] = geo_df.apply(
        lambda r: h3.latlng_to_cell(r["pickup_lat"], r["pickup_lon"], RES), axis=1
    )
    geo_df["is_cancelled"] = geo_df["Booking Status"].str.contains("Cancel", case=False, na=False)

    hex_stats = geo_df.groupby("h3_cell").agg(
        bookings=("Booking ID", "count"),
        cancellation_rate=("is_cancelled", "mean"),
        avg_fare=("Booking Value", "mean"),
    ).reset_index()
    hex_stats["cancellation_rate_pct"] = hex_stats["cancellation_rate"] * 100

    # Top 10 zones
    top10 = hex_stats.nlargest(10, "bookings")[["h3_cell", "bookings", "cancellation_rate_pct", "avg_fare"]]
    print("\n  -- Top 10 H3 Zones by Booking Volume --")
    print(top10.to_string(index=False))

    def hex_center(cell):
        lat, lon = h3.cell_to_latlng(cell)
        return lat, lon

    def hex_boundary_geojson(cell):
        # h3 v4: cell_to_boundary returns list of (lat,lon) tuples
        boundary_latlon = h3.cell_to_boundary(cell)
        # GeoJSON needs [lon, lat] and must close the ring
        boundary = [[lon, lat] for lat, lon in boundary_latlon]
        boundary.append(boundary[0])  # close ring
        return {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [boundary]},
            "properties": {}
        }


    def build_hex_map(stat_col, title, color_scale, out_name):
        m = folium.Map(location=NCR_CENTER, zoom_start=11,
                       tiles="CartoDB dark_matter")
        vmin = hex_stats[stat_col].quantile(0.05)
        vmax = hex_stats[stat_col].quantile(0.95)

        import branca.colormap as cm
        cmap = cm.linear.YlOrRd_09.scale(vmin, vmax)
        cmap.caption = title

        for _, row in hex_stats.iterrows():
            val = row[stat_col]
            color = cmap(min(max(val, vmin), vmax))
            geo = hex_boundary_geojson(row["h3_cell"])
            folium.GeoJson(
                geo,
                style_function=lambda _, c=color: {
                    "fillColor": c, "color": "#ffffff22",
                    "weight": 0.5, "fillOpacity": 0.75
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=[],
                    aliases=[],
                    localize=True
                )
            ).add_to(m)

        cmap.add_to(m)

        # Mark top 10 centroids
        for _, row in top10.iterrows():
            clat, clon = hex_center(row["h3_cell"])
            folium.CircleMarker(
                [clat, clon], radius=8,
                color="#f5a623", fill=True, fill_color="#f5a623", fill_opacity=0.9,
                tooltip=f"Bookings: {row['bookings']:,} | Cancel: {row['cancellation_rate_pct']:.1f}%"
            ).add_to(m)

        out_path = os.path.join(OUTDIR, out_name)
        m.save(out_path)
        print(f"  [OK] {out_name}")

    build_hex_map("bookings", "Booking Volume", "YlOrRd", "h3_demand_hex.html")
    build_hex_map("cancellation_rate_pct", "Cancellation Rate %", "RdYlGn_r", "cancellation_rate_hex.html")

else:
    print("[2/5] Skipping H3 maps (h3 not installed)")

# -----------------------------------------------------------------------------
# MAP 4: OD Flow map -- top 15 pairs
# -----------------------------------------------------------------------------
print("[4/5] Building OD flow map ...")
od = (df.dropna(subset=["pickup_lat","pickup_lon","drop_lat","drop_lon"])
        .groupby(["Pickup Location","Drop Location","pickup_lat","pickup_lon","drop_lat","drop_lon"])
        .size().reset_index(name="count")
        .sort_values("count", ascending=False).head(15))

m4 = folium.Map(location=NCR_CENTER, zoom_start=11, tiles="CartoDB dark_matter")

max_count = od["count"].max()
for _, row in od.iterrows():
    weight = max(1, int(row["count"] / max_count * 12))
    opacity = 0.4 + 0.5 * (row["count"] / max_count)
    AntPath(
        locations=[[row["pickup_lat"], row["pickup_lon"]],
                   [row["drop_lat"],   row["drop_lon"]]],
        weight=weight, color="#e94560", opacity=opacity,
        dash_array=[10, 20], delay=1200,
        tooltip=f"{row['Pickup Location']} -> {row['Drop Location']}: {row['count']:,} rides"
    ).add_to(m4)
    for (lat, lon, icon) in [
        (row["pickup_lat"], row["pickup_lon"], ">"),
        (row["drop_lat"],   row["drop_lon"],   "o"),
    ]:
        folium.CircleMarker([lat, lon], radius=4, color="#f5a623",
                            fill=True, fill_opacity=0.9).add_to(m4)

out4 = os.path.join(OUTDIR, "od_flow_map.html")
m4.save(out4)
print(f"  [OK] od_flow_map.html")

# -----------------------------------------------------------------------------
# MAP 5: Time-animated Plotly scatter_mapbox by hour
# -----------------------------------------------------------------------------
print("[5/5] Building animated demand map ...")
anim_df = (geo_df.dropna(subset=["hour_of_day"])
                  .assign(hour_of_day=lambda d: d["hour_of_day"].astype(int).astype(str).str.zfill(2))
                  .groupby(["hour_of_day","Pickup Location","pickup_lat","pickup_lon"])
                  .size().reset_index(name="ride_count"))

fig5 = px.scatter_mapbox(
    anim_df,
    lat="pickup_lat", lon="pickup_lon",
    size="ride_count", color="ride_count",
    animation_frame="hour_of_day",
    hover_name="Pickup Location",
    color_continuous_scale="YlOrRd",
    size_max=30,
    zoom=10, center=dict(lat=28.6, lon=77.1),
    mapbox_style=MAPBOX_STYLE,
    title="Hourly Demand Shift Across NCR",
    template="plotly_dark",
    height=700,
)
fig5.update_layout(
    coloraxis_colorbar=dict(title="Rides"),
    paper_bgcolor="#1a1a2e",
    plot_bgcolor="#1a1a2e",
)
out5 = os.path.join(OUTDIR, "demand_animation.html")
fig5.write_html(out5)
print(f"  [OK] demand_animation.html")

# -- Static PNG snapshots via Plotly (kaleido) ---------------------------------
try:
    # Simple static version for portfolio
    snap_df = anim_df.groupby(["Pickup Location","pickup_lat","pickup_lon"])["ride_count"].sum().reset_index()
    fig_snap = px.scatter_mapbox(
        snap_df, lat="pickup_lat", lon="pickup_lon",
        size="ride_count", color="ride_count",
        hover_name="Pickup Location",
        color_continuous_scale="YlOrRd", size_max=35,
        zoom=10, center=dict(lat=28.6, lon=77.1),
        mapbox_style=MAPBOX_STYLE,
        title="NCR Pickup Demand Overview",
        template="plotly_dark", height=700,
    )
    fig_snap.write_image(os.path.join(OUTDIR, "demand_overview_snapshot.png"))
    print("  [OK] demand_overview_snapshot.png")
except Exception as e:
    print(f"  [WARN] PNG snapshot failed: {e}")

print(f"\n[DONE] All geospatial maps saved to {OUTDIR}")
