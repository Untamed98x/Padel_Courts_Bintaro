# scraper_gmaps.py
# Scraping lapangan padel di Bintaro Jaya via Google Maps Places API
#
# Setup:
#   pip install googlemaps pandas tqdm
#   Dapetin API key di: https://console.cloud.google.com
#   Enable: Places API + Geocoding API
#
# Estimasi cost:
#   Nearby Search  = $32 / 1000 req  → 22 kelurahan × 2 query = ~$1.40
#   Place Details  = $17 / 1000 req  → per tempat ditemukan    = ~$0.50
#   Total estimasi ≈ $2–5 (masih dalam free tier $200/bln)

import os
import time
import json
import pandas as pd
from tqdm import tqdm
import googlemaps
from data.kelurahan_master import KELURAHAN_BINTARO, get_search_queries

# ─── Config ──────────────────────────────────────────────────────────────────
API_KEY       = os.getenv("GMAPS_API_KEY", "ISI_API_KEY_LO_DI_SINI")
OUTPUT_RAW    = "output/raw_places.json"
OUTPUT_CSV    = "output/padel_bintaro.csv"
SEARCH_RADIUS = 3000   # meter — radius search per kelurahan centroid
DELAY_SEC     = 0.5    # jeda antar request biar aman

# Keywords yang dicari
KEYWORDS = ["lapangan padel", "padel court", "padel center"]

# ─── Init client ─────────────────────────────────────────────────────────────
gmaps = googlemaps.Client(key=API_KEY)

# ─── Step 1: Geocode tiap kelurahan buat dapetin centroid ────────────────────
def geocode_kelurahan(kelurahan_list):
    """
    Convert nama kelurahan → lat/lon centroid.
    Ini jadi titik tengah buat Nearby Search.
    """
    results = []
    print("\n[1/3] Geocoding kelurahan...")

    for k in tqdm(kelurahan_list):
        query = f"{k['kelurahan']}, {k['kecamatan']}, {k['kota']}, Indonesia"
        try:
            geocode = gmaps.geocode(query)
            if geocode:
                loc = geocode[0]["geometry"]["location"]
                results.append({
                    **k,
                    "lat": loc["lat"],
                    "lon": loc["lng"],
                    "geocode_status": "ok",
                })
            else:
                results.append({**k, "lat": None, "lon": None, "geocode_status": "not_found"})
            time.sleep(DELAY_SEC)
        except Exception as e:
            results.append({**k, "lat": None, "lon": None, "geocode_status": f"error: {e}"})

    df = pd.DataFrame(results)
    df.to_csv("output/kelurahan_geocoded.csv", index=False)
    print(f"   → {len([r for r in results if r['geocode_status'] == 'ok'])} kelurahan berhasil di-geocode")
    return results

# ─── Step 2: Nearby Search lapangan padel per kelurahan ──────────────────────
def search_padel_places(geocoded_kelurahan):
    """
    Untuk tiap kelurahan, cari semua tempat padel dalam radius SEARCH_RADIUS.
    Pakai beberapa keyword buat maximize recall.
    """
    all_places = {}   # keyed by place_id buat auto-dedup
    print("\n[2/3] Searching lapangan padel per kelurahan...")

    for k in tqdm(geocoded_kelurahan):
        if not k["lat"]:
            continue

        location = (k["lat"], k["lon"])

        for keyword in KEYWORDS:
            try:
                # First page
                response = gmaps.places_nearby(
                    location=location,
                    radius=SEARCH_RADIUS,
                    keyword=keyword,
                    type="establishment",
                )
                places = response.get("results", [])

                # Paginate kalau ada next_page_token
                while "next_page_token" in response:
                    time.sleep(2)  # wajib delay sebelum pakai next_page_token
                    response = gmaps.places_nearby(
                        page_token=response["next_page_token"]
                    )
                    places += response.get("results", [])

                # Simpan ke dict (auto-dedup by place_id)
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

    print(f"   → {len(all_places)} unique places ditemukan (sebelum filter)")

    # Simpan raw buat reference
    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_RAW, "w", encoding="utf-8") as f:
        json.dump(list(all_places.values()), f, ensure_ascii=False, indent=2)

    return list(all_places.values())

# ─── Step 3: Place Details — ambil info lengkap per tempat ───────────────────
def enrich_place_details(places):
    """
    Dari hasil Nearby Search, ambil detail lengkap:
    - Alamat lengkap
    - Rating & jumlah review
    - Jam operasional
    - Nomor telepon / website
    - Koordinat presisi
    """
    enriched = []
    print("\n[3/3] Enriching place details...")

    FIELDS = [
        "name", "formatted_address", "geometry",
        "rating", "user_ratings_total",
        "opening_hours", "formatted_phone_number",
        "website", "price_level", "type",
    ]

    for place in tqdm(places):
        try:
            detail = gmaps.place(
                place_id=place["place_id"],
                fields=FIELDS,
            )
            result = detail.get("result", {})

            # Flatten ke struktur yang kita mau
            enriched.append({
                "place_id":       place["place_id"],
                "name":           result.get("name", ""),
                "address":        result.get("formatted_address", ""),
                "lat":            result.get("geometry", {}).get("location", {}).get("lat"),
                "lon":            result.get("geometry", {}).get("location", {}).get("lng"),
                "rating":         result.get("rating"),
                "review_count":   result.get("user_ratings_total"),
                "phone":          result.get("formatted_phone_number", ""),
                "website":        result.get("website", ""),
                "open_now":       result.get("opening_hours", {}).get("open_now"),
                "hours":          str(result.get("opening_hours", {}).get("weekday_text", "")),
                "types":          ", ".join(result.get("types", [])),
                "_source_kelurahan": place.get("_found_in_kelurahan", ""),
                "_source_keyword":   place.get("_found_via_keyword", ""),
            })

            time.sleep(DELAY_SEC)

        except Exception as e:
            print(f"   [!] Error detail {place.get('name', '?')}: {e}")

    return enriched

# ─── Step 4: Filter & validasi — pastiin ini beneran lapangan padel ──────────
def filter_padel_only(enriched_places):
    """
    Dari semua results, filter yang beneran lapangan padel.
    Google Maps kadang return tempat yang cuma nyebut 'padel' di review/deskripsi.

    Kriteria INCLUDE:
    - Nama mengandung: padel, paddle (typo umum)
    - Types mengandung: sports_complex, gym, stadium

    Kriteria EXCLUDE:
    - Nama mengandung: restaurant, cafe, salon, hotel (false positive)
    """
    INCLUDE_KEYWORDS = ["padel", "paddle", "sport", "court", "lapangan"]
    EXCLUDE_KEYWORDS = ["restaurant", "cafe", "salon", "hotel", "mall", "market"]

    filtered = []
    rejected = []

    for p in enriched_places:
        name_lower = p["name"].lower()
        types_lower = p["types"].lower()

        is_relevant = any(kw in name_lower or kw in types_lower for kw in INCLUDE_KEYWORDS)
        is_noise    = any(kw in name_lower for kw in EXCLUDE_KEYWORDS)

        if is_relevant and not is_noise:
            filtered.append({**p, "_validated": True})
        else:
            rejected.append({**p, "_validated": False, "_reject_reason": "filtered out"})

    print(f"\n   Hasil filter:")
    print(f"   → {len(filtered)} tempat VALID (lapangan padel)")
    print(f"   → {len(rejected)} tempat REJECTED (false positive)")

    # Simpan rejected juga buat manual review
    pd.DataFrame(rejected).to_csv("output/rejected_places.csv", index=False)

    return filtered

# ─── Main pipeline ────────────────────────────────────────────────────────────
def main():
    os.makedirs("output", exist_ok=True)

    print("=" * 55)
    print("  PADEL BINTARO — Google Maps Scraper")
    print("  Scope: 22 kelurahan Bintaro Jaya")
    print("=" * 55)

    # 1. Geocode semua kelurahan
    geocoded = geocode_kelurahan(KELURAHAN_BINTARO)

    # 2. Search lapangan padel per kelurahan
    raw_places = search_padel_places(geocoded)

    # 3. Enrich dengan Place Details
    enriched = enrich_place_details(raw_places)

    # 4. Filter false positive
    valid_places = filter_padel_only(enriched)

    # 5. Export ke CSV
    df = pd.DataFrame(valid_places)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"\n✓ Done! Output tersimpan di: {OUTPUT_CSV}")
    print(f"  Total lapangan padel ditemukan: {len(valid_places)}")
    print(f"\nPreview:")
    print(df[["name", "address", "rating", "review_count"]].head(10).to_string(index=False))

if __name__ == "__main__":
    main()