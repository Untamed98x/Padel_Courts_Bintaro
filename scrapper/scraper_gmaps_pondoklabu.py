# scraper_gmaps_pondoklabu.py
# Scraping lapangan padel area Pondok Labu (Cilandak, Cinere, Jagakarsa)
# via Google Maps Places API
#
# Output:
#   output/padel_pondoklabu.csv  — semua lapangan valid
#   output/padel_pondoklabu_density.csv — density analysis per court
#
# Estimasi cost:
#   Nearby Search  = $32 / 1000 req  → 18 kelurahan × 3 keyword = ~$1.73
#   Place Details  = $17 / 1000 req  → per tempat ditemukan      = ~$0.50
#   Total estimasi ≈ $2–5 (dalam free tier $200/bln)

import os
import sys
import time
import json
import math
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import googlemaps
from dotenv import load_dotenv

# ─── Path setup ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")
from data.kelurahan_master import KELURAHAN_PONDOK_LABU, get_search_queries

# ─── Config ──────────────────────────────────────────────────────────────────
API_KEY        = os.getenv("GMAPS_API_KEY")
OUTPUT_CSV     = ROOT / "output" / "padel_pondoklabu.csv"
OUTPUT_DENSITY = ROOT / "output" / "padel_pondoklabu_density.csv"
OUTPUT_RAW     = ROOT / "output" / "raw_places_pondoklabu.json"
SEARCH_RADIUS  = 3000   # meter
DELAY_SEC      = 0.5
KEYWORDS       = ["lapangan padel", "padel court", "padel center"]

# Sense Padel Pondok Labu — titik anchor untuk density analysis
# Script akan mencarinya otomatis, fallback ke koordinat approximate
SENSE_PADEL_QUERY = "Sense Padel Pondok Labu Jakarta"
SENSE_PADEL_APPROX = {"lat": -6.2870, "lon": 106.7980}

if not API_KEY:
    print("[error] GMAPS_API_KEY not found in .env")
    sys.exit(1)

gmaps = googlemaps.Client(key=API_KEY)


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def geocode_kelurahan(kelurahan_list):
    results = []
    print("\n[1/4] Geocoding kelurahan Pondok Labu area...")
    for k in tqdm(kelurahan_list):
        query = f"{k['kelurahan']}, {k['kecamatan']}, {k['kota']}, Indonesia"
        try:
            geocode = gmaps.geocode(query)
            if geocode:
                loc = geocode[0]["geometry"]["location"]
                results.append({**k, "lat": loc["lat"], "lon": loc["lng"], "geocode_status": "ok"})
            else:
                results.append({**k, "lat": None, "lon": None, "geocode_status": "not_found"})
            time.sleep(DELAY_SEC)
        except Exception as e:
            results.append({**k, "lat": None, "lon": None, "geocode_status": f"error: {e}"})

    df = pd.DataFrame(results)
    df.to_csv(ROOT / "output" / "kelurahan_geocoded_pondoklabu.csv", index=False)
    print(f"   → {df[df['geocode_status']=='ok'].shape[0]} / {len(kelurahan_list)} kelurahan geocoded")
    return results


def search_padel_places(geocoded_kelurahan):
    all_places = {}
    print("\n[2/4] Searching lapangan padel per kelurahan...")
    for k in tqdm(geocoded_kelurahan):
        if not k.get("lat"):
            continue
        location = (k["lat"], k["lon"])
        for keyword in KEYWORDS:
            try:
                response = gmaps.places_nearby(
                    location=location,
                    radius=SEARCH_RADIUS,
                    keyword=keyword,
                    type="establishment",
                )
                places = response.get("results", [])
                while "next_page_token" in response:
                    time.sleep(2)
                    response = gmaps.places_nearby(page_token=response["next_page_token"])
                    places += response.get("results", [])

                for place in places:
                    pid = place["place_id"]
                    if pid not in all_places:
                        all_places[pid] = {
                            **place,
                            "_found_in_kelurahan": k["kelurahan"],
                            "_found_via_keyword":  keyword,
                        }
                time.sleep(DELAY_SEC)
            except Exception as e:
                print(f"   [!] Error {k['kelurahan']} / {keyword}: {e}")

    # Also search specifically for Sense Padel to ensure it's included
    print(f"\n   [+] Explicit search: '{SENSE_PADEL_QUERY}'")
    try:
        result = gmaps.places(SENSE_PADEL_QUERY)
        for place in result.get("results", []):
            pid = place["place_id"]
            if pid not in all_places:
                all_places[pid] = {
                    **place,
                    "_found_in_kelurahan": "Pondok Labu",
                    "_found_via_keyword":  "explicit_search",
                }
    except Exception as e:
        print(f"   [!] Sense Padel explicit search error: {e}")

    print(f"   → {len(all_places)} unique places (sebelum filter)")
    os.makedirs(ROOT / "output", exist_ok=True)
    with open(OUTPUT_RAW, "w", encoding="utf-8") as f:
        json.dump(list(all_places.values()), f, ensure_ascii=False, indent=2)

    return list(all_places.values())


def enrich_place_details(places):
    enriched = []
    print("\n[3/4] Enriching place details...")
    FIELDS = [
        "name", "formatted_address", "geometry",
        "rating", "user_ratings_total",
        "opening_hours", "formatted_phone_number",
        "website", "price_level", "type",
    ]
    for place in tqdm(places):
        try:
            detail = gmaps.place(place_id=place["place_id"], fields=FIELDS)
            result = detail.get("result", {})
            enriched.append({
                "place_id":          place["place_id"],
                "name":              result.get("name", ""),
                "address":           result.get("formatted_address", ""),
                "lat":               result.get("geometry", {}).get("location", {}).get("lat"),
                "lon":               result.get("geometry", {}).get("location", {}).get("lng"),
                "rating":            result.get("rating"),
                "review_count":      result.get("user_ratings_total"),
                "phone":             result.get("formatted_phone_number", ""),
                "website":           result.get("website", ""),
                "open_now":          result.get("opening_hours", {}).get("open_now"),
                "hours":             str(result.get("opening_hours", {}).get("weekday_text", "")),
                "types":             ", ".join(result.get("type", [])),
                "_source_kelurahan": place.get("_found_in_kelurahan", ""),
                "_source_keyword":   place.get("_found_via_keyword", ""),
            })
            time.sleep(DELAY_SEC)
        except Exception as e:
            print(f"   [!] Error detail {place.get('name', '?')}: {e}")
    return enriched


def filter_padel_only(enriched_places):
    INCLUDE_KEYWORDS = ["padel", "paddle", "sport", "court", "lapangan"]
    EXCLUDE_KEYWORDS = ["restaurant", "cafe", "salon", "hotel", "mall", "market"]
    filtered, rejected = [], []
    for p in enriched_places:
        name_lower  = p["name"].lower()
        types_lower = p["types"].lower()
        is_relevant = any(kw in name_lower or kw in types_lower for kw in INCLUDE_KEYWORDS)
        is_noise    = any(kw in name_lower for kw in EXCLUDE_KEYWORDS)
        if is_relevant and not is_noise:
            filtered.append({**p, "_validated": True})
        else:
            rejected.append({**p, "_validated": False, "_reject_reason": "filtered out"})

    pd.DataFrame(rejected).to_csv(ROOT / "output" / "rejected_places_pondoklabu.csv", index=False)
    print(f"\n   → {len(filtered)} VALID | {len(rejected)} REJECTED")
    return filtered


def compute_density(valid_places_df):
    """
    Hitung density: berapa court competitor dalam radius 3km / 5km dari Sense Padel.
    3km ≈ 10 menit, 5km ≈ 15 menit berkendara di dalam kota.
    """
    # Locate Sense Padel
    sense = valid_places_df[valid_places_df["name"].str.contains("Sense", case=False, na=False)]
    if not sense.empty:
        sense_lat = float(sense.iloc[0]["lat"])
        sense_lon = float(sense.iloc[0]["lon"])
        print(f"\n   Sense Padel found: {sense.iloc[0]['name']} @ ({sense_lat:.4f}, {sense_lon:.4f})")
    else:
        sense_lat = SENSE_PADEL_APPROX["lat"]
        sense_lon = SENSE_PADEL_APPROX["lon"]
        print(f"\n   [!] Sense Padel not in results. Using approx coords: ({sense_lat}, {sense_lon})")

    df = valid_places_df.copy()
    df["dist_km"] = df.apply(
        lambda r: haversine_km(sense_lat, sense_lon, float(r["lat"]), float(r["lon"]))
        if pd.notna(r["lat"]) and pd.notna(r["lon"]) else 999,
        axis=1
    )
    df["is_sense_padel"] = df["name"].str.contains("Sense", case=False, na=False)
    df["within_3km"]     = df["dist_km"] <= 3.0
    df["within_5km"]     = df["dist_km"] <= 5.0

    competitor_3km = df[~df["is_sense_padel"] & df["within_3km"]]
    competitor_5km = df[~df["is_sense_padel"] & df["within_5km"]]

    n3 = len(competitor_3km)
    n5 = len(competitor_5km)

    if n3 > 6:
        verdict = "MERAH — Sangat Padat (>6 court dalam 10 mnt). Wajib Niche Strategy."
    elif n3 >= 3:
        verdict = "KUNING — Sedang (3-6 court). Community Moat jadi diferensiasi kunci."
    else:
        verdict = "HIJAU — Relatif Kosong (<3 court). Growth play masih bisa."

    print(f"\n{'='*55}")
    print(f"  DENSITY VERDICT")
    print(f"{'='*55}")
    print(f"  Competitor dalam 3km (≈10 mnt): {n3}")
    print(f"  Competitor dalam 5km (≈15 mnt): {n5}")
    print(f"  Status: {verdict}")

    df.sort_values("dist_km").to_csv(OUTPUT_DENSITY, index=False)
    print(f"\n  Saved: {OUTPUT_DENSITY}")
    return df, sense_lat, sense_lon


def main():
    os.makedirs(ROOT / "output", exist_ok=True)
    print("=" * 55)
    print("  PADEL PONDOK LABU — Google Maps Scraper")
    print(f"  Scope: {len(KELURAHAN_PONDOK_LABU)} kelurahan")
    print("=" * 55)

    geocoded     = geocode_kelurahan(KELURAHAN_PONDOK_LABU)
    raw_places   = search_padel_places(geocoded)
    enriched     = enrich_place_details(raw_places)
    valid_places = filter_padel_only(enriched)

    df = pd.DataFrame(valid_places)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n✓ Courts saved: {OUTPUT_CSV}  ({len(valid_places)} tempat)")

    print("\n[4/4] Density analysis...")
    df_density, _, _ = compute_density(df)

    print(f"\nPreview:")
    print(df[["name", "address", "rating", "review_count"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
