import os, subprocess, zipfile
from pathlib import Path

CWD = Path.cwd()
PROJECT_ROOT = CWD if (CWD / "manage.py").exists() else (CWD / "gridx_project")

# 1. Update CSS: Remove grayscale paper filter & add Radar Pulse + Flowing Route animations
style_path = PROJECT_ROOT / "static/css/style.css"
style_code = style_path.read_text(encoding="utf-8")

# Remove grayscale filter that made the map look like paper
style_code = style_code.replace("filter: grayscale(100%) contrast(125%) brightness(104%);", "filter: none;")

ANIMATION_CSS = """
/* === UBER-STYLE LIVE MAP ANIMATIONS === */
.leaflet-tile-pane {
    filter: none !important;
}

@keyframes radar-ring {
    0% { transform: scale(0.4); opacity: 0.95; }
    100% { transform: scale(2.8); opacity: 0; }
}

.gps-pulse-wrap {
    position: relative;
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.gps-pulse-ring {
    position: absolute;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: rgba(255, 208, 0, 0.45);
    border: 2px solid #FFD000;
    animation: radar-ring 2s cubic-bezier(0.2, 0.8, 0.4, 1) infinite;
}

.gps-pin-core {
    position: relative;
    z-index: 2;
    background: #FFD000;
    color: #07080B;
    border: 3px solid #07080B;
    padding: 4px 10px;
    border-radius: 20px;
    font-weight: 900;
    font-size: 11px;
    white-space: nowrap;
    box-shadow: 0 6px 16px rgba(0,0,0,0.5);
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

.mechanic-live-marker {
    transition: transform 0.15s linear;
}

.mechanic-badge {
    background: #07080B;
    color: #FFD000;
    border: 2.5px solid #FFD000;
    padding: 4px 10px;
    border-radius: 20px;
    font-weight: 900;
    font-size: 11px;
    white-space: nowrap;
    box-shadow: 0 6px 18px rgba(0,0,0,0.65);
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

@keyframes route-flow {
    to { stroke-dashoffset: -36; }
}

.animated-route-line {
    animation: route-flow 1s linear infinite;
}

.map-Layer-switcher {
    position: absolute;
    bottom: 14px;
    left: 14px;
    z-index: 600;
    display: flex;
    gap: 6px;
}
"""

if "UBER-STYLE LIVE MAP ANIMATIONS" not in style_code:
    style_path.write_text(style_code + "\n" + ANIMATION_CSS, encoding="utf-8")

# 2. Upgrade static/js/maps.js with Smooth 60FPS Interpolation, Live GPS watchPosition, and Layer Switcher
MAPS_JS = """window.gridxMap = null;
window.customerMarker = null;
window.watchId = null;

window.createCustomerPulsePin = function(labelText = 'YOUR LIVE GPS') {
    return L.divIcon({
        className: 'custom-pulse-pin',
        html: `<div class="gps-pulse-wrap">
                <div class="gps-pulse-ring"></div>
                <div class="gps-pin-core"><i class="bi bi-broadcast"></i> ${labelText}</div>
               </div>`,
        iconSize: [140, 44],
        iconAnchor: [70, 22]
    });
};

window.createMechanicVehiclePin = function(nameText = 'MECHANIC', rating = '4.9') {
    return L.divIcon({
        className: 'mechanic-live-marker',
        html: `<div class="mechanic-badge">
                <span style="background:#FFD000;color:#000;width:22px;height:22px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;">
                    <i class="bi bi-truck-front-fill"></i>
                </span>
                <span>${nameText} ★${rating}</span>
               </div>`,
        iconSize: [150, 34],
        iconAnchor: [75, 17]
    });
};

window.attachMapLayers = function(mapInstance) {
    const streetLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: '&copy; Esri &copy; OpenStreetMap'
    });

    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: '&copy; Esri Satellite'
    });

    const osmProxyLayer = L.tileLayer('/api/map-tiles/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap'
    });

    streetLayer.addTo(mapInstance);

    L.control.layers({
        "🗺️ Street Map": streetLayer,
        "🛰️ Satellite View": satelliteLayer,
        "⚡ High-Speed Roads": osmProxyLayer
    }, null, { position: 'topright' }).addTo(mapInstance);
};

// Smooth 60FPS marker movement between two GPS coordinates
window.animateMarkerGlide = function(marker, startLatLng, endLatLng, durationMs = 1800) {
    if (!marker) return;
    const startTime = performance.now();
    const sLat = startLatLng.lat, sLng = startLatLng.lng;
    const eLat = endLatLng.lat, eLng = endLatLng.lng;

    function frame(now) {
        const progress = Math.min(1, (now - startTime) / durationMs);
        // Ease-in-out cubic curve
        const ease = progress < 0.5 ? 4 * progress * progress * progress : 1 - Math.pow(-2 * progress + 2, 3) / 2;
        const curLat = sLat + (eLat - sLat) * ease;
        const curLng = sLng + (eLng - sLng) * ease;
        marker.setLatLng([curLat, curLng]);
        if (progress < 1) {
            requestAnimationFrame(frame);
        }
    }
    requestAnimationFrame(frame);
};

window.initCustomerDashboardMap = function(defaultLat, defaultLng, providersData) {
    const mapEl = document.getElementById('dashboard-map');
    if (!mapEl || typeof L === 'undefined') return;

    if (window.gridxMap) window.gridxMap.remove();

    window.gridxMap = L.map('dashboard-map', { zoomControl: true }).setView([defaultLat, defaultLng], 14);
    window.attachMapLayers(window.gridxMap);

    setTimeout(() => { window.gridxMap.invalidateSize(); }, 200);

    window.customerMarker = L.marker([defaultLat, defaultLng], {
        draggable: true,
        icon: window.createCustomerPulsePin('YOUR SPOT')
    }).addTo(window.gridxMap).bindPopup('<b>Your Service Location</b><br><span style="color:#FFD000;">Drag pin or click anywhere on map</span>');

    window.zoneCircle = L.circle([defaultLat, defaultLng], {
        radius: 1800,
        color: '#07080B',
        weight: 2,
        dashArray: '6, 6',
        fillColor: '#FFD000',
        fillOpacity: 0.14
    }).addTo(window.gridxMap);

    window.customerMarker.on('dragend', function(e) {
        const p = e.target.getLatLng();
        window.zoneCircle.setLatLng(p);
        window.updateBookingCoordinates(p.lat, p.lng);
    });

    window.gridxMap.on('click', function(e) {
        window.animateMarkerGlide(window.customerMarker, window.customerMarker.getLatLng(), e.latlng, 450);
        window.zoneCircle.setLatLng(e.latlng);
        window.updateBookingCoordinates(e.latlng.lat, e.latlng.lng);
    });

    // Render nearby mechanics with gentle patrol animation
    window.dashboardProviderMarkers = [];
    (providersData || []).forEach((p, idx) => {
        const m = L.marker([p.lat, p.lng], {
            icon: window.createMechanicVehiclePin('MECHANIC', p.rating || '4.9')
        }).addTo(window.gridxMap).bindPopup(`<b style="color:#FFD000;">${p.name}</b><br>Live GPS Online`);
        window.dashboardProviderMarkers.push({ marker: m, baseLat: p.lat, baseLng: p.lng, phase: idx * 1.7 });
    });

    // Subtle real-time patrol movement so dashboard map feels alive
    setInterval(() => {
        const t = Date.now() / 4000;
        (window.dashboardProviderMarkers || []).forEach(item => {
            const newLat = item.baseLat + Math.sin(t + item.phase) * 0.0009;
            const newLng = item.baseLng + Math.cos(t + item.phase) * 0.0009;
            window.animateMarkerGlide(item.marker, item.marker.getLatLng(), { lat: newLat, lng: newLng }, 1900);
        });
    }, 2000);
};

window.updateBookingCoordinates = async function(lat, lng) {
    const latEl = document.getElementById('customer_lat');
    const lngEl = document.getElementById('customer_lng');
    if (latEl) latEl.value = Number(lat).toFixed(6);
    if (lngEl) lngEl.value = Number(lng).toFixed(6);

    try {
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`);
        if (res.ok) {
            const data = await res.json();
            if (data.display_name) {
                const addrEl = document.getElementById('customer_address');
                if (addrEl) addrEl.value = data.display_name.split(',').slice(0, 3).join(', ');
            }
        }
    } catch (e) {}
};

window.setQuickCityPreset = function(lat, lng, label) {
    window.updateBookingCoordinates(lat, lng);
    const addrEl = document.getElementById('customer_address');
    if (addrEl) addrEl.value = label;
    if (window.gridxMap && window.customerMarker) {
        window.gridxMap.flyTo([lat, lng], 15, { animate: true, duration: 1.2 });
        window.customerMarker.setLatLng([lat, lng]);
        if (window.zoneCircle) window.zoneCircle.setLatLng([lat, lng]);
    }
    showToast(`Moved map to ${label}`);
};

window.detectBrowserGeolocation = function() {
    if (!navigator.geolocation) return showToast('GPS not supported on this device.', 'danger');
    showToast('Connecting to live GPS satellite...');
    navigator.geolocation.getCurrentPosition(pos => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        window.updateBookingCoordinates(lat, lng);
        if (window.gridxMap && window.customerMarker) {
            window.gridxMap.flyTo([lat, lng], 16, { animate: true, duration: 1.4 });
            window.customerMarker.setLatLng([lat, lng]);
            if (window.zoneCircle) window.zoneCircle.setLatLng([lat, lng]);
        }
        showToast('Live GPS location locked!');
    }, () => showToast('GPS permission denied. Tap any road on the map to set your spot.', 'warning'), { enableHighAccuracy: true });
};
"""

(PROJECT_ROOT / "static/js/maps.js").write_text(MAPS_JS.strip() + "\n", encoding="utf-8")

# 3. Upgrade templates/pages/tracking.html with Continuous Live Drive Animation Along Road Geometry
TRACKING_HTML = """{% extends 'base.html' %}
{% block content %}
<div class="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
    <div>
        <span class="badge bg-warning text-dark fw-black me-2">BOOKING #{{ booking.id }}</span>
        <h4 class="fw-black d-inline mb-0">{{ booking.category.name }}</h4>
    </div>
    <div class="d-flex flex-wrap gap-2">
        <button id="live-drive-btn" class="btn btn-sm btn-gridx" onclick="startSmoothRoadDriveDemo()">
            <i class="bi bi-play-circle-fill me-1"></i> Start Live Mechanic Drive
        </button>
        <button class="btn btn-sm btn-gridx-outline" onclick="recenterRadar()">
            <i class="bi bi-arrows-fullscreen"></i> Fit Route on Map
        </button>
        <a href="{% url 'booking_detail' booking.id %}" class="btn btn-sm btn-outline-light">View Bill & Rating</a>
    </div>
</div>

<div class="stepper-wrapper mb-4">
    {% for key, label, icon in steps %}
        <div class="stepper-item {% if forloop.counter0 < current_idx %}completed{% elif forloop.counter0 == current_idx %}active{% endif %}">
            <i class="bi {{ icon }} d-block fs-5 mb-1"></i>
            <div style="font-size:0.75rem;">{{ label }}</div>
        </div>
    {% endfor %}
</div>

<div class="row g-4">
    <div class="col-lg-8">
        <div class="gridx-card p-3">
            <div class="map-wrapper">
                <div id="tracking-map" class="map-container" style="height:450px !important;"></div>
            </div>
            <div class="d-flex flex-wrap justify-content-between align-items-center mt-2 small text-secondary">
                <span id="tracking-eta-banner"><span class="live-dot me-2"></span>Connecting to live GPS map...</span>
                <span id="tracking-timestamp" class="text-warning fw-bold"></span>
            </div>
        </div>
    </div>

    <div class="col-lg-4">
        <div class="gridx-card p-4 mb-3 border-top border-3 border-warning">
            <div class="small text-warning fw-bold text-uppercase">Booking Status</div>
            <h3 id="live-status-label" class="fw-black mb-2">{{ booking.get_status_display }}</h3>
            <p class="small text-secondary mb-3"><i class="bi bi-geo-alt text-warning"></i> {{ booking.customer_address }}</p>

            <div class="p-3 rounded mb-3" style="background:#0B0E14; border:1px solid var(--border-grid);">
                <div class="d-flex justify-content-between small mb-1">
                    <span class="text-secondary">Live Distance:</span>
                    <strong id="hud-dist" class="text-white">{{ booking.distance_km }} km</strong>
                </div>
                <div class="d-flex justify-content-between small">
                    <span class="text-secondary">Estimated Arrival:</span>
                    <strong id="hud-eta" class="text-warning">~8 mins</strong>
                </div>
            </div>

            {% if is_assigned_provider %}
                <div class="d-grid gap-2 mb-3">
                    {% if booking.status == 'accepted' %}
                        <button class="btn btn-gridx" onclick="performBookingAction({{ booking.id }}, 'en_route')">Start Going to Customer</button>
                    {% elif booking.status == 'en_route' %}
                        <button class="btn btn-gridx" onclick="performBookingAction({{ booking.id }}, 'arrived')">Reached Customer Spot</button>
                    {% elif booking.status == 'arrived' %}
                        <button class="btn btn-gridx" onclick="performBookingAction({{ booking.id }}, 'in_progress')">Start Repair Work</button>
                    {% elif booking.status == 'in_progress' %}
                        <button class="btn btn-success fw-bold" onclick="performBookingAction({{ booking.id }}, 'completed')">Work Finished & Create Bill</button>
                    {% endif %}
                </div>
            {% endif %}

            {% if booking.status in 'requested,searching,no_provider' and is_owner %}
                <div class="d-grid gap-2">
                    <button class="btn btn-sm btn-gridx" onclick="performBookingAction({{ booking.id }}, 'expand_radius')">
                        Search Mechanics in Wider Area (35 km)
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="performBookingAction({{ booking.id }}, 'cancel')">
                        Cancel Booking
                    </button>
                </div>
            {% endif %}
        </div>

        <div class="gridx-card p-4">
            <h6 class="fw-bold text-warning mb-3"><i class="bi bi-clock-history me-1"></i> Live Updates</h6>
            <div id="timeline-box" class="small">
                {% for h in booking.status_history.all %}
                    <div class="mb-2 border-start border-2 border-warning ps-2">
                        <strong class="text-white text-uppercase">{{ h.to_status }}</strong>
                        <div class="text-secondary" style="font-size:0.76rem;">{{ h.note }} • {{ h.timestamp|date:"H:i:s" }}</div>
                    </div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
let tMap = null, cMarker = null, pMarker = null, routeOutline = null, routeFlowLine = null;
let cachedRoadCoords = [];
let driveInterval = null;
const custLat = {{ booking.customer_lat }};
const custLng = {{ booking.customer_lng }};

window.addEventListener('load', function() {
    tMap = L.map('tracking-map', { zoomControl: true }).setView([custLat, custLng], 14);
    window.attachMapLayers(tMap);
    setTimeout(() => { tMap.invalidateSize(); }, 200);

    cMarker = L.marker([custLat, custLng], {
        icon: window.createCustomerPulsePin('YOUR LOCATION')
    }).addTo(tMap).bindPopup('<b>Your Location</b>');

    pollTracking(true);
    setInterval(() => pollTracking(false), 4000);
});

async function drawAnimatedRoadRoute(lat1, lng1, lat2, lng2, fitView = false) {
    let coords = [[lat1, lng1], [lat2, lng2]];
    try {
        const res = await fetch(`https://router.project-osrm.org/route/v1/driving/${lng1},${lat1};${lng2},${lat2}?overview=full&geometries=geojson`);
        if (res.ok) {
            const data = await res.json();
            if (data.routes && data.routes.length > 0) {
                coords = data.routes[0].geometry.coordinates.map(c => [c[1], c[0]]);
            }
        }
    } catch (e) {}

    cachedRoadCoords = coords;

    if (routeOutline) tMap.removeLayer(routeOutline);
    if (routeFlowLine) tMap.removeLayer(routeFlowLine);

    routeOutline = L.polyline(coords, { color: '#07080B', weight: 10, opacity: 0.9 }).addTo(tMap);
    routeFlowLine = L.polyline(coords, {
        color: '#FFD000',
        weight: 5,
        opacity: 1.0,
        dashArray: '12, 12',
        className: 'animated-route-line'
    }).addTo(tMap);

    if (fitView && coords.length > 1) {
        tMap.fitBounds(routeOutline.getBounds(), { padding: [50, 50] });
    }
}

async function pollTracking(initialFit = false) {
    try {
        const res = await fetch('/api/bookings/{{ booking.id }}/tracking/');
        if (!res.ok) return;
        const d = await res.json();
        document.getElementById('live-status-label').textContent = d.status_display;
        document.getElementById('tracking-timestamp').textContent = 'LIVE GPS ACTIVE • ' + new Date().toLocaleTimeString();

        // Even if no provider accepted yet, show nearest demo mechanic on map so user can see live animation
        const pLoc = d.provider_location || {
            lat: custLat + 0.011,
            lng: custLng - 0.012,
            name: 'Sri Kanaka Durga Mechanic',
            phone: '9848011223',
            rating: '4.9'
        };

        const distKm = d.distance_km !== null ? d.distance_km : 1.6;
        const etaMins = d.eta_mins !== null ? d.eta_mins : 5;

        document.getElementById('hud-dist').textContent = distKm + ' km';
        document.getElementById('hud-eta').textContent = '~' + etaMins + ' mins';

        if (!pMarker) {
            pMarker = L.marker([pLoc.lat, pLoc.lng], {
                icon: window.createMechanicVehiclePin(pLoc.name.split(' ')[0], pLoc.rating || '4.9')
            }).addTo(tMap).bindPopup(`<b style="color:#FFD000;">${pLoc.name}</b><br>Phone: ${pLoc.phone}`);
            await drawAnimatedRoadRoute(pLoc.lat, pLoc.lng, custLat, custLng, true);
        } else if (!driveInterval) {
            window.animateMarkerGlide(pMarker, pMarker.getLatLng(), { lat: pLoc.lat, lng: pLoc.lng }, 1800);
            await drawAnimatedRoadRoute(pLoc.lat, pLoc.lng, custLat, custLng, initialFit);
        }

        document.getElementById('tracking-eta-banner').innerHTML =
            `<span class="live-dot me-2"></span><strong class="text-warning">${pLoc.name}</strong> is <strong>${distKm} km</strong> away • Reaching in <strong>~${etaMins} mins</strong>`;
    } catch (e) {}
}

// Smoothly drives the mechanic marker step-by-step along the real road curve!
async function startSmoothRoadDriveDemo() {
    if (!pMarker) return;
    const btn = document.getElementById('live-drive-btn');
    if (driveInterval) {
        clearInterval(driveInterval);
        driveInterval = null;
        btn.innerHTML = '<i class="bi bi-play-circle-fill me-1"></i> Start Live Mechanic Drive';
        return;
    }

    btn.innerHTML = '<span class="spinner-grow spinner-grow-sm me-1"></span> Mechanic Driving Live...';
    showToast('Live GPS Tracking Started! Watch the mechanic drive along the road.');

    if (cachedRoadCoords.length < 2) {
        const cur = pMarker.getLatLng();
        await drawAnimatedRoadRoute(cur.lat, cur.lng, custLat, custLng, true);
    }

    let stepIndex = 0;
    const pathPoints = cachedRoadCoords.slice();

    driveInterval = setInterval(async () => {
        if (stepIndex >= pathPoints.length - 1) {
            clearInterval(driveInterval);
            driveInterval = null;
            btn.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Mechanic Arrived!';
            document.getElementById('hud-dist').textContent = '0.0 km (Arrived)';
            document.getElementById('hud-eta').textContent = 'Arrived at Spot!';
            showToast('Mechanic has reached your location!');
            return;
        }

        const nextPt = pathPoints[stepIndex + 1];
        window.animateMarkerGlide(pMarker, pMarker.getLatLng(), { lat: nextPt[0], lng: nextPt[1] }, 650);

        const remainingRatio = 1 - (stepIndex / pathPoints.length);
        const remKm = (1.6 * remainingRatio).toFixed(2);
        const remMins = Math.max(1, Math.round(5 * remainingRatio));
        document.getElementById('hud-dist').textContent = remKm + ' km';
        document.getElementById('hud-eta').textContent = '~' + remMins + ' mins';

        // Slice remaining route line dynamically as mechanic drives
        const remainingCoords = pathPoints.slice(stepIndex + 1);
        if (routeOutline) routeOutline.setLatLngs(remainingCoords);
        if (routeFlowLine) routeFlowLine.setLatLngs(remainingCoords);

        stepIndex++;
    }, 700);

    // Also update backend coordinate step
    performBookingAction({{ booking.id }}, 'simulate_step');
}

function recenterRadar() {
    if (tMap && routeOutline) {
        tMap.fitBounds(routeOutline.getBounds(), { padding: [55, 55] });
    } else if (tMap) {
        tMap.flyTo([custLat, custLng], 15);
    }
}
</script>
{% endblock %}
"""

(PROJECT_ROOT / "templates/pages/tracking.html").write_text(TRACKING_HTML.strip() + "\n", encoding="utf-8")

# Commit and update ZIP
try:
    subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT, check=False)
    subprocess.run(["git", "commit", "-m", "feat: add Uber-style 60fps smooth vehicle glide, radar pulse, flowing route line, and satellite switcher"], cwd=PROJECT_ROOT, check=False)
except Exception:
    pass

zip_path = PROJECT_ROOT.parent / "gridx_project_refined.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for fp in PROJECT_ROOT.rglob("*"):
        if fp.is_file() and "venv" not in fp.parts and ".git" not in fp.parts and "__pycache__" not in fp.parts and fp.name != "db.sqlite3":
            zf.write(fp, fp.relative_to(PROJECT_ROOT.parent))

print("[OK] Live Animated Map (Radar Pulse + Smooth Road Glide + Satellite Switcher) Ready!")
print("[OK] Updated ZIP:", zip_path.resolve())
