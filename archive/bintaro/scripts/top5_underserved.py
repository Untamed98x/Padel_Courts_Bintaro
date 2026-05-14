import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import folium

ROOT = Path(__file__).resolve().parents[1]
GAP_CSV = ROOT / "output" / "gap_analysis.csv"
OUT = ROOT / "output"

def top5():
    df = pd.read_csv(GAP_CSV)
    # pastikan gap_score numeric
    df["gap_score"] = pd.to_numeric(df["gap_score"], errors="coerce").fillna(0)
    top5 = df.sort_values("gap_score", ascending=False).head(5).reset_index(drop=True)
    print(top5[["kelurahan","kecamatan","kota","gap_score","jumlah_lapangan","populasi"]])
    # simpan ringkasan
    top5.to_csv(OUT / "top5_underserved.csv", index=False, encoding="utf-8-sig")
    # buat bar chart
    plt.figure(figsize=(8,4))
    plt.bar(top5["kelurahan"], top5["gap_score"], color="tab:red")
    plt.ylabel("gap_score")
    plt.title("Top 5 Kelurahan Paling Underserved")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(OUT / "top5_gap.png", dpi=150)
    plt.close()
    # buat peta sederhana
    m = folium.Map(location=[top5["lat"].mean(), top5["lon"].mean()], zoom_start=13)
    for _, r in top5.iterrows():
        folium.Marker([r["lat"], r["lon"]],
                      popup=f"{r['kelurahan']} (gap {r['gap_score']:.3f})").add_to(m)
    m.save(OUT / "top5_map.html")
    print(f"\nSaved: {OUT/'top5_underserved.csv'}, {OUT/'top5_gap.png'}, {OUT/'top5_map.html'}")

if __name__ == "__main__":
    top5()