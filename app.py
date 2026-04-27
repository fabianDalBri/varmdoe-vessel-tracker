from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import psycopg2
from config import DB_PASSWORD

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_vessels():
    conn = psycopg2.connect(
        dbname="varmdoe_geodata",
        user="postgres",
        password=DB_PASSWORD,
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT ON (mmsi)
            mmsi, vessel_name, lat, lon, speed, heading, timestamp
        FROM vessels
        ORDER BY mmsi, timestamp DESC;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "mmsi": r[0],
            "name": r[1],
            "lat": r[2],
            "lon": r[3],
            "speed": r[4],
            "heading": r[5] if r[5] != 511 else 0,
            "timestamp": str(r[6])
        }
        for r in rows
    ]

@app.get("/vessels")
def vessels_endpoint():
    return get_vessels()

@app.get("/", response_class=HTMLResponse)
def map_page():
    return """
<!DOCTYPE html>
<html lang="sv">
<head>
    <title>Värmdö Fartygsövervakning</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@300;400;600;700&family=Source+Serif+4:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --navy: #1a3a5c;
            --accent: #c8a84b;
            --accent-light: #e8c87b;
        }

        [data-theme="dark"] {
            --bg: #0d1520;
            --surface: #152030;
            --surface2: #1e2f42;
            --text-main: #e8eef5;
            --text-muted: #8aa0b8;
            --border-col: #2a3f55;
        }

        [data-theme="light"] {
            --bg: #f0f4f8;
            --surface: #ffffff;
            --surface2: #e8eef5;
            --text-main: #1a2533;
            --text-muted: #5a6a7a;
            --border-col: #dde3ea;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Source Sans 3', sans-serif;
            background: var(--bg);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        #top-bar {
            height: 42px;
            background: var(--navy);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 28px;
            font-size: 13px;
            color: rgba(255,255,255,0.7);
            flex-shrink: 0;
        }

        #top-bar a {
            color: rgba(255,255,255,0.6);
            text-decoration: none;
            margin-right: 20px;
            transition: color 0.2s;
        }

        #top-bar a:hover { color: white; }

        #navbar {
            height: 72px;
            background: var(--surface);
            border-bottom: 3px solid var(--accent);
            display: flex;
            align-items: center;
            padding: 0 28px;
            gap: 18px;
            flex-shrink: 0;
            box-shadow: 0 2px 12px rgba(0,0,0,0.12);
            z-index: 1000;
        }

        #logo-area {
            display: flex;
            align-items: center;
            gap: 14px;
            margin-right: 28px;
        }

        #logo-area img {
            height: 48px;
            width: auto;
            display: block;
        }

        #logo-text .main {
            font-family: 'Source Serif 4', serif;
            font-size: 20px;
            font-weight: 600;
            color: var(--navy);
            display: block;
            line-height: 1.1;
        }

        [data-theme="dark"] #logo-text .main { color: var(--text-main); }

        #logo-text .sub {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-weight: 600;
            display: block;
        }

        .nav-divider {
            width: 1px;
            height: 32px;
            background: var(--border-col);
        }

        #nav-stats {
            display: flex;
            gap: 24px;
            flex: 1;
        }

        .stat-item {
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .stat-value {
            font-size: 23px;
            font-weight: 700;
            color: var(--navy);
            line-height: 1;
        }

        [data-theme="dark"] .stat-value { color: var(--accent-light); }

        .stat-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            font-weight: 600;
            margin-top: 2px;
        }

        #live-badge {
            display: flex;
            align-items: center;
            gap: 7px;
            background: rgba(0,200,100,0.1);
            border: 1px solid rgba(0,200,100,0.3);
            border-radius: 20px;
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 700;
            color: #00c864;
            letter-spacing: 1px;
        }

        .live-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #00c864;
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.7); }
        }

        #theme-toggle {
            background: var(--surface2);
            border: 1px solid var(--border-col);
            border-radius: 20px;
            padding: 8px 16px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 7px;
            transition: all 0.2s;
            font-family: 'Source Sans 3', sans-serif;
            white-space: nowrap;
        }

        #theme-toggle:hover {
            background: var(--navy);
            color: white;
            border-color: var(--navy);
        }

        #map-wrap {
            position: relative;
            flex: 1;
            min-height: 0;
        }

        #map {
            width: 100%;
            height: 100%;
        }

        #legend {
            position: absolute;
            bottom: 32px;
            left: 14px;
            background: var(--surface);
            border: 1px solid var(--border-col);
            border-radius: 8px;
            padding: 12px 16px;
            z-index: 900;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }

        #legend h4 {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-bottom: 9px;
            font-weight: 700;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 9px;
            margin-bottom: 6px;
            color: var(--text-main);
            font-size: 13px;
        }

        .legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 2px;
            flex-shrink: 0;
        }

        .leaflet-popup-content-wrapper {
            border-radius: 8px !important;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2) !important;
            padding: 0 !important;
            overflow: hidden;
        }

        .leaflet-popup-content { margin: 0 !important; }

        .vessel-popup { min-width: 230px; }

        .popup-header {
            background: var(--navy);
            color: white;
            padding: 12px 16px;
            font-weight: 700;
            font-size: 16px;
            font-family: 'Source Sans 3', sans-serif;
        }

        .popup-body {
            padding: 14px 16px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            background: white;
        }

        .popup-field-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #8aa0b8;
            font-weight: 700;
            margin-bottom: 3px;
            display: block;
        }

        .popup-field-value {
            font-size: 15px;
            font-weight: 600;
            color: #1a2533;
            display: block;
        }

        .popup-age-row {
            grid-column: 1 / -1;
            padding-top: 8px;
            border-top: 1px solid #eee;
            font-size: 13px;
        }

        .leaflet-popup-tip-container { display: none; }
    </style>
</head>
<body data-theme="light">

    <div id="top-bar">
        <div>
            <a href="#">Startsida</a>
            <a href="#">Om tjänsten</a>
            <a href="#">Kontakt</a>
        </div>
        <span id="last-update-bar">Senast uppdaterad: –</span>
    </div>

    <div id="navbar">
        <div id="logo-area">
            <img src="/static/varmdoe.png" alt="Värmdö Kommun logotyp"/>
            <div id="logo-text">
                <span class="main">Värmdö Kommun</span>
                <span class="sub">Fartygsövervakning · Live AIS</span>
            </div>
        </div>

        <div class="nav-divider"></div>

        <div id="nav-stats">
            <div class="stat-item">
                <span class="stat-value" id="stat-total">–</span>
                <span class="stat-label">Totalt</span>
            </div>
            <div class="stat-item">
                <span class="stat-value" id="stat-moving">–</span>
                <span class="stat-label">I rörelse</span>
            </div>
            <div class="stat-item">
                <span class="stat-value" id="stat-fast">–</span>
                <span class="stat-label">&gt;5 knop</span>
            </div>
            <div class="stat-item">
                <span class="stat-value" id="stat-stationary">–</span>
                <span class="stat-label">Stationära</span>
            </div>
        </div>

        <div id="live-badge">
            <div class="live-dot"></div>
            LIVE
        </div>

        <button id="theme-toggle" onclick="toggleTheme()">Mörkt läge</button>
    </div>

    <div id="map-wrap">
        <div id="map"></div>
        <div id="legend">
            <h4>Hastighet</h4>
            <div class="legend-item">
                <div class="legend-dot" style="background:#00ffcc"></div>
                Snabb (&gt;5 knop)
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background:#ffaa00"></div>
                Långsam (1–5 knop)
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background:#ff4444"></div>
                Stationär (0 knop)
            </div>
        </div>
    </div>

<script>
    let isDark = false;
    let currentTileLayer = null;

    const darkTiles = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
    const lightTiles = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';

    const map = L.map('map', { center: [59.2, 18.6], zoom: 10, zoomControl: true });

    currentTileLayer = L.tileLayer(darkTiles, {
        attribution: '© OpenStreetMap © CartoDB', maxZoom: 18
    }).addTo(map);

    function toggleTheme() {
        isDark = !isDark;
        document.body.setAttribute('data-theme', isDark ? 'dark' : 'light');
        document.getElementById('theme-toggle').textContent = isDark ? 'Ljust läge' : 'Mörkt läge';
        map.removeLayer(currentTileLayer);
        currentTileLayer = L.tileLayer(isDark ? darkTiles : lightTiles, {
            attribution: '© OpenStreetMap © CartoDB', maxZoom: 18
        }).addTo(map);
    }

    const markers = {};
    const vesselTimestamps = {};

    function createArrowIcon(heading, speed) {
        const color = speed > 5 ? '#00ffcc' : speed > 0 ? '#ffaa00' : '#ff4444';
        const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24">
            <g transform="rotate(${heading}, 12, 12)">
                <polygon points="12,2 18,20 12,16 6,20" fill="${color}" stroke="#000" stroke-width="1"/>
            </g>
        </svg>`;
        return L.divIcon({ html: svg, className: '', iconSize: [28, 28], iconAnchor: [14, 14] });
    }

    function getAgeHTML(mmsi) {
        const ts = vesselTimestamps[mmsi];
        if (!ts) return '<span style="color:#888">okänd tid</span>';
        const diff = Math.floor((new Date() - new Date(ts + 'Z')) / 1000);
        if (isNaN(diff) || diff < 0) return '<span style="color:#888">okänd tid</span>';
        const m = Math.floor(diff / 60);
        const s = diff % 60;
        const age = m > 0 ? `${m}m ${s}s sedan` : `${s}s sedan`;
        const color = diff > 120 ? '#ff4444' : diff > 30 ? '#ffaa00' : '#00c864';
        return `<span style="color:${color}; font-weight:600;">⏱ ${age}</span>`;
    }

    function buildPopup(v) {
        const time = new Date(v.timestamp + 'Z').toLocaleTimeString('sv-SE');
        return `<div class="vessel-popup">
            <div class="popup-header">⚓ ${v.name || 'Okänt fartyg'}</div>
            <div class="popup-body">
                <div>
                    <span class="popup-field-label">MMSI</span>
                    <span class="popup-field-value">${v.mmsi}</span>
                </div>
                <div>
                    <span class="popup-field-label">Hastighet</span>
                    <span class="popup-field-value">${v.speed} kn</span>
                </div>
                <div>
                    <span class="popup-field-label">Kurs</span>
                    <span class="popup-field-value">${v.heading}°</span>
                </div>
                <div>
                    <span class="popup-field-label">Senast sedd</span>
                    <span class="popup-field-value">${time}</span>
                </div>
                <div class="popup-age-row">
                    <span id="age-${v.mmsi}">${getAgeHTML(v.mmsi)}</span>
                </div>
            </div>
        </div>`;
    }

    function updateVessels() {
        fetch('/vessels')
            .then(r => r.json())
            .then(vessels => {
                const active = new Set();
                let moving = 0, fast = 0, stationary = 0;

                vessels.forEach(v => {
                    active.add(v.mmsi);
                    vesselTimestamps[v.mmsi] = v.timestamp;
                    if (v.speed > 5) fast++;
                    else if (v.speed > 0) moving++;
                    else stationary++;

                    const icon = createArrowIcon(v.heading, v.speed);
                    if (markers[v.mmsi]) {
                        markers[v.mmsi].setLatLng([v.lat, v.lon]);
                        markers[v.mmsi].setIcon(icon);
                        markers[v.mmsi].setPopupContent(buildPopup(v));
                    } else {
                        markers[v.mmsi] = L.marker([v.lat, v.lon], { icon })
                            .bindPopup(buildPopup(v), { maxWidth: 280 })
                            .addTo(map);
                    }
                });

                Object.keys(markers).forEach(mmsi => {
                    if (!active.has(mmsi)) {
                        map.removeLayer(markers[mmsi]);
                        delete markers[mmsi];
                    }
                });

                document.getElementById('stat-total').textContent = vessels.length;
                document.getElementById('stat-moving').textContent = moving + fast;
                document.getElementById('stat-fast').textContent = fast;
                document.getElementById('stat-stationary').textContent = stationary;
                document.getElementById('last-update-bar').textContent =
                    'Senast uppdaterad: ' + new Date().toLocaleTimeString('sv-SE');
            });
    }

    function updateAges() {
        Object.keys(vesselTimestamps).forEach(mmsi => {
            const el = document.getElementById('age-' + mmsi);
            if (el) el.innerHTML = getAgeHTML(mmsi);
        });
    }

    updateVessels();
    setInterval(updateVessels, 5000);
    setInterval(updateAges, 1000);
</script>
</body>
</html>
    """