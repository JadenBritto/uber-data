"""
Task 5: Advanced Analysis
- DBSCAN hotspot clustering on pickup coords -> hotspot_clusters.csv
- Isolation Forest anomaly detection on Booking Value
- Prophet demand forecasting per top-5 zones -> forecast_results.csv
- VTAT supply-demand proxy heatmap (saved as PNG)
"""
import sys, os, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

warnings.filterwarnings("ignore")

BASE         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA         = os.path.join(BASE, "data", "cleaned_uber_data.csv")
CLUSTER_OUT  = os.path.join(BASE, "hotspot_clusters.csv")
FORECAST_OUT = os.path.join(BASE, "forecast_results.csv")
OUTDIR       = os.path.join(BASE, "output", "eda")

PALETTE = "#1a1a2e"
TEAL    = "#16213e"
ACCENT  = "#e94560"
GOLD    = "#f5a623"

plt.rcParams.update({
    "figure.facecolor": PALETTE, "axes.facecolor": TEAL,
    "axes.edgecolor": "#ffffff33", "axes.labelcolor": "white",
    "xtick.color": "white", "ytick.color": "white", "text.color": "white",
    "grid.color": "#ffffff22", "grid.linestyle": "--",
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.titlesize": 14, "axes.titleweight": "bold",
})

# ── Load ───────────────────────────────────────────────────────────────────────
print("Loading cleaned data ...")
df = pd.read_csv(DATA, low_memory=False)
df["Date"]          = pd.to_datetime(df["Date"], errors="coerce")
df["hour_of_day"]   = pd.to_numeric(df["hour_of_day"],   errors="coerce")
df["Booking Value"] = pd.to_numeric(df["Booking Value"], errors="coerce")
df["Ride Distance"] = pd.to_numeric(df["Ride Distance"], errors="coerce")
df["Avg VTAT"]      = pd.to_numeric(df["Avg VTAT"],      errors="coerce")

HAS_GEO = "pickup_lat" in df.columns
if HAS_GEO:
    df["pickup_lat"] = pd.to_numeric(df["pickup_lat"], errors="coerce")
    df["pickup_lon"] = pd.to_numeric(df["pickup_lon"], errors="coerce")
    print(f"  Geocoords available: {df['pickup_lat'].notna().sum():,} rows")
else:
    print("  [INFO] No geocoords - DBSCAN will be skipped")
print(f"  {len(df):,} total rows")


# =============================================================================
# PART 1: DBSCAN Clustering
# =============================================================================
print("\n[1/4] DBSCAN hotspot clustering ...")
if not HAS_GEO:
    print("  [SKIP] Run 02_geocoding.py then 02b_merge_geocoords.py first")
else:
    geo = df.dropna(subset=["pickup_lat","pickup_lon"])[["pickup_lat","pickup_lon"]].copy()
    coords_rad = np.radians(geo.values)
    eps_rad = 1.0 / 6371.0   # 1 km radius in radians

    db = DBSCAN(eps=eps_rad, min_samples=50, algorithm="ball_tree", metric="haversine")
    labels = db.fit_predict(coords_rad)
    geo["cluster"] = labels

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise    = (labels == -1).sum()
    print(f"  Clusters found: {n_clusters}")
    print(f"  Noise points:   {n_noise:,} ({n_noise/len(geo):.1%})")

    cluster_summary = geo.groupby("cluster").agg(
        count=("cluster","size"),
        centroid_lat=("pickup_lat","mean"),
        centroid_lon=("pickup_lon","mean"),
    ).reset_index()
    cluster_summary = (cluster_summary[cluster_summary["cluster"] != -1]
                       .sort_values("count", ascending=False))
    print("\n  Top 10 clusters:")
    print(cluster_summary.head(10).to_string(index=False))

    cluster_summary.to_csv(CLUSTER_OUT, index=False)
    print(f"  [OK] Saved -> {CLUSTER_OUT}")

    # Cluster scatter plot
    fig, ax = plt.subplots(figsize=(10, 10))
    colors_cm = plt.cm.tab20(np.linspace(0, 1, max(n_clusters, 1)))
    for i, lbl in enumerate(sorted(set(labels))):
        mask  = geo["cluster"] == lbl
        color = "#555555" if lbl == -1 else colors_cm[i % len(colors_cm)]
        alpha = 0.12 if lbl == -1 else 0.6
        sz    = 1    if lbl == -1 else 8
        ax.scatter(geo.loc[mask, "pickup_lon"], geo.loc[mask, "pickup_lat"],
                   c=[color], s=sz, alpha=alpha)
    for _, row in cluster_summary.head(15).iterrows():
        ax.scatter(row["centroid_lon"], row["centroid_lat"],
                   s=120, marker="*", color=GOLD, zorder=5)
        ax.annotate(f"C{int(row['cluster'])}", (row["centroid_lon"], row["centroid_lat"]),
                    color="white", fontsize=7, ha="center", va="bottom")
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    ax.set_title(f"DBSCAN Pickup Hotspots -- {n_clusters} clusters (eps=1 km, min_samples=50)")
    ax.grid(zorder=0)
    fig.savefig(os.path.join(OUTDIR, "dbscan_clusters.png"), dpi=150,
                bbox_inches="tight", facecolor=PALETTE)
    plt.close(fig)
    print("  [OK] dbscan_clusters.png")


# =============================================================================
# PART 2: Isolation Forest
# =============================================================================
print("\n[2/4] Isolation Forest anomaly detection ...")
feat_cols = ["Booking Value", "Ride Distance", "hour_of_day"]
iso_df = df[feat_cols].dropna().copy()
scaler = StandardScaler()
X = scaler.fit_transform(iso_df)

iso = IsolationForest(n_estimators=200, contamination=0.02, random_state=42, n_jobs=-1)
iso_df["anomaly"]       = iso.fit_predict(X)
iso_df["anomaly_score"] = iso.score_samples(X)

n_anom = (iso_df["anomaly"] == -1).sum()
print(f"  Anomalies detected: {n_anom:,} ({n_anom/len(iso_df):.1%})")

df_idx = df[feat_cols].dropna().index
df.loc[df_idx, "anomaly_flag"]  = iso_df["anomaly"].values
df.loc[df_idx, "anomaly_score"] = iso_df["anomaly_score"].values

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
for ax, col in zip(axes, ["Booking Value", "Ride Distance"]):
    normal  = iso_df[iso_df["anomaly"] ==  1][col]
    anomaly = iso_df[iso_df["anomaly"] == -1][col]
    ax.hist(normal,  bins=60, alpha=0.7, color="#4ecdc4", label="Normal",  density=True)
    ax.hist(anomaly, bins=30, alpha=0.7, color=ACCENT,    label="Anomaly", density=True)
    ax.set_xlabel(col); ax.set_ylabel("Density")
    ax.set_title(f"Anomaly Distribution -- {col}")
    ax.legend(facecolor=TEAL, edgecolor="none")
    ax.grid(axis="y")
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "anomaly_distribution.png"), dpi=150,
            bbox_inches="tight", facecolor=PALETTE)
plt.close(fig)
print("  [OK] anomaly_distribution.png")


# =============================================================================
# PART 3: Prophet demand forecasting
# =============================================================================
print("\n[3/4] Prophet demand forecasting ...")
try:
    from prophet import Prophet

    top5_zones = df["Pickup Location"].value_counts().head(5).index.tolist()
    all_forecasts = []

    for zone in top5_zones:
        zone_df = (df[df["Pickup Location"] == zone]
                   .groupby("Date").size().reset_index(name="y"))
        zone_df.columns = ["ds", "y"]
        zone_df = zone_df.dropna()

        if len(zone_df) < 30:
            print(f"  [SKIP] {zone}: only {len(zone_df)} days of data")
            continue

        m = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.1,
            seasonality_mode="multiplicative",
        )
        # Suppress Prophet output
        import logging
        logging.getLogger("prophet").setLevel(logging.ERROR)
        logging.getLogger("cmdstanpy").setLevel(logging.ERROR)

        m.fit(zone_df)
        future   = m.make_future_dataframe(periods=30)
        forecast = m.predict(future)
        forecast["zone"] = zone
        all_forecasts.append(forecast[["ds","zone","yhat","yhat_lower","yhat_upper"]])

        fig, ax = plt.subplots(figsize=(14, 5))
        ax.fill_between(forecast["ds"], forecast["yhat_lower"], forecast["yhat_upper"],
                        alpha=0.2, color=GOLD, label="Uncertainty band")
        ax.plot(forecast["ds"], forecast["yhat"], color=GOLD, lw=2, label="Forecast")
        ax.scatter(zone_df["ds"], zone_df["y"], s=10, color="#4ecdc4",
                   alpha=0.7, label="Actual", zorder=3)
        ax.axvline(zone_df["ds"].max(), color="white", linestyle="--", alpha=0.5, lw=1,
                   label="Forecast start")
        ax.set_title(f"Prophet Forecast -- {zone}")
        ax.set_xlabel("Date"); ax.set_ylabel("Daily Bookings")
        ax.legend(facecolor=TEAL, edgecolor="none")
        ax.grid(zorder=0)
        safe_name = zone.replace(" ", "_").replace("/", "_")
        fig.savefig(os.path.join(OUTDIR, f"forecast_{safe_name}.png"),
                    dpi=150, bbox_inches="tight", facecolor=PALETTE)
        plt.close(fig)
        print(f"  [OK] Forecast chart for '{zone}'")

    if all_forecasts:
        pd.concat(all_forecasts).to_csv(FORECAST_OUT, index=False)
        print(f"  [OK] Saved -> {FORECAST_OUT}")

except ImportError:
    print("  [SKIP] Prophet not installed")


# =============================================================================
# PART 4: VTAT supply-demand proxy heatmap
# =============================================================================
print("\n[4/4] VTAT supply-demand proxy ...")
vtat_df = (df[df["Avg VTAT"].notna() & df["hour_of_day"].notna()]
             .groupby(["Pickup Location","hour_of_day"])["Avg VTAT"]
             .mean().reset_index())

vtat_pivot = vtat_df.pivot(index="Pickup Location",
                            columns="hour_of_day",
                            values="Avg VTAT")
top20 = vtat_pivot.notna().sum(axis=1).nlargest(20).index
vtat_pivot = vtat_pivot.loc[top20]

fig, ax = plt.subplots(figsize=(18, 8))
sns.heatmap(vtat_pivot, ax=ax, cmap="YlOrRd",
            linewidths=0.3, linecolor="#00000033",
            cbar_kws={"label": "Avg VTAT (min)", "shrink": 0.8})
ax.set_title("Supply-Demand Imbalance Proxy (Avg VTAT by Location x Hour)\n"
             "Higher VTAT = longer driver wait = under-supply")
ax.set_xlabel("Hour of Day"); ax.set_ylabel("Pickup Location")
ax.tick_params(axis="x", labelsize=9)
ax.tick_params(axis="y", labelsize=8)
fig.savefig(os.path.join(OUTDIR, "vtat_heatmap.png"), dpi=150,
            bbox_inches="tight", facecolor=PALETTE)
plt.close(fig)
print("  [OK] vtat_heatmap.png")

# Save anomaly flags back to cleaned CSV
df.to_csv(DATA, index=False)
print(f"\n[DONE] Advanced analysis complete. Cleaned data updated -> {DATA}")
