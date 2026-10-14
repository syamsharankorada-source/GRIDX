window.gridxMap = null;
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
    // Primary: CartoDB Positron/Voyager + Fallback: Esri World Street Map (Never returns 403 OSM volunteer block)
    const primaryLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd',
        attribution: '&copy; OpenStreetMap &copy; CARTO'
    });

    const backupLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: '&copy; Esri &copy; OpenStreetMap'
    });

    let switchedToBackup = false;
    primaryLayer.on('tileerror', function() {
        if (!switchedToBackup) {
            switchedToBackup = true;
            mapInstance.removeLayer(primaryLayer);
            backupLayer.addTo(mapInstance);
        }
    });

    primaryLayer.addTo(mapInstance);
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
