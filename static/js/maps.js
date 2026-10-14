window.gridxMap = null;
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
