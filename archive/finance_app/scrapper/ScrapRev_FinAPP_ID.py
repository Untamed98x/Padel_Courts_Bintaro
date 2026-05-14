import os
import pandas as pd
from google_play_scraper import Sort, reviews
from google.cloud import language_v1
import time

# 1. SET KUNCI GCP
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/muhammadfauzy/Documents/2.Data_Analyst/Segment_Analyst_FinAPP/API-Json/fauzyportfolanlyst-28d46567c40b.json'

# 2. LIST TOP 10 (Campuran Lokal & Global Populer di Indo)
target_apps = {
    'Catatan_Keuangan_Lokal': 'com.tokodev.catatankeuangan',
    'Jenius_Moneytory': 'com.btpn.dc',
    'Pina': 'id.pina.app',
    'Finku': 'id.finku.finku',
    'Catatab': 'devtechtif.catatan_tabungan',
    'Wallet_BudgetBakers': 'com.droid4you.application.wallet',
    'Money_Lover': 'com.bookmark.money',
    'Bluecoins': 'com.rammigsoftware.bluecoins',
    'Monefy': 'com.monefy.app.lite',
    'Spendee': 'com.cleevio.spendee'
}

client = language_v1.LanguageServiceClient()

def get_sentiment(text):
    try:
        # GCP Natural Language otomatis deteksi bahasa Indo/English
        document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
        sentiment = client.analyze_sentiment(request={'document': document}).document_sentiment
        return sentiment.score
    except:
        return 0

all_results = []
print("🚀 Memulai Riset Pasar Indonesia (Target: 1.000 Reviews)...")

for name, app_id in target_apps.items():
    print(f"🇮🇩 Scraping {name}...")
    try:
        # Tarik review bahasa Indonesia (lang='id') dan English (lang='en')
        # Kita fokus ke region Indonesia (country='id')
        result, _ = reviews(
            app_id,
            lang='id',
            country='id',
            sort=Sort.NEWEST,
            count=150
        )

        for r in result:
            score = get_sentiment(r['content'])
            all_results.append({
                'App': name,
                'Review': r['content'],
                'Rating': r['score'],
                'Sentiment_Score': score,
                'At': r['at']
            })
        time.sleep(1.5) # Jeda aman
    except Exception as e:
        print(f"⚠️ Gagal tarik {name}: {e}")

# Save ke CSV
df = pd.DataFrame(all_results)
df.to_csv('riset_pasar_indo_1000.csv', index=False)

print("\n✅ DATA BERHASIL DIKUMPULKAN!")
print(f"Total Review: {len(df)}")