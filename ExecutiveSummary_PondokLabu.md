# Sense Padel Pondok Labu — Strategic Snapshot

> **Konteks:** Analisis ini gw buat dari data publik Google Maps (142 courts, 41 reviews dari 9 courts).
> Bukan riset pasar yang lengkap — anggap ini *peta awal* buat mulai diskusi, bukan kesimpulan final.

---

## Peta Kompetisi

![Isochrone Map — 10 Menit Berkendara](output/isochrone_map_pondoklabu.png)

*Zona merah = coverage area Sense Padel Margasatwa. Biru = kompetitor. Heatmap = kepadatan lapangan.*

> [Buka peta interaktif (web) →](https://sense-padel-pondoklabu.vercel.app) · [Local →](output/isochrone_map_pondoklabu.html)

---

## Yang Datanya Ngomong

### Kepadatan Kompetitor

| Radius | Jumlah Lapangan |
| ------ | --------------- |
| ≤ 3 km (≈ 10 mnt) | **41 lapangan** |
| ≤ 5 km (≈ 15 mnt) | **86 lapangan** |
| ≤ 10 km (≈ 20 mnt) | **140 lapangan** |

Dari sisi kepadatan, zona ini salah satu yang paling kompetitif di Jakarta Selatan.
Margin hampir pasti akan tertekan saat growth padel mulai melandai — ini bukan spekulasi,
ini pola yang terjadi di hampir semua olahraga hype cycle sebelumnya.

### Apa yang Customer Tulis di Review

|  | Sense Padel | Rata-rata Kompetitor |
|--|-------------|----------------------|
| Experience (fasilitas, lapangan) | **80%** | 77% |
| Service (staf, booking, harga) | 10% | 6% |
| Social (komunitas, liga, event) | 10% | 10% |

Hampir semua orang nulis soal fasilitas. Hampir nggak ada yang nulis soal komunitas atau teman.
Bisa jadi karena memang belum ada — atau bisa jadi karena orang yang punya experience itu
belum nulis review sama sekali.

### Community Moat Score

![Strategic Dashboard](output/strategic_dashboard_pondoklabu.png)

| Court | Moat Score |
|-------|-----------|
| Quattro Padel | 59.1 / 100 |
| Hi Padel Andara | 39.8 / 100 |
| three one three padel court | 36.7 / 100 |
| **Sense Padel Margasatwa** | **35.7 / 100** |
| Sense Padel Kemang | 19.4 / 100 |

Sense Padel unggul tipis dari rata-rata (25.7). Tapi yang menarik: **belum ada satu pun pemain
yang punya moat kuat di atas 60**. Ini window yang masih terbuka — entah berapa lama.

### Gap Niche

| Niche | Demand Signal | Comp Coverage | Gap |
| ----- | ------------ | ------------- | --- |
| **Beginner Academy** | 2.4% | 0.0% | **2.4** |
| Liga & Kompetisi | 4.9% | 6.5% | — |
| Ladies Community | 0.0% | 0.0% | 0.0 |
| Business Networking | 0.0% | 0.0% | 0.0 |

Ada sinyal demand untuk pemula, nol kompetitor yang eksplisit melayani. Tapi sinyal 2.4%
dari 41 review itu kecil banget — perlu dicek langsung ke lapangan.

---

## Yang Datanya Nggak Bisa Ngomong

Ini yang paling penting buat didiskusikan sebelum ambil keputusan besar:

**Data Google Review punya blind spot sistemik:**

- **Mayoritas customer nggak nulis review.** Dari 142 lapangan, hanya 41 review yang bisa
  di-scrape dengan detail. Orang yang puas seringkali diam — yang nulis review biasanya yang
  sangat senang atau yang kecewa. Distribusinya nggak representatif.

- **Nggak keliatan siapa yang balik.** Review nggak bisa ngukur retention rate — berapa persen
  customer yang datang bulan lalu masih datang bulan ini. Ini metrik yang jauh lebih penting
  dari rating.

- **Nggak keliatan siapa customernya.** Umur, pekerjaan, sudah berapa lama main padel,
  datang sendiri atau bareng komunitas — semua invisible dari data ini.

- **Nggak keliatan pricing pressure.** Siapa yang lagi promo, siapa yang naik harga,
  bagaimana elastisitas demand di zona ini — data public nggak nyentuh ini sama sekali.

- **Komunitas yang ada belum tentu keliatan di review.** Kalau sebenarnya sudah ada WhatsApp
  grup aktif, regular players yang loyal, atau mini-tournament informal — itu nggak akan
  muncul di Google Maps. Moat score 35.7 bisa terlalu rendah, bisa juga terlalu tinggi.

---

## Pertanyaan yang Lebih Berguna dari Kesimpulan

Daripada langsung ke rekomendasi, mungkin lebih worth it nanya dulu:

1. **Siapa regular players sekarang?** Ada nggak segment yang sudah balik konsisten tiap minggu?
   Kalau ada — mereka ngapain aja selain main? Ada nggak interaksi sosial yang terjadi secara organik?

2. **Kenapa orang baru pertama kali datang?** Referral dari teman, atau nemu sendiri di Maps?
   Rasionya kira-kira berapa?

3. **Kenapa orang berhenti datang?** Ini yang paling susah ditanya tapi paling valuable.

4. **Quattro Padel moat-nya tinggi (59.1) — mereka ngapain berbeda?**
   Kalau bisa diobservasi langsung, itu lebih informative dari semua data ini.

5. **Beginner Academy — sudah pernah coba?** Atau ada hambatan operasional yang bikin itu
   susah dijalanin?

---

## Kalau Dipaksa Milih Satu Arah

Dari semua yang ada, kalau harus pilih satu fokus sebelum punya data yang lebih baik:
**jadikan regular players yang ada sekarang sebagai basis — bukan akuisisi customer baru.**

Bukan karena ini strategi yang paling menarik, tapi karena:

- Datanya sudah ada (tinggal ngobrol sama mereka)
- Biayanya paling rendah
- Dan kalau community moat itu memang jalan yang bener, inilah starting point-nya

Angka-angka di atas bisa jadi titik awal diskusi — bukan peta jalan yang sudah pasti.

---

*Data: Google Maps scraping, 142 courts, 41 reviews dari 9 courts terdekat. Periode: Mei 2026.*
*Metode: review classification NLP, haversine distance, community moat scoring berbasis dimensi sosial/engagement/liga/niche.*
*Limitasi: sample size kecil, survivorship bias pada review, tidak ada data operasional, tidak ada customer interview.*

---

**Peta interaktif (mobile-friendly):** <https://sense-padel-pondoklabu.vercel.app>
