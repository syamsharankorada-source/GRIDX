from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.http import HttpResponseForbidden
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.throttling import ScopedRateThrottle

from users.models import ProviderProfile, CustomerProfile, Vehicle
from .models import (
    ServiceCategory, PricingRule, Booking, BookingStatusHistory,
    ProviderLocation, Invoice, Review, Notification, AIConversation, AIMessage
)
from .serializers import ServiceCategorySerializer, BookingSerializer, ProviderPublicSerializer
from .pricing import calculate_itemized_estimate
from .dispatch import (
    find_ranked_eligible_providers, broadcast_booking_to_providers,
    accept_booking_atomic, complete_booking_and_issue_invoice, haversine_km
)
from .ai.client import query_gridx_ai

def ensure_seed_catalog():
    if ServiceCategory.objects.exists():
        return
    catalog = [
        ("emergency-repair", "Emergency Roadside Repair", "OUTDOOR", "bi-wrench-adjustable-circle-fill", "Immediate on-spot mechanical breakdown diagnostics & repair", "300.00", "25.00", "150.00"),
        ("mechanic-service", "Bike & Car Mechanic", "OUTDOOR", "bi-gear-wide-connected", "Engine stalling, clutch, belt, brake & general mechanical service", "250.00", "20.00", "100.00"),
        ("towing", "Vehicle Towing", "OUTDOOR", "bi-truck-flatbed", "Flatbed & wheel-lift towing to nearest workshop or safe zone", "600.00", "40.00", "200.00"),
        ("flat-tyre", "Flat Tyre Assistance", "OUTDOOR", "bi-disc-fill", "Tubeless puncture repair, stepney swap & air pressure restore", "180.00", "15.00", "80.00"),
        ("battery-ev", "Battery & EV Jump-Start", "OUTDOOR", "bi-battery-charging", "12V dead battery jump-start, terminal replacement & EV support", "220.00", "18.00", "100.00"),
        ("fuel-delivery", "Emergency Fuel Assistance", "OUTDOOR", "bi-fuel-pump-fill", "Subject to local regulations & operational availability", "200.00", "20.00", "100.00"),
        ("inspection", "Vehicle Inspection & Maintenance", "OUTDOOR", "bi-clipboard2-check-fill", "Pre-trip multipoint check & scheduled maintenance", "350.00", "15.00", "0.00"),
        ("electrician", "Emergency Electrician", "INDOOR", "bi-lightning-charge-fill", "MCB tripping, wiring fault, inverter & switchboard repair", "200.00", "15.00", "100.00"),
        ("plumber", "Plumber & Pipe Leak", "INDOOR", "bi-droplet-fill", "Burst pipe, tap replacement, drainage block & tank repair", "200.00", "15.00", "100.00"),
        ("ac-appliances", "AC & Appliances Repair", "INDOOR", "bi-snow", "AC cooling issue, refrigerator & home appliance diagnostics", "300.00", "18.00", "120.00"),
        ("carpenter", "Carpenter & Locksmith", "INDOOR", "bi-hammer", "Door lock jam, hinge repair & structural woodwork fixes", "220.00", "15.00", "90.00"),
    ]
    created_cats = []
    for slug, name, domain, icon, desc, base, per_km, surg in catalog:
        c = ServiceCategory.objects.create(slug=slug, name=name, domain=domain, icon=icon, description=desc)
        PricingRule.objects.create(category=c, base_charge=Decimal(base), per_km_charge=Decimal(per_km), emergency_surcharge=Decimal(surg))
        created_cats.append(c)

    demo_providers = [
        ("ravi_mech", "Sri Kanaka Durga Auto & Roadside Grid (Vijayawada)", "9848011223", 16.5125, 80.6410, "BIKE,CAR,SUV,EV,HOME"),
        ("guntur_tow", "Amaravati Rapid Tow & Battery Pro (Guntur)", "9848044556", 16.4980, 80.6350, "BIKE,CAR,SUV,EV,HOME"),
        ("nh16_grid", "NH-16 Smart Living Indoor & Outdoor Squad", "9848077889", 16.5010, 80.6560, "BIKE,CAR,SUV,EV,HOME"),
    ]
    for uname, bname, phone, lat, lng, veh in demo_providers:
        if not User.objects.filter(username=uname).exists():
            u = User.objects.create_user(username=uname, email=f"{uname}@gridx.local", password="gridxpassword123")
            p = ProviderProfile.objects.create(
                user=u, phone=phone, business_name=bname, is_verified=True, is_available=True,
                service_radius_km=30.0, supported_vehicles=veh, current_lat=lat, current_lng=lng,
                rating_avg=Decimal('4.90'), completed_jobs_count=48, total_earnings=Decimal('2450.00')
            )
            p.skills.set(created_cats)

    if not User.objects.filter(username="demo_customer").exists():
        cu = User.objects.create_user(username="demo_customer", email="customer@gridx.local", password="gridxpassword123")
        CustomerProfile.objects.create(user=cu, phone="9848000111")
        Vehicle.objects.create(owner=cu, vehicle_type="CAR", make_model="Hyundai Creta SX", registration_number="AP 16 DX 2026")
        Vehicle.objects.create(owner=cu, vehicle_type="BIKE", make_model="Royal Enfield Classic 350", registration_number="AP 07 BK 9900")
        Vehicle.objects.create(owner=cu, vehicle_type="HOME", make_model="Smart Living Apartment #302", registration_number="Benz Circle Zone")

def home_view(request):
    ensure_seed_catalog()
    categories = ServiceCategory.objects.filter(is_active=True).select_related('pricing_rule')
    providers = ProviderProfile.objects.filter(is_available=True, is_verified=True)[:6]
    return render(request, 'pages/home.html', {'categories': categories, 'providers': providers})

@login_required
def customer_dashboard_view(request):
    ensure_seed_catalog()
    if hasattr(request.user, 'provider_profile'):
        return redirect('provider_dashboard')
    CustomerProfile.objects.get_or_create(user=request.user, defaults={'phone': '9000000000'})
    if not request.user.vehicles.exists():
        Vehicle.objects.create(owner=request.user, vehicle_type='CAR', make_model='Hyundai i20', registration_number='AP 16 DX 2026')
    categories = ServiceCategory.objects.filter(is_active=True).select_related('pricing_rule')
    vehicles = request.user.vehicles.all()
    bookings = Booking.objects.filter(customer=request.user).select_related('category', 'provider', 'invoice')
    active_booking = bookings.exclude(status__in=['completed', 'cancelled']).first()
    providers = list(ProviderProfile.objects.filter(is_available=True, is_verified=True))
    for p in providers:
        p.dist_km = haversine_km(16.5062, 80.6480, p.current_lat, p.current_lng)
        p.eta_mins = max(4, int(round(p.dist_km * 2.5)))
    notifications = request.user.notifications.filter(is_read=False)[:6]
    return render(request, 'pages/dashboard.html', {
        'categories': categories, 'vehicles': vehicles, 'bookings': bookings,
        'active_booking': active_booking, 'providers': providers, 'notifications': notifications
    })

@login_required
def provider_dashboard_view(request):
    ensure_seed_catalog()
    if not hasattr(request.user, 'provider_profile'):
        return redirect('dashboard')
    provider = request.user.provider_profile
    open_bookings = Booking.objects.filter(
        status__in=['requested', 'searching', 'no_provider'],
        category__in=provider.skills.all()
    ).exclude(declined_by=provider).select_related('category', 'customer', 'vehicle')

    incoming_requests = []
    for b in open_bookings:
        dist = haversine_km(b.customer_lat, b.customer_lng, provider.current_lat, provider.current_lng)
        if dist <= max(provider.service_radius_km, b.search_radius_km):
            est_low = int(float(b.estimated_total) * 0.9)
            est_high = int(float(b.estimated_total) * 1.1)
            incoming_requests.append({
                'booking': b,
                'distance_km': dist,
                'eta_mins': max(4, int(round(dist * 2.5))),
                'price_range': f"₹{est_low}–₹{est_high}"
            })
    assigned_bookings = Booking.objects.filter(provider=provider).select_related('category', 'customer', 'vehicle', 'invoice')
    active_job = assigned_bookings.exclude(status__in=['completed', 'cancelled']).first()
    reviews = provider.reviews.all().order_by('-created_at')[:5]
    notifications = request.user.notifications.filter(is_read=False)[:6]
    return render(request, 'pages/provider_dashboard.html', {
        'provider': provider, 'incoming_requests': incoming_requests,
        'assigned_bookings': assigned_bookings, 'active_job': active_job,
        'reviews': reviews, 'notifications': notifications
    })

@login_required
def booking_detail_view(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related('category', 'provider', 'vehicle'), id=booking_id)
    is_owner = (booking.customer_id == request.user.id)
    is_assigned_provider = hasattr(request.user, 'provider_profile') and (booking.provider_id == request.user.provider_profile.id)
    if not (is_owner or is_assigned_provider or request.user.is_staff):
        return HttpResponseForbidden("Unauthorized")
    return render(request, 'pages/booking_detail.html', {'booking': booking, 'is_owner': is_owner, 'is_assigned_provider': is_assigned_provider})

@login_required
def tracking_view(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related('category', 'provider', 'vehicle'), id=booking_id)
    is_owner = (booking.customer_id == request.user.id)
    is_assigned_provider = hasattr(request.user, 'provider_profile') and (booking.provider_id == request.user.provider_profile.id)
    if not (is_owner or is_assigned_provider or request.user.is_staff):
        return HttpResponseForbidden("Unauthorized")
    steps = [
        ('requested', 'Requested', 'bi-send-check'),
        ('searching', 'Broadcasted', 'bi-broadcast-pin'),
        ('accepted', 'Accepted', 'bi-person-check-fill'),
        ('en_route', 'En Route', 'bi-truck-front-fill'),
        ('arrived', 'Arrived', 'bi-geo-alt-fill'),
        ('in_progress', 'In Progress', 'bi-tools'),
        ('completed', 'Completed', 'bi-patch-check-fill'),
    ]
    status_order = [s[0] for s in steps]
    current_idx = status_order.index(booking.status) if booking.status in status_order else 0
    return render(request, 'pages/tracking.html', {
        'booking': booking, 'is_owner': is_owner,
        'is_assigned_provider': is_assigned_provider,
        'steps': steps, 'current_idx': current_idx
    })

@login_required
def ai_assistant_page_view(request):
    ensure_seed_catalog()
    conv, _ = AIConversation.objects.get_or_create(user=request.user)
    categories = ServiceCategory.objects.filter(is_active=True).select_related('pricing_rule')
    return render(request, 'pages/ai_assistant.html', {
        'messages_history': conv.messages.all(),
        'categories': categories
    })

class ServiceCatalogAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        ensure_seed_catalog()
        qs = ServiceCategory.objects.filter(is_active=True).select_related('pricing_rule')
        return Response({"categories": ServiceCategorySerializer(qs, many=True).data})

class PriceEstimateAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        cat_id = request.query_params.get('category_id')
        dist = float(request.query_params.get('distance_km', 3.4))
        is_emg = request.query_params.get('is_emergency', 'true').lower() == 'true'
        category = get_object_or_404(ServiceCategory, id=cat_id)
        return Response(calculate_itemized_estimate(category, distance_km=dist, is_emergency=is_emg))

class BookingListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        qs = Booking.objects.filter(provider=request.user.provider_profile) if hasattr(request.user, 'provider_profile') else Booking.objects.filter(customer=request.user)
        return Response(BookingSerializer(qs, many=True).data)

    def post(self, request):
        category = get_object_or_404(ServiceCategory, id=request.data.get('category_id'))
        vehicle_id = request.data.get('vehicle_id')
        vehicle = Vehicle.objects.filter(id=vehicle_id, owner=request.user).first() if vehicle_id else request.user.vehicles.first()
        try:
            lat = float(request.data.get('customer_lat', 16.5062))
            lng = float(request.data.get('customer_lng', 80.6480))
        except (TypeError, ValueError):
            return Response({"error": "Invalid coordinates."}, status=status.HTTP_400_BAD_REQUEST)
        issue_description = (request.data.get('issue_description') or "").strip()
        if len(issue_description) < 5:
            return Response({"error": "Please describe the problem (minimum 5 characters)."}, status=status.HTTP_400_BAD_REQUEST)
        is_emergency = str(request.data.get('is_emergency', 'true')).lower() in ('true', '1', 'on')
        est = calculate_itemized_estimate(category, distance_km=3.4, is_emergency=is_emergency)
        booking = Booking.objects.create(
            customer=request.user, vehicle=vehicle, category=category, is_emergency=is_emergency,
            issue_description=issue_description, customer_address=request.data.get('customer_address', 'Benz Circle, NH-16, Vijayawada'),
            customer_lat=lat, customer_lng=lng,
            issue_photo=request.FILES.get('issue_photo'),
            estimated_base=Decimal(est['base_charge']), estimated_distance_cost=Decimal(est['distance_charge']),
            estimated_surcharge=Decimal(est['emergency_surcharge']), estimated_platform_fee=Decimal(est['platform_fee']),
            estimated_tax=Decimal(est['tax']), estimated_total=Decimal(est['estimated_total']),
        )
        BookingStatusHistory.objects.create(booking=booking, from_status='', to_status='requested', changed_by=request.user, note="Service request created by customer.")
        matches = broadcast_booking_to_providers(booking)
        return Response({"booking": BookingSerializer(booking).data, "matched_providers_count": len(matches)}, status=status.HTTP_201_CREATED)

class BookingActionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)
        action = request.data.get('action')

        if action == 'accept':
            if not hasattr(request.user, 'provider_profile'):
                return Response({"error": "Only registered service providers can accept jobs."}, status=status.HTTP_403_FORBIDDEN)
            try:
                updated = accept_booking_atomic(booking.id, request.user.provider_profile)
                return Response(BookingSerializer(updated).data)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)

        if action == 'reject':
            if hasattr(request.user, 'provider_profile'):
                booking.declined_by.add(request.user.provider_profile)
            return Response({"status": "declined", "booking_id": booking.id})

        if action == 'simulate_step':
            # Moves assigned provider 35% closer to customer on each click for live tracking demo
            if not booking.provider:
                return Response({"error": "Assign a provider first before simulating movement."}, status=status.HTTP_400_BAD_REQUEST)
            p = booking.provider
            p.current_lat = round(p.current_lat + (booking.customer_lat - p.current_lat) * 0.38, 6)
            p.current_lng = round(p.current_lng + (booking.customer_lng - p.current_lng) * 0.38, 6)
            p.save()
            ProviderLocation.objects.create(provider=p, booking=booking, latitude=p.current_lat, longitude=p.current_lng)
            new_dist = haversine_km(booking.customer_lat, booking.customer_lng, p.current_lat, p.current_lng)
            booking.distance_km = Decimal(str(new_dist))
            if booking.status == 'accepted':
                booking.transition_to('en_route', actor=request.user, note="Provider started navigation toward customer.")
            elif new_dist < 0.25 and booking.status == 'en_route':
                booking.transition_to('arrived', actor=request.user, note="Provider arrived at customer GPS pin.")
            booking.save(update_fields=['distance_km'])
            return Response({"status": "moved", "distance_km": new_dist, "booking_status": booking.status})

        if action == 'expand_radius':
            if booking.customer_id != request.user.id:
                return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
            matches = broadcast_booking_to_providers(booking, expand_radius=True)
            return Response({"booking": BookingSerializer(booking).data, "matched_providers_count": len(matches)})

        if action == 'cancel':
            if booking.customer_id != request.user.id:
                return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
            if booking.status in ('in_progress', 'completed'):
                return Response({"error": "Cannot cancel an in-progress or completed job."}, status=status.HTTP_400_BAD_REQUEST)
            booking.transition_to('cancelled', actor=request.user, note="Cancelled by customer.")
            return Response(BookingSerializer(booking).data)

        if action in ('en_route', 'arrived', 'in_progress', 'completed'):
            if not hasattr(request.user, 'provider_profile') or booking.provider_id != request.user.provider_profile.id:
                return Response({"error": "Only the assigned provider can update job status."}, status=status.HTTP_403_FORBIDDEN)
            if action == 'completed':
                complete_booking_and_issue_invoice(booking, actor=request.user)
            else:
                booking.transition_to(action, actor=request.user, note=f"Provider marked job as {action.replace('_', ' ').upper()}.")
            return Response(BookingSerializer(booking).data)

        if action == 'confirm_payment':
            if hasattr(booking, 'invoice'):
                booking.invoice.payment_status = 'PAID'
                booking.invoice.payment_method = request.data.get('payment_method', 'CASH')
                booking.invoice.paid_at = timezone.now()
                booking.invoice.save()
                Notification.objects.create(recipient=booking.customer, title=f"Payment Verified (#INV-{booking.invoice.id})", message=f"₹{booking.invoice.final_amount} recorded as PAID via {booking.invoice.payment_method}.")
                return Response({"payment_status": "PAID"})
            return Response({"error": "Invoice not found."}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'submit_review':
            if booking.customer_id != request.user.id or booking.status != 'completed' or not booking.provider:
                return Response({"error": "Review allowed only after completion."}, status=status.HTTP_400_BAD_REQUEST)
            rating_val = max(1, min(5, int(request.data.get('rating', 5))))
            Review.objects.update_or_create(
                booking=booking,
                defaults={'reviewer': request.user, 'provider': booking.provider, 'rating': rating_val, 'comment': request.data.get('comment', '')}
            )
            all_ratings = list(booking.provider.reviews.values_list('rating', flat=True))
            booking.provider.rating_avg = Decimal(str(round(sum(all_ratings) / len(all_ratings), 2)))
            booking.provider.save(update_fields=['rating_avg'])
            return Response({"status": "review_saved"})

        if action == 'clear_notifications':
            request.user.notifications.filter(is_read=False).update(is_read=True)
            return Response({"status": "cleared"})

        return Response({"error": "Unsupported action."}, status=status.HTTP_400_BAD_REQUEST)

class LiveTrackingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, booking_id):
        booking = get_object_or_404(Booking.objects.select_related('provider', 'category'), id=booking_id)
        is_owner = (booking.customer_id == request.user.id)
        is_assigned_provider = hasattr(request.user, 'provider_profile') and (booking.provider_id == request.user.provider_profile.id)
        if not (is_owner or is_assigned_provider or request.user.is_staff):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        provider_coords, dist_km, eta_mins, last_updated = None, None, None, None
        if booking.provider:
            provider_coords = {
                "lat": booking.provider.current_lat, "lng": booking.provider.current_lng,
                "name": booking.provider.business_name, "phone": booking.provider.phone,
                "rating": str(booking.provider.rating_avg)
            }
            dist_km = haversine_km(booking.customer_lat, booking.customer_lng, booking.provider.current_lat, booking.provider.current_lng)
            eta_mins = max(2, int(round(dist_km * 2.5)))
            last_updated = booking.provider.last_location_update.isoformat()
        return Response({
            "booking_id": booking.id, "status": booking.status, "status_display": booking.get_status_display(),
            "customer_location": {"lat": booking.customer_lat, "lng": booking.customer_lng, "address": booking.customer_address},
            "provider_location": provider_coords, "distance_km": dist_km, "eta_mins": eta_mins, "last_updated": last_updated,
            "history": [{"to_status": h.to_status, "note": h.note, "timestamp": h.timestamp.strftime("%H:%M:%S")} for h in booking.status_history.all()]
        })

class ProviderLocationUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        if not hasattr(request.user, 'provider_profile'):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        p = request.user.provider_profile
        if 'is_available' in request.data:
            p.is_available = bool(request.data.get('is_available'))
        if 'lat' in request.data and 'lng' in request.data:
            p.current_lat = float(request.data['lat'])
            p.current_lng = float(request.data['lng'])
            ProviderLocation.objects.create(provider=p, latitude=p.current_lat, longitude=p.current_lng)
        if 'service_radius_km' in request.data:
            p.service_radius_km = float(request.data['service_radius_km'])
        p.save()
        return Response({"is_available": p.is_available, "current_lat": p.current_lat, "current_lng": p.current_lng, "service_radius_km": p.service_radius_km})

class AIAssistantAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai_assistant'
    def post(self, request):
        msg = (request.data.get('message') or '').strip()
        if not msg:
            return Response({"error": "Empty message"}, status=status.HTTP_400_BAD_REQUEST)
        conv, _ = AIConversation.objects.get_or_create(user=request.user)
        past_msgs = [{"role": m.role, "content": m.content} for m in conv.messages.all().order_by('-created_at')[:6]][::-1]
        AIMessage.objects.create(conversation=conv, role='user', content=msg[:1000])
        result = query_gridx_ai(request.user, msg, past_msgs)
        AIMessage.objects.create(conversation=conv, role='assistant', content=result['reply'])
        return Response(result)


import requests as http_requests
from django.http import HttpResponse

def map_tile_proxy(request, z, x, y):
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    try:
        r = http_requests.get(url, headers={"User-Agent": "GRIDX-Roadside-Assistance-Platform/2.0 (Vijayawada-Guntur)"}, timeout=5)
        if r.status_code == 200:
            res = HttpResponse(r.content, content_type="image/png")
            res["Cache-Control"] = "public, max-age=86400"
            return res
    except Exception:
        pass
    return HttpResponse(status=404)
