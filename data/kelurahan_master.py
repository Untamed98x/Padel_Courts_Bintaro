# kelurahan_master.py
# Master list 27 kelurahan scope Bintaro Jaya
# Primary key untuk semua dataset project ini

KELURAHAN_BINTARO = [
    # ─── Kecamatan Pondok Aren (Tangerang Selatan) ───────────────────────
    {"kelurahan": "Jurangmangu Barat",   "kecamatan": "Pondok Aren",   "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Jurangmangu Timur",   "kecamatan": "Pondok Aren",   "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Pondok Kacang Barat", "kecamatan": "Pondok Aren",   "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Pondok Kacang Timur", "kecamatan": "Pondok Aren",   "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Perigi Lama",         "kecamatan": "Pondok Aren",   "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Perigi Baru",         "kecamatan": "Pondok Aren",   "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Pondok Aren",         "kecamatan": "Pondok Aren",   "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Pondok Karya",        "kecamatan": "Pondok Aren",   "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Pondok Jaya",         "kecamatan": "Pondok Aren",   "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Pondok Betung",       "kecamatan": "Pondok Aren",   "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Pondok Pucung",       "kecamatan": "Pondok Aren",   "kota": "Tangerang Selatan", "provinsi": "Banten"},

    # ─── Kecamatan Ciputat Timur (Tangerang Selatan) ─────────────────────
    {"kelurahan": "Pisangan",            "kecamatan": "Ciputat Timur", "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Cirendeu",            "kecamatan": "Ciputat Timur", "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Cempaka Putih",       "kecamatan": "Ciputat Timur", "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Pondok Ranji",        "kecamatan": "Ciputat Timur", "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Rempoa",              "kecamatan": "Ciputat Timur", "kota": "Tangerang Selatan", "provinsi": "Banten"},
    {"kelurahan": "Rengas",              "kecamatan": "Ciputat Timur", "kota": "Tangerang Selatan", "provinsi": "Banten"},

    # ─── Kecamatan Pesanggrahan (Jakarta Selatan / DKI) ──────────────────
    {"kelurahan": "Bintaro",             "kecamatan": "Pesanggrahan",  "kota": "Jakarta Selatan",   "provinsi": "DKI Jakarta"},
    {"kelurahan": "Pesanggrahan",        "kecamatan": "Pesanggrahan",  "kota": "Jakarta Selatan",   "provinsi": "DKI Jakarta"},
    {"kelurahan": "Ulujami",             "kecamatan": "Pesanggrahan",  "kota": "Jakarta Selatan",   "provinsi": "DKI Jakarta"},
    {"kelurahan": "Petukangan Utara",    "kecamatan": "Pesanggrahan",  "kota": "Jakarta Selatan",   "provinsi": "DKI Jakarta"},
    {"kelurahan": "Petukangan Selatan",  "kecamatan": "Pesanggrahan",  "kota": "Jakarta Selatan",   "provinsi": "DKI Jakarta"},
]

# Search queries untuk tiap kelurahan — dipakai pas scraping Google Maps
def get_search_queries():
    queries = []
    for k in KELURAHAN_BINTARO:
        kel = k["kelurahan"]
        kec = k["kecamatan"]
        queries.append({
            **k,
            "query": f"lapangan padel {kel} {kec}",
            "query_broad": f"padel {kel}",
        })
    return queries

if __name__ == "__main__":
    import json
    queries = get_search_queries()
    print(f"Total kelurahan: {len(KELURAHAN_BINTARO)}")
    print(f"Total queries  : {len(queries)}")
    print("\nContoh query:")
    for q in queries[:3]:
        print(f"  - {q['query']}")
    print("\nFull list:")
    print(json.dumps(KELURAHAN_BINTARO, indent=2, ensure_ascii=False))