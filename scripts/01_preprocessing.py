"""
Task 1: Data Preprocessing
Loads ncr_ride_bookings.csv, cleans, enriches, validates KPIs,
outputs data/cleaned_uber_data.csv + quality report.
"""

import os
import re
import math
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW  = os.path.join(BASE, "ncr_ride_bookings.csv")
OUT  = os.path.join(BASE, "data", "cleaned_uber_data.csv")

# ── KPI benchmarks ──────────────────────────────────────────────────────────
KPI = dict(success=0.6596, cancel_total=0.25,
           cancel_cust=0.1915, cancel_driver=0.0745)

# ── 1. Load ──────────────────────────────────────────────────────────────────
print("Loading dataset …")
df = pd.read_csv(RAW, low_memory=False)
print(f"  Raw shape: {df.shape}")

# ── 2. Strip stray quotes from ID columns ────────────────────────────────────
for col in ["Booking ID", "Customer ID"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip('"').str.strip("'").str.strip()

# ── 3. Datetime parsing ───────────────────────────────────────────────────────
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Time"] = pd.to_datetime(df["Time"], format="%H:%M:%S", errors="coerce").dt.time

# ── 4. Numeric columns ────────────────────────────────────────────────────────
NUM_COLS = [
    "Avg VTAT", "Avg CTAT",
    "Cancelled Rides by Customer", "Cancelled Rides by Driver",
    "Incomplete Rides", "Booking Value", "Ride Distance",
    "Driver Ratings", "Customer Rating",
]
for c in NUM_COLS:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c].replace("null", np.nan), errors="coerce")

# ── 5. Deduplicate on Booking ID ──────────────────────────────────────────────
before = len(df)
df = df.drop_duplicates(subset=["Booking ID"])
print(f"  Dropped {before - len(df)} duplicate Booking IDs")

# ── 6. Derived features ──────────────────────────────────────────────────────
df["hour_of_day"]  = df["Time"].apply(lambda t: t.hour if pd.notna(t) else np.nan)
df["day_of_week"]  = df["Date"].dt.day_name()
df["is_weekend"]   = df["Date"].dt.dayofweek.isin([5, 6]).astype(int)
df["month"]        = df["Date"].dt.month
df["week_of_year"] = df["Date"].dt.isocalendar().week.astype(int)

def peak_flag(h):
    if pd.isna(h):
        return 0
    h = int(h)
    return 1 if (7 <= h <= 9) or (17 <= h <= 20) else 0

df["peak_flag"] = df["hour_of_day"].apply(peak_flag)

def duration_bucket(km):
    if pd.isna(km):
        return "Unknown"
    if km < 5:
        return "Short (<5 km)"
    elif km < 15:
        return "Medium (5-15 km)"
    elif km < 30:
        return "Long (15-30 km)"
    else:
        return "Very Long (>30 km)"

df["trip_duration_bucket"] = df["Ride Distance"].apply(duration_bucket)
df["fare_per_km"] = np.where(
    (df["Ride Distance"] > 0) & df["Ride Distance"].notna(),
    df["Booking Value"] / df["Ride Distance"],
    np.nan,
)

# ── 7. Consistency flags ──────────────────────────────────────────────────────
# Cancellation reason present but flag == 0
df["flag_cust_reason_no_cancel"] = (
    df["Reason for cancelling by Customer"].notna() &
    (df["Reason for cancelling by Customer"].astype(str).str.lower() != "null") &
    (df["Cancelled Rides by Customer"].fillna(0) == 0)
).astype(int)

df["flag_driver_reason_no_cancel"] = (
    df["Driver Cancellation Reason"].notna() &
    (df["Driver Cancellation Reason"].astype(str).str.lower() != "null") &
    (df["Cancelled Rides by Driver"].fillna(0) == 0)
).astype(int)

# Replace string "null" in reason columns with actual NaN
for c in ["Reason for cancelling by Customer", "Driver Cancellation Reason",
          "Incomplete Rides Reason"]:
    if c in df.columns:
        df[c] = df[c].replace("null", np.nan)

# ── 8. KPI cross-validation ──────────────────────────────────────────────────
status_counts = df["Booking Status"].value_counts(normalize=True)
actual_success = status_counts.get("Completed", 0)
actual_cancel  = status_counts.filter(regex="[Cc]ancel").sum()

# Customer / driver cancellation rate from flag columns
total = len(df)
actual_cust   = (df["Cancelled Rides by Customer"].fillna(0) > 0).sum() / total
actual_driver = (df["Cancelled Rides by Driver"].fillna(0) > 0).sum() / total

print("\n── KPI Cross-Validation ─────────────────────────")
for label, actual, bench in [
    ("Success Rate",          actual_success, KPI["success"]),
    ("Total Cancellation",    actual_cancel,  KPI["cancel_total"]),
    ("Customer Cancellation", actual_cust,    KPI["cancel_cust"]),
    ("Driver Cancellation",   actual_driver,  KPI["cancel_driver"]),
]:
    drift = abs(actual - bench)
    flag  = "⚠ DRIFT" if drift > 0.05 else "✓"
    print(f"  {flag} {label:28s}  actual={actual:.2%}  bench={bench:.2%}  Δ={drift:.2%}")

# ── 9. IQR outlier detection ──────────────────────────────────────────────────
def iqr_outliers(series, name):
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    n_out = ((series < lo) | (series > hi)).sum()
    print(f"  {name}: Q1={q1:.2f} Q3={q3:.2f} IQR={iqr:.2f}  "
          f"bounds=[{lo:.2f}, {hi:.2f}]  outliers={n_out:,}")

print("\n── IQR Outlier Report ───────────────────────────")
iqr_outliers(df["Booking Value"].dropna(),  "Booking Value")
iqr_outliers(df["Ride Distance"].dropna(),  "Ride Distance")

# ── 10. Missingness report ─────────────────────────────────────────────────────
print("\n── Missingness (%) ──────────────────────────────")
miss = (df.isnull().sum() / len(df) * 100).sort_values(ascending=False)
for col, pct in miss[miss > 0].items():
    print(f"  {col:45s}  {pct:.1f}%")

# ── 11. Consistency inconsistency summary ─────────────────────────────────────
print(f"\n  Customer reason but no cancel flag: {df['flag_cust_reason_no_cancel'].sum():,}")
print(f"  Driver reason but no cancel flag:   {df['flag_driver_reason_no_cancel'].sum():,}")

# ── 12. Save ───────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUT), exist_ok=True)
df.to_csv(OUT, index=False)
print(f"\n✅ Saved cleaned dataset → {OUT}")
print(f"   Final shape: {df.shape}")
