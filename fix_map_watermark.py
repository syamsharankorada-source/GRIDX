import os, subprocess, zipfile
from pathlib import Path

CWD = Path.cwd()
PROJECT_ROOT = CWD if (CWD / "manage.py").exists() else (CWD / "gridx_project")

# 1. Update static/js/maps.js to use Esri World Street Map (No API Key Required, No Watermark) + Django Proxy backup
MAPS_JS = """window.gridxMap = null;
window.customerMarker = null;

window.createGridXPin = function(bgHex, textHex, borderHex, labelText) {
    return L.divIcon({
        className: 'gridx-custom-pin',
        html: `<div style="background:${bgHex};color:${textHex};border:2.5px solid ${borderHex};padding:4px 10px;border-radius:20px;font-weight:800;font-size:11px;white-space:nowrap;box-shadow:0 4px 12px rgba(0,0,0,0.45);display:inline-flex;align-items:center;gap:5px;">
                <span style="width:8px;height:8px;border-radius:50%;background:${textHex};display:inline-block;"></span>${labelText}
               </div>`,
        iconSize: [120, 30],
        iconAnchor: [60, 15]
    });
};

window.addReliableMapTiles = function(mapInstance) {
    // Primary: Esri World Street Map — 100% Free, No API Key Required, No 403 Block, No Watermarks
    const esriStreetLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: '&copy; Esri &copy; OpenStreetMap'
    });

    // Backup: Local Django Server Tile Proxy
    const djangoProxyLayer = L.tileLayer('/api/map-tiles/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap'
    });

    let switched = false;
    esriStreetLayer.on('tileerror', function() {
        if (!switched) {
            switched = true;
            mapInstance.removeLayer(esriStreetLayer);
            djangoProxyLayer.addTo(mapInstance);
        }
    });

    esriStreetLayer.addTo(mapInstance);
};

window.initCustomerDashboardMap = function(defaultLat, defaultLng, providersData) {
    const mapEl = document.getElementById('dashboard-map');
    if (!mapEl || typeof L === 'undefined') return;

    if (window.gridxMap) {
        window.gridxMap.remove();
    }

    window.gridxMap = L.map('dashboard-map', { zoomControl: true }).setView([defaultLat, defaultLng], 13);
    window.addReliableMapTiles(window.gridxMap);

    setTimeout(() => { window.gridxMap.invalidateSize(); }, 200);

    window.customerMarker = L.marker([defaultLat, defaultLng], {
        draggable: true,
        icon: window.createGridXPin('#FFD000', '#07080B', '#07080B', 'YOUR LOCATION')
    }).addTo(window.gridxMap).bindPopup('<b>Your Location</b><br><span style="color:#FFD000;">Touch or drag this pin to your exact spot</span>').openPopup();

    window.zoneCircle = L.circle([defaultLat, defaultLng], {
        radius: 2500,
        color: '#07080B',
        weight: 2,
        dashArray: '6, 6',
        fillColor: '#FFD000',
        fillOpacity: 0.15
    }).addTo(window.gridxMap);

    window.customerMarker.on('dragend', function(e) {
        const p = e.target.getLatLng();
        window.zoneCircle.setLatLng(p);
        window.updateBookingCoordinates(p.lat, p.lng);
    });

    window.gridxMap.on('click', function(e) {
        window.customerMarker.setLatLng(e.latlng);
        window.zoneCircle.setLatLng(e.latlng);
        window.updateBookingCoordinates(e.latlng.lat, e.latlng.lng);
    });

    (providersData || []).forEach(p => {
        L.marker([p.lat, p.lng], {
            icon: window.createGridXPin('#07080B', '#FFD000', '#FFD000', 'MECHANIC ★ ' + (p.rating || '4.9'))
        }).addTo(window.gridxMap).bindPopup(`<b style="color:#FFD000;">${p.name}</b><br>Available Nearby`);
    });
};

window.updateBookingCoordinates = async function(lat, lng) {
    const latEl = document.getElementById('customer_lat');
    const lngEl = document.getElementById('customer_lng');
    if (latEl) latEl.value = Number(lat).toFixed(6);
    if (lngEl) lngEl.value = Number(lng).toFixed(6);
};

window.setQuickCityPreset = function(lat, lng, label) {
    window.updateBookingCoordinates(lat, lng);
    const addrEl = document.getElementById('customer_address');
    if (addrEl) addrEl.value = label;
    if (window.gridxMap && window.customerMarker) {
        window.gridxMap.setView([lat, lng], 14);
        window.customerMarker.setLatLng([lat, lng]);
        if (window.zoneCircle) window.zoneCircle.setLatLng([lat, lng]);
        window.gridxMap.invalidateSize();
    }
    showToast(`Location set to ${label}`);
};

window.detectBrowserGeolocation = function() {
    if (!navigator.geolocation) return showToast('Phone/Browser GPS not available.', 'danger');
    navigator.geolocation.getCurrentPosition(pos => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        window.updateBookingCoordinates(lat, lng);
        if (window.gridxMap && window.customerMarker) {
            window.gridxMap.setView([lat, lng], 15);
            window.customerMarker.setLatLng([lat, lng]);
            if (window.zoneCircle) window.zoneCircle.setLatLng([lat, lng]);
            window.gridxMap.invalidateSize();
        }
        showToast('Found your current location!');
    }, () => showToast('Could not get GPS. Please click your spot on the map.', 'warning'));
};
"""

(PROJECT_ROOT / "static/js/maps.js").write_text(MAPS_JS.strip() + "\n", encoding="utf-8")

# 2. Add Server-Side Tile Proxy in services/views.py & services/urls.py so OSM never blocks
views_path = PROJECT_ROOT / "services/views.py"
views_code = views_path.read_text(encoding="utf-8")
if "def map_tile_proxy" not in views_code:
    proxy_func = """
import requests as http_requests
from django.http import HttpResponse

def map_tile_proxy(request, z, x, y):
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    try:
        r = http_requests.get(url, headers={"User-Agent": "GRIDX-Roadside-Assistance-Platform/2.0 (Vijayawada-Guntur)"}, timeout=5)
        if r.status_code == 200:
            res = HttpResponse(r.content, content_type="image/png")
            res["Cache-Control"] = "public, max-age=86400"
            return res
    except Exception:
        pass
    return HttpResponse(status=404)
"""
    views_path.write_text(views_code + "\n" + proxy_func, encoding="utf-8")

urls_path = PROJECT_ROOT / "services/urls.py"
urls_code = urls_path.read_text(encoding="utf-8")
if "map_tile_proxy" not in urls_code:
    urls_code = urls_code.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('api/map-tiles/<int:z>/<int:x>/<int:y>.png', views.map_tile_proxy, name='map_tile_proxy'),"
    )
    urls_path.write_text(urls_code, encoding="utf-8")

# 3. Commit to Git and update ZIP
try:
    subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT, check=False)
    subprocess.run(["git", "commit", "-m", "fix: replace Carto watermarked tiles with key-free Esri World Street Map and Django tile proxy"], cwd=PROJECT_ROOT, check=False)
except Exception:
    pass

zip_path = PROJECT_ROOT.parent / "gridx_project_refined.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for fp in PROJECT_ROOT.rglob("*"):
        if fp.is_file() and "venv" not in fp.parts and ".git" not in fp.parts and "__pycache__" not in fp.parts and fp.name != "db.sqlite3":
            zf.write(fp, fp.relative_to(PROJECT_ROOT.parent))

print("[OK] Removed Carto API Key Watermark! Esri Street Map + Django Tile Proxy Active.")
print("[OK] Updated ZIP:", zip_path.resolve())
