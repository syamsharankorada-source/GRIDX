function getCSRFToken() {
    const row = document.cookie.split('; ').find(r => r.startsWith('csrftoken='));
    return row ? decodeURIComponent(row.split('=')[1]) : '';
}

function showToast(message, type = 'warning') {
    const c = document.getElementById('toast-container');
    if (!c) return;
    const el = document.createElement('div');
    el.className = `alert alert-${type} shadow-lg py-2 px-3 mb-2 fw-bold d-flex align-items-center justify-content-between`;
    el.style.borderLeft = '5px solid #FFD000';
    el.style.background = '#121621';
    el.style.color = '#FFF';
    el.innerHTML = `<span>${message}</span><button type="button" class="btn-close btn-close-white ms-2" onclick="this.parentElement.remove()"></button>`;
    c.appendChild(el);
    setTimeout(() => el.remove(), 4500);
}

function filterCategoryDomain(domain, btnEl) {
    document.querySelectorAll('.domain-filter-btn').forEach(b => b.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');
    document.querySelectorAll('.service-cat-col').forEach(col => {
        if (domain === 'ALL' || col.dataset.domain === domain) {
            col.style.display = '';
        } else {
            col.style.display = 'none';
        }
    });
}
