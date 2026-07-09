"""
02b_merge_geocoords.py
The geocoding cache (locations_geocoded.csv) is already saved.
This script merges lat/lon back into cleaned_uber_data.csv and
computes haversine distances.
"""
import sys, os, math
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEANED   = os.path.join(BASE, "data", "cleaned_uber_data.csv")
GEO_CACHE = os.path.join(BASE, "data", "locations_geocoded.csv")

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))

print("Loading data ...")
df       = pd.read_csv(CLEANED, low_memory=False)
cache_df = pd.read_csv(GEO_CACHE)

print(f"  Cleaned rows:          {len(df):,}")
print(f"  Geocoded locations:    {len(cache_df):,}  (success: {cache_df['lat'].notna().sum()})")

# Drop old geo columns if they exist (from a previous partial run)
for col in ["pickup_lat","pickup_lon","drop_lat","drop_lon","haversine_km","dist_deviation_pct"]:
    if col in df.columns:
        df.drop(columns=[col], inplace=True)

# Build lookup dict
geo_map = {row.location: (row.lat, row.lon) for row in cache_df.itertuples()}

df["pickup_lat"] = df["Pickup Location"].map(lambda x: geo_map.get(x, (np.nan, np.nan))[0])
df["pickup_lon"] = df["Pickup Location"].map(lambda x: geo_map.get(x, (np.nan, np.nan))[1])
df["drop_lat"]   = df["Drop Location"].map(lambda x: geo_map.get(x, (np.nan, np.nan))[0])
df["drop_lon"]   = df["Drop Location"].map(lambda x: geo_map.get(x, (np.nan, np.nan))[1])

geo_ok = df["pickup_lat"].notna().sum()
print(f"  Rows with pickup coords: {geo_ok:,} ({geo_ok/len(df):.1%})")

# Haversine vs Ride Distance
print("Computing haversine distances ...")
def safe_haversine(row):
    try:
        if any(pd.isna([row.pickup_lat, row.pickup_lon, row.drop_lat, row.drop_lon])):
            return np.nan
        return haversine(float(row.pickup_lat), float(row.pickup_lon),
                         float(row.drop_lat),   float(row.drop_lon))
    except Exception:
        return np.nan

df["haversine_km"] = df.apply(safe_haversine, axis=1)

ride_dist = pd.to_numeric(df["Ride Distance"], errors="coerce")
df["dist_deviation_pct"] = (
    abs(df["haversine_km"] - ride_dist) / ride_dist.replace(0, np.nan) * 100
)
flagged = (df["dist_deviation_pct"] > 20).sum()
valid   = df["haversine_km"].notna().sum()
print(f"  Rows with haversine computed:   {valid:,}")
print(f"  Rows with >20%% distance drift:  {flagged:,} ({flagged/max(valid,1):.1%})")

df.to_csv(CLEANED, index=False)
print(f"\n[DONE] Geocoords merged -> {CLEANED}  (shape: {df.shape})")
