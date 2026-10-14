import os, subprocess, zipfile
from pathlib import Path

CWD = Path.cwd()
PROJECT_ROOT = CWD if (CWD / "manage.py").exists() else (CWD / "gridx_project")

FILES = {
    "gridx/settings.py": """import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-gridx-local-key')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,testserver').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'users',
    'services',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Essential so map tile servers receive Referer header and never return 403 Blocked
SECURE_REFERRER_POLICY = 'origin-when-cross-origin'

ROOT_URLCONF = 'gridx.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gridx.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/minute',
        'user': '240/minute',
        'ai_assistant': '40/minute',
    },
}

GROQ_API_KEY = os.getenv('GROQ_API_KEY', '').strip()
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile').strip()
GROQ_TIMEOUT = int(os.getenv('GROQ_TIMEOUT', '15'))

DEFAULT_CITY = os.getenv('DEFAULT_CITY', 'Vijayawada & Guntur')
DEFAULT_LAT = float(os.getenv('DEFAULT_LAT', '16.5062'))
DEFAULT_LNG = float(os.getenv('DEFAULT_LNG', '80.6480'))
DEFAULT_SEARCH_RADIUS_KM = float(os.getenv('DEFAULT_SEARCH_RADIUS_KM', '15.0'))
MAX_EXPANDED_RADIUS_KM = float(os.getenv('MAX_EXPANDED_RADIUS_KM', '35.0'))
""",

    "services/ai/prompts.py": """SYSTEM_PROMPT = \"\"\"You are GRIDX Help Assistant. Speak in very simple, friendly English that anyone in a small town or village can easily understand.
Rules:
1. Keep sentences short and clear. Avoid complicated technical words.
2. First, tell the user how to stay safe (for example: park on the side of the road, turn on parking lights, stay away from fast vehicles).
3. Clearly say this is basic guidance, and a mechanic will check the vehicle properly.
4. Ask 1 simple question about the problem and tell them the estimated price from the SERVER CONTEXT.
\"\"\"
""",

    "services/ai/client.py": """import requests
from django.conf import settings
from .prompts import SYSTEM_PROMPT
from .tools import build_authorized_user_context, recommend_structured_actions

def build_simple_smart_reply(clean_msg: str, context: dict) -> str:
    msg = clean_msg.lower()
    ab = context.get("active_booking")

    if any(k in msg for k in ["status", "where", "mechanic", "booking", "eta", "track"]):
        if ab:
            return (
                f"**Your Booking (#{ab['booking_id']}) Details:**\\n"
                f"• **Service:** {ab['service']}\\n"
                f"• **Current Status:** {ab['status']}\\n"
                f"• **Assigned Mechanic:** {ab['provider']} ({ab['distance_and_eta']})\\n"
                f"• **Estimated Cost:** {ab['estimated_total']}\\n\\n"
                f"Click the button below to see the mechanic on the map."
            )
        return "You do not have an active booking right now. Select a service on the home screen and click **Book Mechanic Now**."

    if any(k in msg for k in ["bike", "stopped", "scooter", "two wheeler", "start"]):
        return (
            "**Do Not Worry — Follow These Simple Steps:**\\n"
            "1. **Stay Safe:** Push your bike safely to the left side of the road away from moving vehicles.\\n"
            "2. **Simple Check:** Check if there is petrol in the tank and if the engine kill-switch (red button on handle) is ON.\\n"
            "3. **Book a Mechanic:** If it still does not start, do not force the kick/self-start. Book a **Bike & Car Mechanic** (starts around **₹250**).\\n\\n"
            "*(Note: This is basic advice. Our mechanic will come and check your bike properly.)*"
        )

    if any(k in msg for k in ["battery", "dead", "click", "jump", "light"]):
        return (
            "**Car / Bike Battery Help:**\\n"
            "1. **Stay Safe:** Turn on your hazard/parking lights and keep the vehicle on the side of the road.\\n"
            "2. **Simple Check:** When you turn the key, do the dashboard lights come on, or do you hear a 'click-click' sound?\\n"
            "3. **Solution:** If the battery is weak, our mechanic can come with a jump-start cable and start your vehicle in 10 minutes (starts around **₹220**).\\n\\n"
            "*(Note: Preliminary check only. Click below to call Battery Help.)*"
        )

    if any(k in msg for k in ["tyre", "tire", "flat", "puncture", "air", "stepney"]):
        return (
            "**Flat Tyre / Puncture Help:**\\n"
            "1. **Stay Safe:** Do not drive on a flat tyre — it can spoil the wheel rim. Park safely on a flat road.\\n"
            "2. **Solution:** Our tyre repair person will come to your spot to fix the puncture or change your spare tyre.\\n"
            "3. **Estimated Cost:** Starts at **₹180** plus small distance travel charge.\\n\\n"
            "Click below to book **Flat Tyre Repair**."
        )

    if any(k in msg for k in ["tow", "towing", "accident", "breakdown", "pull"]):
        return (
            "**Vehicle Towing Service:**\\n"
            "1. **Stay Safe:** Stand away from the road and turn on hazard lights. If anyone is hurt, call **112** immediately.\\n"
            "2. **Solution:** Our towing vehicle will safely lift your car or bike and take it to the nearest workshop.\\n"
            "3. **Estimated Cost:** Starts at **₹600**."
        )

    if any(k in msg for k in ["electric", "power", "current", "mcb", "wire", "fan", "plumb", "water", "leak", "pipe", "ac", "home"]):
        return (
            "**Home Repair Help (Electrician / Plumber / AC):**\\n"
            "1. **Stay Safe:** If there is a wire spark, turn OFF the main switch. If a water pipe broke, close the main water tap.\\n"
            "2. **Solution:** Select **Home Services** on the dashboard to call a verified local Electrician or Plumber near you (starts around **₹200**)."
        )

    if any(k in msg for k in ["cost", "price", "charge", "rate", "money", "how much"]):
        lines = ["**Simple Price List (Before Booking):**"]
        for item in context.get("configured_pricing", [])[:6]:
            lines.append(f"• **{item['name']}:** Base {item['base_charge']} (Total usually {item['typical_range']})")
        lines.append("\\nYou can see the exact bill before you book. Pay by Cash or UPI after the work is done!")
        return "\\n".join(lines)

    return (
        "**Hello! I am your GRIDX Help Assistant.**\\n"
        "Tell me what problem you are facing in simple words:\\n"
        "• *'My bike stopped on the road'*\\n"
        "• *'Car battery is not starting'*\\n"
        "• *'Tyre puncture help'*\\n"
        "• *'Need electrician or plumber at home'*\\n"
        "• *'Where is my mechanic?'*"
    )

def query_gridx_ai(user, user_message: str, history: list) -> dict:
    clean_msg = (user_message or "").strip()[:1000]
    if not clean_msg:
        return {"error": "Please type your question."}

    context = build_authorized_user_context(user)
    actions = recommend_structured_actions(clean_msg, context)

    # If no Groq API key is configured, return clean, helpful, villager-friendly guidance without scary technical warnings
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
        return {
            "reply": build_simple_smart_reply(clean_msg, context),
            "actions": actions,
            "model": "gridx-smart-assistant",
            "live_llm": False
        }

    context_block = f"SERVER CONTEXT:\\nActive Booking: {context['active_booking']}\\nPrices: {context['configured_pricing']}"
    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\\n\\n" + context_block}]
    for h in history[-6:]:
        messages.append({"role": h["role"], "content": h["content"][:600]})
    messages.append({"role": "user", "content": clean_msg})

    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": settings.GROQ_MODEL, "messages": messages, "temperature": 0.3, "max_tokens": 400},
            timeout=settings.GROQ_TIMEOUT,
        )
        res.raise_for_status()
        return {
            "reply": res.json()["choices"][0]["message"]["content"],
            "actions": actions,
            "model": settings.GROQ_MODEL,
            "live_llm": True
        }
    except Exception:
        return {
            "reply": build_simple_smart_reply(clean_msg, context),
            "actions": actions,
            "model": "gridx-smart-assistant",
            "live_llm": False
        }
""",

    "static/js/maps.js": """window.gridxMap = null;
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
""",

    "templates/base.html": """{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="referrer" content="origin-when-cross-origin">
    <title>GRIDX — Easy Roadside & Home Mechanic Help</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="{% static 'css/style.css' %}">
</head>
<body>
    {% include 'components/navbar.html' %}
    <div id="toast-container" class="position-fixed top-0 end-0 p-3" style="z-index:2000;"></div>
    <main class="container py-4">{% block content %}{% endblock %}</main>
    {% if user.is_authenticated %}
    <button class="ai-fab" onclick="toggleAIDrawer()"><i class="bi bi-chat-dots-fill me-1"></i> Ask Help Assistant</button>
    <div id="ai-drawer" class="ai-drawer">
        <div class="p-3 border-bottom border-secondary d-flex justify-content-between align-items-center" style="background:#0D1017;">
            <div>
                <span class="fw-black text-warning">GRIDX HELP ASSISTANT</span>
                <small class="d-block text-secondary" style="font-size:0.72rem;">Simple advice & price check</small>
            </div>
            <button class="btn btn-sm btn-outline-light" onclick="toggleAIDrawer()"><i class="bi bi-x-lg"></i></button>
        </div>
        <div id="ai-messages-list" class="ai-messages">
            <div class="msg-bubble msg-assistant">
                👋 <b>Namaste! How can I help you today?</b><br>Tap a question below or type your problem:
                <div class="mt-2 d-flex flex-wrap gap-1">
                    <button class="btn btn-sm btn-gridx-outline py-1 px-2" style="font-size:0.74rem;" onclick="sendQuickPrompt('My bike stopped on the road')">🚲 Bike stopped</button>
                    <button class="btn btn-sm btn-gridx-outline py-1 px-2" style="font-size:0.74rem;" onclick="sendQuickPrompt('My car battery is dead')">🔋 Battery dead</button>
                    <button class="btn btn-sm btn-gridx-outline py-1 px-2" style="font-size:0.74rem;" onclick="sendQuickPrompt('Tyre puncture repair cost')">🛞 Tyre puncture price</button>
                    <button class="btn btn-sm btn-gridx-outline py-1 px-2" style="font-size:0.74rem;" onclick="sendQuickPrompt('Where is my mechanic?')">📍 Where is my mechanic?</button>
                </div>
            </div>
        </div>
        <form onsubmit="sendAIMessage(event)" class="p-2 border-top border-secondary d-flex gap-2">
            <input id="ai-chat-input" type="text" class="form-control form-control-sm" placeholder="Type your vehicle or home problem...">
            <button type="submit" class="btn btn-sm btn-gridx"><i class="bi bi-send-fill"></i></button>
        </form>
    </div>
    {% endif %}
    {% include 'components/footer.html' %}
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="{% static 'js/main.js' %}"></script>
    <script src="{% static 'js/maps.js' %}"></script>
    <script src="{% static 'js/booking.js' %}"></script>
    <script src="{% static 'js/ai-chat.js' %}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
""",

    "templates/components/navbar.html": """<nav class="navbar navbar-expand-lg navbar-dark navbar-gridx sticky-top py-2">
    <div class="container">
        <a class="brand-logo" href="{% url 'home' %}">GRID <span>X</span></a>
        <span class="badge bg-dark border border-warning text-warning ms-2 d-none d-md-inline-flex align-items-center gap-1">
            <span class="live-dot"></span> Vijayawada • Guntur
        </span>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#gridxNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="gridxNav">
            <ul class="navbar-nav ms-auto align-items-lg-center gap-2 mt-2 mt-lg-0">
                {% if user.is_authenticated %}
                    {% if user.provider_profile %}
                        <li class="nav-item">
                            <a class="btn btn-sm btn-gridx" href="{% url 'provider_dashboard' %}">
                                <i class="bi bi-tools me-1"></i> Mechanic Jobs
                            </a>
                        </li>
                    {% else %}
                        <li class="nav-item">
                            <a class="btn btn-sm btn-gridx" href="{% url 'dashboard' %}">
                                <i class="bi bi-house-door-fill me-1"></i> Book a Service
                            </a>
                        </li>
                    {% endif %}
                    <li class="nav-item">
                        <a class="btn btn-sm btn-gridx-outline" href="{% url 'ai_assistant' %}">
                            <i class="bi bi-chat-dots-fill me-1"></i> Help Assistant
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="btn btn-sm btn-outline-light" href="{% url 'logout' %}">
                            Logout ({{ user.username }})
                        </a>
                    </li>
                {% else %}
                    <li class="nav-item"><a class="btn btn-sm btn-outline-light" href="{% url 'login' %}">Login</a></li>
                    <li class="nav-item"><a class="btn btn-sm btn-gridx" href="{% url 'register' %}?role=customer">Need Help (Customer)</a></li>
                    <li class="nav-item"><a class="btn btn-sm btn-gridx-outline" href="{% url 'register' %}?role=provider">Join as Mechanic</a></li>
                {% endif %}
            </ul>
        </div>
    </div>
</nav>
""",

    "templates/components/service_cards.html": """<div class="d-flex flex-wrap gap-2 mb-3">
    <button type="button" class="btn btn-sm btn-gridx-outline domain-filter-btn active" onclick="filterCategoryDomain('ALL', this)">
        All Services ({{ categories|length }})
    </button>
    <button type="button" class="btn btn-sm btn-gridx-outline domain-filter-btn" onclick="filterCategoryDomain('OUTDOOR', this)">
        🚲🚗 Vehicle & Road Help
    </button>
    <button type="button" class="btn btn-sm btn-gridx-outline domain-filter-btn" onclick="filterCategoryDomain('INDOOR', this)">
        🏠 Home Repair (Electrician / Plumber)
    </button>
</div>

<div class="row g-3">
    {% for cat in categories %}
    <div class="col-6 col-md-4 col-xl-3 service-cat-col" data-domain="{{ cat.domain }}" data-slug="{{ cat.slug }}">
        <div class="gridx-card service-cat-card p-3 h-100 d-flex flex-column justify-content-between {% if forloop.first %}active{% endif %}"
             data-id="{{ cat.id }}"
             onclick="selectServiceCategory('{{ cat.id }}', '{{ cat.name|escapejs }}')">
            <div>
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div class="p-2 rounded-3" style="background:rgba(255,208,0,0.12);">
                        <i class="bi {{ cat.icon }} fs-4 text-warning"></i>
                    </div>
                    <span class="badge {% if cat.domain == 'OUTDOOR' %}badge-domain-outdoor{% else %}badge-domain-indoor{% endif %}" style="font-size:0.65rem;">
                        {% if cat.domain == 'OUTDOOR' %}VEHICLE{% else %}HOME{% endif %}
                    </span>
                </div>
                <h6 class="fw-bold mb-1 text-white">{{ cat.name }}</h6>
                <p class="text-secondary small mb-2" style="font-size:0.76rem; line-height:1.35;">{{ cat.description|truncatechars:60 }}</p>
            </div>
            <div class="d-flex justify-content-between align-items-center pt-2 border-top border-secondary">
                <span class="small text-secondary">Starts at</span>
                <span class="fw-black text-warning">₹{{ cat.pricing_rule.base_charge|default:"250.00" }}</span>
            </div>
        </div>
    </div>
    {% endfor %}
</div>
""",

    "templates/pages/dashboard.html": """{% extends 'base.html' %}
{% block content %}
{% if active_booking %}
<div class="gridx-card-yellow p-3 mb-4 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-2">
    <div class="d-flex align-items-center gap-3">
        <div class="p-2 bg-dark text-warning rounded-3"><i class="bi bi-truck-front-fill fs-4"></i></div>
        <div>
            <div class="small text-uppercase fw-black">YOUR CURRENT BOOKING (#{{ active_booking.id }})</div>
            <div class="fw-bold">{{ active_booking.category.name }} — Status: <span class="badge bg-dark text-warning">{{ active_booking.get_status_display }}</span>
                {% if active_booking.provider %}• Mechanic: <u>{{ active_booking.provider.business_name }}</u>{% endif %}
            </div>
        </div>
    </div>
    <div class="d-flex gap-2">
        <a href="{% url 'tracking' active_booking.id %}" class="btn btn-dark btn-sm fw-bold px-3"><i class="bi bi-geo-alt-fill me-1"></i> See Mechanic on Map</a>
        <a href="{% url 'booking_detail' active_booking.id %}" class="btn btn-outline-dark btn-sm fw-bold">View Bill</a>
    </div>
</div>
{% endif %}

<div class="row g-4" id="booking-section">
    <div class="col-lg-7">
        <div class="d-flex flex-wrap justify-content-between align-items-center mb-2 gap-2">
            <h5 class="fw-bold mb-0"><span class="text-warning">Step 1:</span> What Help Do You Need?</h5>
            <div class="d-flex gap-1">
                <button type="button" class="btn btn-sm btn-gridx-outline" onclick="setQuickCityPreset(16.5062, 80.6480, 'Benz Circle, Vijayawada')">Vijayawada</button>
                <button type="button" class="btn btn-sm btn-gridx-outline" onclick="setQuickCityPreset(16.3067, 80.4365, 'Arundelpet, Guntur')">Guntur</button>
                <button type="button" class="btn btn-sm btn-gridx" onclick="detectBrowserGeolocation()"><i class="bi bi-crosshair"></i> Use My Current GPS</button>
            </div>
        </div>

        {% include 'components/service_cards.html' %}

        <div class="gridx-card p-3 mt-3">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="fw-bold mb-0"><i class="bi bi-geo-alt-fill text-warning me-1"></i> Your Location Map (Touch or Drag Yellow Pin)</h6>
                <span class="badge bg-warning text-dark fw-black">{{ providers|length }} Mechanics Available</span>
            </div>
            <div class="map-wrapper">
                <div id="dashboard-map" class="map-container"></div>
            </div>
        </div>

        <div class="gridx-card p-3 mt-3">
            <h6 class="fw-bold text-warning mb-2"><i class="bi bi-person-check-fill me-1"></i> Nearby Verified Mechanics Ready to Help</h6>
            <div class="row g-2">
                {% for p in providers %}
                <div class="col-md-4">
                    <div class="p-2 rounded border border-secondary" style="background:#0B0E14;">
                        <div class="fw-bold small text-white text-truncate">{{ p.business_name }}</div>
                        <div class="d-flex justify-content-between small text-secondary mt-1">
                            <span class="text-warning fw-bold">★ {{ p.rating_avg }}</span>
                            <span>{{ p.dist_km }} km away (~{{ p.eta_mins }} mins)</span>
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
                <h5 class="fw-bold mb-0"><span class="text-warning">Step 2:</span> Confirm & Book</h5>
                <span id="selected-cat-badge" class="badge badge-domain-outdoor">{{ categories.0.name }}</span>
            </div>

            <form onsubmit="submitServiceBooking(event)">
                <input type="hidden" id="selected_category_id" value="{{ categories.0.id }}">
                <input type="hidden" id="customer_lat" value="16.5062">
                <input type="hidden" id="customer_lng" value="80.6480">

                <div class="mb-3">
                    <label class="form-label small fw-bold text-secondary">Choose Your Vehicle / Home</label>
                    <select id="vehicle_id" class="form-select gridx-input">
                        {% for v in vehicles %}
                            <option value="{{ v.id }}">{{ v.make_model }} ({{ v.registration_number }})</option>
                        {% endfor %}
                    </select>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-secondary">Your Place / Nearby Landmark</label>
                    <input type="text" id="customer_address" class="form-control gridx-input" value="Benz Circle, NH-16, Vijayawada" required>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-secondary">Tell Us What Happened (In Simple Words)</label>
                    <textarea id="issue_description" class="form-control gridx-input" rows="2" placeholder="Example: Bike stopped suddenly, tyre puncture, or battery not starting..." required></textarea>
                </div>

                <div class="mb-3">
                    <label class="form-label small text-secondary">Upload Photo of Problem (Optional)</label>
                    <input type="file" id="issue_photo" class="form-control form-control-sm" accept="image/*">
                </div>

                <div class="form-check form-switch mb-3 p-2 rounded ps-5" style="background:rgba(255,208,0,0.08); border:1px solid var(--border-grid);">
                    <input class="form-check-input" type="checkbox" id="is_emergency" checked onchange="refreshPriceEstimate()">
                    <label class="form-check-label small fw-bold text-warning" for="is_emergency">
                        Need Urgent Help Right Now
                    </label>
                </div>

                <div class="p-3 rounded mb-3" style="background:#080A0F; border:1px solid var(--border-grid);">
                    <div class="small fw-bold text-uppercase text-warning mb-2"><i class="bi bi-currency-rupee"></i> Estimated Bill (Pay After Work)</div>
                    <div id="estimate-breakdown">Calculating...</div>
                </div>

                <button type="submit" id="submit-booking-btn" class="btn btn-gridx w-100 py-2 fs-6">
                    <i class="bi bi-telephone-outbound-fill me-1"></i> BOOK MECHANIC NOW
                </button>
            </form>
        </div>

        <div class="gridx-card p-3 mt-3">
            <h6 class="fw-bold mb-2"><i class="bi bi-plus-circle text-warning me-1"></i> Add Another Bike, Car or Home</h6>
            <form method="post" action="{% url 'add_vehicle' %}" class="row g-2 mb-2">
                {% csrf_token %}
                <div class="col-4">
                    <select name="vehicle_type" class="form-select form-select-sm">
                        <option value="BIKE">Bike</option>
                        <option value="CAR">Car</option>
                        <option value="SUV">SUV</option>
                        <option value="EV">Electric</option>
                        <option value="HOME">Home</option>
                    </select>
                </div>
                <div class="col-4"><input type="text" name="make_model" class="form-control form-control-sm" placeholder="Vehicle Name" required></div>
                <div class="col-4"><input type="text" name="registration_number" class="form-control form-control-sm" placeholder="Number Plate" required></div>
                <div class="col-12"><button class="btn btn-sm btn-gridx-outline w-100">+ Save Vehicle</button></div>
            </form>
        </div>
    </div>
</div>

<div class="gridx-card p-4 mt-4">
    <h5 class="fw-bold mb-3"><i class="bi bi-clock-history text-warning me-2"></i>Your Past Bookings</h5>
    <div class="table-responsive">
        <table class="table table-dark table-hover align-middle mb-0">
            <thead>
                <tr class="text-secondary small">
                    <th>Booking No</th><th>Service</th><th>Vehicle</th><th>Mechanic</th><th>Status</th><th>Estimated Cost</th><th>Action</th>
                </tr>
            </thead>
            <tbody>
                {% for b in bookings %}
                <tr>
                    <td class="fw-bold">#{{ b.id }}</td>
                    <td>{{ b.category.name }}</td>
                    <td class="small text-secondary">{{ b.vehicle.make_model|default:"Vehicle" }}</td>
                    <td>{{ b.provider.business_name|default:"Finding Mechanic..." }}</td>
                    <td><span class="badge bg-warning text-dark">{{ b.get_status_display }}</span></td>
                    <td class="text-warning fw-bold">₹{{ b.estimated_total }}</td>
                    <td>
                        <a href="{% url 'tracking' b.id %}" class="btn btn-sm btn-gridx py-1">Track on Map</a>
                        <a href="{% url 'booking_detail' b.id %}" class="btn btn-sm btn-outline-light py-1">View Bill</a>
                    </td>
                </tr>
                {% empty %}
                <tr><td colspan="7" class="text-center text-secondary py-3">You have not booked any service yet.</td></tr>
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
        <span class="badge bg-warning text-dark fw-black me-2">BOOKING #{{ booking.id }}</span>
        <h4 class="fw-black d-inline mb-0">{{ booking.category.name }}</h4>
    </div>
    <div class="d-flex flex-wrap gap-2">
        {% if booking.provider and booking.status in 'accepted,en_route' %}
            <button class="btn btn-sm btn-gridx" onclick="performBookingAction({{ booking.id }}, 'simulate_step')">
                <i class="bi bi-truck-front-fill me-1"></i> Move Mechanic Closer (Demo)
            </button>
        {% endif %}
        <button class="btn btn-sm btn-gridx-outline" onclick="recenterRadar()"><i class="bi bi-arrows-fullscreen"></i> Center Map</button>
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
                <div id="tracking-map" class="map-container" style="height:430px !important;"></div>
            </div>
            <div class="d-flex flex-wrap justify-content-between align-items-center mt-2 small text-secondary">
                <span id="tracking-eta-banner"><span class="live-dot me-2"></span>Checking mechanic location...</span>
                <span id="tracking-timestamp"></span>
            </div>
        </div>
    </div>

    <div class="col-lg-4">
        <div class="gridx-card p-4 mb-3 border-top border-3 border-warning">
            <div class="small text-warning fw-bold text-uppercase">Booking Status</div>
            <h3 id="live-status-label" class="fw-black mb-2">{{ booking.get_status_display }}</h3>
            <p class="small text-secondary mb-3"><i class="bi bi-geo-alt text-warning"></i> {{ booking.customer_address }}</p>

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
            <h6 class="fw-bold text-warning mb-3"><i class="bi bi-clock-history me-1"></i> Updates</h6>
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
    window.addReliableMapTiles(tMap);
    setTimeout(() => { tMap.invalidateSize(); }, 200);

    cMarker = L.marker([custLat, custLng], {
        icon: window.createGridXPin('#FFD000', '#07080B', '#07080B', 'YOUR LOCATION')
    }).addTo(tMap).bindPopup('<b>Your Location</b>').openPopup();

    pollTracking();
    setInterval(pollTracking, 4000);
});

async function drawRoadRoute(lat1, lng1, lat2, lng2) {
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

    routeOutline = L.polyline(coords, { color: '#07080B', weight: 9, opacity: 0.95 }).addTo(tMap);
    routeCenterLine = L.polyline(coords, { color: '#FFD000', weight: 5, opacity: 1.0 }).addTo(tMap);
}

async function pollTracking() {
    try {
        const res = await fetch('/api/bookings/{{ booking.id }}/tracking/');
        if (!res.ok) return;
        const d = await res.json();
        document.getElementById('live-status-label').textContent = d.status_display;
        document.getElementById('tracking-timestamp').textContent = d.last_updated ? 'Updated: ' + new Date(d.last_updated).toLocaleTimeString() : '';

        if (d.provider_location) {
            const pLat = d.provider_location.lat;
            const pLng = d.provider_location.lng;
            if (!pMarker) {
                pMarker = L.marker([pLat, pLng], {
                    icon: window.createGridXPin('#07080B', '#FFD000', '#FFD000', 'MECHANIC')
                }).addTo(tMap).bindPopup(`<b style="color:#FFD000;">${d.provider_location.name}</b><br>Phone: ${d.provider_location.phone}`);
            } else {
                pMarker.setLatLng([pLat, pLng]);
            }
            await drawRoadRoute(pLat, pLng, custLat, custLng);
            document.getElementById('tracking-eta-banner').innerHTML = `<span class="live-dot me-2"></span><strong class="text-warning">${d.provider_location.name}</strong> • <strong>${d.distance_km} km</strong> away • Reaching in <strong>~${d.eta_mins} mins</strong>`;
        } else {
            document.getElementById('tracking-eta-banner').innerHTML = `<span class="live-dot me-2"></span>Calling nearby mechanics in your area...`;
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
""",

    "templates/pages/ai_assistant.html": """{% extends 'base.html' %}
{% block content %}
<div class="row g-4">
    <div class="col-lg-4">
        <div class="gridx-card p-4 h-100">
            <span class="badge badge-domain-outdoor mb-2">EASY HELP GUIDE</span>
            <h4 class="fw-black text-warning mb-2"><i class="bi bi-chat-dots-fill me-1"></i> GRIDX HELP ASSISTANT</h4>
            <p class="small text-secondary mb-3">
                Not sure which mechanic to call or how much it costs? Tap any question below to get simple, clear advice.
            </p>
            <h6 class="small fw-bold text-uppercase text-white mb-2">Common Questions (Tap One):</h6>
            <div class="d-grid gap-2">
                <button class="btn btn-sm btn-gridx-outline text-start py-2" onclick="sendQuickPrompt('My bike stopped on the road. What should I do?', 'studio-input', 'studio-messages')">
                    🚲 My bike stopped on the road
                </button>
                <button class="btn btn-sm btn-gridx-outline text-start py-2" onclick="sendQuickPrompt('My car battery is dead and not starting.', 'studio-input', 'studio-messages')">
                    🔋 Car battery is not starting
                </button>
                <button class="btn btn-sm btn-gridx-outline text-start py-2" onclick="sendQuickPrompt('How much does tyre puncture repair cost?', 'studio-input', 'studio-messages')">
                    🛞 How much for tyre puncture repair?
                </button>
                <button class="btn btn-sm btn-gridx-outline text-start py-2" onclick="sendQuickPrompt('Where is my mechanic right now?', 'studio-input', 'studio-messages')">
                    📍 Where is my mechanic right now?
                </button>
                <button class="btn btn-sm btn-gridx-outline text-start py-2" onclick="sendQuickPrompt('Need an electrician or plumber at home.', 'studio-input', 'studio-messages')">
                    🏠 Need Electrician or Plumber at home
                </button>
            </div>
        </div>
    </div>

    <div class="col-lg-8">
        <div class="gridx-card d-flex flex-column" style="height: 540px;">
            <div class="p-3 border-bottom border-secondary d-flex justify-content-between align-items-center">
                <div>
                    <span class="live-dot me-2"></span>
                    <strong class="text-warning">HELP CHAT</strong>
                </div>
                <a href="{% url 'dashboard' %}" class="btn btn-sm btn-gridx">Back to Booking Page</a>
            </div>

            <div id="studio-messages" class="ai-messages flex-grow-1">
                <div class="msg-bubble msg-assistant">
                    👋 <strong class="text-warning">Namaste!</strong> Tell me your vehicle or home problem in simple words, and I will guide you.
                </div>
                {% for m in messages_history %}
                    <div class="msg-bubble {% if m.role == 'user' %}msg-user{% else %}msg-assistant{% endif %}">
                        {{ m.content|linebreaksbr }}
                    </div>
                {% endfor %}
            </div>

            <form onsubmit="sendAIMessage(event, 'studio-input', 'studio-messages')" class="p-3 border-top border-secondary d-flex gap-2">
                <input id="studio-input" type="text" class="form-control gridx-input" placeholder="Type your problem here (e.g., bike stopped, tyre puncture)...">
                <button type="submit" class="btn btn-gridx px-4"><i class="bi bi-send-fill"></i> Ask</button>
            </form>
        </div>
    </div>
</div>
{% endblock %}
"""
}

for rel, content in FILES.items():
    p = PROJECT_ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.strip() + "\n", encoding="utf-8")

# Commit updated files to Git
try:
    subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT, check=False)
    subprocess.run(["git", "commit", "-m", "fix: resolve 403 map tiles, simplify UI language for everyone, and upgrade AI assistant"], cwd=PROJECT_ROOT, check=False)
except Exception:
    pass

# Rebuild clean ZIP
zip_path = PROJECT_ROOT.parent / "gridx_project_refined.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for fp in PROJECT_ROOT.rglob("*"):
        if fp.is_file() and "venv" not in fp.parts and ".git" not in fp.parts and "__pycache__" not in fp.parts and fp.name != "db.sqlite3":
            zf.write(fp, fp.relative_to(PROJECT_ROOT.parent))

print(f"\n[OK] Map 403 Fixed, Simple Language Applied & AI Assistant Ready!")
print(f"[OK] Updated ZIP: {zip_path.resolve()}")
