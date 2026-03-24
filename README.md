# 🏓 Padel Courts Bintaro — Isochrone & Gap Analysis

> Membuktikan apakah distribusi lapangan padel di Bintaro Jaya sudah merata secara geografis — menggunakan data spasial dan analisis aksesibilitas untuk mengidentifikasi peluang investasi.

---

## 📌 Latar Belakang

Padel adalah olahraga dengan pertumbuhan tercepat di Indonesia dalam beberapa tahun terakhir. Namun pertanyaannya: **apakah supply lapangan padel sudah mengikuti distribusi demand secara geografis?**

Project ini menganalisis aksesibilitas lapangan padel di kawasan **Bintaro Jaya** — mencakup 22 kelurahan di 3 kecamatan lintas 2 provinsi (Tangerang Selatan & Jakarta Selatan) — untuk menjawab pertanyaan tersebut dengan data, bukan asumsi.

---

## 🗺️ Scope Wilayah

| Kecamatan | Kota | Provinsi | Jumlah Kelurahan |
|---|---|---|---|
| Pondok Aren | Tangerang Selatan | Banten | 11 |
| Ciputat Timur | Tangerang Selatan | Banten | 6 |
| Pesanggrahan | Jakarta Selatan | DKI Jakarta | 5 |

**Total: 22 kelurahan sebagai unit analisis**

---

## 🔍 Metodologi

```
[1] Define scope wilayah     → 22 kelurahan Bintaro Jaya
[2] Scraping lokasi padel    → Google Maps Places API
[3] Data populasi            → BPS Tangsel + BPS Jaksel
[4] Cleaning & deduplication → pandas
[5] Assign ke kelurahan      → Haversine distance
[6] Gap analysis             → Rasio lapangan per kapita
[7] Isochrone generation     → OpenRouteService API
[8] Visualisasi              → Folium / Kepler.gl
```

### Gap Score Formula

```
gap_score = (kekosongan_lapangan × 0.6) + (kepadatan_penduduk × 0.4)
```

Skala 0–1. Makin tinggi = makin underserved = makin potensial untuk investasi lapangan baru.

---

## 🛠️ Tech Stack

| Layer | Tools |
|---|---|
| Scraping | `googlemaps` Python SDK |
| Processing | `pandas`, `geopandas` |
| Isochrone | OpenRouteService API |
| Visualisasi | `folium`, Kepler.gl |

---

## 📁 Struktur Project

```
padel_bintaro/
├── data/
│   ├── kelurahan_master.py        # 22 kelurahan scope Bintaro Jaya
│   └── populasi_kelurahan.csv     # Data BPS (tidak di-push)
├── output/                        # Auto-generated (tidak di-push)
├── .env                           # API keys (tidak di-push)
├── .gitignore
├── scraper_gmaps.py               # Scraping Google Maps Places API
├── assign_to_kelurahan.py         # Gap analysis per kelurahan
└── isochrone.py                   # Isochrone generation (Phase 2)
```

---

## ⚙️ Setup & Cara Jalanin

### 1. Clone repo

```bash
git clone https://github.com/Untamed98x/Padel_Courts_Bintaro.git
cd Padel_Courts_Bintaro/padel_bintaro
```

### 2. Install dependencies

```bash
pip install googlemaps pandas tqdm python-dotenv
```

### 3. Setup API key

Buat file `.env` di dalam folder `padel_bintaro/`:

```
GMAPS_API_KEY=your_api_key_here
```

Dapetin API key di [Google Cloud Console](https://console.cloud.google.com) — enable **Places API** dan **Geocoding API**.

### 4. Jalanin scraper

```bash
python scraper_gmaps.py
```

### 5. Jalanin gap analysis

```bash
python assign_to_kelurahan.py
```

---

## 📊 Output

| File | Deskripsi |
|---|---|
| `output/padel_bintaro.csv` | Semua lapangan padel valid hasil scraping |
| `output/gap_analysis.csv` | Gap score per kelurahan (metric utama) |
| `output/rejected_places.csv` | False positive untuk review manual |

---
## 📊 Live Interactive Map

👉 **Explore the map:** "https://padel-gap-analysis.vercel.app"
"
![Gap Analysis Preview](padel-visual/preview.png)

---

## 📌 Konteks Penting

Pemerintah DKI Jakarta baru mengeluarkan regulasi pelarangan pembangunan lapangan padel baru di zona perumahan. Ini berpotensi menggeser demand dari Jakarta Selatan ke Bintaro sisi Tangerang Selatan — memperkuat narasi investasi di area Pondok Aren dan Ciputat Timur.

---

## 👤 Author

**Muhammad Fauzy** — Data Analyst & Visual Thinker  
[Portfolio](https://Muhammad%20Fauzy%20—%20Data%20Analyst%20&%20Visual%20Thinker) · [GitHub](https://github.com/Untamed98x)

---

*Project ini dibuat untuk keperluan analisis investasi lapangan padel di kawasan Bintaro Jaya.*