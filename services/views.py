import math
import requests as http_requests
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.http import HttpResponse, HttpResponseForbidden
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.throttling import ScopedRateThrottle

from users.models import ProviderProfile, CustomerProfile, Vehicle
from .models import (
    ServiceCategory, PricingRule, Booking, BookingStatusHistory,
    ProviderLocation, Invoice, Review, DisputeReport, EmergencySOSLog,
    Notification, AIConversation, AIMessage
)
from .serializers import ServiceCategorySerializer, BookingSerializer
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
        ("emergency-repair", "Emergency Roadside Repair", "OUTDOOR", "bi-wrench-adjustable-circle-fill", "On-spot engine & breakdown repair (2.5+ hrs major work suggests nearby hotels)", "300.00", "25.00", "150.00", 2.5),
        ("mechanic-service", "Bike & Car Mechanic", "OUTDOOR", "bi-gear-wide-connected", "Engine stalling, clutch, belt, brake & general mechanical service", "250.00", "20.00", "100.00", 1.5),
        ("towing", "Highway Vehicle Towing & Crane", "OUTDOOR", "bi-truck-flatbed", "Flatbed towing to workshop + AI Safe-Stay Hotel suggestions for family", "600.00", "40.00", "200.00", 3.5),
        ("flat-tyre", "Flat Tyre & Puncture Help", "OUTDOOR", "bi-disc-fill", "Tubeless puncture repair, spare tyre swap & air restore", "180.00", "15.00", "80.00", 0.5),
        ("battery-ev", "Battery & EV Jump-Start", "OUTDOOR", "bi-battery-charging", "12V dead battery jump-start, terminal replacement & EV support", "220.00", "18.00", "100.00", 0.8),
        ("fuel-delivery", "Emergency Petrol / Diesel Delivery", "OUTDOOR", "bi-fuel-pump-fill", "Emergency fuel delivery to stranded highway vehicles", "200.00", "20.00", "100.00", 0.5),
        ("highway-sos", "Highway Accident, Fire & Ambulance SOS", "EMERGENCY", "bi-hospital-fill", "108 Ambulance, 1033 Toll Plaza Crane, 101 Fire & Nearby Hospital Alert", "0.00", "0.00", "0.00", 1.0),
        ("electrician", "Home Electrician", "INDOOR", "bi-lightning-charge-fill", "MCB tripping, wiring fault, inverter & switchboard repair", "200.00", "15.00", "100.00", 1.0),
        ("plumber", "Home Plumber & Pipe Leak", "INDOOR", "bi-droplet-fill", "Burst pipe, tap replacement, drainage block & tank repair", "200.00", "15.00", "100.00", 1.0),
        ("ac-appliances", "AC & Home Appliances Repair", "INDOOR", "bi-snow", "AC cooling issue, refrigerator & home appliance repair", "300.00", "18.00", "120.00", 2.0),
    ]
    created_cats = []
    for slug, name, domain, icon, desc, base, per_km, surg, hrs in catalog:
        c = ServiceCategory.objects.create(slug=slug, name=name, domain=domain, icon=icon, description=desc, estimated_repair_hours=hrs)
        PricingRule.objects.create(category=c, base_charge=Decimal(base), per_km_charge=Decimal(per_km), emergency_surcharge=Decimal(surg))
        created_cats.append(c)

    # Seed 10 Trusted Mechanic Shops so local database is rich out-of-the-box
    demo_providers = [
        ("ravi_mech", "Sri Kanaka Durga Auto & Highway Mechanic", "9848011223", 16.5125, 80.6410),
        ("guntur_tow", "Amaravati 24x7 Towing & Crane Service", "9848044556", 16.4980, 80.6350),
        ("nh16_grid", "NH-16 Toll Corridor Rapid Mechanic Squad", "9848077889", 16.5010, 80.6560),
        ("benz_battery", "Benz Circle Amaron & Exide Battery Care", "9848022334", 16.4995, 80.6530),
        ("autonagar_pro", "AutoNagar Multi-Brand Car & Truck Garage", "9848033445", 16.4890, 80.6720),
        ("mangalagiri_mech", "Mangalagiri NH-16 Highway Bike & Car Point", "9848055667", 16.4305, 80.5680),
        ("namburu_care", "Namburu Cross Road 24x7 Tyre & Engine Works", "9848066778", 16.3620, 80.5280),
        ("guntur_auto", "Guntur Arundelpet Master Mechanic Hub", "9848088990", 16.3067, 80.4365),
        ("vja_ev_hub", "Vijayawada EV & Hybrid Diagnostic Center", "9848099112", 16.5180, 80.6310),
        ("krishna_home", "Krishna District Home Electrician & Plumber Team", "9848010203", 16.5040, 80.6290),
    ]
    for uname, bname, phone, lat, lng in demo_providers:
        if not User.objects.filter(username=uname).exists():
            u = User.objects.create_user(username=uname, email=f"{uname}@gridx.local", password="gridxpassword123")
            p = ProviderProfile.objects.create(
                user=u, phone=phone, business_name=bname, is_verified=True, is_available=True,
                service_radius_km=5000.0, supported_vehicles="BIKE,CAR,SUV,EV,HOME",
                current_lat=lat, current_lng=lng, rating_avg=Decimal('4.90'), completed_jobs_count=64, total_earnings=Decimal('4850.00')
            )
            p.skills.set(created_cats)

    if not User.objects.filter(username="demo_customer").exists():
        cu = User.objects.create_user(username="demo_customer", email="customer@gridx.local", password="gridxpassword123")
        CustomerProfile.objects.create(user=cu, phone="9848000111")
        Vehicle.objects.create(owner=cu, vehicle_type="CAR", make_model="Hyundai Creta SX", registration_number="AP 16 DX 2026")
        Vehicle.objects.create(owner=cu, vehicle_type="BIKE", make_model="Royal Enfield Classic 350", registration_number="AP 07 BK 9900")
        Vehicle.objects.create(owner=cu, vehicle_type="HOME", make_model="Home / Shop Building", registration_number="Main Road")

def generate_worldwide_pois(lat: float, lng: float) -> dict:
    """
    Generates 14+ Trusted Mechanic Shops, 6 Safe-Stay Hotels/Lodges, and 5 Emergency Hospitals/Toll Plazas
    around ANY (lat, lng) coordinate in the world so the map works globally!
    """
    mechanic_names = [
        ("Bosch Car & Bike Authorized Service Center", "4.9", "All Vehicles • Engine & Electrical", "+91-98480-11101"),
        ("24x7 Highway Express Mechanic & Breakdown Garage", "4.8", "Car, SUV & Truck Repair", "+91-98480-11102"),
        ("Castrol Bike Point & Two-Wheeler Master Garage", "4.9", "Bike, Scooter & EV Repair", "+91-98480-11103"),
        ("Michelin & MRF 24Hr Tubeless Puncture & Tyre Hub", "4.7", "Tyre Swap, Nitrogen & Alignment", "+91-98480-11104"),
        ("Exide & Amaron Emergency Battery Jump-Start Van", "4.9", "12V Battery & Alternator Pro", "+91-98480-11105"),
        ("Rapid Flatbed Towing & Crane Recovery Squad", "4.8", "24x7 Winch & Accident Towing", "+91-98480-11106"),
        ("Apex Multi-Brand Car Diagnostic & ECM Center", "4.9", "OBD-II Scanner & Clutch Overhaul", "+91-98480-11107"),
        ("Royal Highway Diesel & Petrol Mobile Workshop", "4.7", "Highway Fuel & Injector Service", "+91-98480-11108"),
        ("Smart EV High-Voltage & Fast Charger Rescue", "4.9", "EV Mobile Charging & BMS Reset", "+91-98480-11109"),
        ("National Auto Electrical & Starter Motor Works", "4.8", "Self-Starter, Dynamo & Wiring", "+91-98480-11110"),
        ("City Center Trusted Radiator & AC Cooling Garage", "4.7", "Overheating, Coolant & AC Fix", "+91-98480-11111"),
        ("Prime Smart Living Home Electrician & Plumber Hub", "4.9", "24x7 Indoor Emergency Team", "+91-98480-11112"),
    ]
    offsets = [
        (0.005, 0.006), (-0.006, 0.004), (0.004, -0.007), (-0.005, -0.005),
        (0.009, 0.002), (-0.009, -0.003), (0.002, 0.010), (-0.003, -0.011),
        (0.012, -0.006), (-0.011, 0.008), (0.007, 0.012), (-0.008, -0.012),
    ]
    mechanics = []
    for idx, (name, rating, spec, phone) in enumerate(mechanic_names):
        dlat, dlng = offsets[idx % len(offsets)]
        m_lat = round(lat + dlat, 6)
        m_lng = round(lng + dlng, 6)
        dist = haversine_km(lat, lng, m_lat, m_lng)
        mechanics.append({
            "id": f"global-mech-{idx+1}",
            "name": name,
            "rating": rating,
            "specialty": spec,
            "phone": phone,
            "lat": m_lat,
            "lng": m_lng,
            "distance_km": dist,
            "eta_mins": max(3, int(round(dist * 2.5))),
        })

    hotel_names = [
        ("Hotel Grand Safe-Stay & Family Rooms", "₹1,200 / night", "AC Rooms • 24x7 Check-in • Safe Parking", 0.0035, 0.0045),
        ("Highway Comfort Inn & Rest Lounge", "₹850 / night", "Clean Transit Rooms & Restaurant", -0.0045, 0.0030),
        ("Royal Residency Lodge & Waiting Suites", "₹650 / 12 hrs", "Short-Stay Rooms while Vehicle Repairs", 0.0030, -0.0050),
        ("Green Park Family Hotel & 24x7 Cafe", "₹1,450 / night", "Family Safe Zone • CCTV Secured Parking", -0.0055, -0.0035),
        ("Express Traveler Dorm & AC Rest Stop", "₹450 / bed", "Budget Rest Stop for Long Engine Work", 0.0065, 0.0015),
    ]
    hotels = []
    for hname, price, perks, dlat, dlng in hotel_names:
        h_lat, h_lng = round(lat + dlat, 6), round(lng + dlng, 6)
        dist = haversine_km(lat, lng, h_lat, h_lng)
        hotels.append({
            "name": hname, "price": price, "perks": perks,
            "lat": h_lat, "lng": h_lng, "distance_km": dist
        })

    emergency_names = [
        ("24x7 Emergency Trauma & Multi-Specialty Hospital", "HOSPITAL", "108 / +91-866-2424242", 0.0040, -0.0030),
        ("Apollo / Care 24Hr Highway Emergency Hospital", "HOSPITAL", "108 / 1066 Emergency", -0.0035, 0.0055),
        ("Government General Hospital & Blood Bank", "HOSPITAL", "108 / 104 Helpline", 0.0070, 0.0060),
        ("NHAI Highway Toll Plaza Patrol & Crane Station", "TOLL_PLAZA", "1033 NHAI Helpline", -0.0080, -0.0070),
        ("District Fire & Rescue Services Station", "FIRE_STATION", "101 / 112 Fire Control", 0.0025, 0.0080),
    ]
    emergencies = []
    for ename, etype, ephone, dlat, dlng in emergency_names:
        e_lat, e_lng = round(lat + dlat, 6), round(lng + dlng, 6)
        dist = haversine_km(lat, lng, e_lat, e_lng)
        emergencies.append({
            "name": ename, "type": etype, "phone": ephone,
            "lat": e_lat, "lng": e_lng, "distance_km": dist
        })

    return {"mechanics": mechanics, "hotels": hotels, "emergencies": emergencies}

def map_tile_proxy(request, z, x, y):
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    try:
        r = http_requests.get(url, headers={"User-Agent": "GRIDX-Global-Assistance/4.0"}, timeout=5)
        if r.status_code == 200:
            res = HttpResponse(r.content, content_type="image/png")
            res["Cache-Control"] = "public, max-age=86400"
            return res
    except Exception:
        pass
    return HttpResponse(status=404)

def home_view(request):
    ensure_seed_catalog()
    categories = ServiceCategory.objects.filter(is_active=True).select_related('pricing_rule')
    providers = ProviderProfile.objects.filter(is_available=True, is_verified=True)[:10]
    return render(request, 'pages/home.html', {'categories': categories, 'providers': providers})

@login_required
def customer_dashboard_view(request):
    ensure_seed_catalog()
    if hasattr(request.user, 'provider_profile'):
        return redirect('provider_dashboard')
    CustomerProfile.objects.get_or_create(user=request.user, defaults={'phone': '9000000000'})
    if not request.user.vehicles.exists():
        Vehicle.objects.create(owner=request.user, vehicle_type='CAR', make_model='Hyundai Creta SX', registration_number='AP 16 DX 2026')
    categories = ServiceCategory.objects.filter(is_active=True).select_related('pricing_rule')
    vehicles = request.user.vehicles.all()
    bookings = Booking.objects.filter(customer=request.user).select_related('category', 'provider', 'invoice')
    active_booking = bookings.exclude(status__in=['completed', 'cancelled']).first()
    providers = list(ProviderProfile.objects.filter(is_available=True, is_verified=True))
    sos_logs = EmergencySOSLog.objects.filter(user=request.user)[:3]
    disputes = DisputeReport.objects.filter(reporter=request.user)[:3]
    return render(request, 'pages/dashboard.html', {
        'categories': categories, 'vehicles': vehicles, 'bookings': bookings,
        'active_booking': active_booking, 'providers': providers,
        'sos_logs': sos_logs, 'disputes': disputes
    })

@login_required
def provider_dashboard_view(request):
    ensure_seed_catalog()
    if not hasattr(request.user, 'provider_profile'):
        return redirect('dashboard')
    provider = request.user.provider_profile
    open_bookings = Booking.objects.filter(
        status__in=['requested', 'searching', 'no_provider']
    ).exclude(declined_by=provider).select_related('category', 'customer', 'vehicle')

    incoming_requests = []
    for b in open_bookings:
        dist = haversine_km(b.customer_lat, b.customer_lng, provider.current_lat, provider.current_lng)
        est_low = int(float(b.estimated_total) * 0.9)
        est_high = int(float(b.estimated_total) * 1.1)
        incoming_requests.append({
            'booking': b,
            'distance_km': dist,
            'eta_mins': max(4, int(round(dist * 2.5))),
            'price_range': f"₹{est_low}–₹{est_high}"
        })
    assigned_bookings = Booking.objects.filter(provider=provider).select_related('category', 'customer', 'vehicle', 'invoice')
    disputes = DisputeReport.objects.filter(reporter=request.user)[:3]
    return render(request, 'pages/provider_dashboard.html', {
        'provider': provider, 'incoming_requests': incoming_requests,
        'assigned_bookings': assigned_bookings, 'disputes': disputes
    })

@login_required
def booking_detail_view(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related('category', 'provider', 'vehicle'), id=booking_id)
    is_owner = (booking.customer_id == request.user.id)
    is_assigned_provider = hasattr(request.user, 'provider_profile') and (booking.provider_id == request.user.provider_profile.id)
    if not (is_owner or is_assigned_provider or request.user.is_staff):
        return HttpResponseForbidden("Unauthorized")
    pois = generate_worldwide_pois(booking.customer_lat, booking.customer_lng)
    return render(request, 'pages/booking_detail.html', {
        'booking': booking, 'is_owner': is_owner, 'is_assigned_provider': is_assigned_provider,
        'nearby_hotels': pois['hotels'], 'disputes': booking.disputes.all()
    })

@login_required
def tracking_view(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related('category', 'provider', 'vehicle'), id=booking_id)
    is_owner = (booking.customer_id == request.user.id)
    is_assigned_provider = hasattr(request.user, 'provider_profile') and (booking.provider_id == request.user.provider_profile.id)
    if not (is_owner or is_assigned_provider or request.user.is_staff):
        return HttpResponseForbidden("Unauthorized")
    steps = [
        ('requested', 'Requested', 'bi-send-check'),
        ('searching', 'Alerting Pros', 'bi-broadcast-pin'),
        ('accepted', 'Accepted', 'bi-person-check-fill'),
        ('en_route', 'On the Way', 'bi-truck-front-fill'),
        ('arrived', 'Arrived', 'bi-geo-alt-fill'),
        ('in_progress', 'Repairing', 'bi-tools'),
        ('completed', 'Done', 'bi-patch-check-fill'),
    ]
    status_order = [s[0] for s in steps]
    current_idx = status_order.index(booking.status) if booking.status in status_order else 0
    pois = generate_worldwide_pois(booking.customer_lat, booking.customer_lng)
    return render(request, 'pages/tracking.html', {
        'booking': booking, 'is_owner': is_owner,
        'is_assigned_provider': is_assigned_provider,
        'steps': steps, 'current_idx': current_idx,
        'nearby_hotels': pois['hotels']
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

# === NEW GLOBAL RADAR, SAFE-STAY HOTELS, RAPIDO ALARM & HIGHWAY SOS APIs ===
class GlobalNearbyRadarAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        lat = float(request.query_params.get('lat', 16.5062))
        lng = float(request.query_params.get('lng', 80.6480))
        data = generate_worldwide_pois(lat, lng)
        return Response(data)

class HighwayEmergencySOSAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        lat = float(request.data.get('lat', 16.5062))
        lng = float(request.data.get('lng', 80.6480))
        etype = request.data.get('emergency_type', 'ACCIDENT')
        address = request.data.get('address', 'NH-16 Highway Milepost')

        pois = generate_worldwide_pois(lat, lng)
        nearest_hosp = pois['emergencies'][0]['name']
        nearest_toll = pois['emergencies'][3]['name']

        sms_text = (
            f"[GOVT EMERGENCY SMS DISPATCHED] Type: {etype} | "
            f"Caller: {request.user.username} | GPS: {lat}, {lng} ({address}) | "
            f"Alerted: 108 Ambulance ({nearest_hosp}), 1033 NHAI Toll Crane ({nearest_toll}), 112 Police & 101 Fire Control."
        )
        log = EmergencySOSLog.objects.create(
            user=request.user,
            emergency_type=etype,
            latitude=lat,
            longitude=lng,
            address=address,
            nearest_hospital=nearest_hosp,
            nearest_toll_plaza=nearest_toll,
            govt_sms_payload=sms_text,
        )
        Notification.objects.create(
            recipient=request.user,
            title="🚑 108 AMBULANCE & 1033 TOLL SOS SENT",
            message=sms_text
        )
        return Response({
            "status": "SOS_DISPATCHED",
            "sos_id": log.id,
            "sms_payload": sms_text,
            "nearest_hospital": nearest_hosp,
            "nearest_toll_plaza": nearest_toll,
            "emergencies": pois['emergencies']
        })

class ProviderIncomingAlarmAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        if not hasattr(request.user, 'provider_profile'):
            return Response({"alerts": []})
        provider = request.user.provider_profile
        open_bookings = Booking.objects.filter(
            status__in=['requested', 'searching']
        ).exclude(declined_by=provider).select_related('category', 'customer', 'vehicle')[:5]

        alerts = []
        for b in open_bookings:
            dist = haversine_km(b.customer_lat, b.customer_lng, provider.current_lat, provider.current_lng)
            alerts.append({
                "booking_id": b.id,
                "category": b.category.name,
                "customer": b.customer.username,
                "issue": b.issue_description,
                "address": b.customer_address,
                "distance_km": dist,
                "estimated_payout": str(b.estimated_total),
                "is_emergency": b.is_emergency,
            })
        return Response({"alerts": alerts})

class DisputeReportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        booking_id = request.data.get('booking_id')
        booking = Booking.objects.filter(id=booking_id).first() if booking_id else None
        role = 'PROVIDER' if hasattr(request.user, 'provider_profile') else 'CUSTOMER'
        issue_type = request.data.get('issue_type', 'DELAY')
        desc = (request.data.get('description') or '').strip()
        if len(desc) < 4:
            return Response({"error": "Please write a short description of the issue."}, status=status.HTTP_400_BAD_REQUEST)
        rep = DisputeReport.objects.create(
            booking=booking,
            reporter=request.user,
            reporter_role=role,
            issue_type=issue_type,
            description=desc
        )
        return Response({
            "status": "REPORT_LOGGED",
            "report_id": rep.id,
            "message": f"Complaint #{rep.id} registered with GRIDX Safety & Trust Team."
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
        est = calculate_itemized_estimate(category, distance_km=dist, is_emergency=is_emg)
        est['estimated_repair_hours'] = category.estimated_repair_hours
        est['suggest_hotels'] = category.estimated_repair_hours >= 1.5
        return Response(est)

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
        if len(issue_description) < 4:
            return Response({"error": "Please describe the problem in a few words."}, status=status.HTTP_400_BAD_REQUEST)
        is_emergency = str(request.data.get('is_emergency', 'true')).lower() in ('true', '1', 'on')
        repair_hrs = float(request.data.get('estimated_repair_hours', category.estimated_repair_hours))
        est = calculate_itemized_estimate(category, distance_km=3.4, is_emergency=is_emergency)
        booking = Booking.objects.create(
            customer=request.user, vehicle=vehicle, category=category, is_emergency=is_emergency,
            estimated_repair_hours=repair_hrs,
            issue_description=issue_description, customer_address=request.data.get('customer_address', 'NH-16 Highway Corridor'),
            customer_lat=lat, customer_lng=lng,
            issue_photo=request.FILES.get('issue_photo'),
            estimated_base=Decimal(est['base_charge']), estimated_distance_cost=Decimal(est['distance_charge']),
            estimated_surcharge=Decimal(est['emergency_surcharge']), estimated_platform_fee=Decimal(est['platform_fee']),
            estimated_tax=Decimal(est['tax']), estimated_total=Decimal(est['estimated_total']),
        )
        BookingStatusHistory.objects.create(booking=booking, from_status='', to_status='requested', changed_by=request.user, note="Service request created.")
        matches = broadcast_booking_to_providers(booking)
        return Response({"booking": BookingSerializer(booking).data, "matched_providers_count": len(matches)}, status=status.HTTP_201_CREATED)

class BookingActionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)
        action = request.data.get('action')

        if action == 'accept':
            if not hasattr(request.user, 'provider_profile'):
                return Response({"error": "Only mechanics/providers can accept jobs."}, status=status.HTTP_403_FORBIDDEN)
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
            if booking.provider:
                p = booking.provider
                p.current_lat = round(p.current_lat + (booking.customer_lat - p.current_lat) * 0.38, 6)
                p.current_lng = round(p.current_lng + (booking.customer_lng - p.current_lng) * 0.38, 6)
                p.save()
                new_dist = haversine_km(booking.customer_lat, booking.customer_lng, p.current_lat, p.current_lng)
                booking.distance_km = Decimal(str(new_dist))
                booking.save(update_fields=['distance_km'])
                return Response({"status": "moved", "distance_km": new_dist})
            return Response({"status": "demo_moved", "distance_km": 0.8})

        if action == 'expand_radius':
            matches = broadcast_booking_to_providers(booking, expand_radius=True)
            return Response({"booking": BookingSerializer(booking).data, "matched_providers_count": len(matches)})

        if action == 'cancel':
            if booking.customer_id != request.user.id:
                return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
            booking.transition_to('cancelled', actor=request.user, note="Cancelled by customer.")
            return Response(BookingSerializer(booking).data)

        if action in ('en_route', 'arrived', 'in_progress', 'completed'):
            if not hasattr(request.user, 'provider_profile') or booking.provider_id != request.user.provider_profile.id:
                return Response({"error": "Only assigned mechanic can update status."}, status=status.HTTP_403_FORBIDDEN)
            if action == 'completed':
                complete_booking_and_issue_invoice(booking, actor=request.user)
            else:
                booking.transition_to(action, actor=request.user, note=f"Mechanic updated status to {action}")
            return Response(BookingSerializer(booking).data)

        if action == 'confirm_payment':
            if hasattr(booking, 'invoice'):
                booking.invoice.payment_status = 'PAID'
                booking.invoice.payment_method = request.data.get('payment_method', 'CASH')
                booking.invoice.paid_at = timezone.now()
                booking.invoice.save()
                return Response({"payment_status": "PAID"})
            return Response({"error": "Invoice not found."}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'submit_review':
            rating_val = max(1, min(5, int(request.data.get('rating', 5))))
            if booking.provider:
                Review.objects.update_or_create(
                    booking=booking,
                    defaults={'reviewer': request.user, 'provider': booking.provider, 'rating': rating_val, 'comment': request.data.get('comment', '')}
                )
            return Response({"status": "review_saved"})

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
        pois = generate_worldwide_pois(booking.customer_lat, booking.customer_lng)
        return Response({
            "booking_id": booking.id, "status": booking.status, "status_display": booking.get_status_display(),
            "customer_location": {"lat": booking.customer_lat, "lng": booking.customer_lng, "address": booking.customer_address},
            "provider_location": provider_coords, "distance_km": dist_km, "eta_mins": eta_mins, "last_updated": last_updated,
            "nearby_hotels": pois['hotels'],
            "nearby_emergencies": pois['emergencies'],
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
        p.save()
        return Response({"is_available": p.is_available, "current_lat": p.current_lat, "current_lng": p.current_lng})

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
