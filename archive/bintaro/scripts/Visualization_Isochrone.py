"""
visualize_isochrone_v3.py
UI/UX upgrade:
- Collapsible sidebar (hidden by default on mobile)
- User location input + find nearest padel
- Sorting by distance / rating
- Mobile-first responsive design
- Clean dark theme
"""

import json
import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap, LocateControl
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT / "output"

# ── Load data ─────────────────────────────────────────────────────────────────
with open(OUT / "isochrones.geojson") as f:
    isochrones_geojson = json.load(f)

padel_df     = pd.read_csv(OUT / "padel_assigned.csv").dropna(subset=["lat", "lon"])
kelurahan_df = pd.read_csv(OUT / "kelurahan_geocoded.csv").dropna(subset=["lat", "lon"])
coverage_df  = pd.read_csv(OUT / "coverage_analysis.csv")

# ── Base map ──────────────────────────────────────────────────────────────────
m = folium.Map(
    location=[-6.27, 106.73],
    zoom_start=13,
    tiles="CartoDB positron",
    prefer_canvas=True,
    zoom_control=False,
)

# ── Layer 1: Isochrone polygons ───────────────────────────────────────────────
iso_layer = folium.FeatureGroup(name="Isochrone Coverage", show=True)
for feature in isochrones_geojson["features"]:
    name   = feature["properties"].get("name", "Unknown")
    rating = feature["properties"].get("rating", "-")
    folium.GeoJson(
        feature,
        style_function=lambda x: {
            "fillColor": "#00C896",
            "color": "#00C896",
            "weight": 0.5,
            "fillOpacity": 0.05,
        },
        tooltip=folium.Tooltip(f"<b>{name}</b> ⭐{rating}")
    ).add_to(iso_layer)
iso_layer.add_to(m)

# ── Layer 2: Heatmap ──────────────────────────────────────────────────────────
heat_layer = folium.FeatureGroup(name="Density Heatmap", show=False)
heat_data = [
    [float(r["lat"]), float(r["lon"]), float(r["rating"]) if pd.notna(r.get("rating")) else 3.0]
    for _, r in padel_df.iterrows()
]
HeatMap(heat_data, min_opacity=0.3, radius=40, blur=30, max_zoom=14,
        gradient={"0.0": "#0f0c29", "0.4": "#00C896", "0.7": "#FFD700", "1.0": "#FF4D4D"}
).add_to(heat_layer)
heat_layer.add_to(m)

# ── Layer 3: Padel markers ────────────────────────────────────────────────────
padel_layer    = folium.FeatureGroup(name="Lapangan Padel", show=True)
marker_cluster = MarkerCluster(
    options={"maxClusterRadius": 40, "disableClusteringAtZoom": 15}
).add_to(padel_layer)

def rating_color(rating):
    if pd.isna(rating):          return "#888"
    if float(rating) >= 4.7:     return "#00C896"
    if float(rating) >= 4.4:     return "#3B9EFF"
    if float(rating) >= 4.0:     return "#FFD700"
    return "#FF6B6B"

for _, r in padel_df.iterrows():
    name    = r.get("name", "Unknown")
    rating  = r.get("rating")
    reviews = r.get("review_count", "-")
    address = r.get("address", "-")
    kel     = r.get("assigned_kelurahan", "-")
    color   = rating_color(rating)
    lat, lon = float(r["lat"]), float(r["lon"])

    popup_html = f"""
    <div style="font-family:'DM Sans',sans-serif;min-width:220px;font-size:13px;padding:4px">
        <div style="font-weight:700;font-size:15px;margin-bottom:6px">{name}</div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
            <span style="background:{color};color:#000;padding:2px 8px;border-radius:20px;font-weight:700;font-size:13px">
                ⭐ {rating if pd.notna(rating) else '—'}
            </span>
            <span style="color:#888;font-size:12px">{reviews} reviews</span>
        </div>
        <div style="color:#555;font-size:12px;margin-top:4px">📍 {address}</div>
        <div style="color:#888;font-size:11px;margin-top:3px">🏘 {kel}</div>
        <div style="margin-top:8px">
            <a href="https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
               target="_blank"
               style="background:#1a1a2e;color:white;padding:5px 12px;border-radius:6px;
                      text-decoration:none;font-size:12px;font-weight:600">
                🧭 Directions
            </a>
        </div>
    </div>
    """
    folium.CircleMarker(
        location=[lat, lon],
        radius=7,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.85,
        weight=1.5,
        popup=folium.Popup(popup_html, max_width=280),
        tooltip=f"{'⭐'+str(rating) if pd.notna(rating) else '?'} {name}",
    ).add_to(marker_cluster)

padel_layer.add_to(m)

# ── Layer 4: Kelurahan labels ─────────────────────────────────────────────────
kel_layer = folium.FeatureGroup(name="Kelurahan Labels", show=True)
merged = kelurahan_df.merge(
    coverage_df[["kelurahan", "covered_10min", "nearest_padel", "dist_to_nearest_m"]],
    on="kelurahan", how="left"
)
for _, k in merged.iterrows():
    kel_name = k.get("kelurahan", "-")
    covered  = k.get("covered_10min", 0)
    count    = len(padel_df[padel_df["assigned_kelurahan"] == kel_name])
    folium.Marker(
        location=[float(k["lat"]), float(k["lon"])],
        icon=folium.DivIcon(
            html=f"""<div style="
                font-family:'DM Sans',sans-serif;font-size:10px;font-weight:700;
                color:#1a1a2e;background:rgba(255,255,255,0.9);
                border:1.5px solid {'#00C896' if covered else '#FF6B6B'};
                border-radius:4px;padding:2px 6px;white-space:nowrap;
                box-shadow:0 1px 4px rgba(0,0,0,0.12)">
                {kel_name}
                <span style="font-weight:400;color:#777;font-size:9px"> {count}</span>
            </div>""",
            icon_size=(130, 28), icon_anchor=(65, 14),
        )
    ).add_to(kel_layer)
kel_layer.add_to(m)

# ── Layer control ─────────────────────────────────────────────────────────────
folium.LayerControl(collapsed=True, position="topright").add_to(m)

# ── Zoom control (custom position) ────────────────────────────────────────────
folium.plugins.Fullscreen(position="topright").add_to(m)

# ── Stats ─────────────────────────────────────────────────────────────────────
total_lapangan = len(padel_df)
avg_rating     = round(padel_df["rating"].mean(), 2) if "rating" in padel_df else 0
covered_count  = int(coverage_df["covered_10min"].sum()) if "covered_10min" in coverage_df.columns else 22

top5 = []
if "rating" in padel_df.columns:
    top5 = padel_df.nlargest(5, "rating")[["name", "rating", "lat", "lon"]].values.tolist()

top5_html = "".join([
    f"""<div class="padel-item" onclick="flyTo({lat},{lon})" data-lat="{lat}" data-lon="{lon}" data-rating="{r}" data-name="{n}">
        <div class="padel-name">{n}</div>
        <div class="padel-rating" style="background:{'#00C896' if float(r)>=4.7 else '#3B9EFF' if float(r)>=4.4 else '#FFD700'}">⭐ {r}</div>
    </div>"""
    for n, r, lat, lon in top5
])

padel_list_html = "".join([
    f"""<div class="padel-item" onclick="flyTo({float(r['lat'])},{float(r['lon'])})"
         data-lat="{float(r['lat'])}" data-lon="{float(r['lon'])}"
         data-rating="{r.get('rating','0') or '0'}"
         data-name="{r.get('name','')}">
        <div class="padel-name">{r.get('name','Unknown')}</div>
        <div class="padel-rating" style="background:{'#00C896' if pd.notna(r.get('rating')) and float(r.get('rating',0))>=4.7 else '#3B9EFF' if pd.notna(r.get('rating')) and float(r.get('rating',0))>=4.4 else '#FFD700' if pd.notna(r.get('rating')) and float(r.get('rating',0))>=4.0 else '#FF6B6B'}">
            {'⭐ '+str(r.get('rating','—')) if pd.notna(r.get('rating')) else '—'}
        </div>
    </div>"""
    for _, r in padel_df.sort_values("rating", ascending=False).iterrows()
])

# ── Inject full UI ────────────────────────────────────────────────────────────
ui_html = f"""
<!-- Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">

<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
    --bg: #0d0d14;
    --surface: #161622;
    --surface2: #1e1e2e;
    --border: #2a2a3e;
    --text: #e8e8f0;
    --muted: #888;
    --accent: #00C896;
    --accent2: #3B9EFF;
    --danger: #FF6B6B;
    --gold: #FFD700;
    --radius: 12px;
    --sidebar-w: 320px;
}}

body {{ font-family: 'DM Sans', sans-serif; }}

/* ── Sidebar ── */
#sidebar {{
    position: fixed;
    top: 0; left: 0;
    width: var(--sidebar-w);
    height: 100vh;
    background: var(--bg);
    border-right: 1px solid var(--border);
    z-index: 10000;
    display: flex;
    flex-direction: column;
    transform: translateX(0);
    transition: transform 0.35s cubic-bezier(0.4,0,0.2,1);
    overflow: hidden;
}}

#sidebar.collapsed {{
    transform: translateX(calc(-1 * var(--sidebar-w)));
}}

/* ── Toggle button ── */
#toggle-btn {{
    position: fixed;
    top: 16px; left: 16px;
    width: 44px; height: 44px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    cursor: pointer;
    z-index: 10001;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.2s;
    color: var(--text);
    font-size: 18px;
}}

#toggle-btn:hover {{ background: var(--surface2); border-color: var(--accent); }}

#sidebar:not(.collapsed) + #toggle-btn {{
    left: calc(var(--sidebar-w) + 12px);
}}

/* ── Sidebar header ── */
.sidebar-header {{
    padding: 20px 20px 16px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}}

.sidebar-title {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 18px;
    font-weight: 700;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 8px;
}}

.sidebar-sub {{
    font-size: 12px;
    color: var(--muted);
    margin-top: 3px;
}}

/* ── Stats row ── */
.stats-row {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 8px;
    padding: 14px 16px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}}

.stat-card {{
    background: var(--surface);
    border-radius: 8px;
    padding: 10px 8px;
    text-align: center;
    border: 1px solid var(--border);
}}

.stat-num {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 20px;
    font-weight: 700;
    color: var(--accent);
    line-height: 1;
}}

.stat-label {{
    font-size: 10px;
    color: var(--muted);
    margin-top: 3px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ── Search & sort ── */
.search-section {{
    padding: 14px 16px 10px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}}

.search-label {{
    font-size: 11px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 8px;
}}

.location-input-wrap {{
    display: flex;
    gap: 8px;
    margin-bottom: 10px;
}}

.location-input {{
    flex: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 9px 12px;
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;
}}

.location-input:focus {{ border-color: var(--accent); }}
.location-input::placeholder {{ color: var(--muted); }}

.locate-btn {{
    background: var(--accent);
    border: none;
    border-radius: 8px;
    padding: 0 12px;
    cursor: pointer;
    font-size: 16px;
    transition: opacity 0.2s;
    flex-shrink: 0;
}}

.locate-btn:hover {{ opacity: 0.8; }}

.sort-row {{
    display: flex;
    gap: 6px;
}}

.sort-btn {{
    flex: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 0;
    color: var(--muted);
    font-family: 'DM Sans', sans-serif;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;
}}

.sort-btn.active {{
    background: var(--accent);
    border-color: var(--accent);
    color: #000;
    font-weight: 700;
}}

/* ── Padel list ── */
.list-section {{
    flex: 1;
    overflow-y: auto;
    padding: 10px 16px 80px;
}}

.list-section::-webkit-scrollbar {{ width: 4px; }}
.list-section::-webkit-scrollbar-track {{ background: transparent; }}
.list-section::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

.padel-item {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 6px;
    cursor: pointer;
    transition: all 0.15s;
    gap: 8px;
}}

.padel-item:hover {{
    border-color: var(--accent);
    background: var(--surface2);
    transform: translateX(2px);
}}

.padel-item.nearby {{
    border-color: var(--accent2);
    background: rgba(59,158,255,0.08);
}}

.padel-name {{
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.padel-rating {{
    font-size: 11px;
    font-weight: 700;
    color: #000;
    padding: 3px 8px;
    border-radius: 20px;
    white-space: nowrap;
    flex-shrink: 0;
}}

.padel-dist {{
    font-size: 11px;
    color: var(--accent2);
    white-space: nowrap;
    flex-shrink: 0;
}}

/* ── Nearest result banner ── */
#nearest-banner {{
    display: none;
    padding: 10px 16px;
    background: rgba(0,200,150,0.1);
    border-bottom: 1px solid var(--accent);
    flex-shrink: 0;
}}

.nearest-title {{
    font-size: 11px;
    font-weight: 600;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 4px;
}}

.nearest-name {{
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
}}

.nearest-dist {{
    font-size: 12px;
    color: var(--muted);
    margin-top: 2px;
}}

/* ── Legend ── */
.legend-section {{
    padding: 12px 16px;
    border-top: 1px solid var(--border);
    flex-shrink: 0;
}}

.legend-title {{
    font-size: 10px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 8px;
}}

.legend-row {{
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}}

.legend-item {{
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    color: var(--muted);
}}

.legend-dot {{
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}}

/* ── Mobile ── */
@media (max-width: 640px) {{
    :root {{ --sidebar-w: 100vw; }}

    #sidebar {{
        transform: translateX(-100%);
    }}

    #sidebar:not(.collapsed) {{
        transform: translateX(0);
    }}

    #toggle-btn {{
        top: 12px; left: 12px;
        width: 40px; height: 40px;
    }}

    #sidebar:not(.collapsed) + #toggle-btn {{
        left: calc(100vw - 52px);
        top: 12px;
    }}
}}

/* ── Map offset ── */
@media (min-width: 641px) {{
    #map {{
        margin-left: var(--sidebar-w);
        transition: margin-left 0.35s cubic-bezier(0.4,0,0.2,1);
    }}

    body.sidebar-collapsed #map {{
        margin-left: 0;
    }}
}}
</style>

<!-- Sidebar -->
<div id="sidebar">
    <div class="sidebar-header">
        <div class="sidebar-title">🎾 Padel Bintaro</div>
        <div class="sidebar-sub">Isochrone Coverage · 10 min drive</div>
    </div>

    <div class="stats-row">
        <div class="stat-card">
            <div class="stat-num">{total_lapangan}</div>
            <div class="stat-label">Lapangan</div>
        </div>
        <div class="stat-card">
            <div class="stat-num">{avg_rating}</div>
            <div class="stat-label">Avg ⭐</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" style="color:var(--accent)">{covered_count}</div>
            <div class="stat-label">Covered</div>
        </div>
    </div>

    <!-- Nearest result -->
    <div id="nearest-banner">
        <div class="nearest-title">📍 Lapangan Terdekat</div>
        <div class="nearest-name" id="nearest-name">—</div>
        <div class="nearest-dist" id="nearest-dist">—</div>
    </div>

    <!-- Search & sort -->
    <div class="search-section">
        <div class="search-label">Cari lapangan terdekat</div>
        <div class="location-input-wrap">
            <input class="location-input" id="loc-input"
                   placeholder="Ketik alamat / area lo..." type="text"
                   onkeydown="if(event.key==='Enter') geocodeAndFind()">
            <button class="locate-btn" onclick="useMyLocation()" title="Pakai lokasi saya">📍</button>
        </div>
        <div class="sort-row">
            <button class="sort-btn active" id="sort-rating" onclick="sortList('rating')">⭐ Rating</button>
            <button class="sort-btn" id="sort-dist" onclick="sortList('distance')">📏 Jarak</button>
            <button class="sort-btn" id="sort-name" onclick="sortList('name')">🔤 Nama</button>
        </div>
    </div>

    <!-- Padel list -->
    <div class="list-section" id="padel-list">
        {padel_list_html}
    </div>

    <!-- Legend -->
    <div class="legend-section">
        <div class="legend-title">Rating</div>
        <div class="legend-row">
            <div class="legend-item"><div class="legend-dot" style="background:#00C896"></div>≥ 4.7</div>
            <div class="legend-item"><div class="legend-dot" style="background:#3B9EFF"></div>≥ 4.4</div>
            <div class="legend-item"><div class="legend-dot" style="background:#FFD700"></div>≥ 4.0</div>
            <div class="legend-item"><div class="legend-dot" style="background:#FF6B6B"></div>< 4.0</div>
        </div>
    </div>
</div>

<!-- Toggle button -->
<button id="toggle-btn" onclick="toggleSidebar()">☰</button>

<script>
// ── Sidebar toggle ─────────────────────────────────────────────────────────
function toggleSidebar() {{
    const sidebar = document.getElementById('sidebar');
    const btn     = document.getElementById('toggle-btn');
    sidebar.classList.toggle('collapsed');
    document.body.classList.toggle('sidebar-collapsed');
    btn.textContent = sidebar.classList.contains('collapsed') ? '☰' : '✕';
    setTimeout(() => {{ window.dispatchEvent(new Event('resize')); }}, 360);
}}

// Auto-collapse on mobile
if (window.innerWidth <= 640) {{
    document.getElementById('sidebar').classList.add('collapsed');
    document.getElementById('toggle-btn').textContent = '☰';
}}

// ── Padel data (injected from Python) ─────────────────────────────────────
const padelData = {padel_df[['name','lat','lon','rating','assigned_kelurahan']].to_json(orient='records')};

// ── Fly to location on map ─────────────────────────────────────────────────
function flyTo(lat, lon) {{
    const map = document.querySelector('#map iframe') ||
                window.frames[0];
    // Try to pan the folium map
    try {{
        const leafletMap = Object.values(window).find(v => v && v._leaflet_id);
        if (leafletMap) leafletMap.setView([lat, lon], 16);
    }} catch(e) {{}}

    // Mobile: collapse sidebar after click
    if (window.innerWidth <= 640) {{
        document.getElementById('sidebar').classList.add('collapsed');
        document.getElementById('toggle-btn').textContent = '☰';
    }}
}}

// ── Haversine distance ─────────────────────────────────────────────────────
function haversine(lat1, lon1, lat2, lon2) {{
    const R = 6371000;
    const dLat = (lat2-lat1) * Math.PI/180;
    const dLon = (lon2-lon1) * Math.PI/180;
    const a = Math.sin(dLat/2)**2 +
              Math.cos(lat1*Math.PI/180) * Math.cos(lat2*Math.PI/180) * Math.sin(dLon/2)**2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}}

// ── Find nearest from coords ───────────────────────────────────────────────
function findNearest(userLat, userLon) {{
    let nearest = null, minDist = Infinity;
    padelData.forEach(p => {{
        const d = haversine(userLat, userLon, p.lat, p.lon);
        if (d < minDist) {{ minDist = d; nearest = p; }}
    }});

    if (!nearest) return;

    // Show banner
    const banner = document.getElementById('nearest-banner');
    banner.style.display = 'block';
    document.getElementById('nearest-name').textContent = nearest.name;
    document.getElementById('nearest-dist').textContent =
        minDist < 1000
            ? `${Math.round(minDist)} m dari lokasi lo`
            : `${(minDist/1000).toFixed(1)} km dari lokasi lo`;

    // Highlight in list
    document.querySelectorAll('.padel-item').forEach(el => {{
        el.classList.toggle('nearby', el.dataset.name === nearest.name);
    }});

    // Sort by distance from user
    sortList('distance', userLat, userLon);
    flyTo(nearest.lat, nearest.lon);
}}

// ── Geocode address then find nearest ─────────────────────────────────────
function geocodeAndFind() {{
    const q = document.getElementById('loc-input').value.trim();
    if (!q) return;
    const query = q + ', Bintaro, Indonesia';
    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${{encodeURIComponent(query)}}&limit=1`)
        .then(r => r.json())
        .then(data => {{
            if (!data.length) {{ alert('Lokasi tidak ditemukan, coba lebih spesifik'); return; }}
            const {{ lat, lon }} = data[0];
            findNearest(parseFloat(lat), parseFloat(lon));
        }})
        .catch(() => alert('Gagal geocode, cek koneksi internet'));
}}

// ── Use device GPS ─────────────────────────────────────────────────────────
function useMyLocation() {{
    if (!navigator.geolocation) {{ alert('GPS tidak tersedia'); return; }}
    const btn = document.querySelector('.locate-btn');
    btn.textContent = '⏳';
    navigator.geolocation.getCurrentPosition(
        pos => {{
            btn.textContent = '📍';
            findNearest(pos.coords.latitude, pos.coords.longitude);
        }},
        () => {{ btn.textContent = '📍'; alert('Izin lokasi ditolak'); }}
    );
}}

// ── Sort list ──────────────────────────────────────────────────────────────
function sortList(by, userLat, userLon) {{
    const list  = document.getElementById('padel-list');
    const items = [...list.querySelectorAll('.padel-item')];

    items.sort((a, b) => {{
        if (by === 'rating') {{
            return parseFloat(b.dataset.rating||0) - parseFloat(a.dataset.rating||0);
        }} else if (by === 'name') {{
            return (a.dataset.name||'').localeCompare(b.dataset.name||'');
        }} else if (by === 'distance' && userLat != null) {{
            const da = haversine(userLat, userLon, parseFloat(a.dataset.lat), parseFloat(a.dataset.lon));
            const db = haversine(userLat, userLon, parseFloat(b.dataset.lat), parseFloat(b.dataset.lon));
            return da - db;
        }}
        return 0;
    }});

    // Update distance labels if sorting by distance
    if (by === 'distance' && userLat != null) {{
        items.forEach(item => {{
            const d = haversine(userLat, userLon, parseFloat(item.dataset.lat), parseFloat(item.dataset.lon));
            let distEl = item.querySelector('.padel-dist');
            if (!distEl) {{
                distEl = document.createElement('div');
                distEl.className = 'padel-dist';
                item.appendChild(distEl);
            }}
            distEl.textContent = d < 1000 ? `${{Math.round(d)}}m` : `${{(d/1000).toFixed(1)}}km`;
        }});
    }}

    list.innerHTML = '';
    items.forEach(el => list.appendChild(el));

    // Update active sort btn
    ['rating','dist','name'].forEach(s => {{
        document.getElementById('sort-'+s)?.classList.toggle('active', s === by || (s==='dist' && by==='distance'));
    }});
}}
</script>
"""

m.get_root().html.add_child(folium.Element(ui_html))

# ── Save ──────────────────────────────────────────────────────────────────────
out_path = OUT / "isochrone_map_v3.html"
m.save(str(out_path))
print(f"✓ Saved → {out_path}")
print("  Open di browser — sidebar collapsible, input lokasi, sort by rating/jarak/nama")