from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import psycopg2
from config import DB_PASSWORD
 
app = FastAPI()
 
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
<html>
<head>
    <title>Värmdö Vessel Tracker</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body { margin: 0; background: #0a0a0a; font-family: monospace; }
        #map { height: 100vh; width: 100%; }
        #hud {
            position: fixed;
            top: 15px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.75);
            color: #00ffcc;
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 13px;
            z-index: 1000;
            border: 1px solid #00ffcc44;
        }
        #vessel-count {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(0,0,0,0.75);
            color: #00ffcc;
            padding: 8px 16px;
            border-radius: 10px;
            font-size: 12px;
            z-index: 1000;
            border: 1px solid #00ffcc44;
        }
    </style>
</head>
<body>
    <div id="hud">⚓ VÄRMDÖ VESSEL TRACKER — live AIS — updates every 5s</div>
    <div id="vessel-count">Loading...</div>
    <div id="map"></div>
 
<script>
    const map = L.map('map', {
        center: [59.2, 18.6],
        zoom: 10,
        zoomControl: true
    });
 
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap © CartoDB',
        maxZoom: 18
    }).addTo(map);
 
    const markers = {};
    const vesselTimestamps = {};
 
    function createArrowIcon(heading, speed) {
        const color = speed > 5 ? '#00ffcc' : speed > 0 ? '#ffaa00' : '#ff4444';
        const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
            <g transform="rotate(${heading}, 12, 12)">
                <polygon points="12,2 18,20 12,16 6,20" 
                         fill="${color}" 
                         stroke="#000" 
                         stroke-width="1"/>
            </g>
        </svg>`;
        return L.divIcon({
            html: svg,
            className: '',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        });
    }
 
    function getAgeHTML(mmsi) {
        const timestamp = vesselTimestamps[mmsi];
        if (!timestamp) return '<span style="color:#888">⏱ unknown</span>';
        const diff = Math.floor((new Date() - new Date(timestamp + 'Z')) / 1000);
        if (isNaN(diff) || diff < 0) return '<span style="color:#888">⏱ unknown</span>';
        const m = Math.floor(diff / 60);
        const s = diff % 60;
        const age = m > 0 ? `${m}m ${s}s ago` : `${s}s ago`;
        const color = diff > 120 ? '#ff4444' : diff > 30 ? '#ffaa00' : '#00ffcc';
        return `<span style="color:${color}">⏱ ${age}</span>`;
    }
 
    function buildPopup(v) {
        return `
            <b>${v.name || 'Unknown'}</b><br>
            MMSI: ${v.mmsi}<br>
            Speed: ${v.speed} knots<br>
            Heading: ${v.heading}°<br>
            Last seen: ${new Date(v.timestamp + 'Z').toLocaleTimeString('sv-SE')}<br>
            <span id="age-${v.mmsi}">${getAgeHTML(v.mmsi)}</span>
        `;
    }
 
    function updateVessels() {
        fetch('/vessels')
            .then(r => r.json())
            .then(vessels => {
                const active = new Set();
 
                vessels.forEach(v => {
                    active.add(v.mmsi);
                    vesselTimestamps[v.mmsi] = v.timestamp;
                    const icon = createArrowIcon(v.heading, v.speed);
 
                    if (markers[v.mmsi]) {
                        markers[v.mmsi].setLatLng([v.lat, v.lon]);
                        markers[v.mmsi].setIcon(icon);
                        markers[v.mmsi].setPopupContent(buildPopup(v));
                    } else {
                        markers[v.mmsi] = L.marker([v.lat, v.lon], { icon })
                            .bindPopup(buildPopup(v))
                            .addTo(map);
                    }
                });
 
                Object.keys(markers).forEach(mmsi => {
                    if (!active.has(mmsi)) {
                        map.removeLayer(markers[mmsi]);
                        delete markers[mmsi];
                    }
                });
 
                document.getElementById('vessel-count').textContent =
                    `${vessels.length} vessels tracked`;
            });
    }
 
    function updateAges() {
        Object.keys(vesselTimestamps).forEach(mmsi => {
            const el = document.getElementById(`age-${mmsi}`);
            if (el) {
                el.innerHTML = getAgeHTML(mmsi);
            }
        });
    }
 
    updateVessels();
    setInterval(updateVessels, 5000);
    setInterval(updateAges, 1000);
</script>
</body>
</html>
    """