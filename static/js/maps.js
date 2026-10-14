window.gridxMap = null;
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
