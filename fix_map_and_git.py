import os, subprocess, zipfile
from pathlib import Path

CWD = Path.cwd()
PROJECT_ROOT = CWD if (CWD / "manage.py").exists() else (CWD / "gridx_project")

FILES = {
    "static/css/style.css": """@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Space+Grotesk:wght@600;700;800&display=swap');

:root {
    --bg-grid-dark: #07080B;
    --bg-surface: #10131A;
    --bg-surface-elevated: #171B26;
    --gridx-yellow: #FFD000;
    --gridx-yellow-hover: #FFDF33;
    --gridx-green: #00E676;
    --text-primary: #F8FAFC;
    --text-secondary: #94A3B8;
    --border-grid: rgba(255, 208, 0, 0.28);
    --border-subtle: rgba(255, 255, 255, 0.1);
    --radius-card: 16px;
    --radius-btn: 10px;
}

body {
    background-color: var(--bg-grid-dark);
    background-image:
        linear-gradient(to right, rgba(255, 255, 255, 0.035) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
    background-size: 36px 36px;
    color: var(--text-primary);
    font-family: 'Inter', system-ui, sans-serif;
    min-height: 100vh;
}

h1, h2, h3, h4, .brand-logo { font-family: 'Space Grotesk', 'Inter', sans-serif; }
.navbar-gridx { background: rgba(7, 8, 11, 0.95); backdrop-filter: blur(14px); border-bottom: 2px solid var(--gridx-yellow); }
.brand-logo { font-weight: 800; letter-spacing: 1.5px; font-size: 1.55rem; color: #FFF; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }
.brand-logo span { background: var(--gridx-yellow); color: #07080B; padding: 0px 8px; border-radius: 6px; font-weight: 900; }

.gridx-card { background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-card); box-shadow: 0 14px 34px rgba(0, 0, 0, 0.65); }
.gridx-card-yellow { background: linear-gradient(135deg, #FFD000 0%, #F5B700 100%); color: #07080B; border-radius: var(--radius-card); font-weight: 700; }

.btn-gridx { background-color: var(--gridx-yellow); color: #07080B !important; font-weight: 800; border: 2px solid #000; border-radius: var(--radius-btn); padding: 0.6rem 1.2rem; text-transform: uppercase; letter-spacing: 0.5px; }
.btn-gridx:hover { background-color: var(--gridx-yellow-hover); transform: translateY(-1px); }
.btn-gridx-outline { background: transparent; color: var(--gridx-yellow) !important; border: 1.5px solid var(--gridx-yellow); font-weight: 700; border-radius: var(--radius-btn); }
.btn-gridx-outline:hover, .btn-gridx-outline.active { background: var(--gridx-yellow); color: #07080B !important; }

.badge-domain-outdoor { background: rgba(255, 208, 0, 0.15); color: var(--gridx-yellow); border: 1px solid var(--gridx-yellow); font-weight: 700; }
.badge-domain-indoor { background: #FFF; color: #07080B; border: 1px solid #FFF; font-weight: 700; }

.service-cat-card { cursor: pointer; border: 1.5px solid var(--border-subtle); position: relative; transition: 0.15s; }
.service-cat-card.active, .service-cat-card:hover { border-color: var(--gridx-yellow); background: var(--bg-surface-elevated); box-shadow: 0 0 0 2px rgba(255, 208, 0, 0.25); }
.service-cat-card.active::after { content: "✓ SELECTED"; position: absolute; top: 8px; right: 10px; font-size: 0.62rem; font-weight: 900; background: var(--gridx-yellow); color: #000; padding: 2px 6px; border-radius: 4px; }

/* WHITE, YELLOW & BLACK MAP THEME */
.map-wrapper {
    position: relative;
    border-radius: var(--radius-card);
    border: 3px solid var(--gridx-yellow);
    box-shadow: 0 10px 30px rgba(0,0,0,0.7);
    overflow: hidden;
    background: #FFFFFF;
}

.map-container {
    height: 390px !important;
    width: 100% !important;
    min-height: 390px !important;
    background-color: #FFFFFF !important;
    background-image:
        linear-gradient(to right, rgba(0, 0, 0, 0.08) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(0, 0, 0, 0.08) 1px, transparent 1px) !important;
    background-size: 28px 28px !important;
    z-index: 1;
}

/* Crisp White & High-Contrast Black Road Filter for Map Tiles */
.leaflet-tile-pane {
    filter: grayscale(100%) contrast(125%) brightness(104%);
}

/* Black & Yellow Styled Map Popups & Controls */
.leaflet-popup-content-wrapper {
    background: #07080B !important;
    color: #FFFFFF !important;
    border: 2px solid #FFD000 !important;
    border-radius: 10px !important;
    font-weight: 600;
}
.leaflet-popup-tip { background: #FFD000 !important; }
.leaflet-bar a {
    background-color: #07080B !important;
    color: #FFD000 !important;
    border-bottom: 1px solid #FFD000 !important;
    font-weight: 900 !important;
}
.leaflet-bar a:hover {
    background-color: #FFD000 !important;
    color: #07080B !important;
}

.map-hud-badge {
    position: absolute;
    top: 12px;
    right: 12px;
    z-index: 500;
    background: #07080B;
    color: #FFD000;
    border: 2px solid #FFD000;
    padding: 5px 12px;
    border-radius: 8px;
    font-size: 0.78rem;
    font-weight: 800;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}

.gridx-input, .form-control, .form-select {
    background-color: #0B0E14 !important;
    border: 1.5px solid rgba(255, 255, 255, 0.16) !important;
    color: var(--text-primary) !important;
    border-radius: 10px !important;
}
.gridx-input:focus, .form-control:focus, .form-select:focus {
    border-color: var(--gridx-yellow) !important;
    box-shadow: 0 0 0 3px rgba(255, 208, 0, 0.22) !important;
}

.stepper-wrapper { display: flex; justify-content: space-between; gap: 8px; overflow-x: auto; padding-bottom: 6px; }
.stepper-item { flex: 1; min-width: 95px; text-align: center; padding: 10px 6px; border-radius: 10px; background: #0C0F17; border: 1px solid var(--border-subtle); opacity: 0.5; }
.stepper-item.completed { opacity: 1; border-color: #FFF; color: #FFF; }
.stepper-item.active { opacity: 1; border: 2px solid var(--gridx-yellow); background: var(--gridx-yellow); color: #000; font-weight: 900; }

.live-dot { width: 10px; height: 10px; background: var(--gridx-yellow); border-radius: 50%; display: inline-block; }

.ai-fab { position: fixed; bottom: 24px; right: 24px; z-index: 1050; background: var(--gridx-yellow); color: #07080B; font-weight: 900; border-radius: 50px; padding: 12px 22px; border: 2px solid #000; box-shadow: 0 10px 28px rgba(255, 208, 0, 0.45); }
.ai-drawer { position: fixed; bottom: 88px; right: 24px; width: 395px; max-width: calc(100vw - 32px); height: 520px; background: var(--bg-surface); border: 2px solid var(--gridx-yellow); border-radius: var(--radius-card); z-index: 1055; display: none; flex-direction: column; box-shadow: 0 20px 50px rgba(0, 0, 0, 0.9); }
.ai-drawer.open { display: flex; }
.ai-messages { flex: 1; overflow-y: auto; padding: 14px; }
.msg-bubble { padding: 10px 14px; border-radius: 12px; margin-bottom: 10px; font-size: 0.88rem; }
.msg-user { background: var(--gridx-yellow); color: #07080B; font-weight: 700; margin-left: 40px; }
.msg-assistant { background: var(--bg-surface-elevated); color: var(--text-primary); border: 1px solid var(--border-subtle); margin-right: 20px; }
""",

    "static/js/maps.js": """window.gridxMap = null;
window.customerMarker = null;

window.createGridXPin = function(bgHex, textHex, borderHex, labelText) {
    return L.divIcon({
        className: 'gridx-custom-pin',
        html: `<div style="background:${bgHex};color:${textHex};border:3px solid ${borderHex};padding:4px 9px;border-radius:20px;font-weight:900;font-size:11px;white-space:nowrap;box-shadow:0 4px 12px rgba(0,0,0,0.45);display:inline-flex;align-items:center;gap:4px;">
                <span style="width:8px;height:8px;border-radius:50%;background:${textHex};display:inline-block;"></span>${labelText}
               </div>`,
        iconSize: [110, 30],
        iconAnchor: [55, 15]
    });
};

window.initCustomerDashboardMap = function(defaultLat, defaultLng, providersData) {
    const mapEl = document.getElementById('dashboard-map');
    if (!mapEl) return;

    if (typeof L === 'undefined') {
        mapEl.innerHTML = '<div class="p-4 text-dark fw-bold">Interactive Coordinate Grid Active (16.5062, 80.6480)</div>';
        return;
    }

    if (window.gridxMap) {
        window.gridxMap.remove();
    }

    window.gridxMap = L.map('dashboard-map', { zoomControl: true }).setView([defaultLat, defaultLng], 13);

    // Reliable OpenStreetMap Standard Tiles (styled in White, Black & Yellow via CSS)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap | GRIDX White-Black-Yellow Radar'
    }).addTo(window.gridxMap);

    // Force Leaflet container resize calculation so tiles never appear grey/blank
    setTimeout(() => { window.gridxMap.invalidateSize(); }, 200);

    // Yellow & Black Customer Pin
    window.customerMarker = L.marker([defaultLat, defaultLng], {
        draggable: true,
        icon: window.createGridXPin('#FFD000', '#07080B', '#07080B', 'YOUR LOCATION')
    }).addTo(window.gridxMap).bindPopup('<b>YOUR SERVICE PIN</b><br><span style="color:#FFD000;">Drag pin or click anywhere on map</span>').openPopup();

    // Service Zone Circle in Black + Yellow
    window.zoneCircle = L.circle([defaultLat, defaultLng], {
        radius: 2500,
        color: '#07080B',
        weight: 2,
        dashArray: '6, 6',
        fillColor: '#FFD000',
        fillOpacity: 0.18
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

    // Black & Yellow Provider Markers
    (providersData || []).forEach(p => {
        L.marker([p.lat, p.lng], {
            icon: window.createGridXPin('#07080B', '#FFD000', '#FFD000', 'PRO ★ ' + (p.rating || '4.9'))
        }).addTo(window.gridxMap).bindPopup(`<b style="color:#FFD000;">${p.name}</b><br>Verified GRIDX Partner`);
    });
};

window.updateBookingCoordinates = async function(lat, lng) {
    const latEl = document.getElementById('customer_lat');
    const lngEl = document.getElementById('customer_lng');
    if (latEl) latEl.value = Number(lat).toFixed(6);
    if (lngEl) lngEl.value = Number(lng).toFixed(6);
    const hud = document.getElementById('map-coord-hud');
    if (hud) hud.textContent = `PIN: ${Number(lat).toFixed(4)}, ${Number(lng).toFixed(4)}`;
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
    showToast(`Switched Grid Zone: ${label}`);
};

window.detectBrowserGeolocation = function() {
    if (!navigator.geolocation) return showToast('Browser Geolocation not supported.', 'danger');
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
        showToast('Live GPS coordinates locked!');
    }, () => showToast('GPS permission denied. Click on the white/yellow map to set pin.', 'warning'));
};
""",

    "templates/pages/dashboard.html": """{% extends 'base.html' %}
{% block content %}
{% if active_booking %}
<div class="gridx-card-yellow p-3 mb-4 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-2">
    <div class="d-flex align-items-center gap-3">
        <div class="p-2 bg-dark text-warning rounded-3"><i class="bi bi-broadcast fs-4"></i></div>
        <div>
            <div class="small text-uppercase fw-black">LIVE ACTIVE DISPATCH #{{ active_booking.id }}</div>
            <div class="fw-bold">{{ active_booking.category.name }} — Status: <span class="badge bg-dark text-warning">{{ active_booking.get_status_display }}</span>
                {% if active_booking.provider %}• Assigned to <u>{{ active_booking.provider.business_name }}</u>{% endif %}
            </div>
        </div>
    </div>
    <div class="d-flex gap-2">
        <a href="{% url 'tracking' active_booking.id %}" class="btn btn-dark btn-sm fw-bold px-3"><i class="bi bi-geo-alt-fill me-1"></i> Open Live Radar</a>
        <a href="{% url 'booking_detail' active_booking.id %}" class="btn btn-outline-dark btn-sm fw-bold">Invoice / Details</a>
    </div>
</div>
{% endif %}

<div class="row g-4" id="booking-section">
    <div class="col-lg-7">
        <div class="d-flex flex-wrap justify-content-between align-items-center mb-2 gap-2">
            <h5 class="fw-bold mb-0"><span class="text-warning">01.</span> Select Service Category</h5>
            <div class="d-flex gap-1">
                <button type="button" class="btn btn-sm btn-gridx-outline" onclick="setQuickCityPreset(16.5062, 80.6480, 'Benz Circle, Vijayawada')">Vijayawada</button>
                <button type="button" class="btn btn-sm btn-gridx-outline" onclick="setQuickCityPreset(16.3067, 80.4365, 'Arundelpet, Guntur')">Guntur</button>
                <button type="button" class="btn btn-sm btn-gridx" onclick="detectBrowserGeolocation()"><i class="bi bi-crosshair"></i> Live GPS</button>
            </div>
        </div>

        {% include 'components/service_cards.html' %}

        <div class="gridx-card p-3 mt-3">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="fw-bold mb-0"><i class="bi bi-geo-alt-fill text-warning me-1"></i> White-Black-Yellow Service Radar (Click or Drag Pin)</h6>
                <span class="badge bg-warning text-dark fw-black">{{ providers|length }} PROS ONLINE</span>
            </div>
            <div class="map-wrapper">
                <div id="map-coord-hud" class="map-hud-badge">PIN: 16.5062, 80.6480</div>
                <div id="dashboard-map" class="map-container"></div>
            </div>
        </div>

        <div class="gridx-card p-3 mt-3">
            <h6 class="fw-bold text-warning mb-2"><i class="bi bi-shield-check me-1"></i> Nearby Verified Professionals on Grid</h6>
            <div class="row g-2">
                {% for p in providers %}
                <div class="col-md-4">
                    <div class="p-2 rounded border border-secondary" style="background:#0B0E14;">
                        <div class="fw-bold small text-white text-truncate">{{ p.business_name }}</div>
                        <div class="d-flex justify-content-between small text-secondary mt-1">
                            <span class="text-warning fw-bold">★ {{ p.rating_avg }}</span>
                            <span>~{{ p.dist_km }} km ({{ p.eta_mins }}m)</span>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <div class="col-lg-5">
        <div class="gridx-card p-4 border-top border-3 border-warning">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="fw-bold mb-0"><span class="text-warning">02.</span> Dispatch Details</h5>
                <span id="selected-cat-badge" class="badge badge-domain-outdoor">{{ categories.0.name }}</span>
            </div>

            <form onsubmit="submitServiceBooking(event)">
                <input type="hidden" id="selected_category_id" value="{{ categories.0.id }}">

                <div class="mb-3">
                    <label class="form-label small fw-bold text-secondary">Select Vehicle or Home Unit</label>
                    <select id="vehicle_id" class="form-select gridx-input">
                        {% for v in vehicles %}
                            <option value="{{ v.id }}">{{ v.make_model }} — {{ v.registration_number }} ({{ v.get_vehicle_type_display }})</option>
                        {% endfor %}
                    </select>
                </div>

                <div class="row g-2 mb-3">
                    <div class="col-6">
                        <label class="form-label small text-secondary">GPS Latitude</label>
                        <input type="text" id="customer_lat" class="form-control form-control-sm" value="16.5062" readonly>
                    </div>
                    <div class="col-6">
                        <label class="form-label small text-secondary">GPS Longitude</label>
                        <input type="text" id="customer_lng" class="form-control form-control-sm" value="80.6480" readonly>
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-secondary">Exact Location / Landmark</label>
                    <input type="text" id="customer_address" class="form-control gridx-input" value="Benz Circle, NH-16, Vijayawada" required>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-secondary">Describe Symptoms / Problem</label>
                    <textarea id="issue_description" class="form-control gridx-input" rows="2" placeholder="e.g. Bike stopped suddenly, dead battery, or pipe leak..." required></textarea>
                </div>

                <div class="mb-3">
                    <label class="form-label small text-secondary">Optional Issue Photo</label>
                    <input type="file" id="issue_photo" class="form-control form-control-sm" accept="image/*">
                </div>

                <div class="form-check form-switch mb-3 p-2 rounded ps-5" style="background:rgba(255,208,0,0.08); border:1px solid var(--border-grid);">
                    <input class="form-check-input" type="checkbox" id="is_emergency" checked onchange="refreshPriceEstimate()">
                    <label class="form-check-label small fw-bold text-warning" for="is_emergency">
                        HIGH URGENCY / EMERGENCY DISPATCH MODE
                    </label>
                </div>

                <div class="p-3 rounded mb-3" style="background:#080A0F; border:1px solid var(--border-grid);">
                    <div class="small fw-bold text-uppercase text-warning mb-2"><i class="bi bi-calculator"></i> Transparent Price Estimate</div>
                    <div id="estimate-breakdown">Calculating...</div>
                </div>

                <button type="submit" id="submit-booking-btn" class="btn btn-gridx w-100 py-2 fs-6">
                    <i class="bi bi-broadcast-pin me-1"></i> BROADCAST REQUEST NOW
                </button>
            </form>
        </div>

        <div class="gridx-card p-3 mt-3">
            <h6 class="fw-bold mb-2"><i class="bi bi-car-front text-warning me-1"></i> Manage Your Garage / Premises</h6>
            <form method="post" action="{% url 'add_vehicle' %}" class="row g-2 mb-2">
                {% csrf_token %}
                <div class="col-4">
                    <select name="vehicle_type" class="form-select form-select-sm">
                        <option value="CAR">Car</option>
                        <option value="BIKE">Bike</option>
                        <option value="SUV">SUV</option>
                        <option value="EV">EV</option>
                        <option value="HOME">Home</option>
                    </select>
                </div>
                <div class="col-4"><input type="text" name="make_model" class="form-control form-control-sm" placeholder="Make/Model" required></div>
                <div class="col-4"><input type="text" name="registration_number" class="form-control form-control-sm" placeholder="AP 16 ..." required></div>
                <div class="col-12"><button class="btn btn-sm btn-gridx-outline w-100">+ Add Vehicle / Home Unit</button></div>
            </form>
        </div>
    </div>
</div>

<div class="gridx-card p-4 mt-4">
    <h5 class="fw-bold mb-3"><i class="bi bi-clock-history text-warning me-2"></i>Your Dispatch & Service History</h5>
    <div class="table-responsive">
        <table class="table table-dark table-hover align-middle mb-0">
            <thead>
                <tr class="text-secondary small">
                    <th>ID</th><th>Category</th><th>Vehicle / Unit</th><th>Assigned Pro</th><th>Status</th><th>Est. Total</th><th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for b in bookings %}
                <tr>
                    <td class="fw-bold">#{{ b.id }}</td>
                    <td>{{ b.category.name }}</td>
                    <td class="small text-secondary">{{ b.vehicle.make_model|default:"Standard" }}</td>
                    <td>{{ b.provider.business_name|default:"Broadcasting..." }}</td>
                    <td><span class="badge bg-warning text-dark">{{ b.get_status_display }}</span></td>
                    <td class="text-warning fw-bold">₹{{ b.estimated_total }}</td>
                    <td>
                        <a href="{% url 'tracking' b.id %}" class="btn btn-sm btn-gridx py-1">Live Radar</a>
                        <a href="{% url 'booking_detail' b.id %}" class="btn btn-sm btn-outline-light py-1">Invoice</a>
                    </td>
                </tr>
                {% empty %}
                <tr><td colspan="7" class="text-center text-secondary py-3">No service requests yet. Select a category above to dispatch!</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
window.addEventListener('load', function() {
    const providers = [
        {% for p in providers %}
            { lat: {{ p.current_lat }}, lng: {{ p.current_lng }}, name: "{{ p.business_name|escapejs }}", rating: "{{ p.rating_avg }}" },
        {% endfor %}
    ];
    window.initCustomerDashboardMap(16.5062, 80.6480, providers);

    const params = new URLSearchParams(window.location.search);
    const slug = params.get('cat');
    if (slug) {
        const col = document.querySelector(`.service-cat-col[data-slug="${slug}"] .service-cat-card`);
        if (col) col.click();
    } else {
        refreshPriceEstimate();
    }
});
</script>
{% endblock %}
""",

    "templates/pages/tracking.html": """{% extends 'base.html' %}
{% block content %}
<div class="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
    <div>
        <span class="badge bg-warning text-dark fw-black me-2">LIVE TELEMETRY #{{ booking.id }}</span>
        <h4 class="fw-black d-inline mb-0">{{ booking.category.name }}</h4>
    </div>
    <div class="d-flex flex-wrap gap-2">
        {% if booking.provider and booking.status in 'accepted,en_route' %}
            <button class="btn btn-sm btn-gridx" onclick="performBookingAction({{ booking.id }}, 'simulate_step')">
                <i class="bi bi-cursor-fill me-1"></i> Simulate Provider Moving Closer
            </button>
        {% endif %}
        <button class="btn btn-sm btn-gridx-outline" onclick="recenterRadar()"><i class="bi bi-arrows-fullscreen"></i> Recenter</button>
        <a href="{% url 'booking_detail' booking.id %}" class="btn btn-sm btn-outline-light">Invoice & Review</a>
    </div>
</div>

<div class="stepper-wrapper mb-4">
    {% for key, label, icon in steps %}
        <div class="stepper-item {% if forloop.counter0 < current_idx %}completed{% elif forloop.counter0 == current_idx %}active{% endif %}">
            <i class="bi {{ icon }} d-block fs-5 mb-1"></i>
            <div style="font-size:0.72rem;">{{ label }}</div>
        </div>
    {% endfor %}
</div>

<div class="row g-4">
    <div class="col-lg-8">
        <div class="gridx-card p-3">
            <div class="map-wrapper">
                <div class="map-hud-badge">WHITE • BLACK • YELLOW LIVE RADAR</div>
                <div id="tracking-map" class="map-container" style="height:430px !important;"></div>
            </div>
            <div class="d-flex flex-wrap justify-content-between align-items-center mt-2 small text-secondary">
                <span id="tracking-eta-banner"><span class="live-dot me-2"></span>Syncing GRIDX GPS Telemetry...</span>
                <span id="tracking-timestamp"></span>
            </div>
        </div>
    </div>

    <div class="col-lg-4">
        <div class="gridx-card p-4 mb-3 border-top border-3 border-warning">
            <div class="small text-warning fw-bold text-uppercase">Current Dispatch State</div>
            <h3 id="live-status-label" class="fw-black mb-2">{{ booking.get_status_display }}</h3>
            <p class="small text-secondary mb-3"><i class="bi bi-geo-alt text-warning"></i> {{ booking.customer_address }}</p>

            {% if is_assigned_provider %}
                <div class="d-grid gap-2 mb-3">
                    {% if booking.status == 'accepted' %}
                        <button class="btn btn-gridx" onclick="performBookingAction({{ booking.id }}, 'en_route')">Mark En Route</button>
                    {% elif booking.status == 'en_route' %}
                        <button class="btn btn-gridx" onclick="performBookingAction({{ booking.id }}, 'arrived')">Mark Arrived at Customer</button>
                    {% elif booking.status == 'arrived' %}
                        <button class="btn btn-gridx" onclick="performBookingAction({{ booking.id }}, 'in_progress')">Start Repair Work</button>
                    {% elif booking.status == 'in_progress' %}
                        <button class="btn btn-success fw-bold" onclick="performBookingAction({{ booking.id }}, 'completed')">Complete Job & Generate Invoice</button>
                    {% endif %}
                </div>
            {% endif %}

            {% if booking.status in 'requested,searching,no_provider' and is_owner %}
                <div class="alert alert-dark border-warning small py-2">
                    Tip: Open an Incognito window and log in as <code>ravi_mech</code> / <code>gridxpassword123</code> to accept this broadcast!
                </div>
                <div class="d-grid gap-2">
                    <button class="btn btn-sm btn-gridx" onclick="performBookingAction({{ booking.id }}, 'expand_radius')">
                        <i class="bi bi-arrows-angle-expand"></i> Emergency Radius Expansion (35 km)
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="performBookingAction({{ booking.id }}, 'cancel')">
                        Cancel Service Request
                    </button>
                </div>
            {% endif %}
        </div>

        <div class="gridx-card p-4">
            <h6 class="fw-bold text-warning mb-3"><i class="bi bi-activity me-1"></i> Audit Timeline</h6>
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
let tMap = null, cMarker = null, pMarker = null, routeOutline = null, routeCenterLine = null;
const custLat = {{ booking.customer_lat }};
const custLng = {{ booking.customer_lng }};

window.addEventListener('load', function() {
    tMap = L.map('tracking-map').setView([custLat, custLng], 14);

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap | GRIDX Radar'
    }).addTo(tMap);

    setTimeout(() => { tMap.invalidateSize(); }, 200);

    cMarker = L.marker([custLat, custLng], {
        icon: window.createGridXPin('#FFD000', '#07080B', '#07080B', 'CUSTOMER PIN')
    }).addTo(tMap).bindPopup('<b>Customer Breakdown Location</b>').openPopup();

    pollTracking();
    setInterval(pollTracking, 4000);
});

async function drawBlackYellowRoute(lat1, lng1, lat2, lng2) {
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

    if (routeOutline) tMap.removeLayer(routeOutline);
    if (routeCenterLine) tMap.removeLayer(routeCenterLine);

    // Outer Black Casing + Inner Electric Yellow Line for high contrast on White Map
    routeOutline = L.polyline(coords, { color: '#07080B', weight: 9, opacity: 0.95 }).addTo(tMap);
    routeCenterLine = L.polyline(coords, { color: '#FFD000', weight: 5, opacity: 1.0 }).addTo(tMap);
}

async function pollTracking() {
    try {
        const res = await fetch('/api/bookings/{{ booking.id }}/tracking/');
        if (!res.ok) return;
        const d = await res.json();
        document.getElementById('live-status-label').textContent = d.status_display;
        document.getElementById('tracking-timestamp').textContent = d.last_updated ? 'Telemetry synced: ' + new Date(d.last_updated).toLocaleTimeString() : 'Waiting for assignment';

        if (d.provider_location) {
            const pLat = d.provider_location.lat;
            const pLng = d.provider_location.lng;
            if (!pMarker) {
                pMarker = L.marker([pLat, pLng], {
                    icon: window.createGridXPin('#07080B', '#FFD000', '#FFD000', 'MECHANIC EN ROUTE')
                }).addTo(tMap).bindPopup(`<b style="color:#FFD000;">${d.provider_location.name}</b><br>Tel: ${d.provider_location.phone}`);
            } else {
                pMarker.setLatLng([pLat, pLng]);
            }
            await drawBlackYellowRoute(pLat, pLng, custLat, custLng);
            document.getElementById('tracking-eta-banner').innerHTML = `<span class="live-dot me-2"></span><strong class="text-warning">${d.provider_location.name}</strong> (★ ${d.provider_location.rating}) • <strong>${d.distance_km} km</strong> away • Est. ETA: <strong>~${d.eta_mins} mins</strong>`;
        } else {
            document.getElementById('tracking-eta-banner').innerHTML = `<span class="live-dot me-2"></span>Broadcasting to verified providers in Vijayawada-Guntur Grid...`;
        }
    } catch (e) {}
}

function recenterRadar() {
    if (tMap) {
        tMap.setView([custLat, custLng], 14);
        tMap.invalidateSize();
    }
}
</script>
{% endblock %}
"""
}

for rel, content in FILES.items():
    p = PROJECT_ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.strip() + "\n", encoding="utf-8")

# Initialize clean Git repository & commit everything for 2:30 PM submission
try:
    subprocess.run(["git", "init"], cwd=PROJECT_ROOT, check=False)
    subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT, check=False)
    subprocess.run(["git", "commit", "-m", "feat: complete GRIDX v2.0 AI Roadside & Indoor Dispatch Platform with White-Black-Yellow Map"], cwd=PROJECT_ROOT, check=False)
    print("[OK] Git repository initialized and committed inside:", PROJECT_ROOT)
except Exception as e:
    print("[INFO] Git init skipped:", e)

# Update the clean zip file
zip_path = PROJECT_ROOT.parent / "gridx_project_refined.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for fp in PROJECT_ROOT.rglob("*"):
        if fp.is_file() and "venv" not in fp.parts and ".git" not in fp.parts and "__pycache__" not in fp.parts and fp.name != "db.sqlite3":
            zf.write(fp, fp.relative_to(PROJECT_ROOT.parent))

print(f"[OK] White-Yellow-Black Map Fixed & ZIP Updated: {zip_path.resolve()}")
