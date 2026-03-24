import math
from pathlib import Path
import pandas as pd
import folium

ROOT = Path(__file__).resolve().parents[1]
GAP_CSV = ROOT / "output" / "gap_analysis.csv"
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)
OUT_HTML = OUT / "gap_map_pretty.html"

def make_map():
    df = pd.read_csv(GAP_CSV)
    df["gap_score"] = pd.to_numeric(df["gap_score"], errors="coerce").fillna(0)
    df["populasi"] = pd.to_numeric(df["populasi"], errors="coerce").fillna(0)
    df = df.dropna(subset=["lat","lon"]).reset_index(drop=True)
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    center = [df["lat"].mean(), df["lon"].mean()]
    m = folium.Map(location=center, zoom_start=12, tiles="OpenStreetMap")

    top5 = df.sort_values("gap_score", ascending=False).head(5).index.tolist()

    for idx, r in df.iterrows():
        gap = float(r["gap_score"])
        if gap >= 0.65:
            color = "red"
        elif gap >= 0.4:
            color = "orange"
        elif gap >= 0.2:
            color = "yellow"
        else:
            color = "green"

        popup_text = f"{r['kelurahan']}<br>Gap: {gap:.3f}<br>Pop: {int(r['populasi']):,}<br>Lap: {int(r['jumlah_lapangan'])}"
        icon_char = "★" if idx in top5 else "●"
        folium.Marker(
            location=[r["lat"], r["lon"]],
            popup=folium.Popup(popup_text, max_width=200),
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(m)

    m.save(OUT_HTML)
    print(f"[saved] {OUT_HTML}")

if __name__ == "__main__":
    make_map()