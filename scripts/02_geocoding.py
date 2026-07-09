"""
Task 2: Geocoding
Geocodes all unique Pickup/Drop location strings for NCR via Nominatim.
Saves data/locations_geocoded.csv lookup table (cached).
Merges lat/lon back into cleaned_uber_data.csv.
Computes haversine distance vs Ride Distance and flags outliers.
"""

import os, time, math
import numpy as np
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEANED    = os.path.join(BASE, "data", "cleaned_uber_data.csv")
GEO_CACHE  = os.path.join(BASE, "data", "locations_geocoded.csv")

# NCR viewbox: SW (27.7, 76.5) → NE (29.0, 77.8) — Delhi + Gurgaon + Noida + Faridabad
NCR_VIEWBOX = [(76.5, 27.7), (77.8, 29.0)]  # (lon_min, lat_min), (lon_max, lat_max)

# ── Haversine ─────────────────────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlam  = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# ── Load cleaned data ─────────────────────────────────────────────────────────
print("Loading cleaned dataset …")
df = pd.read_csv(CLEANED, low_memory=False)
print(f"  Shape: {df.shape}")

# ── Unique locations ──────────────────────────────────────────────────────────
locs_pickup = df["Pickup Location"].dropna().unique().tolist()
locs_drop   = df["Drop Location"].dropna().unique().tolist()
all_locs    = list(set(locs_pickup + locs_drop))
print(f"  Unique locations to geocode: {len(all_locs)}")

# ── Load or create cache ──────────────────────────────────────────────────────
if os.path.exists(GEO_CACHE):
    cache_df = pd.read_csv(GEO_CACHE)
    cache    = dict(zip(cache_df["location"], zip(cache_df["lat"], cache_df["lon"])))
    print(f"  Cache loaded: {len(cache)} entries")
else:
    cache = {}

# ── Geocode missing entries ───────────────────────────────────────────────────
geolocator = Nominatim(user_agent="uber_ncr_analytics_v1", timeout=10)
geocode    = RateLimiter(geolocator.geocode, min_delay_seconds=1.1, error_wait_seconds=5)

to_geocode = [l for l in all_locs if l not in cache]
print(f"  Locations to geocode (not cached): {len(to_geocode)}")

for i, loc in enumerate(to_geocode):
    query = f"{loc}, Delhi NCR, India"
    try:
        result = geocode(query, viewbox=NCR_VIEWBOX, bounded=True)
        if result:
            cache[loc] = (result.latitude, result.longitude)
        else:
            # widen search
            result2 = geocode(f"{loc}, India")
            cache[loc] = (result2.latitude, result2.longitude) if result2 else (np.nan, np.nan)
    except Exception as e:
        print(f"  ⚠ {loc}: {e}")
        cache[loc] = (np.nan, np.nan)

    if (i + 1) % 10 == 0:
        print(f"  … {i+1}/{len(to_geocode)} done")

# ── Save cache ────────────────────────────────────────────────────────────────
cache_rows = [{"location": k, "lat": v[0], "lon": v[1]} for k, v in cache.items()]
cache_df   = pd.DataFrame(cache_rows)
cache_df.to_csv(GEO_CACHE, index=False)
print(f"  Geocoding success: {cache_df['lat'].notna().sum()}/{len(cache_df)} locations")
print(f"  Saved → {GEO_CACHE}")

# ── Merge back ────────────────────────────────────────────────────────────────
geo_map = {row.location: (row.lat, row.lon) for row in cache_df.itertuples()}

df["pickup_lat"] = df["Pickup Location"].map(lambda x: geo_map.get(x, (np.nan, np.nan))[0])
df["pickup_lon"] = df["Pickup Location"].map(lambda x: geo_map.get(x, (np.nan, np.nan))[1])
df["drop_lat"]   = df["Drop Location"].map(lambda x: geo_map.get(x, (np.nan, np.nan))[0])
df["drop_lon"]   = df["Drop Location"].map(lambda x: geo_map.get(x, (np.nan, np.nan))[1])

# ── Haversine comparison ──────────────────────────────────────────────────────
def safe_haversine(row):
    try:
        if any(pd.isna([row.pickup_lat, row.pickup_lon, row.drop_lat, row.drop_lon])):
            return np.nan
        return haversine(row.pickup_lat, row.pickup_lon, row.drop_lat, row.drop_lon)
    except:
        return np.nan

print("Computing haversine distances …")
df["haversine_km"] = df.apply(safe_haversine, axis=1)
df["dist_deviation_pct"] = abs(df["haversine_km"] - df["Ride Distance"]) / df["Ride Distance"].replace(0, np.nan) * 100
flagged = (df["dist_deviation_pct"] > 20).sum()
print(f"  Rows with >20% distance deviation: {flagged:,} ({flagged/len(df):.1%})")

# ── Save updated cleaned CSV ──────────────────────────────────────────────────
df.to_csv(CLEANED, index=False)
print(f"\n✅ Updated cleaned dataset with geocoords → {CLEANED}")
