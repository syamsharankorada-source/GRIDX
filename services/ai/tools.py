from services.models import Booking, ServiceCategory
from services.pricing import calculate_itemized_estimate
from services.dispatch import haversine_km

def build_authorized_user_context(user) -> dict:
    categories = ServiceCategory.objects.filter(is_active=True)
    pricing_summary = []
    for cat in categories:
        est = calculate_itemized_estimate(cat, distance_km=3.5, is_emergency=True)
        pricing_summary.append({
            "slug": cat.slug, "name": cat.name, "domain": cat.domain,
            "base_charge": f"₹{est['base_charge']}", "typical_range": f"₹{est['min_range']}–₹{est['max_range']}"
        })
    active_booking_data = None
    if user and user.is_authenticated:
        ab = Booking.objects.filter(customer=user).exclude(status__in=['completed', 'cancelled']).select_related('category', 'provider').first()
        if ab:
            eta_info = "Searching nearby grid"
            if ab.provider:
                dist = haversine_km(ab.customer_lat, ab.customer_lng, ab.provider.current_lat, ab.provider.current_lng)
                eta_info = f"{dist} km away (~{max(4, int(round(dist * 2.6)))} mins)"
            active_booking_data = {
                "booking_id": ab.id, "service": ab.category.name, "status": ab.get_status_display(),
                "provider": ab.provider.business_name if ab.provider else "Searching...",
                "distance_and_eta": eta_info, "estimated_total": f"₹{ab.estimated_total}"
            }
    return {"service_area": "Guntur & Vijayawada, AP", "configured_pricing": pricing_summary, "active_booking": active_booking_data}

def recommend_structured_actions(user_message: str, context: dict) -> list:
    msg = user_message.lower()
    actions = []
    if context.get("active_booking"):
        b_id = context["active_booking"]["booking_id"]
        actions.append({"label": f"Track Booking #{b_id}", "action": "OPEN_TRACKING", "url": f"/bookings/{b_id}/tracking/"})
    if any(k in msg for k in ["battery", "dead", "won't start", "click"]):
        actions.append({"label": "Book Battery & EV Jump-Start", "action": "SELECT_CATEGORY", "category_slug": "battery-ev"})
    if any(k in msg for k in ["tyre", "tire", "flat", "puncture"]):
        actions.append({"label": "Book Flat Tyre Repair", "action": "SELECT_CATEGORY", "category_slug": "flat-tyre"})
    if any(k in msg for k in ["tow", "stalled", "stopped"]):
        actions.append({"label": "Book Vehicle Towing", "action": "SELECT_CATEGORY", "category_slug": "towing"})
    if not actions:
        actions.append({"label": "Open Dispatch Console", "action": "SCROLL_BOOKING", "url": "/dashboard/#booking-section"})
    return actions
