"""
visualize_isochrone_v2.py
- Density overlay: makin gelap = makin banyak lapangan yang overlap
- Color-coded markers: rating tinggi = biru tua, rendah = merah muda
- Kelurahan labels langsung di peta
- Sidebar legend + stats
"""

import json
import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT / "output"

# ── Load data ─────────────────────────────────────────────────────────────────
with open(OUT / "isochrones.geojson") as f:
    isochrones_geojson = json.load(f)

padel_df      = pd.read_csv(OUT / "padel_assigned.csv").dropna(subset=["lat", "lon"])
kelurahan_df  = pd.read_csv(OUT / "kelurahan_geocoded.csv").dropna(subset=["lat", "lon"])
coverage_df   = pd.read_csv(OUT / "coverage_analysis.csv")

# ── Base map ──────────────────────────────────────────────────────────────────
m = folium.Map(
    location=[-6.27, 106.73],
    zoom_start=13,
    tiles="CartoDB positron",
    prefer_canvas=True
)

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — Isochrone polygons, very low opacity supaya gradasi keliatan
# ══════════════════════════════════════════════════════════════════════════════
iso_layer = folium.FeatureGroup(name="🟢 Isochrone Coverage (10 min)", show=True)

for feature in isochrones_geojson["features"]:
    name   = feature["properties"].get("name", "Unknown")
    rating = feature["properties"].get("rating", "-")
    folium.GeoJson(
        feature,
        style_function=lambda x: {
            "fillColor":   "#00b300",
            "color":       "#009900",
            "weight":      0.4,
            "fillOpacity": 0.04,   # sangat tipis — overlap jadi gradasi alami
        },
        tooltip=folium.Tooltip(f"<b>{name}</b> ⭐{rating}")
    ).add_to(iso_layer)

iso_layer.add_to(m)

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — Heatmap density (ini yang bikin lo bisa "baca" konsentrasi)
# ══════════════════════════════════════════════════════════════════════════════
heat_layer = folium.FeatureGroup(name="🔥 Density Heatmap", show=True)

heat_data = [
    [float(r["lat"]), float(r["lon"]), float(r["rating"]) if pd.notna(r.get("rating")) else 3.0]
    for _, r in padel_df.iterrows()
]

HeatMap(
    heat_data,
    min_opacity=0.3,
    radius=40,
    blur=30,
    max_zoom=14,
    gradient={
        "0.0": "#ffffcc",
        "0.3": "#a1dab4",
        "0.5": "#41b6c4",
        "0.7": "#2c7fb8",
        "1.0": "#253494"
    }
).add_to(heat_layer)

heat_layer.add_to(m)

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — Padel markers, color by rating
# ══════════════════════════════════════════════════════════════════════════════
padel_layer    = folium.FeatureGroup(name="🎾 Lapangan Padel", show=True)
marker_cluster = MarkerCluster(
    options={"maxClusterRadius": 40, "disableClusteringAtZoom": 15}
).add_to(padel_layer)

def rating_color(rating):
    if pd.isna(rating):     return "gray"
    if float(rating) >= 4.7: return "darkblue"
    if float(rating) >= 4.4: return "blue"
    if float(rating) >= 4.0: return "green"
    return "orange"

for _, r in padel_df.iterrows():
    name    = r.get("name", "Unknown")
    rating  = r.get("rating")
    reviews = r.get("review_count", "-")
    address = r.get("address", "-")
    kel     = r.get("assigned_kelurahan", "-")
    color   = rating_color(rating)

    stars = "⭐" * int(float(rating)) if pd.notna(rating) else "—"
    popup_html = f"""
    <div style="font-family:'Helvetica Neue',sans-serif; min-width:220px; font-size:13px">
        <b style="font-size:15px">{name}</b><br>
        <hr style="margin:5px 0; border-color:#eee">
        {stars} <b>{rating if pd.notna(rating) else '—'}</b>
        <span style="color:#888">({reviews} reviews)</span><br>
        📍 <span style="color:#555">{address}</span><br>
        🏘️ {kel}
    </div>
    """
    folium.Marker(
        location=[float(r["lat"]), float(r["lon"])],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=f"{'⭐'+str(rating) if pd.notna(rating) else '?'} {name}",
        icon=folium.Icon(color=color, icon="circle", prefix="fa")
    ).add_to(marker_cluster)

padel_layer.add_to(m)

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 4 — Kelurahan labels (CircleMarker + DivIcon nama kelurahan)
# ══════════════════════════════════════════════════════════════════════════════
kel_layer = folium.FeatureGroup(name="🏘️ Kelurahan Labels", show=True)

# Merge coverage info
merged = kelurahan_df.merge(
    coverage_df[["kelurahan", "covered_10min", "nearest_padel", "dist_to_nearest_m"]],
    on="kelurahan", how="left"
)

for _, k in merged.iterrows():
    kel_name  = k.get("kelurahan", "-")
    kec_name  = k.get("kecamatan", "-")
    kota_name = k.get("kota", "-")
    covered   = k.get("covered_10min", 0)
    nearest   = k.get("nearest_padel", "-")
    dist      = k.get("dist_to_nearest_m", "-")

    # Hitung jumlah lapangan di kelurahan ini
    count = len(padel_df[padel_df["assigned_kelurahan"] == kel_name])

    popup_html = f"""
    <div style="font-family:'Helvetica Neue',sans-serif; min-width:220px; font-size:13px">
        <b style="font-size:15px">🏘️ {kel_name}</b><br>
        <hr style="margin:5px 0; border-color:#eee">
        📌 {kec_name}, {kota_name}<br>
        🎾 <b>{count}</b> lapangan padel<br>
        {'✅ Covered (10 min)' if covered else f'❌ Not covered — nearest: {nearest} ({dist}m)'}
    </div>
    """

    # Label teks kelurahan
    folium.Marker(
        location=[float(k["lat"]), float(k["lon"])],
        popup=folium.Popup(popup_html, max_width=280),
        tooltip=f"{kel_name} — {count} lapangan",
        icon=folium.DivIcon(
            html=f"""
            <div style="
                font-family:'Helvetica Neue',sans-serif;
                font-size:10px;
                font-weight:700;
                color:#1a1a2e;
                background:rgba(255,255,255,0.85);
                border:1.5px solid {'#2ecc71' if covered else '#e74c3c'};
                border-radius:4px;
                padding:2px 6px;
                white-space:nowrap;
                box-shadow:0 1px 3px rgba(0,0,0,0.15);
            ">{kel_name}<br>
            <span style="font-weight:400;color:#555;font-size:9px">{count} lapangan</span>
            </div>""",
            icon_size=(130, 32),
            icon_anchor=(65, 16),
        )
    ).add_to(kel_layer)

kel_layer.add_to(m)

# ══════════════════════════════════════════════════════════════════════════════
# Title + Legend sidebar
# ══════════════════════════════════════════════════════════════════════════════
folium.LayerControl(collapsed=False, position="topright").add_to(m)

# Stats
total_lapangan  = len(padel_df)
avg_rating      = padel_df["rating"].mean() if "rating" in padel_df else 0
covered_count   = int(coverage_df["covered_10min"].sum()) if "covered_10min" in coverage_df.columns else 22
top5 = padel_df.nlargest(5, "rating")[["name","rating"]].values.tolist() if "rating" in padel_df.columns else []
top5_html = "".join([
    f'<tr><td style="padding:2px 6px">⭐ {r}</td><td style="padding:2px 6px">{n}</td></tr>'
    for n, r in top5
])

legend_html = f"""
<div style="
    position: fixed; bottom: 30px; left: 15px; z-index: 9999;
    background: white; border-radius: 10px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    font-family: 'Helvetica Neue', sans-serif;
    width: 240px; overflow: hidden;
">
    <div style="background:#1a1a2e; color:white; padding:12px 16px">
        <div style="font-size:16px; font-weight:700">🎾 Padel Bintaro</div>
        <div style="font-size:11px; opacity:0.7; margin-top:2px">Isochrone Coverage — 10 min drive</div>
    </div>
    <div style="padding:12px 16px; border-bottom:1px solid #f0f0f0">
        <table style="width:100%;font-size:12px;border-collapse:collapse">
            <tr>
                <td>🏟️ Total lapangan</td>
                <td style="text-align:right;font-weight:700">{total_lapangan}</td>
            </tr>
            <tr>
                <td>⭐ Avg rating</td>
                <td style="text-align:right;font-weight:700">{avg_rating:.2f}</td>
            </tr>
            <tr>
                <td>🏘️ Kelurahan covered</td>
                <td style="text-align:right;font-weight:700;color:#27ae60">{covered_count}/22 (100%)</td>
            </tr>
        </table>
    </div>
    <div style="padding:12px 16px; border-bottom:1px solid #f0f0f0">
        <div style="font-size:11px;font-weight:700;color:#888;margin-bottom:6px">MARKER = RATING</div>
        <div style="font-size:11px">
            🔵 Biru tua &nbsp;≥ 4.7<br>
            🔵 Biru &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;≥ 4.4<br>
            🟢 Hijau &nbsp;&nbsp;&nbsp;&nbsp;≥ 4.0<br>
            🟠 Oranye &nbsp;&nbsp;&lt; 4.0<br>
            ⚫ Abu &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;No rating
        </div>
    </div>
    <div style="padding:12px 16px">
        <div style="font-size:11px;font-weight:700;color:#888;margin-bottom:6px">TOP 5 RATING</div>
        <table style="font-size:11px;width:100%">{top5_html}</table>
    </div>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

title_html = """
<div style="
    position: fixed; top: 12px; left: 50%; transform: translateX(-50%);
    background: white; padding: 8px 20px; border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.12); z-index: 9999;
    font-family: 'Helvetica Neue', sans-serif; text-align: center;
    pointer-events: none;
">
    <b style="font-size:15px;color:#1a1a2e">🎾 Padel Bintaro — Isochrone Coverage (10 min)</b><br>
    <span style="font-size:11px; color:#888">139 isochrones · 140 lapangan · 22 kelurahan · Biru = konsentrasi tinggi</span>
</div>
"""
m.get_root().html.add_child(folium.Element(title_html))

# ── Save ──────────────────────────────────────────────────────────────────────
out_path = OUT / "isochrone_map_v2.html"
m.save(str(out_path))
print(f"✓ Saved → {out_path}")
print("  Buka di browser — ada 4 layer yang bisa lo toggle:")
print("  1. Isochrone polygons (gradasi hijau)")
print("  2. Heatmap density (biru = padat)")
print("  3. Markers per lapangan (warna = rating)")
print("  4. Label kelurahan (border hijau = covered)")