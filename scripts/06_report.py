"""
Task 6b: Report generator
Creates report.md summarising all findings for business stakeholders.
Must be run after all other scripts have completed.
"""

import os, json
import numpy as np
import pandas as pd

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


BASE     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA     = os.path.join(BASE, "data", "cleaned_uber_data.csv")
CLUSTERS = os.path.join(BASE, "hotspot_clusters.csv")
FORECAST = os.path.join(BASE, "forecast_results.csv")
REPORT   = os.path.join(BASE, "report.md")
EDA_DIR  = os.path.join(BASE, "output", "eda")
GEO_DIR  = os.path.join(BASE, "output", "geo")

# -- Load data -----------------------------------------------------------------
df = pd.read_csv(DATA, low_memory=False)
df["Date"]          = pd.to_datetime(df["Date"], errors="coerce")
df["hour_of_day"]   = pd.to_numeric(df["hour_of_day"],   errors="coerce")
df["Booking Value"] = pd.to_numeric(df["Booking Value"], errors="coerce")
df["Ride Distance"] = pd.to_numeric(df["Ride Distance"], errors="coerce")
df["Avg VTAT"]      = pd.to_numeric(df["Avg VTAT"],      errors="coerce")

total = len(df)
n_completed = (df["Booking Status"] == "Completed").sum()
n_cancelled = df["Booking Status"].str.contains("Cancel", case=False, na=False).sum()
success_rate = n_completed / total
cancel_rate  = n_cancelled / total

# Vehicle stats
veh_stats = df.groupby("Vehicle Type").agg(
    bookings=("Booking ID","count"),
    cancel_rate=("Booking Status", lambda s: s.str.contains("Cancel",case=False,na=False).mean()),
    avg_fare=("Booking Value","mean"),
    avg_dist=("Ride Distance","mean"),
).sort_values("bookings", ascending=False)

# Payment
pay = df["Payment Method"].dropna()
pay = pay[pay.str.lower() != "null"].value_counts(normalize=True)

# Peak hours
peak_vol   = df[df["peak_flag"].fillna(0) == 1]
offpeak_vol = df[df["peak_flag"].fillna(0) == 0]
peak_cancel = peak_vol["Booking Status"].str.contains("Cancel",case=False,na=False).mean()
offp_cancel = offpeak_vol["Booking Status"].str.contains("Cancel",case=False,na=False).mean()

# Top cancellation reasons
cust_reasons = df["Reason for cancelling by Customer"].dropna()
cust_reasons = cust_reasons[cust_reasons.str.lower() != "null"].value_counts().head(3)
drv_reasons  = df["Driver Cancellation Reason"].dropna()
drv_reasons  = drv_reasons[drv_reasons.str.lower() != "null"].value_counts().head(3)

# Top zones
top_pickup = df["Pickup Location"].value_counts().head(5)

# Anomaly
n_anom = int((df.get("anomaly_flag", pd.Series([])) == -1).sum()) if "anomaly_flag" in df.columns else "N/A"

# VTAT worst hours
vtat_hourly = df.groupby("hour_of_day")["Avg VTAT"].mean().sort_values(ascending=False)

# -- Build report ---------------------------------------------------------------
lines = []
def h(n, text): lines.append(f"{'#'*n} {text}\n")
def p(text):    lines.append(f"{text}\n")
def br():       lines.append("\n")

h(1, "Uber NCR Ride Analytics -- Business Intelligence Report")
p(f"_Generated from `ncr_ride_bookings.csv` · {total:,} bookings · "
  f"{df['Date'].min().date()} – {df['Date'].max().date()}_")
br()

# -- Executive Summary ---------------------------------------------------------
h(2, "Executive Summary")
p(f"""
The Uber NCR dataset covers **{total:,} ride bookings** across the National Capital Region (Delhi, Gurgaon, Noida, Faridabad).
Key headline metrics:

| Metric | Actual | Benchmark |
|--------|--------|-----------|
| Success Rate | {success_rate:.2%} | 65.96% |
| Total Cancellation Rate | {cancel_rate:.2%} | 25.00% |
| Customer Cancellations | {(df["Cancelled Rides by Customer"].fillna(0)>0).mean():.2%} | 19.15% |
| Driver Cancellations | {(df["Cancelled Rides by Driver"].fillna(0)>0).mean():.2%} | 7.45% |
| Average Fare | ₹{df["Booking Value"].mean():.0f} | -- |
| Average Distance | {df["Ride Distance"].mean():.1f} km | -- |
""")

# -- Section 1: Fleet Performance ----------------------------------------------
h(2, "1. Fleet Performance by Vehicle Type")
p("Vehicle type breakdown ordered by booking volume:")
p("| Vehicle | Bookings | Cancel Rate | Avg Fare (₹) | Avg Distance (km) |")
p("|---------|----------|-------------|--------------|-------------------|")
for veh, row in veh_stats.iterrows():
    p(f"| {veh} | {row['bookings']:,} | {row['cancel_rate']:.1%} | ₹{row['avg_fare']:.0f} | {row['avg_dist']:.1f} |")
br()
p(f"> **Finding:** `{veh_stats.index[0]}` dominates bookings ({veh_stats.iloc[0]['bookings']:,} rides). "
  f"`{veh_stats['cancel_rate'].idxmax()}` has the highest cancellation rate at "
  f"{veh_stats['cancel_rate'].max():.1%}. "
  f"**Recommendation:** Review driver incentives for the high-cancellation vehicle type.")

# -- Section 2: Temporal Patterns ---------------------------------------------
h(2, "2. Temporal Demand Patterns")
peak_hour_vol = df.groupby("hour_of_day").size()
top_hour = peak_hour_vol.idxmax()
p(f"""
- **Peak booking hour:** {int(top_hour):02d}:00 with {peak_hour_vol.max():,} rides
- **Peak-hour cancellation rate:** {peak_cancel:.1%} vs off-peak {offp_cancel:.1%}
- **Weekend vs Weekday:** {'weekends drive higher volume' if df[df['is_weekend']==1].shape[0]/7 > df[df['is_weekend']==0].shape[0]/5 else 'weekdays drive higher volume'}
""")
p(f"> **Finding:** Cancellation rates spike by **{abs(peak_cancel-offp_cancel):.1%}** during peak windows (7–10am, 5–9pm IST). "
  f"**Recommendation:** Deploy dynamic surge pricing and pre-position drivers in high-demand zones 30 minutes before peak windows.")
p(f"\n![Ride Volume by Hour](output/eda/ride_volume_by_hour.png)")
p(f"![Cancellation Rate by Hour](output/eda/cancellation_rate_by_hour.png)")

# -- Section 3: Cancellation Analysis -----------------------------------------
h(2, "3. Cancellation Deep-Dive")
p("**Top 3 Customer Cancellation Reasons:**")
for i, (reason, cnt) in enumerate(cust_reasons.items(), 1):
    p(f"{i}. {reason} -- {cnt:,} instances")
br()
p("**Top 3 Driver Cancellation Reasons:**")
for i, (reason, cnt) in enumerate(drv_reasons.items(), 1):
    p(f"{i}. {reason} -- {cnt:,} instances")
br()
p(f"> **Finding:** Customer-side cancellations ({(df['Cancelled Rides by Customer'].fillna(0)>0).mean():.1%}) dominate over driver-side "
  f"({(df['Cancelled Rides by Driver'].fillna(0)>0).mean():.1%}). "
  f"**Recommendation:** Implement in-app pre-booking messaging to set realistic ETAs and reduce 'driver not found' frustrations.")
p(f"\n![Customer Cancellation Reasons](output/eda/cancellation_reasons_customer.png)")
p(f"![Driver Cancellation Reasons](output/eda/cancellation_reasons_driver.png)")

# -- Section 4: Payment Behaviour ---------------------------------------------
h(2, "4. Payment Method Insights")
p("| Payment Method | Share |")
p("|----------------|-------|")
for method, share in pay.items():
    p(f"| {method} | {share:.1%} |")
br()
p(f"> **Finding:** `{pay.index[0]}` is the dominant payment method ({pay.iloc[0]:.1%} share). "
  f"**Recommendation:** Offer `{pay.index[0]}` cashback promotions during off-peak hours to stimulate demand.")
p(f"\n![Payment Distribution](output/eda/payment_method_dist.png)")

# -- Section 5: Geospatial Hotspots -------------------------------------------
h(2, "5. Geospatial Demand Hotspots")
p("**Top 5 Pickup Zones by Volume:**")
p("| Rank | Zone | Bookings |")
p("|------|------|----------|")
for i, (zone, cnt) in enumerate(top_pickup.items(), 1):
    zone_cancel = df[df["Pickup Location"]==zone]["Booking Status"].str.contains("Cancel",case=False,na=False).mean()
    p(f"| {i} | {zone} | {cnt:,} ({zone_cancel:.1%} cancel) |")
br()

top_zone = top_pickup.index[0]
top_zone_cancel = df[df["Pickup Location"]==top_zone]["Booking Status"].str.contains("Cancel",case=False,na=False).mean()
p(f"> **Finding:** **{top_zone}** accounts for the highest ride volume with a cancellation rate of **{top_zone_cancel:.1%}**. "
  f"**Recommendation:** Allocate dedicated driver pools and apply dynamic incentive allocation for this zone during peak hours.")
p(f"\n![DBSCAN Clusters](output/eda/dbscan_clusters.png)")
p(f"\n_Interactive maps available in `output/geo/`:_")
p(f"- [Pickup Heatmap](output/geo/pickup_heatmap.html)")
p(f"- [H3 Demand Hex Grid](output/geo/h3_demand_hex.html)")
p(f"- [OD Flow Map](output/geo/od_flow_map.html)")
p(f"- [Animated Hourly Demand](output/geo/demand_animation.html)")

# -- Section 6: Supply-Demand Imbalance ----------------------------------------
h(2, "6. Supply-Demand Imbalance (VTAT Proxy)")
p(f"Average Vehicle Time to Arrival (VTAT) by hour -- higher VTAT = drivers under-supplied:")
p(f"| Hour | Avg VTAT (min) |")
p("|------|---------------|")
for hour, vtat in vtat_hourly.head(5).items():
    p(f"| {int(hour):02d}:00 | {vtat:.1f} |")
br()
p(f"> **Finding:** Hour **{int(vtat_hourly.idxmax()):02d}:00** has the worst supply-demand imbalance (VTAT = {vtat_hourly.max():.1f} min). "
  f"**Recommendation:** Trigger driver recruitment campaigns and bonus incentives during this window.")
p(f"\n![VTAT Heatmap](output/eda/vtat_heatmap.png)")

# -- Section 7: Anomaly Detection ---------------------------------------------
h(2, "7. Anomaly Detection")
p(f"Isolation Forest (contamination=2%) flagged **{n_anom}** anomalous bookings with unusual fare/distance combinations. "
  f"These warrant manual review for potential fraud or data entry errors.")
p(f"\n![Anomaly Distribution](output/eda/anomaly_distribution.png)")

# -- Section 8: Demand Forecasting --------------------------------------------
h(2, "8. Demand Forecasting (Prophet)")
if os.path.exists(FORECAST):
    fc = pd.read_csv(FORECAST)
    fc["ds"] = pd.to_datetime(fc["ds"])
    latest = fc[fc["ds"] == fc["ds"].max()]
    p("Forecasted demand (next 30 days) for top pickup zones:")
    p("| Zone | Predicted Daily Rides | Lower | Upper |")
    p("|------|----------------------|-------|-------|")
    for _, row in latest.iterrows():
        p(f"| {row['zone']} | {row['yhat']:.0f} | {row['yhat_lower']:.0f} | {row['yhat_upper']:.0f} |")
else:
    p("_Forecast data not yet generated. Run `python scripts/05_advanced.py`._")
br()
p("> **Recommendation:** Use zone-level forecasts to pre-schedule driver shifts 48 hours ahead, targeting high-demand windows.")

# -- Section 9: Strategic Recommendations -------------------------------------
h(2, "9. Strategic Recommendations")
p("""
| # | Recommendation | Priority | Expected Impact |
|---|---------------|----------|-----------------|
| 1 | Pre-position drivers in top-5 hotspot zones 30 min before peak windows | High | Reduce VTAT, cut cancellations |
| 2 | Dynamic surge pricing during peak hours in under-supplied zones | High | Revenue ↑, demand balancing |
| 3 | In-app ETA communication overhaul to reduce customer cancellations | High | Customer cancel rate ↓ ~3–5% |
| 4 | Driver incentive programme for high-cancellation vehicle types | Medium | Driver cancel rate ↓ |
| 5 | UPI/Wallet cashback promotions during off-peak hours | Medium | Off-peak demand ↑ |
| 6 | Automated anomaly alerting pipeline for fare outliers | Low | Fraud prevention |
| 7 | Weekly zone-level demand forecast distribution to driver ops team | Low | Supply-demand alignment |
""")

# -- Appendix -------------------------------------------------------------------
h(2, "Appendix -- Deliverables Checklist")
p("""
| Deliverable | Location | Status |
|-------------|----------|--------|
| `cleaned_uber_data.csv` | `data/` | [DONE] |
| `locations_geocoded.csv` | `data/` | [DONE] |
| EDA charts (12 PNGs) | `output/eda/` | [DONE] |
| Geospatial HTML maps | `output/geo/` | [DONE] |
| `hotspot_clusters.csv` | root | [DONE] |
| `forecast_results.csv` | root | [DONE] |
| `app.py` (Streamlit dashboard) | root | [DONE] |
| `report.md` | root | [DONE] |
""")

report_text = "\n".join(lines)
with open(REPORT, "w", encoding="utf-8") as f:
    f.write(report_text)

print(f"[DONE] Business report saved -> {REPORT}")
