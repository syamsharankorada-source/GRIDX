import requests
from django.conf import settings
from .prompts import SYSTEM_PROMPT
from .tools import build_authorized_user_context, recommend_structured_actions

def query_gridx_ai(user, user_message: str, history: list) -> dict:
    clean_msg = (user_message or "").strip()[:1000]
    if not clean_msg:
        return {"error": "Empty message."}
    context = build_authorized_user_context(user)
    actions = recommend_structured_actions(clean_msg, context)
    context_block = f"SERVER CONTEXT:\nActive Booking: {context['active_booking']}\nPricing: {context['configured_pricing']}"

    if not settings.GROQ_API_KEY:
        reply = (
            "**Preliminary Safety & Diagnostic Guidance:**\n"
            "1. **Safety First:** Turn on hazard lights and stay clear of moving traffic.\n"
            "2. **Preliminary Check:** Note whether dashboard lights appear or if the starter clicks (this is a preliminary check, not a confirmed diagnosis).\n"
        )
        if context['active_booking']:
            ab = context['active_booking']
            reply += f"\n**Active Booking #{ab['booking_id']}:** Status is **{ab['status']}** with **{ab['provider']}** ({ab['distance_and_eta']})."
        else:
            reply += "\nSelect an action below to dispatch a verified GRIDX professional."
        return {"reply": reply, "actions": actions, "model": "gridx-safe-fallback", "live_llm": False}

    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context_block}]
    for h in history[-6:]:
        messages.append({"role": h["role"], "content": h["content"][:600]})
    messages.append({"role": "user", "content": clean_msg})

    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": settings.GROQ_MODEL, "messages": messages, "temperature": 0.3, "max_tokens": 450},
            timeout=settings.GROQ_TIMEOUT,
        )
        res.raise_for_status()
        return {"reply": res.json()["choices"][0]["message"]["content"], "actions": actions, "model": settings.GROQ_MODEL, "live_llm": True}
    except Exception:
        return {"reply": "⚠️ Live AI temporarily unreachable. Keep hazard lights ON and use quick dispatch actions below.", "actions": actions, "model": "fallback", "live_llm": False}
