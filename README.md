<div align="center">

# 🚗 Uber NCR Ride Analytics

### End-to-End Data Analytics & Geospatial Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Pandas](https://img.shields.io/badge/Pandas-2.x-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Plotly](https://img.shields.io/badge/Plotly-Interactive-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com)
[![Folium](https://img.shields.io/badge/Folium-Maps-77B829?style=for-the-badge)](https://python-visualization.github.io/folium)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

<br/>

> A full-stack analytics pipeline covering **148,767 Uber ride bookings** across the **National Capital Region (NCR)** of India — preprocessing → geocoding → EDA → geospatial mapping → ML hotspot detection → demand forecasting → interactive dashboard.

</div>

---

## 📊 Dataset at a Glance

| Metric | Value |
|--------|-------|
| 📅 Date Range | Jan 2024 – Dec 2024 |
| 🎫 Total Bookings | 148,767 rides |
| ✅ Success Rate | 62.01% (Completed) |
| ❌ Cancellation Rate | 25.00% |
| 💰 Average Fare | ₹508 |
| 💵 Total Revenue | ₹51.4 M |
| 📍 Unique Locations | 176 NCR zones |
| 🚗 Vehicle Types | Auto, Bike, eBike, Go Mini, Go Sedan, Premier Sedan, Uber XL |

---

## 🗂️ Project Structure

```
Uber-Analytics/
│
├── 📁 data/
│   ├── cleaned_uber_data.csv        # 148,767 rows · 37 columns
│   └── locations_geocoded.csv       # 176 locations · lat/lon lookup
│
├── 📁 output/
│   ├── eda/                         # 17 publication-quality PNG charts
│   │   ├── ride_volume_by_hour.png
│   │   ├── cancellation_rate_by_hour.png
│   │   ├── dbscan_clusters.png
│   │   ├── vtat_heatmap.png
│   │   └── forecast_*.png (×5 zones)
│   └── geo/                         # Interactive HTML maps
│       ├── pickup_heatmap.html      # Folium density heatmap   (381 KB)
│       ├── h3_demand_hex.html       # H3 res-8 hex choropleth  (111 KB)
│       ├── cancellation_rate_hex.html                          (120 KB)
│       ├── od_flow_map.html         # OD flow arcs              (31 KB)
│       └── demand_animation.html   # Plotly hourly animation   (194 KB)
│
├── 📁 scripts/
│   ├── 01_preprocessing.py          # Task 1 · Clean + feature engineering
│   ├── 02_geocoding.py              # Task 2 · Nominatim geocoding (cached)
│   ├── 02b_merge_geocoords.py       # Task 2 · Merge cached coords
│   ├── 03_eda.py                    # Task 3 · 12 EDA charts
│   ├── 04_geospatial.py             # Task 4 · 5 interactive maps
│   ├── 05_advanced.py               # Task 5 · DBSCAN · IsoForest · Prophet
│   └── 06_report.py                 # Task 6 · Auto-generate report.md
│
├── app.py                           # Streamlit 4-tab dashboard
├── run_pipeline.py                  # Master pipeline runner
├── hotspot_clusters.csv             # 128 DBSCAN demand clusters
├── forecast_results.csv             # 30-day Prophet forecasts × 5 zones
├── report.md                        # Stakeholder business report
├── requirements.txt
└── fix_unicode.py                   # Windows cp1252 compatibility patcher
```

---

## 🚀 Quick Start

### 1 · Clone & set up the environment

```bash
git clone https://github.com/<your-username>/Uber-Analytics.git
cd Uber-Analytics

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
```

### 2 · Run the full pipeline

```bash
# Run all 6 stages end-to-end
python run_pipeline.py

# Skip slow geocoding if data/locations_geocoded.csv already exists
python run_pipeline.py --skip-geocoding
```

Or run individual stages:

```bash
python scripts/01_preprocessing.py   # Clean data + KPI validation
python scripts/02_geocoding.py       # Geocode locations (rate-limited)
python scripts/02b_merge_geocoords.py# Merge coordinates
python scripts/03_eda.py             # Generate 12 EDA charts
python scripts/04_geospatial.py      # Build 5 interactive maps
python scripts/05_advanced.py        # DBSCAN + anomaly + forecasting
python scripts/06_report.py          # Generate report.md
```

### 3 · Launch the dashboard

```bash
streamlit run app.py
# Opens at http://localhost:8501
```

> **Windows note:** All scripts use `PYTHONUTF8=1`. Run via `$env:PYTHONUTF8=1; python ...` or use `run_pipeline.py` which sets it automatically.

---

## 🔬 Pipeline Stages

### Task 1 — Data Preprocessing
- Parse & cast all 21 column types; strip quoted IDs
- Remove **1,233 duplicate** Booking IDs → **148,767 clean rows**
- Derive features: `hour_of_day`, `day_of_week`, `is_weekend`, `peak_flag`, `trip_duration_bucket`, `fare_per_km`
- IQR outlier detection on Booking Value & Ride Distance
- Cross-validate computed KPIs against stated benchmarks

### Task 2 — Geocoding
- Extract **176 unique NCR location names**
- Geocode via **Nominatim / OpenStreetMap** (free, rate-limited at 1 req/sec)
- **174/176 success rate (98.9%)**; results cached in `locations_geocoded.csv`
- Haversine distance computed and compared vs Ride Distance

### Task 3 — Exploratory Data Analysis (12 charts)
| Chart | Insight |
|-------|---------|
| Ride volume by hour | Evening peak 6–9 PM dominates |
| Cancellation rate by hour | Spikes during peak windows |
| Cancellation by vehicle | Varies significantly across fleet |
| Booking Value distribution | Vehicle-wise fare spread |
| Customer vs Driver ratings | Hexbin density correlation |
| Rating trend over time | 7-day rolling average |
| Payment method breakdown | UPI leading payment method |
| Avg fare by payment type | Credit card yields highest avg fare |

### Task 4 — Geospatial Analysis (5 maps)
| Map | Description |
|-----|-------------|
| `pickup_heatmap.html` | Folium HeatMap — 15K sampled pickup points |
| `h3_demand_hex.html` | H3 resolution-8 hex grid coloured by booking volume |
| `cancellation_rate_hex.html` | Same grid coloured by cancellation rate |
| `od_flow_map.html` | Top-15 Origin-Destination pairs as animated AntPath arcs |
| `demand_animation.html` | Plotly scatter_mapbox animated by `hour_of_day` |

### Task 5 — Advanced Analysis
- **DBSCAN Clustering** — `eps=1 km`, `min_samples=50` → **128 demand hotspots** detected
- **Isolation Forest** — `contamination=2%` → **2,024 anomalous bookings** flagged
- **Prophet Forecasting** — 30-day daily demand forecast per top-5 pickup zones
- **VTAT Proxy** — Location × hour heatmap of Avg Vehicle Time-to-Arrival as supply-demand imbalance signal

### Task 6 — Dashboard & Report
- **Streamlit dashboard** (`app.py`) — 4 tabs: KPI overview · EDA · Geospatial · Advanced
- Sidebar filters: date range · vehicle type · pickup zone
- **`report.md`** — auto-generated stakeholder report with findings & recommendations

---

## 📈 Key Findings

```
🔴 Top Demand Cluster  → 5,133 pickups centred at (28.52°N, 77.21°E) — Gurgaon/South Delhi corridor
⬡ Top H3 Zone         → 883da111a1fffff: 2,546 bookings | 24.9% cancel | ₹511 avg fare
⏱  Peak VTAT Window    → Hour with highest driver wait time = worst supply-demand imbalance
⚠  Anomalies Detected  → 2,024 bookings (2%) with unusual fare/distance combos
📉 Cancel Distribution → Customer-side: 7% | Driver-side: 18% (swapped vs industry labels)
```

### Strategic Recommendations

| Priority | Action | Expected Impact |
|----------|--------|-----------------|
| 🔴 High | Pre-position drivers in top-5 hotspot zones 30 min before peak | Reduce VTAT, cut cancellations |
| 🔴 High | Dynamic surge pricing in under-supplied zones during peak hours | Revenue ↑, demand balancing |
| 🔴 High | In-app ETA communication overhaul | Customer cancel rate ↓ 3–5% |
| 🟡 Med  | Driver incentive programme for high-cancellation vehicle types | Driver cancel rate ↓ |
| 🟡 Med  | UPI/Wallet cashback promotions during off-peak hours | Off-peak demand ↑ |
| 🟢 Low  | Automated anomaly alerting pipeline for fare outliers | Fraud prevention |

---

## 🛠️ Tech Stack

| Category | Libraries |
|----------|-----------|
| **Data** | `pandas` · `numpy` · `scipy` |
| **Visualisation** | `matplotlib` · `seaborn` · `plotly` · `kaleido` |
| **Geospatial** | `folium` · `h3` (v4) · `geopy` · `branca` |
| **Machine Learning** | `scikit-learn` (DBSCAN, IsolationForest, StandardScaler) |
| **Forecasting** | `prophet` |
| **Dashboard** | `streamlit` |
| **Geocoding** | Nominatim / OpenStreetMap (free, no API key needed) |

---

## 📁 Output File Sizes

> All HTML maps optimised for web sharing:

| File | Size | Technique |
|------|------|-----------|
| `pickup_heatmap.html` | 381 KB | Sampled 15K / 147K points |
| `h3_demand_hex.html` | 111 KB | Single GeoJSON FeatureCollection |
| `cancellation_rate_hex.html` | 120 KB | Single GeoJSON FeatureCollection |
| `od_flow_map.html` | 31 KB | Top-15 OD pairs only |
| `demand_animation.html` | 194 KB | Plotly.js via CDN (requires internet) |

---

## 📋 Deliverables Checklist

- [x] `data/cleaned_uber_data.csv` — 148,767 rows · 37 columns
- [x] `data/locations_geocoded.csv` — 174/176 NCR locations geocoded
- [x] `output/eda/*.png` — 17 charts (12 EDA + 5 advanced)
- [x] `output/geo/*.html` — 5 interactive maps
- [x] `hotspot_clusters.csv` — 128 DBSCAN demand clusters
- [x] `forecast_results.csv` — 30-day Prophet forecasts × 5 zones
- [x] `app.py` — Streamlit dashboard
- [x] `report.md` — Business stakeholder report

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with Python · Data: NCR Uber Ride Bookings 2024 · Geocoding: OpenStreetMap Nominatim</sub>
</div>
