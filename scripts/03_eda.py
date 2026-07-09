"""
Task 3: Exploratory Data Analysis
Produces 12 publication-quality charts saved to output/eda/
"""

import os, warnings
import sys
import numpy as np
import pandas as pd
import matplotlib

# Force UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

warnings.filterwarnings("ignore")

BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA   = os.path.join(BASE, "data", "cleaned_uber_data.csv")
OUTDIR = os.path.join(BASE, "output", "eda")
os.makedirs(OUTDIR, exist_ok=True)

# -- Style ----------------------------------------------------------------------
PALETTE   = "#1a1a2e"   # dark background
ACCENT    = "#e94560"
BLUE      = "#0f3460"
GOLD      = "#f5a623"
TEAL      = "#16213e"
COLORS    = ["#e94560", "#0f3460", "#f5a623", "#16213e", "#4ecdc4", "#45b7d1"]

plt.rcParams.update({
    "figure.facecolor":  PALETTE,
    "axes.facecolor":    TEAL,
    "axes.edgecolor":    "#ffffff33",
    "axes.labelcolor":   "white",
    "xtick.color":       "white",
    "ytick.color":       "white",
    "text.color":        "white",
    "grid.color":        "#ffffff22",
    "grid.linestyle":    "--",
    "font.family":       "DejaVu Sans",
    "font.size":         11,
    "axes.titlesize":    14,
    "axes.titleweight":  "bold",
})

def save(fig, name):
    path = os.path.join(OUTDIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=PALETTE)
    plt.close(fig)
    print(f"  [OK] {name}")

# -- Load -----------------------------------------------------------------------
print("Loading cleaned data ...")
df = pd.read_csv(DATA, low_memory=False)
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["hour_of_day"] = pd.to_numeric(df["hour_of_day"], errors="coerce")
print(f"  {len(df):,} rows")

# -- Chart 1: Ride volume by hour -----------------------------------------------
fig, ax = plt.subplots(figsize=(12, 5))
hourly = df.groupby("hour_of_day").size()
ax.bar(hourly.index, hourly.values, color=ACCENT, alpha=0.85, zorder=3)
# shade peak hours
for shade in [(7, 10), (17, 21)]:
    ax.axvspan(shade[0]-0.5, shade[1]-0.5, alpha=0.12, color=GOLD, label="Peak" if shade[0]==7 else "")
ax.set_xlabel("Hour of Day")
ax.set_ylabel("Number of Rides")
ax.set_title("Ride Volume by Hour of Day")
ax.set_xticks(range(0, 24))
ax.grid(axis="y", zorder=0)
ax.legend(["Peak hours"], facecolor=TEAL, edgecolor="none")
save(fig, "ride_volume_by_hour.png")

# -- Chart 2: Cancellation rate by hour ----------------------------------------
fig, ax = plt.subplots(figsize=(12, 5))
hourly_cancel = df.groupby("hour_of_day").apply(
    lambda g: (g["Booking Status"].str.contains("Cancel", case=False, na=False)).mean() * 100
)
ax.plot(hourly_cancel.index, hourly_cancel.values, color=ACCENT, lw=2.5, marker="o", ms=5, zorder=3)
ax.fill_between(hourly_cancel.index, hourly_cancel.values, alpha=0.2, color=ACCENT)
ax.set_xlabel("Hour of Day")
ax.set_ylabel("Cancellation Rate (%)")
ax.set_title("Cancellation Rate by Hour of Day")
ax.set_xticks(range(0, 24))
ax.grid(zorder=0)
save(fig, "cancellation_rate_by_hour.png")

# -- Chart 3: Ride volume by day-of-week ---------------------------------------
dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
fig, ax = plt.subplots(figsize=(10, 5))
dow = df.groupby("day_of_week").size().reindex(dow_order)
bars = ax.bar(range(7), dow.values,
              color=[ACCENT if d in ["Saturday","Sunday"] else BLUE for d in dow_order],
              zorder=3, width=0.6)
ax.set_xticks(range(7))
ax.set_xticklabels(dow_order, rotation=20)
ax.set_ylabel("Number of Rides")
ax.set_title("Ride Volume by Day of Week  (red = weekend)")
ax.grid(axis="y", zorder=0)
save(fig, "ride_volume_by_dow.png")

# -- Chart 4: Cancellation rate by vehicle type --------------------------------
fig, ax = plt.subplots(figsize=(10, 5))
veh_cancel = df.groupby("Vehicle Type").apply(
    lambda g: (g["Booking Status"].str.contains("Cancel", case=False, na=False)).mean() * 100
).sort_values(ascending=False)
colors_veh = sns.color_palette("husl", len(veh_cancel))
ax.barh(veh_cancel.index, veh_cancel.values, color=colors_veh, zorder=3, height=0.6)
ax.set_xlabel("Cancellation Rate (%)")
ax.set_title("Cancellation Rate by Vehicle Type")
ax.grid(axis="x", zorder=0)
for i, v in enumerate(veh_cancel.values):
    ax.text(v + 0.3, i, f"{v:.1f}%", va="center", color="white", fontsize=10)
save(fig, "cancellation_by_vehicle.png")

# -- Chart 5: Booking Value distribution by vehicle type ----------------------
fig, ax = plt.subplots(figsize=(12, 6))
vehicles = df["Vehicle Type"].dropna().unique()
for i, v in enumerate(sorted(vehicles)):
    subset = df[df["Vehicle Type"] == v]["Booking Value"].dropna()
    subset = subset[subset < subset.quantile(0.99)]
    ax.hist(subset, bins=50, alpha=0.6, label=v, color=COLORS[i % len(COLORS)], density=True)
ax.set_xlabel("Booking Value (₹)")
ax.set_ylabel("Density")
ax.set_title("Booking Value Distribution by Vehicle Type")
ax.legend(facecolor=TEAL, edgecolor="none")
ax.grid(axis="y", zorder=0)
save(fig, "booking_value_dist.png")

# -- Chart 6: Ride Distance distribution by vehicle type ----------------------
fig, ax = plt.subplots(figsize=(12, 6))
for i, v in enumerate(sorted(vehicles)):
    subset = df[df["Vehicle Type"] == v]["Ride Distance"].dropna()
    subset = subset[subset < subset.quantile(0.99)]
    ax.hist(subset, bins=50, alpha=0.6, label=v, color=COLORS[i % len(COLORS)], density=True)
ax.set_xlabel("Ride Distance (km)")
ax.set_ylabel("Density")
ax.set_title("Ride Distance Distribution by Vehicle Type")
ax.legend(facecolor=TEAL, edgecolor="none")
ax.grid(axis="y", zorder=0)
save(fig, "ride_distance_dist.png")

# -- Chart 7: Customer cancellation reasons ------------------------------------
fig, ax = plt.subplots(figsize=(10, 6))
cust_reasons = df["Reason for cancelling by Customer"].dropna()
cust_reasons = cust_reasons[cust_reasons.str.lower() != "null"]
counts = cust_reasons.value_counts().head(10)
colors_r = sns.color_palette("rocket_r", len(counts))
ax.barh(counts.index[::-1], counts.values[::-1], color=colors_r[::-1], zorder=3, height=0.6)
ax.set_xlabel("Number of Cancellations")
ax.set_title("Top Customer Cancellation Reasons")
ax.grid(axis="x", zorder=0)
for i, v in enumerate(counts.values[::-1]):
    ax.text(v + 50, i, f"{v:,}", va="center", color="white", fontsize=9)
save(fig, "cancellation_reasons_customer.png")

# -- Chart 8: Driver cancellation reasons -------------------------------------
fig, ax = plt.subplots(figsize=(10, 6))
drv_reasons = df["Driver Cancellation Reason"].dropna()
drv_reasons = drv_reasons[drv_reasons.str.lower() != "null"]
counts_d = drv_reasons.value_counts().head(10)
colors_d = sns.color_palette("mako_r", len(counts_d))
ax.barh(counts_d.index[::-1], counts_d.values[::-1], color=colors_d[::-1], zorder=3, height=0.6)
ax.set_xlabel("Number of Cancellations")
ax.set_title("Top Driver Cancellation Reasons")
ax.grid(axis="x", zorder=0)
for i, v in enumerate(counts_d.values[::-1]):
    ax.text(v + 50, i, f"{v:,}", va="center", color="white", fontsize=9)
save(fig, "cancellation_reasons_driver.png")

# -- Chart 9: Payment method distribution -------------------------------------
fig, ax = plt.subplots(figsize=(8, 8))
pay = df["Payment Method"].dropna()
pay = pay[pay.str.lower() != "null"].value_counts()
wedge_props = dict(width=0.5, edgecolor=PALETTE, linewidth=2)
ax.pie(pay.values, labels=pay.index, autopct="%1.1f%%",
       colors=COLORS[:len(pay)], wedgeprops=wedge_props,
       startangle=140, pctdistance=0.75)
ax.set_title("Payment Method Distribution", pad=20)
save(fig, "payment_method_dist.png")

# -- Chart 10: Avg fare per payment method ------------------------------------
fig, ax = plt.subplots(figsize=(10, 5))
pay_fare = (df[df["Payment Method"].notna() & (df["Payment Method"] != "null")]
            .groupby("Payment Method")["Booking Value"].mean()
            .sort_values(ascending=False))
bars = ax.bar(pay_fare.index, pay_fare.values,
              color=COLORS[:len(pay_fare)], zorder=3, width=0.5)
ax.set_ylabel("Average Fare (₹)")
ax.set_title("Average Booking Value by Payment Method")
ax.grid(axis="y", zorder=0)
for bar, val in zip(bars, pay_fare.values):
    ax.text(bar.get_x() + bar.get_width()/2, val + 5, f"₹{val:.0f}",
            ha="center", color="white", fontsize=10)
save(fig, "avg_fare_by_payment.png")

# -- Chart 11: Driver vs Customer rating correlation ---------------------------
fig, ax = plt.subplots(figsize=(8, 8))
sub = df[["Driver Ratings", "Customer Rating"]].dropna()
sub = sub[(sub["Driver Ratings"] > 0) & (sub["Customer Rating"] > 0)]
h = ax.hexbin(sub["Driver Ratings"], sub["Customer Rating"],
              gridsize=30, cmap="YlOrRd", mincnt=1)
plt.colorbar(h, ax=ax, label="Count")
ax.set_xlabel("Driver Rating")
ax.set_ylabel("Customer Rating")
ax.set_title("Driver Rating vs Customer Rating (Hexbin)")
corr = sub.corr().iloc[0, 1]
ax.text(0.05, 0.95, f"Pearson r = {corr:.3f}",
        transform=ax.transAxes, color="white",
        bbox=dict(facecolor=BLUE, alpha=0.7, edgecolor="none"))
save(fig, "rating_correlation.png")

# -- Chart 12: Rating trend over time -----------------------------------------
fig, ax = plt.subplots(figsize=(14, 5))
trend = (df.groupby("Date")[["Driver Ratings", "Customer Rating"]]
          .mean().rolling(7).mean())
ax.plot(trend.index, trend["Driver Ratings"],  label="Driver Rating",   color="#4ecdc4", lw=2)
ax.plot(trend.index, trend["Customer Rating"], label="Customer Rating", color=GOLD,     lw=2)
ax.set_xlabel("Date")
ax.set_ylabel("Average Rating (7-day rolling)")
ax.set_title("Driver & Customer Rating Trends Over Time")
ax.legend(facecolor=TEAL, edgecolor="none")
ax.grid(zorder=0)
save(fig, "rating_trend_over_time.png")

print(f"\n[DONE] All EDA charts saved to {OUTDIR}")
