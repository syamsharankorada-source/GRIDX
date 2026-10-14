import math
from decimal import Decimal
from django.db import transaction
from django.conf import settings
from users.models import ProviderProfile
from .models import Booking, BookingStatusHistory, Notification, Invoice

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return round(R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))), 2)

def score_provider(provider: ProviderProfile, distance_km: float) -> float:
    proximity_score = max(0.0, 100.0 - (distance_km * 4.0))
    rating_score = float(provider.rating_avg) * 20.0
    exp_score = min(100.0, provider.completed_jobs_count * 2.0)
    return round((0.65 * proximity_score) + (0.25 * rating_score) + (0.10 * exp_score), 2)

def find_ranked_eligible_providers(booking: Booking, expand_radius: bool = False) -> list:
    vehicle_type = booking.vehicle.vehicle_type if booking.vehicle else 'CAR'
    search_limit = settings.MAX_EXPANDED_RADIUS_KM if expand_radius else booking.search_radius_km
    candidates = ProviderProfile.objects.filter(
        is_available=True, is_verified=True, skills=booking.category
    ).select_related('user')
    ranked = []
    for p in candidates:
        if not p.supports_vehicle(vehicle_type):
            continue
        dist = haversine_km(booking.customer_lat, booking.customer_lng, p.current_lat, p.current_lng)
        effective_radius = max(p.service_radius_km, search_limit) if expand_radius else min(p.service_radius_km, search_limit)
        if dist <= effective_radius:
            ranked.append({
                "provider": p,
                "distance_km": dist,
                "score": score_provider(p, dist),
                "eta_mins": max(4, int(round(dist * 2.6))),
            })
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked

def broadcast_booking_to_providers(booking: Booking, expand_radius: bool = False) -> list:
    if expand_radius:
        booking.search_radius_km = settings.MAX_EXPANDED_RADIUS_KM
        booking.save(update_fields=['search_radius_km'])
    matches = find_ranked_eligible_providers(booking, expand_radius=expand_radius)
    if matches:
        if booking.status in ('requested', 'no_provider'):
            booking.transition_to('searching', note=f"Broadcasted to {len(matches)} nearby providers.")
        for m in matches[:5]:
            Notification.objects.create(
                recipient=m['provider'].user,
                title=f"NEW REQUEST #{booking.id}",
                message=f"{booking.category.name} ({m['distance_km']} km) — Est. ₹{booking.estimated_total}"
            )
    else:
        if booking.status in ('requested', 'searching'):
            booking.transition_to('no_provider', note="No eligible providers within radius.")
    return matches

def accept_booking_atomic(booking_id: int, provider_profile: ProviderProfile) -> Booking:
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(id=booking_id)
        if booking.status not in ('requested', 'searching') or booking.provider_id is not None:
            raise ValueError("Already accepted or unavailable.")
        if not provider_profile.is_available or not provider_profile.is_verified:
            raise ValueError("Provider must be verified and online.")
        dist = haversine_km(booking.customer_lat, booking.customer_lng, provider_profile.current_lat, provider_profile.current_lng)
        booking.provider = provider_profile
        booking.distance_km = Decimal(str(dist))
        booking.status = 'accepted'
        booking.save(update_fields=['provider', 'distance_km', 'status', 'updated_at'])
        BookingStatusHistory.objects.create(
            booking=booking, from_status='searching', to_status='accepted',
            changed_by=provider_profile.user, note=f"Accepted by {provider_profile.business_name}"
        )
        Notification.objects.create(
            recipient=booking.customer,
            title="Provider Assigned!",
            message=f"{provider_profile.business_name} accepted Booking #{booking.id} ({dist} km away)."
        )
        return booking

def complete_booking_and_issue_invoice(booking: Booking, actor):
    with transaction.atomic():
        booking.transition_to('completed', actor=actor, note="Service completed.")
        commission = (booking.estimated_total * Decimal('0.10')).quantize(Decimal('0.01'))
        payout = booking.estimated_total - commission
        invoice, _ = Invoice.objects.get_or_create(
            booking=booking,
            defaults={
                'final_amount': booking.estimated_total,
                'provider_payout': payout,
                'platform_commission': commission,
                'payment_method': 'CASH',
                'payment_status': 'PENDING',
            }
        )
        if booking.provider:
            booking.provider.completed_jobs_count += 1
            booking.provider.total_earnings += payout
            booking.provider.save(update_fields=['completed_jobs_count', 'total_earnings'])
        return invoice
