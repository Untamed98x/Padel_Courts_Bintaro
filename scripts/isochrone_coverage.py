import os
import json
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import time
from shapely.geometry import shape, Point

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
API_KEY = os.getenv("OPENROUTESERVICE_API_KEY")
OUT = ROOT / "output"

if not API_KEY:
    print("[error] OPENROUTESERVICE_API_KEY not found in .env")
    exit(1)

def get_isochrone(lat, lon, minutes=10, retry=3):
    """Fetch isochrone polygon dari OpenRouteService dengan retry"""
    url = "https://api.openrouteservice.org/v2/isochrones/driving-car"

    # ✅ FIX: ORS v2 isochrones HANYA menerima POST + JSON body, bukan GET + params
    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json, application/geo+json"
    }
    body = {
        "locations": [[lon, lat]],   # ✅ ORS pakai [longitude, latitude], BUKAN [lat, lon]
        "range": [minutes * 60],     # dalam detik
        "range_type": "time"
    }

    for attempt in range(retry):
        try:
            print(f"    [attempt {attempt+1}/{retry}]", end=" ", flush=True)
            r = requests.post(url, headers=headers, json=body, timeout=30)  # ✅ POST

            if r.status_code == 429:
                print(f"RATE LIMIT — waiting 60s...")
                time.sleep(60)
                continue

            if r.status_code == 403:
                print(f"FORBIDDEN (API key invalid/expired)")
                return None

            r.raise_for_status()
            data = r.json()

            if "features" in data and len(data["features"]) > 0:
                print("✓")
                return data["features"][0]["geometry"]

            print("NO FEATURES")
            return None

        except requests.exceptions.Timeout:
            print(f"TIMEOUT")
            if attempt < retry - 1:
                time.sleep(5)
        except requests.exceptions.ConnectionError:
            print(f"CONNECTION ERROR")
            if attempt < retry - 1:
                time.sleep(5)
        except Exception as e:
            print(f"ERROR: {str(e)[:80]}")
            return None

    print(f"FAILED after {retry} attempts")
    return None

def main():
    print("=" * 60)
    print("PADEL BINTARO — Isochrone Coverage Analysis")
    print("=" * 60)

    # Load data
    padel_csv = ROOT / "output" / "padel_assigned.csv"
    kelurahan_csv = ROOT / "output" / "kelurahan_geocoded.csv"

    if not padel_csv.exists() or not kelurahan_csv.exists():
        print(f"[error] Missing input files:")
        print(f"  - {padel_csv} {'✓' if padel_csv.exists() else '✗ NOT FOUND'}")
        print(f"  - {kelurahan_csv} {'✓' if kelurahan_csv.exists() else '✗ NOT FOUND'}")
        return

    padel_df = pd.read_csv(padel_csv)
    kelurahan_df = pd.read_csv(kelurahan_csv)

    padel_df = padel_df.dropna(subset=["lat", "lon"])
    kelurahan_df = kelurahan_df.dropna(subset=["lat", "lon"])

    print(f"\n[1/4] Loaded {len(padel_df)} lapangan, {len(kelurahan_df)} kelurahan")
    print(f"[info] API Key: {API_KEY[:30]}...\n")

    # Generate isochrones (10 min only)
    isochrones = []
    geojson_features = []
    success = 0
    failed = 0

    total = len(padel_df)
    for i, r in padel_df.iterrows():
        name = r.get("name", "Unknown")[:40]
        print(f"[{i+1:3d}/{total}] {name:<40}", end=" → ")

        minutes = 10
        geom = get_isochrone(float(r["lat"]), float(r["lon"]), minutes, retry=2)

        if geom:
            isochrones.append({
                "place_id": r.get("place_id"),
                "name": r.get("name"),
                "lat": r.get("lat"),
                "lon": r.get("lon"),
                "minutes": minutes,
                "geometry": json.dumps(geom)
            })
            geojson_features.append({
                "type": "Feature",
                "properties": {
                    "name": r.get("name"),
                    "minutes": minutes,
                    "rating": r.get("rating")
                },
                "geometry": geom
            })
            success += 1
        else:
            failed += 1

        time.sleep(1.5)  # Rate limiting

    if not isochrones:
        print("[error] No isochrones generated.")
        return

    # Save isochrones CSV
    iso_df = pd.DataFrame(isochrones)
    iso_df.to_csv(OUT / "isochrones.csv", index=False)
    print(f"\n[2/4] Generated {success}/{total} isochrone polygons ({failed} failed)")
    print(f"      Saved: {OUT / 'isochrones.csv'}")

    # Save GeoJSON
    geojson = {"type": "FeatureCollection", "features": geojson_features}
    with open(OUT / "isochrones.geojson", "w") as f:
        json.dump(geojson, f)
    print(f"[3/4] Saved GeoJSON: {OUT / 'isochrones.geojson'}")

    # Calculate coverage per kelurahan (point-in-polygon)
    print(f"\n[4/4] Calculating coverage per kelurahan...")
    coverage = []

    for _, k in kelurahan_df.iterrows():
        kelurahan_point = Point(float(k["lon"]), float(k["lat"]))
        covered_10min = False
        nearest_iso = None
        min_dist = float("inf")

        for _, iso in iso_df.iterrows():
            try:
                geom = shape(json.loads(iso["geometry"]))

                if geom.contains(kelurahan_point):
                    covered_10min = True
                    break

                dist = geom.distance(kelurahan_point)
                if dist < min_dist:
                    min_dist = dist
                    nearest_iso = iso["name"]

            except Exception as e:
                pass

        coverage.append({
            "kelurahan": k.get("kelurahan"),
            "kecamatan": k.get("kecamatan"),
            "kota": k.get("kota"),
            "lat": k.get("lat"),
            "lon": k.get("lon"),
            "covered_10min": 1 if covered_10min else 0,
            "nearest_padel": nearest_iso,
            "dist_to_nearest_m": round(min_dist * 111000, 0) if min_dist != float("inf") else None
        })

    cov_df = pd.DataFrame(coverage)
    cov_df = cov_df.sort_values("covered_10min", ascending=False)
    cov_df.to_csv(OUT / "coverage_analysis.csv", index=False)

    cover_count = cov_df["covered_10min"].sum()
    total_count = len(cov_df)
    coverage_pct = (cover_count / total_count * 100) if total_count > 0 else 0

    print(f"\n{'=' * 60}")
    print(f"COVERAGE SUMMARY (10 min isochrone)")
    print(f"{'=' * 60}")
    print(f"Total kelurahan: {total_count}")
    print(f"Covered: {cover_count} ({coverage_pct:.1f}%)")
    print(f"Not covered: {total_count - cover_count} ({100-coverage_pct:.1f}%)")

    print(f"\nCovered kelurahan:")
    for _, r in cov_df[cov_df["covered_10min"] == 1].iterrows():
        print(f"  ✓ {r['kelurahan']} ({r['kecamatan']})")

    print(f"\nNOT covered kelurahan:")
    for _, r in cov_df[cov_df["covered_10min"] == 0].iterrows():
        print(f"  ✗ {r['kelurahan']} ({r['kecamatan']}) — nearest: {r['nearest_padel']}")

    print(f"\n[saved] {OUT / 'coverage_analysis.csv'}")
    print(f"[done]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[interrupted by user]")
        exit(0)