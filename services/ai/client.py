import requests
from django.conf import settings
from .prompts import SYSTEM_PROMPT
from .tools import build_authorized_user_context, recommend_structured_actions

def build_simple_smart_reply(clean_msg: str, context: dict) -> str:
    msg = clean_msg.lower()
    ab = context.get("active_booking")

    if any(k in msg for k in ["status", "where", "mechanic", "booking", "eta", "track"]):
        if ab:
            return (
                f"**Your Booking (#{ab['booking_id']}) Details:**\n"
                f"• **Service:** {ab['service']}\n"
                f"• **Current Status:** {ab['status']}\n"
                f"• **Assigned Mechanic:** {ab['provider']} ({ab['distance_and_eta']})\n"
                f"• **Estimated Cost:** {ab['estimated_total']}\n\n"
                f"Click the button below to see the mechanic on the map."
            )
        return "You do not have an active booking right now. Select a service on the home screen and click **Book Mechanic Now**."

    if any(k in msg for k in ["bike", "stopped", "scooter", "two wheeler", "start"]):
        return (
            "**Do Not Worry — Follow These Simple Steps:**\n"
            "1. **Stay Safe:** Push your bike safely to the left side of the road away from moving vehicles.\n"
            "2. **Simple Check:** Check if there is petrol in the tank and if the engine kill-switch (red button on handle) is ON.\n"
            "3. **Book a Mechanic:** If it still does not start, do not force the kick/self-start. Book a **Bike & Car Mechanic** (starts around **₹250**).\n\n"
            "*(Note: This is basic advice. Our mechanic will come and check your bike properly.)*"
        )

    if any(k in msg for k in ["battery", "dead", "click", "jump", "light"]):
        return (
            "**Car / Bike Battery Help:**\n"
            "1. **Stay Safe:** Turn on your hazard/parking lights and keep the vehicle on the side of the road.\n"
            "2. **Simple Check:** When you turn the key, do the dashboard lights come on, or do you hear a 'click-click' sound?\n"
            "3. **Solution:** If the battery is weak, our mechanic can come with a jump-start cable and start your vehicle in 10 minutes (starts around **₹220**).\n\n"
            "*(Note: Preliminary check only. Click below to call Battery Help.)*"
        )

    if any(k in msg for k in ["tyre", "tire", "flat", "puncture", "air", "stepney"]):
        return (
            "**Flat Tyre / Puncture Help:**\n"
            "1. **Stay Safe:** Do not drive on a flat tyre — it can spoil the wheel rim. Park safely on a flat road.\n"
            "2. **Solution:** Our tyre repair person will come to your spot to fix the puncture or change your spare tyre.\n"
            "3. **Estimated Cost:** Starts at **₹180** plus small distance travel charge.\n\n"
            "Click below to book **Flat Tyre Repair**."
        )

    if any(k in msg for k in ["tow", "towing", "accident", "breakdown", "pull"]):
        return (
            "**Vehicle Towing Service:**\n"
            "1. **Stay Safe:** Stand away from the road and turn on hazard lights. If anyone is hurt, call **112** immediately.\n"
            "2. **Solution:** Our towing vehicle will safely lift your car or bike and take it to the nearest workshop.\n"
            "3. **Estimated Cost:** Starts at **₹600**."
        )

    if any(k in msg for k in ["electric", "power", "current", "mcb", "wire", "fan", "plumb", "water", "leak", "pipe", "ac", "home"]):
        return (
            "**Home Repair Help (Electrician / Plumber / AC):**\n"
            "1. **Stay Safe:** If there is a wire spark, turn OFF the main switch. If a water pipe broke, close the main water tap.\n"
            "2. **Solution:** Select **Home Services** on the dashboard to call a verified local Electrician or Plumber near you (starts around **₹200**)."
        )

    if any(k in msg for k in ["cost", "price", "charge", "rate", "money", "how much"]):
        lines = ["**Simple Price List (Before Booking):**"]
        for item in context.get("configured_pricing", [])[:6]:
            lines.append(f"• **{item['name']}:** Base {item['base_charge']} (Total usually {item['typical_range']})")
        lines.append("\nYou can see the exact bill before you book. Pay by Cash or UPI after the work is done!")
        return "\n".join(lines)

    return (
        "**Hello! I am your GRIDX Help Assistant.**\n"
        "Tell me what problem you are facing in simple words:\n"
        "• *'My bike stopped on the road'*\n"
        "• *'Car battery is not starting'*\n"
        "• *'Tyre puncture help'*\n"
        "• *'Need electrician or plumber at home'*\n"
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

    context_block = f"SERVER CONTEXT:\nActive Booking: {context['active_booking']}\nPrices: {context['configured_pricing']}"
    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context_block}]
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
