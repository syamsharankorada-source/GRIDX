async function selectServiceCategory(catId, catName = '') {
    document.querySelectorAll('.service-cat-card').forEach(el => el.classList.remove('active'));
    const card = document.querySelector(`.service-cat-card[data-id="${catId}"]`);
    if (card) card.classList.add('active');
    const input = document.getElementById('selected_category_id');
    if (input) input.value = catId;
    const badge = document.getElementById('selected-cat-badge');
    if (badge && catName) badge.textContent = catName;
    await refreshPriceEstimate();
}

async function refreshPriceEstimate() {
    const catId = document.getElementById('selected_category_id')?.value;
    if (!catId) return;
    const isEmergency = document.getElementById('is_emergency')?.checked ?? true;
    const res = await fetch(`/api/pricing/estimate/?category_id=${catId}&distance_km=3.4&is_emergency=${isEmergency}`);
    if (!res.ok) return;
    const d = await res.json();
    const box = document.getElementById('estimate-breakdown');
    if (box) {
        box.innerHTML = `
            <div class="d-flex justify-content-between small mb-1"><span class="text-secondary">Category:</span><span class="fw-bold text-white">${d.category_name}</span></div>
            <div class="d-flex justify-content-between small mb-1"><span class="text-secondary">Base Service Charge:</span><span>₹${d.base_charge}</span></div>
            <div class="d-flex justify-content-between small mb-1"><span class="text-secondary">Distance Fee (${d.distance_km} km):</span><span>₹${d.distance_charge}</span></div>
            <div class="d-flex justify-content-between small mb-1"><span class="text-secondary">Priority Emergency Surcharge:</span><span>₹${d.emergency_surcharge}</span></div>
            <div class="d-flex justify-content-between small mb-1"><span class="text-secondary">Platform & GST (18%):</span><span>₹${(parseFloat(d.platform_fee)+parseFloat(d.tax)).toFixed(2)}</span></div>
            <hr class="my-2 border-secondary">
            <div class="d-flex justify-content-between align-items-center">
                <span class="small text-secondary">Est. Band: <strong class="text-white">₹${d.min_range}–₹${d.max_range}</strong></span>
                <span class="fs-5 fw-black text-warning">₹${d.estimated_total}</span>
            </div>
        `;
    }
}

async function submitServiceBooking(e) {
    e.preventDefault();
    const btn = document.getElementById('submit-booking-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>BROADCASTING TO GRID...';

    const formData = new FormData();
    formData.append('category_id', document.getElementById('selected_category_id').value);
    formData.append('vehicle_id', document.getElementById('vehicle_id').value);
    formData.append('issue_description', document.getElementById('issue_description').value);
    formData.append('customer_address', document.getElementById('customer_address').value);
    formData.append('customer_lat', document.getElementById('customer_lat').value);
    formData.append('customer_lng', document.getElementById('customer_lng').value);
    formData.append('is_emergency', document.getElementById('is_emergency').checked);
    const photoInput = document.getElementById('issue_photo');
    if (photoInput && photoInput.files[0]) {
        formData.append('issue_photo', photoInput.files[0]);
    }

    try {
        const res = await fetch('/api/bookings/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCSRFToken() },
            body: formData
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || 'Please check your booking details.', 'danger');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-broadcast-pin me-1"></i> BROADCAST REQUEST NOW';
            return;
        }
        window.location.href = `/bookings/${data.booking.id}/tracking/`;
    } catch (err) {
        showToast('Network error submitting request.', 'danger');
        btn.disabled = false;
    }
}

async function performBookingAction(bookingId, action, extra = {}) {
    const res = await fetch(`/api/bookings/${bookingId}/action/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ action, ...extra })
    });
    const data = await res.json();
    if (!res.ok) return showToast(data.error || 'Action could not be completed.', 'danger');
    if (action === 'simulate_step') {
        showToast(`Provider moved closer (${data.distance_km} km remaining)`);
        if (typeof pollTracking === 'function') pollTracking();
        return;
    }
    window.location.reload();
}
