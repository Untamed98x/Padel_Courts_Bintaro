"""
scraper_osm.py
--------------
    Scraper lapangan padel di area Bintaro & sekitarnya
    menggunakan Overpass API (OpenStreetMap) — GRATIS, no API key.

    Coverage area: Bintaro, Pondok Aren, Ciputat, Ciputat Timur,
                Serpong, Pamulang, Pesanggrahan (Jaksel)

    Output:
    output/padel_courts.csv      → lapangan yang valid
    output/rejected_places.csv   → kandidat yang direject (untuk review manual)

    Usage:
    pip install requests pandas tqdm
    python scraper_osm.py
"""

import requests
import pandas as pd
import json
import time
import os
from tqdm import tqdm

# ─── CONFIG ────────────────────────────────────────────────────────────────────

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Bounding box area: SW corner → NE corner
# Covers Bintaro, Pondok Aren, Ciputat, Ciputat Timur, Serpong, Pesanggrahan
BBOX = {
    "south": -6.3800,
    "west":  106.6800,
    "north": -6.1800,
    "east":  106.8200,
}

OUTPUT_DIR = "output"
OUTPUT_COURTS  = os.path.join(OUTPUT_DIR, "padel_courts.csv")
OUTPUT_REJECTED = os.path.join(OUTPUT_DIR, "rejected_places.csv")

# Keyword yang dianggap valid padel court
PADEL_KEYWORDS = [
    "padel", "paddle"
]

# Keyword yang langsung di-reject meski lolos filter awal
REJECT_KEYWORDS = [
    "futsal", "badminton", "tenis", "tennis", "squash",
    "gym", "fitness", "renang", "swimming", "golf",
    "billiard", "bowling", "gaming", "esport"
]

# ─── OVERPASS QUERIES ──────────────────────────────────────────────────────────

def build_query(bbox):
    """
    Bikin Overpass QL query dengan 3 strategi:
    1. Tag sport=padel (ideal, tapi jarang dipakai di OSM Indonesia)
    2. Tag leisure=sports_centre yang namanya mengandung 'padel'
    3. Name contains 'padel' (paling broad, butuh manual review)
    """
    b = f"{bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']}"
    query = f"""
[out:json][timeout:60];
(
  // Strategi 1: tagged sport=padel
  node["sport"="padel"]({b});
  way["sport"="padel"]({b});
  relation["sport"="padel"]({b});

  // Strategi 2: sports centre / pitch dengan name padel
  node["leisure"="sports_centre"]["name"~"padel",i]({b});
  way["leisure"="sports_centre"]["name"~"padel",i]({b});
  node["leisure"="pitch"]["name"~"padel",i]({b});
  way["leisure"="pitch"]["name"~"padel",i]({b});

  // Strategi 3: amenity atau nama mengandung padel
  node["name"~"padel",i]({b});
  way["name"~"padel",i]({b});

  // Strategi 4: paddle (typo umum)
  node["name"~"paddle",i]({b});
  way["name"~"paddle",i]({b});
);
out center tags;
"""
    return query


# ─── FETCH ─────────────────────────────────────────────────────────────────────

def fetch_from_overpass(query, retries=3):
    for attempt in range(retries):
        try:
            print(f"  → Fetching dari Overpass API (attempt {attempt+1})...")
            resp = requests.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=90,
                headers={"User-Agent": "padel-isochrone-scraper/1.0"}
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            print("  ⚠ Timeout, retry in 10s...")
            time.sleep(10)
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                print("  ⚠ Rate limited, tunggu 30s...")
                time.sleep(30)
            else:
                raise e
    raise RuntimeError("Overpass API gagal setelah 3 kali retry")


# ─── PARSE ELEMENTS ────────────────────────────────────────────────────────────

def extract_coords(element):
    """Extract lat/lon dari node atau way (way pakai center)."""
    if element["type"] == "node":
        return element.get("lat"), element.get("lon")
    elif element["type"] in ("way", "relation"):
        center = element.get("center", {})
        return center.get("lat"), center.get("lon")
    return None, None


def parse_elements(data):
    """Konversi raw Overpass elements ke list of dicts."""
    results = []
    seen_ids = set()

    for el in tqdm(data.get("elements", []), desc="Parsing elements"):
        osm_id = f"{el['type']}/{el['id']}"
        if osm_id in seen_ids:
            continue
        seen_ids.add(osm_id)

        tags = el.get("tags", {})
        lat, lon = extract_coords(el)

        if not lat or not lon:
            continue

        name = tags.get("name", tags.get("name:id", tags.get("name:en", "")))
        sport = tags.get("sport", "")
        leisure = tags.get("leisure", "")
        amenity = tags.get("amenity", "")
        phone = tags.get("phone", tags.get("contact:phone", ""))
        website = tags.get("website", tags.get("contact:website", ""))
        opening_hours = tags.get("opening_hours", "")
        operator = tags.get("operator", "")
        addr_full = tags.get("addr:full",
                    tags.get("addr:street", "") + " " +
                    tags.get("addr:city", "")).strip()

        results.append({
            "osm_id":        osm_id,
            "name":          name,
            "lat":           lat,
            "lon":           lon,
            "sport":         sport,
            "leisure":       leisure,
            "amenity":       amenity,
            "phone":         phone,
            "website":       website,
            "opening_hours": opening_hours,
            "operator":      operator,
            "address":       addr_full,
            "raw_tags":      json.dumps(tags, ensure_ascii=False),
        })

    return results


# ─── FILTER ────────────────────────────────────────────────────────────────────

def is_padel(row):
    """
    Return (is_valid: bool, reason: str)
    Logic:
    - AUTO-ACCEPT: sport tag = padel
    - AUTO-ACCEPT: name mengandung keyword padel/paddle
    - AUTO-REJECT: name mengandung keyword non-padel tanpa 'padel' di nama
    """
    name_lower = (row["name"] or "").lower()
    sport_lower = (row["sport"] or "").lower()

    # Auto-accept: sport tag eksplisit
    if "padel" in sport_lower or "paddle" in sport_lower:
        return True, "sport=padel tag"

    # Cek keyword padel di nama
    has_padel_kw = any(kw in name_lower for kw in PADEL_KEYWORDS)

    # Cek reject keyword
    has_reject_kw = any(kw in name_lower for kw in REJECT_KEYWORDS)

    if has_padel_kw and not has_reject_kw:
        return True, "padel keyword in name"

    if has_padel_kw and has_reject_kw:
        # Misal "Padel & Futsal Center" → masuk review manual
        return False, f"mixed keywords (padel + reject kw) — REVIEW MANUAL"

    if not has_padel_kw:
        return False, "no padel keyword"

    return False, "unknown"


# ─── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("  Padel Courts Scraper — OSM / Overpass API")
    print(f"  Area: {BBOX}")
    print("=" * 60)

    # 1. Fetch
    query = build_query(BBOX)
    raw_data = fetch_from_overpass(query)

    total_raw = len(raw_data.get("elements", []))
    print(f"\n✓ Raw results dari Overpass: {total_raw} elements")

    # 2. Parse
    records = parse_elements(raw_data)
    print(f"✓ Setelah parse & dedup: {len(records)} unik")

    if not records:
        print("\n⚠ Tidak ada data. Kemungkinan area terlalu kosong di OSM,")
        print("  atau Overpass API timeout. Coba jalankan lagi.")
        return

    df = pd.DataFrame(records)

    # 3. Filter
    df["is_valid"], df["reject_reason"] = zip(*df.apply(is_padel, axis=1))

    accepted = df[df["is_valid"]].drop(columns=["is_valid", "reject_reason"])
    rejected = df[~df["is_valid"]].drop(columns=["is_valid"])

    # 4. Save
    out_cols = [
        "osm_id", "name", "lat", "lon",
        "phone", "website", "opening_hours",
        "operator", "address", "sport", "leisure", "amenity"
    ]
    accepted[out_cols].to_csv(OUTPUT_COURTS, index=False, encoding="utf-8-sig")
    rejected[["osm_id", "name", "lat", "lon", "reject_reason", "raw_tags"]].to_csv(
        OUTPUT_REJECTED, index=False, encoding="utf-8-sig"
    )

    # 5. Summary
    print(f"\n{'='*60}")
    print(f"  SELESAI")
    print(f"  ✅ Valid padel courts : {len(accepted)}")
    print(f"  ❌ Rejected           : {len(rejected)}")
    print(f"\n  Output:")
    print(f"  → {OUTPUT_COURTS}")
    print(f"  → {OUTPUT_REJECTED}")
    print(f"{'='*60}")

    if len(accepted) > 0:
        print("\n📍 Preview courts yang ketangkap:")
        for _, row in accepted.iterrows():
            coord_str = f"({row['lat']:.4f}, {row['lon']:.4f})"
            print(f"   • {row['name'] or '(no name)'} {coord_str}")

    print("\n💡 Tips:")
    print("   - Review rejected_places.csv secara manual")
    print("   - Court yang namanya 'Sport Center XYZ' tanpa kata padel")
    print("     mungkin tidak kedetect — cek langsung di overpass-turbo.eu")


if __name__ == "__main__":
    main()