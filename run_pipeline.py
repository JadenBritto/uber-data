"""
run_pipeline.py — master runner
Executes all 6 pipeline stages in order.
Usage: python run_pipeline.py [--skip-geocoding] [--skip-forecast]
"""
import subprocess, sys, os, time, argparse

# Ensure UTF-8 output for all child processes on Windows
os.environ["PYTHONUTF8"] = "1"

BASE = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(BASE, "venv", "Scripts", "python.exe")

parser = argparse.ArgumentParser(description="Uber Analytics Pipeline Runner")
parser.add_argument("--skip-geocoding", action="store_true",
                    help="Skip geocoding step (uses cached coordinates if available)")
parser.add_argument("--skip-forecast",  action="store_true",
                    help="Skip Prophet forecasting (faster run)")
args = parser.parse_args()

STEPS = [
    ("01 — Data Preprocessing",     "scripts/01_preprocessing.py", False),
    ("02 — Geocoding",               "scripts/02_geocoding.py",     args.skip_geocoding),
    ("03 — Exploratory Analysis",    "scripts/03_eda.py",           False),
    ("04 — Geospatial Maps",         "scripts/04_geospatial.py",    False),
    ("05 — Advanced Analysis",       "scripts/05_advanced.py",      args.skip_forecast),
    ("06 — Report Generation",       "scripts/06_report.py",        False),
]

WIDTH = 60
print("=" * WIDTH)
print("   UBER NCR ANALYTICS PIPELINE")
print("=" * WIDTH)

total_start = time.time()
for label, script, skip in STEPS:
    print(f"\n{'─'*WIDTH}")
    if skip:
        print(f"  ⏭  SKIPPED: {label}")
        continue
    print(f"  ▶  RUNNING: {label}")
    print(f"{'─'*WIDTH}")
    t0 = time.time()
    result = subprocess.run(
        [VENV_PY, os.path.join(BASE, script)],
        cwd=BASE,
        capture_output=False,  # stream output live
    )
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f"\n  ❌ FAILED: {label} (exit code {result.returncode})")
        print("  Halting pipeline. Fix the error above and re-run.")
        sys.exit(1)
    print(f"\n  ✅ Done in {elapsed:.1f}s")

total_elapsed = time.time() - total_start
print(f"\n{'='*WIDTH}")
print(f"  🏁 PIPELINE COMPLETE in {total_elapsed:.0f}s")
print(f"{'='*WIDTH}")
print("""
  Outputs:
    data/cleaned_uber_data.csv
    data/locations_geocoded.csv
    output/eda/*.png          (EDA charts)
    output/geo/*.html         (Interactive maps)
    hotspot_clusters.csv
    forecast_results.csv
    report.md

  Start dashboard:
    venv\\Scripts\\streamlit run app.py
""")
