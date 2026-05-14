# assign_to_kelurahan.py
# Setelah scraping selesai, assign tiap lapangan ke kelurahan yang tepat
# lalu hitung rasio distribusi untuk analisis gap
#
# Input:  output/padel_bintaro.csv  (dari scraper_gmaps.py)
# Input:  data/populasi_kelurahan.csv  (manual dari BPS — lihat instruksi di bawah)
# Output: output/gap_analysis.csv

import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2
from data.kelurahan_master import KELURAHAN_BINTARO

# ─── Haversine distance (meter) ──────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    φ1, φ2 = radians(lat1), radians(lat2)
    dφ = radians(lat2 - lat1)
    dλ = radians(lon2 - lon1)
    a = sin(dφ/2)**2 + cos(φ1)*cos(φ2)*sin(dλ/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

# ─── Load data ────────────────────────────────────────────────────────────────
def load_data():
    padel_df = pd.read_csv("output/padel_bintaro.csv")
    kelurahan_df = pd.read_csv("output/kelurahan_geocoded.csv")

    # Populasi dari BPS — lo isi manual dari:
    # Tangsel: https://tangselkota.bps.go.id
    # Jaksel:  https://jaksel.bps.go.id
    # Format file: kelurahan, populasi
    try:
        pop_df = pd.read_csv("data/populasi_kelurahan.csv")
    except FileNotFoundError:
        print("[!] File populasi belum ada — pakai placeholder 10.000 dulu")
        pop_df = pd.DataFrame([
            {"kelurahan": k["kelurahan"], "populasi": 10000}
            for k in KELURAHAN_BINTARO
        ])

    return padel_df, kelurahan_df, pop_df

# ─── Assign lapangan ke kelurahan terdekat ───────────────────────────────────
def assign_to_kelurahan(padel_df, kelurahan_df):
    """
    Tiap lapangan padel di-assign ke kelurahan yang paling dekat
    berdasarkan koordinat centroid kelurahan.
    """
    assignments = []

    for _, padel in padel_df.iterrows():
        if pd.isna(padel["lat"]) or pd.isna(padel["lon"]):
            continue

        min_dist = float("inf")
        closest  = None

        for _, kel in kelurahan_df.iterrows():
            if pd.isna(kel["lat"]):
                continue
            dist = haversine(padel["lat"], padel["lon"], kel["lat"], kel["lon"])
            if dist < min_dist:
                min_dist = dist
                closest  = kel["kelurahan"]

        assignments.append({
            "place_id":          padel["place_id"],
            "name":              padel["name"],
            "lat":               padel["lat"],
            "lon":               padel["lon"],
            "rating":            padel.get("rating"),
            "review_count":      padel.get("review_count"),
            "assigned_kelurahan": closest,
            "dist_to_centroid_m": round(min_dist),
        })

    return pd.DataFrame(assignments)

# ─── Hitung gap analysis per kelurahan ───────────────────────────────────────
def compute_gap_analysis(assigned_df, kelurahan_df, pop_df):
    """
    Hitung metrik distribusi per kelurahan:
    - Jumlah lapangan
    - Populasi
    - Rasio lapangan per 10.000 penduduk
    - Gap score (makin tinggi = makin underserved)
    """
    # Count lapangan per kelurahan
    count_df = assigned_df.groupby("assigned_kelurahan").size().reset_index()
    count_df.columns = ["kelurahan", "jumlah_lapangan"]

    # Merge semua kelurahan (termasuk yang 0 lapangan)
    base = kelurahan_df[["kelurahan", "kecamatan", "kota", "provinsi", "lat", "lon"]].copy()
    merged = base.merge(count_df, on="kelurahan", how="left")
    merged["jumlah_lapangan"] = merged["jumlah_lapangan"].fillna(0).astype(int)

    # Merge populasi
    merged = merged.merge(pop_df[["kelurahan", "populasi"]], on="kelurahan", how="left")
    merged["populasi"] = merged["populasi"].fillna(10000)  # fallback

    # Hitung rasio & gap score
    merged["lapangan_per_10k"] = (merged["jumlah_lapangan"] / merged["populasi"] * 10000).round(2)

    # Gap score: kelurahan dengan 0 lapangan dan populasi tinggi = gap tertinggi
    max_pop = merged["populasi"].max()
    merged["gap_score"] = (
        (1 - merged["jumlah_lapangan"].clip(upper=5) / 5) * 0.6 +   # 60% weight: tidak ada lapangan
        (merged["populasi"] / max_pop) * 0.4                          # 40% weight: populasi besar
    ).round(3)

    # Rank dari yang paling underserved
    merged["gap_rank"] = merged["gap_score"].rank(ascending=False).astype(int)

    return merged.sort_values("gap_rank")

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  PADEL BINTARO — Gap Analysis per Kelurahan")
    print("=" * 55)

    padel_df, kelurahan_df, pop_df = load_data()

    print(f"\n[1/3] Loaded {len(padel_df)} lapangan padel")
    print(f"[2/3] Assigning ke {len(kelurahan_df)} kelurahan...")
    assigned = assign_to_kelurahan(padel_df, kelurahan_df)

    print(f"[3/3] Computing gap analysis...")
    gap_df = compute_gap_analysis(assigned, kelurahan_df, pop_df)

    # Export
    gap_df.to_csv("output/gap_analysis.csv", index=False, encoding="utf-8-sig")
    assigned.to_csv("output/padel_assigned.csv", index=False, encoding="utf-8-sig")

    print(f"\n✓ Done!")
    print(f"\nTop 5 kelurahan paling UNDERSERVED (gap_rank tertinggi):")
    cols = ["kelurahan", "kecamatan", "jumlah_lapangan", "populasi", "lapangan_per_10k", "gap_score"]
    print(gap_df[cols].head(5).to_string(index=False))

    print(f"\nTop 5 kelurahan paling TERSEDIA lapangan:")
    print(gap_df[cols].tail(5).sort_values("gap_score").to_string(index=False))

if __name__ == "__main__":
    main()