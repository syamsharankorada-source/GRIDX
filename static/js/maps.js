window.gridxMap = null;
window.customerMarker = null;
window.mechanicLayerGroup = null;
window.hotelLayerGroup = null;
window.emergencyLayerGroup = null;

window.createCustomerPulsePin = function(labelText = 'YOUR LOCATION') {
    return L.divIcon({
        className: 'custom-pulse-pin',
        html: `<div class="gps-pulse-wrap">
                <div class="gps-pulse-ring"></div>
                <div class="gps-pin-core"><i class="bi bi-person-fill"></i> ${labelText}</div>
               </div>`,
        iconSize: [140, 44],
        iconAnchor: [70, 22]
    });
};

window.createMechanicVehiclePin = function(nameText = 'MECHANIC', rating = '4.9') {
    return L.divIcon({
        className: 'mechanic-live-marker',
        html: `<div class="mechanic-badge">
                <span style="background:#FFD000;color:#000;width:20px;height:20px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;">
                    <i class="bi bi-wrench-adjustable"></i>
                </span>
                <span>${nameText} ★${rating}</span>
               </div>`,
        iconSize: [155, 32],
        iconAnchor: [75, 16]
    });
};

window.createHotelPin = function(nameText = 'HOTEL', price = '₹999') {
    return L.divIcon({
        className: 'hotel-pin',
        html: `<div style="background:#00E676;color:#07080B;border:2.5px solid #07080B;padding:3px 9px;border-radius:18px;font-weight:900;font-size:10.5px;white-space:nowrap;box-shadow:0 4px 12px rgba(0,0,0,0.5);">
                🏨 ${nameText} (${price})
               </div>`,
        iconSize: [145, 28],
        iconAnchor: [72, 14]
    });
};

window.createEmergencyPin = function(label = 'HOSPITAL 108') {
    return L.divIcon({
        className: 'sos-pin',
        html: `<div style="background:#FF3B30;color:#FFF;border:2.5px solid #FFF;padding:3px 9px;border-radius:18px;font-weight:900;font-size:10.5px;white-space:nowrap;box-shadow:0 4px 14px rgba(255,59,48,0.8);">
                🚑 ${label}
               </div>`,
        iconSize: [145, 28],
        iconAnchor: [72, 14]
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
        "⚡ Local Roads": osmProxyLayer
    }, null, { position: 'topright' }).addTo(mapInstance);
};

window.animateMarkerGlide = function(marker, startLatLng, endLatLng, durationMs = 1500) {
    if (!marker) return;
    const startTime = performance.now();
    const sLat = startLatLng.lat, sLng = startLatLng.lng;
    const eLat = endLatLng.lat, eLng = endLatLng.lng;
    function frame(now) {
        const progress = Math.min(1, (now - startTime) / durationMs);
        const ease = progress < 0.5 ? 4 * progress * progress * progress : 1 - Math.pow(-2 * progress + 2, 3) / 2;
        marker.setLatLng([sLat + (eLat - sLat) * ease, sLng + (eLng - sLng) * ease]);
        if (progress < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
};

window.loadGlobalRadarAroundLocation = async function(lat, lng, showHotels = true, showSOS = false) {
    if (!window.gridxMap) return;
    try {
        const res = await fetch(`/api/global-radar/?lat=${lat}&lng=${lng}`);
        if (!res.ok) return;
        const data = await res.json();

        if (window.mechanicLayerGroup) window.mechanicLayerGroup.clearLayers();
        else window.mechanicLayerGroup = L.layerGroup().addTo(window.gridxMap);

        if (window.hotelLayerGroup) window.hotelLayerGroup.clearLayers();
        else window.hotelLayerGroup = L.layerGroup().addTo(window.gridxMap);

        if (window.emergencyLayerGroup) window.emergencyLayerGroup.clearLayers();
        else window.emergencyLayerGroup = L.layerGroup().addTo(window.gridxMap);

        // Render 12+ Trusted Mechanic Shops around the chosen global spot
        const mechListEl = document.getElementById('global-mechanics-list');
        let mechHtml = '';
        (data.mechanics || []).forEach(m => {
            const shortName = m.name.split(' ').slice(0, 2).join(' ');
            L.marker([m.lat, m.lng], {
                icon: window.createMechanicVehiclePin(shortName, m.rating)
            }).addTo(window.mechanicLayerGroup)
              .bindPopup(`<b style="color:#FFD000;">${m.name}</b><br>${m.specialty}<br>Phone: <b>${m.phone}</b><br>Distance: ${m.distance_km} km (~${m.eta_mins} mins)`);

            mechHtml += `
                <div class="col-md-6 col-xl-4">
                    <div class="p-2 rounded border border-secondary h-100 d-flex flex-column justify-content-between" style="background:#0B0E14;">
                        <div>
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="fw-bold small text-white text-truncate">${m.name}</span>
                                <span class="badge bg-warning text-dark" style="font-size:0.65rem;">★ ${m.rating}</span>
                            </div>
                            <div class="text-secondary" style="font-size:0.72rem;">${m.specialty}</div>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mt-1 pt-1 border-top border-secondary" style="font-size:0.72rem;">
                            <span class="text-warning fw-bold">${m.distance_km} km (~${m.eta_mins}m)</span>
                            <a href="tel:${m.phone}" class="text-light text-decoration-none"><i class="bi bi-telephone-fill text-success"></i> Call Shop</a>
                        </div>
                    </div>
                </div>`;
        });
        if (mechListEl) mechListEl.innerHTML = mechHtml;
        const countBadge = document.getElementById('mechanics-count-badge');
        if (countBadge) countBadge.textContent = `${data.mechanics.length} Trusted Mechanic Shops Nearby`;

        // Render Safe-Stay Hotels & Rooms
        const hotelListEl = document.getElementById('safe-stay-hotels-list');
        let hotelHtml = '';
        (data.hotels || []).forEach(h => {
            if (showHotels) {
                L.marker([h.lat, h.lng], {
                    icon: window.createHotelPin(h.name.split(' ').slice(0, 2).join(' '), h.price.split(' ')[0])
                }).addTo(window.hotelLayerGroup)
                  .bindPopup(`<b style="color:#00E676;">🏨 ${h.name}</b><br>${h.perks}<br>Tariff: <b>${h.price}</b> (${h.distance_km} km)`);
            }
            hotelHtml += `
                <div class="col-md-6">
                    <div class="p-2 rounded border border-success" style="background:#091310;">
                        <div class="d-flex justify-content-between">
                            <strong class="small text-white">🏨 ${h.name}</strong>
                            <span class="badge bg-success">${h.price}</span>
                        </div>
                        <div class="text-secondary" style="font-size:0.73rem;">${h.perks} • <b>${h.distance_km} km away</b></div>
                    </div>
                </div>`;
        });
        if (hotelListEl) hotelListEl.innerHTML = hotelHtml;

        // Render Hospitals & NHAI Toll Plazas
        (data.emergencies || []).forEach(em => {
            if (showSOS) {
                L.marker([em.lat, em.lng], {
                    icon: window.createEmergencyPin(em.type === 'TOLL_PLAZA' ? '1033 TOLL CRANE' : '108 HOSPITAL')
                }).addTo(window.emergencyLayerGroup)
                  .bindPopup(`<b style="color:#FF3B30;">🚑 ${em.name}</b><br>Emergency Helpline: <b>${em.phone}</b> (${em.distance_km} km)`);
            }
        });
    } catch (e) {
        console.error(e);
    }
};

window.initCustomerDashboardMap = function(defaultLat, defaultLng) {
    const mapEl = document.getElementById('dashboard-map');
    if (!mapEl || typeof L === 'undefined') return;
    if (window.gridxMap) window.gridxMap.remove();

    window.gridxMap = L.map('dashboard-map', { zoomControl: true }).setView([defaultLat, defaultLng], 14);
    window.attachMapLayers(window.gridxMap);
    setTimeout(() => { window.gridxMap.invalidateSize(); }, 200);

    window.customerMarker = L.marker([defaultLat, defaultLng], {
        draggable: true,
        icon: window.createCustomerPulsePin('YOUR LOCATION')
    }).addTo(window.gridxMap).bindPopup('<b>Your Location</b><br>Drag pin anywhere in the world!');

    window.customerMarker.on('dragend', function(e) {
        const p = e.target.getLatLng();
        window.updateBookingCoordinates(p.lat, p.lng);
        window.loadGlobalRadarAroundLocation(p.lat, p.lng, true, true);
    });

    window.gridxMap.on('click', function(e) {
        window.animateMarkerGlide(window.customerMarker, window.customerMarker.getLatLng(), e.latlng, 450);
        window.updateBookingCoordinates(e.latlng.lat, e.latlng.lng);
        window.loadGlobalRadarAroundLocation(e.latlng.lat, e.latlng.lng, true, true);
    });

    window.loadGlobalRadarAroundLocation(defaultLat, defaultLng, true, false);
};

window.searchWorldLocation = async function(e) {
    if (e) e.preventDefault();
    const q = (document.getElementById('world-search-input')?.value || '').trim();
    if (!q) return;
    showToast(`Searching global map for "${q}"...`);
    try {
        const res = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&q=${encodeURIComponent(q)}&limit=1`);
        if (res.ok) {
            const arr = await res.json();
            if (arr.length > 0) {
                const lat = parseFloat(arr[0].lat);
                const lng = parseFloat(arr[0].lon);
                const label = arr[0].display_name.split(',').slice(0, 3).join(', ');
                window.setQuickCityPreset(lat, lng, label);
                return;
            }
        }
        showToast('Could not find that place name. Try a city or highway name.', 'warning');
    } catch (err) {
        showToast('Search error.', 'danger');
    }
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
        window.gridxMap.flyTo([lat, lng], 14, { animate: true, duration: 1.2 });
        window.customerMarker.setLatLng([lat, lng]);
    }
    window.loadGlobalRadarAroundLocation(lat, lng, true, true);
    showToast(`Switched Map to ${label} — Loaded 12+ Local Mechanic Shops & Hotels!`);
};

window.detectBrowserGeolocation = function() {
    if (!navigator.geolocation) return showToast('GPS not available.', 'danger');
    navigator.geolocation.getCurrentPosition(pos => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        window.setQuickCityPreset(lat, lng, 'My Live GPS Location');
    }, () => showToast('Tap anywhere on the map to set your location.', 'warning'), { enableHighAccuracy: true });
};

window.triggerHighwaySOS = async function(etype = 'ACCIDENT') {
    const lat = document.getElementById('customer_lat')?.value || 16.5062;
    const lng = document.getElementById('customer_lng')?.value || 80.6480;
    const addr = document.getElementById('customer_address')?.value || 'Highway Location';

    const res = await fetch('/api/emergency-sos/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ emergency_type: etype, lat, lng, address: addr })
    });
    if (!res.ok) return;
    const data = await res.json();
    window.loadGlobalRadarAroundLocation(parseFloat(lat), parseFloat(lng), true, true);

    const banner = document.getElementById('sos-live-banner');
    if (banner) {
        banner.style.display = 'block';
        banner.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <strong class="fs-5"><i class="bi bi-broadcast"></i> 108 AMBULANCE, 101 FIRE & 1033 NHAI TOLL PLAZA ALERTED!</strong>
                <a href="tel:108" class="btn btn-sm btn-light fw-black text-danger">📞 Dial 108 Now</a>
            </div>
            <div class="small mt-1">${data.sms_payload}</div>
            <div class="small mt-1 text-warning fw-bold">Nearest Hospital on Map: ${data.nearest_hospital} | Nearest Toll Crane: ${data.nearest_toll_plaza}</div>
        `;
    }
    showToast('🚑 108 Ambulance & Government SMS Dispatched! Nearby Hospitals pinned in RED on map.', 'danger');
};
