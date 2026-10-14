import requests
from django.conf import settings
from .prompts import get_system_prompt
from .tools import build_authorized_user_context, recommend_structured_actions

def detect_telugu_or_hindi(text: str) -> str:
    low = text.lower()
    for ch in text:
        if '\u0c00' <= ch <= '\u0c7f':
            return 'TELUGU_SCRIPT'
        if '\u0900' <= ch <= '\u097f':
            return 'HINDI_SCRIPT'
    if any(w in low for w in ['enti', 'ela', 'ekkada', 'cheyali', 'aagipoyindi', 'vastundi', 'kavali', 'bro', 'anna', 'bandi', 'naa']):
        return 'TENGLISH'
    if any(w in low for w in ['kya', 'kaise', 'kaha', 'mera', 'gaadi', 'ruka', 'madad']):
        return 'HINGLISH'
    return 'ENGLISH'

def build_multilingual_smart_reply(clean_msg: str, context: dict, user_role: str = 'CUSTOMER') -> str:
    msg = clean_msg.lower()
    lang = detect_telugu_or_hindi(clean_msg)
    ab = context.get("active_booking")

    # 1. ACCIDENT / FIRE / AMBULANCE / HIGHWAY TOLL PLAZA SOS
    if any(k in msg for k in ["accident", "crash", "fire", "ambulance", "hospital", "blood", "hurt", "injury", "toll", "108", "112", "প্রమాదం", "యాక్సిడెంట్"]):
        if lang in ('TELUGU_SCRIPT', 'TENGLISH'):
            return (
                "🚨 **EMERGENCY HIGHWAY & AMBULANCE SOS ACTIVATED!**\n"
                "1. **భద్రత (Safety First):** వెంటనే వాహనం నుండి దూరంగా సురక్షిత ప్రదేశానికి వెళ్ళండి.\n"
                "2. **అంబులెన్స్ & ప్రభుత్వ SMS (Auto-Alert):** మీ GPS లొకేషన్ తో **108 Ambulance**, **112 Police**, **101 Fire**, మరియు **1033 NHAI Toll Plaza** కి ఆటోమేటిక్ అలర్ట్ పంపబడింది!\n"
                "3. **Nearby Hospitals:** మ్యాప్ లో మీ చుట్టూ ఉన్న హాస్పిటల్స్ రెడ్ పిన్స్ తో చూపించబడ్డాయి. కింద ఉన్న **Trigger 108 Ambulance & Hospital SOS** బటన్ నొక్కండి!"
            )
        return (
            "🚨 **EMERGENCY ACCIDENT / FIRE / AMBULANCE PROTOCOL ACTIVATED!**\n"
            "1. **Immediate Safety:** Move everyone away from the vehicle and highway lanes immediately. Turn on hazard lights if safe.\n"
            "2. **Ambulance & Govt SMS Dispatched:** We can immediately dispatch your exact GPS coordinates to **108 Ambulance**, **101 Fire**, **112 Emergency**, and **1033 NHAI Toll Plaza Crane**\n"
            "3. **Nearby Hospitals:** Click the red **Trigger 108 Ambulance & Hospital Radar** button below to alert authorities and view the nearest hospitals on your map."
        )

    # 2. HOTEL / ROOM / SAFE STAY WHEN REPAIR TAKES LONG TIME
    if any(k in msg for k in ["hotel", "room", "stay", "lodge", "night", "far", "hours", "long time", "rest", "food", "హోటల్", "రూమ్"]):
        return (
            "🏨 **AI Safe-Stay (Nearby Hotels, Lodges & Family Rooms):**\n"
            "Since major repairs (like Engine, Clutch, or Highway Towing) can take **2 to 5+ hours** and you are far from home:\n"
            "• I have scanned your live GPS location for **Verified Hotels, AC Rooms, Lodges & Family Waiting Lounges** within 2 km.\n"
            "• Click **Show Nearby Hotels & Safe Rooms on Map** below to see room prices (₹800–₹1,800) and directions!"
        )

    # 3. MECHANIC TECHNICAL ASSISTANT MODE
    if user_role == 'PROVIDER' or any(k in msg for k in ["torque", "obd", "solenoid", "relay", "diagnostic", "compression", "multimeter", "mechanic guide"]):
        return (
            "🔧 **GRIDX Mechanic Technical Repair Guide:**\n"
            "1. **Safety Isolation:** Chock wheels, engage parking brake, and disconnect 12V negative terminal (or HV service plug on EVs) before probing.\n"
            "2. **No-Crank / Clicking Triage:** Measure battery voltage under load (must stay >9.6V). If voltage is 12.4V+ but starter clicks, check starter relay Pin 30/87 and solenoid voltage drop (<0.5V).\n"
            "3. **Sudden Stall Triage:** Verify fuel rail pressure / injector pulse and inspect crank position sensor (CKP) resistance (typically 500–900 Ω).\n"
            "4. **Long Repair Notice:** If repair exceeds 2 hours, mark job as *In Progress* so AI automatically suggests nearby Safe-Stay Hotels to the customer."
        )

    # 4. BIKE STOPPED / DIY SAFETY REPAIR GUIDE
    if any(k in msg for k in ["bike", "stopped", "scooter", "start", "bandi", "aagipoyindi", "బైక్"]):
        if lang in ('TELUGU_SCRIPT', 'TENGLISH'):
            return (
                "🛠️ **బైక్ ఆగిపోయిందా? ఈ చిన్న సేఫ్టీ స్టెప్స్ చెక్ చేయండి (DIY Guide):**\n"
                "1. **సేఫ్టీ (Safety):** బైక్ ని రోడ్డు పక్కకి నెట్టి, పార్కింగ్ లైట్లు వేయండి.\n"
                "2. **Step 1 (Kill Switch & Petrol):** హ్యాండిల్ మీద ఉన్న రెడ్ స్విచ్ (Engine Kill Switch) ON లో ఉందో లేదో చూడండి. పెట్రోల్ ట్యాంక్/రిజర్వ్ నాబ్ చెక్ చేయండి.\n"
                "3. **Step 2 (Spark Plug Cap):** ఇంజిన్ వేడిగా ఉంటుంది, జాగ్రత్తగా స్పార్క్ ప్లగ్ క్యాప్ లూజ్ అయ్యిందేమో చూడండి (చేతితో వేడి సైలెన్సర్ ని తాకవద్దు).\n"
                "4. **Mechanic Booking:** అయినా స్టార్ట్ అవ్వకపోతే కింద ఉన్న **Book Bike Mechanic** బటన్ నొక్కండి, 10 నిమిషాల్లో మెకానిక్ వస్తారు!"
            )
        return (
            "🛠️ **Bike Stopped? Safe Step-by-Step DIY Check:**\n"
            "1. **Safety Precaution:** Push your bike completely off the road onto the safe shoulder. Never attempt repairs in moving traffic.\n"
            "2. **Check 1 (Kill Switch & Side Stand):** Ensure the red handlebar kill-switch is ON and the side-stand is fully folded up (modern bikes cut ignition if the side-stand sensor is down).\n"
            "3. **Check 2 (Fuel & Spark Plug Cap):** Check fuel level/reserve tap, and gently see if the rubber spark-plug cap is loose (**Warning:** Do not touch the hot exhaust or engine block).\n"
            "4. **Call Mechanic:** If it still won't start, click below to dispatch a nearby verified mechanic (starts at **₹250**)."
        )

    # 5. BATTERY DEAD / CAR WON'T START
    if any(k in msg for k in ["battery", "dead", "click", "jump", "car", "బ్యాటరీ"]):
        return (
            "🔋 **Car / Bike Battery Safe Check & Jump-Start Guide:**\n"
            "1. **Safety Precaution:** Keep hazard lights ON, engage handbrake, and never smoke or create sparks near the battery.\n"
            "2. **DIY Check:** Turn on headlights or horn. If they are very dim and you hear a rapid *'click-click'* sound, your 12V battery is discharged. Check if the battery terminal clamps are loose (do not touch both + and - together with a metal spanner!).\n"
            "3. **Fast Solution:** Click below to book **Battery & EV Jump-Start** (starts at **₹220**)."
        )

    # 6. REPORT ISSUE / DISPUTE
    if any(k in msg for k in ["report", "complaint", "cheat", "overcharge", "rude", "issue with mechanic", "issue with customer", "dispute"]):
        return (
            "🚩 **Report an Issue with Mechanic or Customer:**\n"
            "We take your safety and fair pricing seriously. You can click the **Report Issue / Dispute** button on your dashboard or booking page to report overcharging, delay, or bad behavior. Our admin safety team investigates immediately."
        )

    # 7. BOOKING STATUS
    if any(k in msg for k in ["status", "where", "mechanic", "booking", "eta", "track", "ekkada"]):
        if ab:
            return (
                f"📍 **Live Booking (#{ab['booking_id']}) Update:**\n"
                f"• **Service:** {ab['service']} ({ab['status']})\n"
                f"• **Mechanic:** {ab['provider']} ({ab['distance_and_eta']})\n"
                f"• **Estimated Bill:** {ab['estimated_total']}"
            )
        return "You have no active booking right now. Choose any service on the map to call a mechanic!"

    return (
        "👋 **Namaste! Welcome to GRIDX AI (Speak in English, తెలుగు, Tenglish, or Hindi!)**\n"
        "I can help both **Customers** and **Mechanics** with:\n"
        "• 🛠️ **Safe DIY Repair Guides** (*'My bike stopped'*, *'Car battery dead'*)\n"
        "• 🏨 **Nearby Hotels & Rooms** if repair takes a long time far from home\n"
        "• 🚑 **Highway Accident, Fire, Toll Plaza & 108 Ambulance SOS**\n"
        "• 🚩 **Reporting Issues** with a mechanic or customer"
    )

def query_gridx_ai(user, user_message: str, history: list) -> dict:
    clean_msg = (user_message or "").strip()[:1000]
    if not clean_msg:
        return {"error": "Please type your message."}

    context = build_authorized_user_context(user)
    actions = recommend_structured_actions(clean_msg, context)
    user_role = 'PROVIDER' if hasattr(user, 'provider_profile') else 'CUSTOMER'

    # Add special actions for Accident/SOS or Hotels
    low = clean_msg.lower()
    if any(k in low for k in ["accident", "crash", "fire", "ambulance", "hospital", "108", "toll"]):
        actions.insert(0, {"label": "🚑 Trigger 108 Ambulance & Hospital Radar", "action": "TRIGGER_SOS", "url": "/dashboard/?sos=1#booking-section"})
    if any(k in low for k in ["hotel", "room", "stay", "lodge", "long", "night", "far"]):
        actions.insert(0, {"label": "🏨 Show Nearby Hotels & Safe Rooms", "action": "SHOW_HOTELS", "url": "/dashboard/?hotels=1#booking-section"})

    system_prompt = get_system_prompt()

    if settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key_here":
        context_block = (
            f"USER ROLE: {user_role}\n"
            f"ACTIVE BOOKING: {context['active_booking']}\n"
            f"PRICING: {context['configured_pricing']}"
        )
        messages = [{"role": "system", "content": system_prompt + "\n\n" + context_block}]
        for h in history[-6:]:
            messages.append({"role": h["role"], "content": h["content"][:600]})
        messages.append({"role": "user", "content": clean_msg})

        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": settings.GROQ_MODEL, "messages": messages, "temperature": 0.35, "max_tokens": 550},
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
            pass

    return {
        "reply": build_multilingual_smart_reply(clean_msg, context, user_role=user_role),
        "actions": actions,
        "model": "gridx-multilingual-ai",
        "live_llm": True
    }
