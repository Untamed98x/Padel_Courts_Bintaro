# scraper_reviews_pondoklabu.py
# Scraping Google Maps reviews untuk Sense Padel + Top 10 kompetitor
# via Google Maps Places API + GCP Natural Language API (sentiment)
#
# LIMIT: Places API returns max 5 reviews per place (most relevant).
# Untuk 50+ reviews/court: gunakan SerpAPI (serpapi.com) atau Outscraper.
# Workaround saat ini: 11 courts × 5 reviews = ~55 reviews corpus.
#
# Output:
#   output/reviews_pondoklabu.csv — semua reviews + klasifikasi
#   output/review_summary_pondoklabu.csv — agregat per court

import os
import sys
import time
import json
import pandas as pd
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv
import googlemaps

# ─── Path setup ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

# ─── GCP NLP credentials ─────────────────────────────────────────────────────
GCP_CREDS = ROOT / "API-Json" / "fauzyportfolanlyst-28d46567c40b.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(GCP_CREDS)

try:
    from google.cloud import language_v1
    nlp_client = language_v1.LanguageServiceClient()
    NLP_ENABLED = True
    print("[+] GCP NLP client initialized")
except Exception as e:
    NLP_ENABLED = False
    print(f"[!] GCP NLP unavailable: {e}. Sentiment = None.")

# ─── Config ──────────────────────────────────────────────────────────────────
API_KEY        = os.getenv("GMAPS_API_KEY")
INPUT_CSV      = ROOT / "output" / "padel_pondoklabu.csv"
OUTPUT_REVIEWS = ROOT / "output" / "reviews_pondoklabu.csv"
OUTPUT_SUMMARY = ROOT / "output" / "review_summary_pondoklabu.csv"
DELAY_SEC      = 0.8
TOP_N_COURTS   = 11   # Sense Padel + 10 kompetitor terdekat

if not API_KEY:
    print("[error] GMAPS_API_KEY not found in .env")
    sys.exit(1)

gmaps = googlemaps.Client(key=API_KEY)

# ─── Keyword Dictionaries ─────────────────────────────────────────────────────

# Dimensi 1: Experience (infrastruktur) vs Service (staf/ops)
EXPERIENCE_KW = [
    "lapangan", "court", "fasilitas", "bersih", "nyaman", "bagus", "luas",
    "kualitas", "lighting", "lampu", "terang", "parkir", "infrastruktur",
    "sarana", "cat", "net", "permukaan", "AC", "adem", "sejuk", "bangunan",
    "loker", "shower", "toilet", "mandi",
]
SERVICE_KW = [
    "staf", "staff", "admin", "pelayanan", "booking", "ramah", "respon",
    "cepat", "membantu", "helpful", "harga", "murah", "mahal", "jadwal",
    "slot", "aplikasi", "sistem", "cs", "customer", "layanan", "operator",
    "penjaga", "kasir", "front desk", "check in",
]

# Dimensi 2: Social Connectivity (indikator kematangan komunitas)
SOCIAL_KW = [
    "teman", "komunitas", "liga", "turnamen", "ketemu", "bergabung", "join",
    "temen baru", "nemu temen", "community", "event", "kompetisi", "ranking",
    "ladder", "club", "bareng", "partner", "lawan baru", "cari lawan",
    "seru bareng", "nongkrong", "social", "networking", "kenal",
]

# Dimensi 3: Pain Points kompetitor (celah buat Sense Padel)
PAIN_KW = [
    "kecewa", "buruk", "jelek", "susah", "lambat", "mahal", "kotor", "penuh",
    "tidak ada", "ngga ada", "ga ada", "kurang", "jutek", "tidak ramah",
    "trouble", "problem", "rusak", "bocor", "panas", "gelap", "sempit",
    "booking susah", "penuh terus", "susah cari lawan", "tidak responsif",
    "slow respon", "lama",
]

# Keyword positif — buat deteksi niche opportunity
NICHE_SIGNALS = {
    "business_networking": ["bisnis", "kantor", "networking", "client", "kolega",
                            "rekan kerja", "profesional", "corporate", "office"],
    "ladies_community":   ["ladies", "wanita", "perempuan", "ibu", "cewek",
                           "ladies day", "girls", "mama", "arisan"],
    "beginner_friendly":  ["pemula", "baru belajar", "newbie", "belajar",
                           "beginner", "latihan", "coach", "kursus", "les"],
}


def get_sentiment(text):
    if not NLP_ENABLED or not text.strip():
        return None
    try:
        document = language_v1.Document(
            content=text,
            type_=language_v1.Document.Type.PLAIN_TEXT
        )
        sentiment = nlp_client.analyze_sentiment(
            request={"document": document}
        ).document_sentiment
        return round(sentiment.score, 3)
    except Exception:
        return None


def score_keywords(text, keywords):
    """Return count of keyword hits in text."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def classify_review(text):
    t = text.lower()
    exp_score  = score_keywords(t, EXPERIENCE_KW)
    svc_score  = score_keywords(t, SERVICE_KW)
    soc_score  = score_keywords(t, SOCIAL_KW)
    pain_score = score_keywords(t, PAIN_KW)

    # Primary dimension
    if exp_score == 0 and svc_score == 0:
        primary_dim = "unclassified"
    elif exp_score > svc_score:
        primary_dim = "experience"
    elif svc_score > exp_score:
        primary_dim = "service"
    else:
        primary_dim = "both"

    # Niche signals
    niche_hits = {k: score_keywords(t, kws) for k, kws in NICHE_SIGNALS.items()}
    niche_label = max(niche_hits, key=niche_hits.get) if max(niche_hits.values()) > 0 else "none"

    return {
        "exp_score":   exp_score,
        "svc_score":   svc_score,
        "soc_score":   soc_score,
        "pain_score":  pain_score,
        "primary_dim": primary_dim,
        "has_social":  soc_score > 0,
        "niche_signal": niche_label,
    }


def get_court_reviews(place_id, court_name):
    """
    Fetch reviews from Place Details API.
    Returns list of dicts. Max 5 reviews per call (Places API limit).
    """
    try:
        detail = gmaps.place(
            place_id=place_id,
            fields=["name", "rating", "user_ratings_total", "reviews"],
        )
        result = detail.get("result", {})
        raw_reviews = result.get("reviews", [])

        reviews = []
        for r in raw_reviews:
            text = r.get("text", "").strip()
            if not text:
                continue

            classification = classify_review(text)
            sentiment_score = get_sentiment(text)
            time.sleep(0.2)  # space NLP calls

            reviews.append({
                "place_id":       place_id,
                "court_name":     court_name,
                "author":         r.get("author_name", ""),
                "rating":         r.get("rating"),
                "review_text":    text,
                "time_published": r.get("relative_time_description", ""),
                "language":       r.get("language", ""),
                "sentiment_score": sentiment_score,
                **classification,
            })

        return reviews

    except Exception as e:
        print(f"   [!] Error reviews {court_name}: {e}")
        return []


def select_target_courts(df):
    """
    Select Sense Padel + top 10 competitors by distance.
    Expects column 'dist_km' from density analysis CSV.
    Falls back to rating sort if dist_km not available.
    """
    sense_mask = df["name"].str.contains("Sense", case=False, na=False)
    sense_rows = df[sense_mask]
    others     = df[~sense_mask]

    if "dist_km" in df.columns:
        others = others.sort_values("dist_km").head(10)
    else:
        print("   [!] dist_km column not found — sorting by rating instead")
        others = others.sort_values("rating", ascending=False).head(10)

    targets = pd.concat([sense_rows, others]).drop_duplicates("place_id")
    return targets


def main():
    print("=" * 60)
    print("  PADEL PONDOK LABU — Review Scraper")
    print("  Target: Sense Padel + Top 10 kompetitor terdekat")
    print(f"  API limit: 5 reviews/court  |  NLP: {'ON' if NLP_ENABLED else 'OFF'}")
    print("=" * 60)

    # 1. Load court data — prefer density CSV (has dist_km)
    density_csv = ROOT / "output" / "padel_pondoklabu_density.csv"
    courts_csv  = INPUT_CSV

    if density_csv.exists():
        df_courts = pd.read_csv(density_csv)
        print(f"\n[+] Loaded density data: {density_csv.name}  ({len(df_courts)} courts)")
    elif courts_csv.exists():
        df_courts = pd.read_csv(courts_csv)
        print(f"\n[+] Loaded courts data: {courts_csv.name}  ({len(df_courts)} courts)")
    else:
        print(f"\n[error] No court data found. Run scraper_gmaps_pondoklabu.py first.")
        sys.exit(1)

    # 2. Select target courts
    targets = select_target_courts(df_courts)
    print(f"\n[1/2] Target courts selected: {len(targets)}")
    for _, row in targets.iterrows():
        dist_str = f"  dist: {row['dist_km']:.1f}km" if "dist_km" in row else ""
        print(f"  - {row['name'][:45]:<45} rating: {row.get('rating', 'N/A')}{dist_str}")

    # 3. Scrape reviews
    all_reviews = []
    print(f"\n[2/2] Fetching reviews...")
    for _, row in targets.iterrows():
        court_name = row["name"]
        place_id   = row["place_id"]
        print(f"  Scraping: {court_name[:50]}...", end=" ")
        reviews = get_court_reviews(place_id, court_name)
        print(f"→ {len(reviews)} reviews")
        all_reviews.extend(reviews)
        time.sleep(DELAY_SEC)

    if not all_reviews:
        print("[error] No reviews scraped. Check API key / place IDs.")
        sys.exit(1)

    # 4. Save reviews
    df_reviews = pd.DataFrame(all_reviews)
    df_reviews.to_csv(OUTPUT_REVIEWS, index=False, encoding="utf-8-sig")
    print(f"\n✓ Reviews saved: {OUTPUT_REVIEWS}  ({len(df_reviews)} reviews)")

    # 5. Build summary per court
    summary = df_reviews.groupby("court_name").agg(
        review_count      = ("review_text", "count"),
        avg_rating        = ("rating", "mean"),
        avg_sentiment     = ("sentiment_score", "mean"),
        pct_experience    = ("exp_score", lambda x: (x > 0).mean() * 100),
        pct_service       = ("svc_score", lambda x: (x > 0).mean() * 100),
        pct_social        = ("has_social", "mean"),
        pct_pain          = ("pain_score", lambda x: (x > 0).mean() * 100),
        top_niche_signal  = ("niche_signal", lambda x: x.value_counts().idxmax()),
    ).round(2).reset_index()

    summary["social_maturity"] = summary["pct_social"].apply(
        lambda p: "Mature" if p > 0.3 else ("Growing" if p > 0.1 else "Early")
    )
    summary.to_csv(OUTPUT_SUMMARY, index=False, encoding="utf-8-sig")
    print(f"✓ Summary saved: {OUTPUT_SUMMARY}")

    # 6. Quick print
    print(f"\n{'='*60}")
    print("  REVIEW SUMMARY")
    print(f"{'='*60}")
    print(summary[["court_name", "review_count", "avg_rating",
                   "pct_experience", "pct_service", "pct_social",
                   "social_maturity"]].to_string(index=False))

    # 7. Competitor pain points highlight
    print(f"\n{'='*60}")
    print("  TOP COMPETITOR PAIN POINTS (celah Sense Padel)")
    print(f"{'='*60}")
    sense_mask   = df_reviews["court_name"].str.contains("Sense", case=False, na=False)
    comp_reviews = df_reviews[~sense_mask & (df_reviews["pain_score"] > 0)]
    pain_corpus  = " ".join(comp_reviews["review_text"].str.lower())
    pain_freq    = Counter(kw for kw in PAIN_KW if kw in pain_corpus)
    for kw, count in pain_freq.most_common(10):
        print(f"  '{kw}': {count}x")

    print(f"\n[done]")


if __name__ == "__main__":
    main()
