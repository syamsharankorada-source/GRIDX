import os, sys, zipfile
from pathlib import Path

# Detect whether we are inside D:\gridx_project or its parent folder
CWD = Path.cwd()
PROJECT_ROOT = CWD if (CWD / "manage.py").exists() else (CWD / "gridx_project")

FILES = {
    "start_gridx.bat": """@echo off
title GRIDX v2.0 - Enterprise Roadside and Indoor Dispatch Network
echo ============================================================
echo   GRIDX v2.0 - ONE GRID. EVERY SOLUTION. (Refined Edition)
echo ============================================================
if not exist .env (
    copy .env.example .env >nul
)
if not exist venv (
    python -m venv venv --system-site-packages
)
call venv\\Scripts\\activate
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt --quiet
python manage.py makemigrations users services
python manage.py migrate
echo.
echo [OK] Launching GRIDX v2.0 at http://127.0.0.1:8000 ...
start http://127.0.0.1:8000
python manage.py runserver
pause
""",

    "users/models.py": """from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=20)
    default_address = models.CharField(max_length=255, blank=True, default="Benz Circle, NH-16, Vijayawada")
    default_lat = models.FloatField(default=16.5062)
    default_lng = models.FloatField(default=80.6480)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Customer: {self.user.username}"

class ProviderProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='provider_profile')
    phone = models.CharField(max_length=20)
    business_name = models.CharField(max_length=120)
    is_verified = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    service_radius_km = models.FloatField(default=20.0, validators=[MinValueValidator(1.0), MaxValueValidator(100.0)])
    supported_vehicles = models.CharField(max_length=120, default="BIKE,CAR,SUV,EV,HOME")
    current_lat = models.FloatField(default=16.5120)
    current_lng = models.FloatField(default=80.6420)
    last_location_update = models.DateTimeField(auto_now=True)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=4.90)
    completed_jobs_count = models.PositiveIntegerField(default=18)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=2450.00)
    skills = models.ManyToManyField('services.ServiceCategory', related_name='providers', blank=True)

    def supports_vehicle(self, vehicle_type: str) -> bool:
        supported = [v.strip().upper() for v in self.supported_vehicles.split(',') if v.strip()]
        return vehicle_type.upper() in supported or 'HOME' in supported

    def __str__(self):
        return f"Provider: {self.business_name}"

class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('BIKE', 'Two-Wheeler / Bike'),
        ('CAR', 'Sedan / Hatchback Car'),
        ('SUV', 'SUV / MUV'),
        ('EV', 'Electric Vehicle (EV)'),
        ('HOME', 'Indoor / Home Premises'),
    ]
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicles')
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_TYPES, default='CAR')
    make_model = models.CharField(max_length=100)
    registration_number = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.make_model} ({self.registration_number})"
""",

    "users/forms.py": """from django import forms
from django.contrib.auth.models import User
from .models import CustomerProfile, ProviderProfile, Vehicle
from services.models import ServiceCategory

class StyledFormMixin:
    def _style_fields(self):
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.update({'class': 'gridx-checkbox-list'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select gridx-input'})
            else:
                field.widget.attrs.update({'class': 'form-control gridx-input'})

class CustomerRegistrationForm(StyledFormMixin, forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Create strong password'}))
    phone = forms.CharField(max_length=20, initial='9848012345', widget=forms.TextInput(attrs={'placeholder': '+91 98480 12345'}))
    vehicle_type = forms.ChoiceField(choices=Vehicle.VEHICLE_TYPES, initial='CAR')
    make_model = forms.CharField(max_length=100, initial='Hyundai Creta SX', widget=forms.TextInput(attrs={'placeholder': 'e.g. Hyundai Creta / Honda Activa'}))
    registration_number = forms.CharField(max_length=30, initial='AP 16 DX 2026', widget=forms.TextInput(attrs={'placeholder': 'e.g. AP 16 DX 2026'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Choose a username'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            CustomerProfile.objects.create(user=user, phone=self.cleaned_data['phone'])
            Vehicle.objects.create(
                owner=user,
                vehicle_type=self.cleaned_data['vehicle_type'],
                make_model=self.cleaned_data['make_model'],
                registration_number=self.cleaned_data['registration_number']
            )
        return user

class ProviderRegistrationForm(StyledFormMixin, forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Create strong password'}))
    phone = forms.CharField(max_length=20, initial='9848099999')
    business_name = forms.CharField(max_length=120, initial='Vijayawada Rapid Roadside & Home Pro')
    service_radius_km = forms.FloatField(initial=20.0)
    supported_vehicles = forms.CharField(initial="BIKE,CAR,SUV,EV,HOME")
    skills = forms.ModelMultipleChoiceField(
        queryset=ServiceCategory.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            profile = ProviderProfile.objects.create(
                user=user,
                phone=self.cleaned_data['phone'],
                business_name=self.cleaned_data['business_name'],
                service_radius_km=self.cleaned_data['service_radius_km'],
                supported_vehicles=self.cleaned_data['supported_vehicles'],
                is_verified=True
            )
            if self.cleaned_data.get('skills'):
                profile.skills.set(self.cleaned_data['skills'])
            else:
                profile.skills.set(ServiceCategory.objects.all())
        return user

class VehicleForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['vehicle_type', 'make_model', 'registration_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
""",

    "users/views.py": """from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomerRegistrationForm, ProviderRegistrationForm, VehicleForm
from .models import Vehicle
from services.views import ensure_seed_catalog

def register_view(request):
    ensure_seed_catalog()
    role = request.GET.get('role', 'customer')
    if request.method == 'POST':
        role = request.POST.get('role', 'customer')
        form = ProviderRegistrationForm(request.POST) if role == 'provider' else CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to GRIDX, {user.username}! Your account is active.")
            return redirect('provider_dashboard' if hasattr(user, 'provider_profile') else 'dashboard')
    else:
        form = ProviderRegistrationForm() if role == 'provider' else CustomerRegistrationForm()
    return render(request, 'pages/register.html', {'form': form, 'role': role})

def login_view(request):
    ensure_seed_catalog()
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Signed in as {user.username}.")
            return redirect('provider_dashboard' if hasattr(user, 'provider_profile') else 'dashboard')
        else:
            messages.error(request, "Invalid username or password. Try demo: ravi_mech / gridxpassword123")
    else:
        form = AuthenticationForm()
    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-control gridx-input'})
    return render(request, 'pages/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out safely.")
    return redirect('home')

@login_required
def add_vehicle_view(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            v = form.save(commit=False)
            v.owner = request.user
            v.save()
            messages.success(request, f"Added {v.make_model} ({v.registration_number}) to your garage.")
    return redirect('dashboard')

@login_required
def delete_vehicle_view(request, vehicle_id):
    v = get_object_or_404(Vehicle, id=vehicle_id, owner=request.user)
    if request.user.vehicles.count() > 1:
        v.delete()
        messages.info(request, "Vehicle removed.")
    else:
        messages.warning(request, "Keep at least one active vehicle/unit in your profile.")
    return redirect('dashboard')
""",

    "users/urls.py": """from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('vehicles/add/', views.add_vehicle_view, name='add_vehicle'),
    path('vehicles/<int:vehicle_id>/delete/', views.delete_vehicle_view, name='delete_vehicle'),
]
""",

    "services/models.py": """from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from users.models import ProviderProfile, Vehicle

class ServiceCategory(models.Model):
    DOMAIN_CHOICES = [
        ('OUTDOOR', 'Outdoor / Roadside'),
        ('INDOOR', 'Indoor / Home Service'),
    ]
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=15, choices=DOMAIN_CHOICES, default='OUTDOOR')
    icon = models.CharField(max_length=50, default='bi-tools')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"[{self.domain}] {self.name}"

class PricingRule(models.Model):
    category = models.OneToOneField(ServiceCategory, on_delete=models.CASCADE, related_name='pricing_rule')
    base_charge = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('250.00'))
    per_km_charge = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('25.00'))
    emergency_surcharge = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('150.00'))
    platform_fee_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.00'))
    tax_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'))
    updated_at = models.DateTimeField(auto_now=True)

class Booking(models.Model):
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('searching', 'Searching Providers'),
        ('accepted', 'Provider Accepted'),
        ('en_route', 'Provider En Route'),
        ('arrived', 'Provider Arrived'),
        ('in_progress', 'Service In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_provider', 'No Provider Available'),
    ]
    VALID_TRANSITIONS = {
        'requested': ['searching', 'accepted', 'cancelled', 'no_provider'],
        'searching': ['accepted', 'cancelled', 'no_provider'],
        'accepted': ['en_route', 'cancelled'],
        'en_route': ['arrived', 'cancelled'],
        'arrived': ['in_progress', 'cancelled'],
        'in_progress': ['completed'],
        'completed': [],
        'cancelled': [],
        'no_provider': ['searching', 'accepted', 'cancelled'],
    }
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_bookings')
    provider = models.ForeignKey(ProviderProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_bookings')
    declined_by = models.ManyToManyField(ProviderProfile, blank=True, related_name='declined_bookings')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested', db_index=True)
    is_emergency = models.BooleanField(default=True)
    issue_description = models.TextField()
    issue_photo = models.ImageField(upload_to='booking_photos/', null=True, blank=True)
    customer_address = models.CharField(max_length=255, default="Benz Circle, NH-16, Vijayawada")
    customer_lat = models.FloatField()
    customer_lng = models.FloatField()
    search_radius_km = models.FloatField(default=15.0)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('3.40'))
    estimated_base = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    estimated_distance_cost = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    estimated_surcharge = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    estimated_tax = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    estimated_platform_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    estimated_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status: str, actor: User = None, note: str = ""):
        if not self.can_transition_to(new_status):
            raise ValidationError(f"Invalid transition from {self.status} to {new_status}")
        old = self.status
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
        BookingStatusHistory.objects.create(booking=self, from_status=old, to_status=new_status, changed_by=actor, note=note)

class BookingStatusHistory(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

class ProviderLocation(models.Model):
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='location_logs')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    recorded_at = models.DateTimeField(auto_now_add=True)

class Invoice(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='invoice')
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    provider_payout = models.DecimalField(max_digits=10, decimal_places=2)
    platform_commission = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, default='CASH')
    payment_status = models.CharField(max_length=20, default='PENDING')
    issued_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

class Review(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=140)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class AIConversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_conversations')
    created_at = models.DateTimeField(auto_now_add=True)

class AIMessage(models.Model):
    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
""",

    "services/views.py": """from decimal import Decimal
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
""",

    "static/css/style.css": """@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Space+Grotesk:wght@600;700;800&display=swap');

:root {
    --bg-grid-dark: #07080B;
    --bg-surface: #10131A;
    --bg-surface-elevated: #171B26;
    --bg-glass: rgba(16, 19, 26, 0.88);
    --gridx-yellow: #FFD000;
    --gridx-yellow-hover: #FFDF33;
    --gridx-yellow-glow: rgba(255, 208, 0, 0.22);
    --gridx-green: #00E676;
    --gridx-danger: #FF3B30;
    --text-primary: #F8FAFC;
    --text-secondary: #94A3B8;
    --border-grid: rgba(255, 208, 0, 0.24);
    --border-subtle: rgba(255, 255, 255, 0.08);
    --radius-card: 16px;
    --radius-btn: 10px;
}

body {
    background-color: var(--bg-grid-dark);
    background-image:
        linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
    background-size: 38px 38px;
    color: var(--text-primary);
    font-family: 'Inter', system-ui, sans-serif;
    min-height: 100vh;
}

h1, h2, h3, h4, .brand-logo, .display-font {
    font-family: 'Space Grotesk', 'Inter', sans-serif;
}

.navbar-gridx {
    background: rgba(7, 8, 11, 0.92);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border-grid);
}

.brand-logo {
    font-weight: 800;
    letter-spacing: 1.5px;
    font-size: 1.55rem;
    color: #FFF;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.brand-logo span {
    background: var(--gridx-yellow);
    color: #07080B;
    padding: 0px 8px;
    border-radius: 6px;
    font-weight: 900;
}

.gridx-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-card);
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.65);
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.gridx-card:hover {
    border-color: rgba(255, 208, 0, 0.35);
}

.gridx-card-yellow {
    background: linear-gradient(135deg, #FFD000 0%, #F5B700 100%);
    color: #07080B;
    border-radius: var(--radius-card);
    box-shadow: 0 12px 30px rgba(255, 208, 0, 0.25);
    font-weight: 700;
}

.btn-gridx {
    background-color: var(--gridx-yellow);
    color: #07080B !important;
    font-weight: 800;
    border: none;
    border-radius: var(--radius-btn);
    padding: 0.62rem 1.25rem;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    transition: all 0.18s ease;
    box-shadow: 0 4px 15px rgba(255, 208, 0, 0.25);
}

.btn-gridx:hover {
    background-color: var(--gridx-yellow-hover);
    transform: translateY(-2px);
    box-shadow: 0 8px 22px rgba(255, 208, 0, 0.4);
}

.btn-gridx-outline {
    background: rgba(255, 208, 0, 0.06);
    color: var(--gridx-yellow) !important;
    border: 1.5px solid var(--gridx-yellow);
    font-weight: 700;
    border-radius: var(--radius-btn);
    transition: all 0.18s ease;
}

.btn-gridx-outline:hover, .btn-gridx-outline.active {
    background: var(--gridx-yellow);
    color: #07080B !important;
}

.badge-domain-outdoor {
    background: rgba(255, 208, 0, 0.15);
    color: var(--gridx-yellow);
    border: 1px solid var(--gridx-yellow);
    font-weight: 700;
}

.badge-domain-indoor {
    background: rgba(0, 230, 118, 0.14);
    color: var(--gridx-green);
    border: 1px solid var(--gridx-green);
    font-weight: 700;
}

.service-cat-card {
    cursor: pointer;
    border: 1.5px solid var(--border-subtle);
    position: relative;
    overflow: hidden;
}

.service-cat-card.active {
    border-color: var(--gridx-yellow);
    background: linear-gradient(180deg, rgba(255, 208, 0, 0.12) 0%, var(--bg-surface-elevated) 100%);
    box-shadow: 0 0 0 2px var(--gridx-yellow-glow);
}

.service-cat-card.active::after {
    content: "✓ SELECTED";
    position: absolute;
    top: 8px;
    right: 10px;
    font-size: 0.62rem;
    font-weight: 900;
    background: var(--gridx-yellow);
    color: #000;
    padding: 2px 6px;
    border-radius: 4px;
}

.map-container {
    height: 380px;
    width: 100%;
    border-radius: var(--radius-card);
    border: 1.5px solid var(--border-grid);
    z-index: 1;
    background: #0B0D13;
}

/* Custom Inputs */
.gridx-input, .form-control, .form-select {
    background-color: #0B0E14 !important;
    border: 1.5px solid rgba(255, 255, 255, 0.14) !important;
    color: var(--text-primary) !important;
    border-radius: 10px !important;
    padding: 0.6rem 0.85rem;
}

.gridx-input:focus, .form-control:focus, .form-select:focus {
    border-color: var(--gridx-yellow) !important;
    box-shadow: 0 0 0 3px rgba(255, 208, 0, 0.2) !important;
}

/* Stepper */
.stepper-wrapper {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 6px;
}

.stepper-item {
    flex: 1;
    min-width: 95px;
    text-align: center;
    padding: 10px 6px;
    border-radius: 10px;
    background: #0C0F17;
    border: 1px solid var(--border-subtle);
    opacity: 0.45;
}

.stepper-item.completed {
    opacity: 0.9;
    border-color: var(--gridx-green);
    color: var(--gridx-green);
}

.stepper-item.active {
    opacity: 1;
    border: 1.5px solid var(--gridx-yellow);
    background: rgba(255, 208, 0, 0.12);
    color: var(--gridx-yellow);
    font-weight: 800;
}

/* Pulse animation for live indicators */
@keyframes pulse-yellow {
    0% { box-shadow: 0 0 0 0 rgba(255, 208, 0, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(255, 208, 0, 0); }
    100% { box-shadow: 0 0 0 0 rgba(255, 208, 0, 0); }
}

.live-dot {
    width: 10px;
    height: 10px;
    background: var(--gridx-yellow);
    border-radius: 50%;
    display: inline-block;
    animation: pulse-yellow 1.8s infinite;
}

/* Floating AI Drawer */
.ai-fab {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 1050;
    background: var(--gridx-yellow);
    color: #07080B;
    font-weight: 900;
    border-radius: 50px;
    padding: 12px 22px;
    border: 2px solid #000;
    box-shadow: 0 10px 28px rgba(255, 208, 0, 0.45);
}

.ai-drawer {
    position: fixed;
    bottom: 88px;
    right: 24px;
    width: 395px;
    max-width: calc(100vw - 32px);
    height: 530px;
    background: var(--bg-surface);
    border: 2px solid var(--gridx-yellow);
    border-radius: var(--radius-card);
    z-index: 1055;
    display: none;
    flex-direction: column;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.9);
}

.ai-drawer.open { display: flex; }
.ai-messages { flex: 1; overflow-y: auto; padding: 14px; }
.msg-bubble { padding: 10px 14px; border-radius: 12px; margin-bottom: 10px; font-size: 0.88rem; line-height: 1.5; }
.msg-user { background: var(--gridx-yellow); color: #07080B; font-weight: 700; margin-left: 40px; }
.msg-assistant { background: var(--bg-surface-elevated); color: var(--text-primary); border: 1px solid var(--border-subtle); margin-right: 20px; }
""",

    "static/js/main.js": """function getCSRFToken() {
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
""",

    "static/js/maps.js": """let gridxMap = null, customerMarker = null;

function createCustomIcon(colorHex, iconClass) {
    return L.divIcon({
        className: 'custom-div-icon',
        html: `<div style="background:${colorHex};color:#07080B;width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.1rem;border:2.5px solid #000;box-shadow:0 0 12px ${colorHex};"><i class="bi ${iconClass}"></i></div>`,
        iconSize: [34, 34],
        iconAnchor: [17, 17]
    });
}

function initCustomerDashboardMap(defaultLat, defaultLng, providersData) {
    const mapEl = document.getElementById('dashboard-map');
    if (!mapEl) return;
    gridxMap = L.map('dashboard-map').setView([defaultLat, defaultLng], 13);

    // High-contrast Dark Matter Map Tiles matching PPT Dark Theme
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(gridxMap);

    customerMarker = L.marker([defaultLat, defaultLng], {
        draggable: true,
        icon: createCustomIcon('#FFD000', 'bi-geo-alt-fill')
    }).addTo(gridxMap).bindPopup('<b>Your Service Location</b><br>Drag pin or click anywhere on map.').openPopup();

    customerMarker.on('dragend', e => {
        const p = e.target.getLatLng();
        updateBookingCoordinates(p.lat, p.lng);
    });

    gridxMap.on('click', e => {
        customerMarker.setLatLng(e.latlng);
        updateBookingCoordinates(e.latlng.lat, e.latlng.lng);
    });

    (providersData || []).forEach(p => {
        L.marker([p.lat, p.lng], {
            icon: createCustomIcon('#00E676', 'bi-wrench-adjustable')
        }).addTo(gridxMap).bindPopup(`<b>${p.name}</b><br>Verified GRIDX Pro • ★ ${p.rating || '4.9'}`);
    });
}

async function updateBookingCoordinates(lat, lng) {
    const latEl = document.getElementById('customer_lat');
    const lngEl = document.getElementById('customer_lng');
    if (latEl) latEl.value = lat.toFixed(6);
    if (lngEl) lngEl.value = lng.toFixed(6);

    // Reverse geocode via Nominatim if available
    try {
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`);
        if (res.ok) {
            const data = await res.json();
            if (data.display_name) {
                const addrEl = document.getElementById('customer_address');
                if (addrEl) addrEl.value = data.display_name.split(',').slice(0, 3).join(', ');
            }
        }
    } catch (err) {}
}

function setQuickCityPreset(lat, lng, label) {
    updateBookingCoordinates(lat, lng);
    const addrEl = document.getElementById('customer_address');
    if (addrEl) addrEl.value = label;
    if (gridxMap && customerMarker) {
        gridxMap.setView([lat, lng], 14);
        customerMarker.setLatLng([lat, lng]);
    }
    showToast(`Switched service zone to ${label}`);
}

function detectBrowserGeolocation() {
    if (!navigator.geolocation) return showToast('Browser Geolocation not supported.', 'danger');
    navigator.geolocation.getCurrentPosition(pos => {
        updateBookingCoordinates(pos.coords.latitude, pos.coords.longitude);
        if (gridxMap && customerMarker) {
            gridxMap.setView([pos.coords.latitude, pos.coords.longitude], 15);
            customerMarker.setLatLng([pos.coords.latitude, pos.coords.longitude]);
        }
        showToast('Locked onto your live GPS coordinates!');
    }, () => showToast('GPS permission denied. Click on the map or use city preset buttons.', 'warning'));
}
""",

    "static/js/booking.js": """async function selectServiceCategory(catId, catName = '') {
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
""",

    "static/js/ai-chat.js": """function formatSafeMarkdown(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/\\*\\*(.*?)\\*\\*/g, '<strong class="text-warning">$1</strong>')
        .replace(/\\n/g, '<br>');
}

function toggleAIDrawer() {
    document.getElementById('ai-drawer')?.classList.toggle('open');
}

function sendQuickPrompt(text, targetInputId = 'ai-chat-input', targetListId = 'ai-messages-list') {
    const input = document.getElementById(targetInputId);
    if (input) {
        input.value = text;
        sendAIMessage(new Event('submit'), targetInputId, targetListId);
    }
}

async function sendAIMessage(e, inputId = 'ai-chat-input', listId = 'ai-messages-list') {
    if (e && e.preventDefault) e.preventDefault();
    const input = document.getElementById(inputId);
    const list = document.getElementById(listId);
    const text = (input?.value || '').trim();
    if (!text || !list) return;
    input.value = '';

    list.innerHTML += `<div class="msg-bubble msg-user">${formatSafeMarkdown(text)}</div>`;
    const tempId = 'ai-load-' + Date.now();
    list.innerHTML += `<div id="${tempId}" class="msg-bubble msg-assistant text-warning"><span class="spinner-grow spinner-grow-sm me-2"></span>Analyzing vehicle telemetry & live grid...</div>`;
    list.scrollTop = list.scrollHeight;

    try {
        const res = await fetch('/api/ai/chat/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        document.getElementById(tempId)?.remove();

        let btns = '<div class="mt-2 d-flex flex-wrap gap-1">';
        (data.actions || []).forEach(a => {
            if (a.url) {
                btns += `<a href="${a.url}" class="btn btn-sm btn-gridx py-1 px-2" style="font-size:0.74rem;">${a.label}</a>`;
            } else if (a.category_slug) {
                btns += `<a href="/dashboard/?cat=${a.category_slug}#booking-section" class="btn btn-sm btn-gridx-outline py-1 px-2" style="font-size:0.74rem;">${a.label}</a>`;
            }
        });
        btns += '</div>';

        list.innerHTML += `<div class="msg-bubble msg-assistant">${formatSafeMarkdown(data.reply)}${btns}</div>`;
        list.scrollTop = list.scrollHeight;
    } catch (err) {
        document.getElementById(tempId)?.remove();
        list.innerHTML += `<div class="msg-bubble msg-assistant text-danger">Connection interrupted. Turn on hazard lights if stranded.</div>`;
    }
}
""",

    "templates/components/navbar.html": """<nav class="navbar navbar-expand-lg navbar-dark navbar-gridx sticky-top py-2">
    <div class="container">
        <a class="brand-logo" href="{% url 'home' %}">GRID <span>X</span></a>
        <span class="badge bg-dark border border-warning text-warning ms-2 d-none d-md-inline-flex align-items-center gap-1">
            <span class="live-dot"></span> Vijayawada • Guntur Grid
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
                                <i class="bi bi-speedometer2 me-1"></i> Provider Console
                            </a>
                        </li>
                    {% else %}
                        <li class="nav-item">
                            <a class="btn btn-sm btn-gridx" href="{% url 'dashboard' %}">
                                <i class="bi bi-grid-1x2-fill me-1"></i> Customer Grid
                            </a>
                        </li>
                    {% endif %}
                    <li class="nav-item">
                        <a class="btn btn-sm btn-gridx-outline" href="{% url 'ai_assistant' %}">
                            <i class="bi bi-robot me-1"></i> GRIDX AI Studio
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="btn btn-sm btn-outline-light" href="{% url 'logout' %}">
                            <i class="bi bi-box-arrow-right"></i> {{ user.username }}
                        </a>
                    </li>
                {% else %}
                    <li class="nav-item"><a class="btn btn-sm btn-outline-light" href="{% url 'login' %}">Sign In</a></li>
                    <li class="nav-item"><a class="btn btn-sm btn-gridx" href="{% url 'register' %}?role=customer">Request Help</a></li>
                    <li class="nav-item"><a class="btn btn-sm btn-gridx-outline" href="{% url 'register' %}?role=provider">Partner With Us</a></li>
                {% endif %}
            </ul>
        </div>
    </div>
</nav>
""",

    "templates/components/service_cards.html": """<div class="d-flex flex-wrap gap-2 mb-3">
    <button type="button" class="btn btn-sm btn-gridx-outline domain-filter-btn active" onclick="filterCategoryDomain('ALL', this)">
        <i class="bi bi-grid-fill me-1"></i> All Grid Services ({{ categories|length }})
    </button>
    <button type="button" class="btn btn-sm btn-gridx-outline domain-filter-btn" onclick="filterCategoryDomain('OUTDOOR', this)">
        <i class="bi bi-car-front-fill me-1"></i> Outdoor Roadside
    </button>
    <button type="button" class="btn btn-sm btn-gridx-outline domain-filter-btn" onclick="filterCategoryDomain('INDOOR', this)">
        <i class="bi bi-house-gear-fill me-1"></i> Indoor Home Assistance
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
                    <span class="badge {% if cat.domain == 'OUTDOOR' %}badge-domain-outdoor{% else %}badge-domain-indoor{% endif %}" style="font-size:0.62rem;">
                        {{ cat.domain }}
                    </span>
                </div>
                <h6 class="fw-bold mb-1 text-white">{{ cat.name }}</h6>
                <p class="text-secondary small mb-2" style="font-size:0.75rem; line-height:1.35;">{{ cat.description|truncatechars:60 }}</p>
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

    "templates/pages/home.html": """{% extends 'base.html' %}
{% block content %}
<div class="row align-items-center g-4 py-3">
    <div class="col-lg-7">
        <div class="d-inline-flex align-items-center gap-2 px-3 py-1 rounded-pill mb-3" style="background:rgba(255,208,0,0.12); border:1px solid var(--gridx-yellow);">
            <span class="live-dot"></span>
            <span class="small fw-bold text-warning">SMART LIVING • REAL-TIME LOCAL DISPATCH NETWORK</span>
        </div>
        <h1 class="display-4 fw-black mb-2">ONE GRID. <span style="color:var(--gridx-yellow);">EVERY SOLUTION.</span></h1>
        <p class="lead text-secondary mb-4">
            Finding help is easy. Finding the right help quickly is not. GRIDX connects you in real-time with GPS-verified **Roadside Mechanics, Towing, Battery/EV Pros** and **Indoor Home Specialists** across Vijayawada & Guntur.
        </p>
        <div class="d-flex flex-wrap gap-3">
            {% if user.is_authenticated %}
                {% if user.provider_profile %}
                    <a href="{% url 'provider_dashboard' %}" class="btn btn-gridx btn-lg"><i class="bi bi-speedometer2 me-1"></i> Open Provider Console</a>
                {% else %}
                    <a href="{% url 'dashboard' %}" class="btn btn-gridx btn-lg"><i class="bi bi-lightning-charge-fill me-1"></i> Launch Customer Grid</a>
                {% endif %}
            {% else %}
                <a href="{% url 'register' %}?role=customer" class="btn btn-gridx btn-lg"><i class="bi bi-lightning-charge-fill me-1"></i> Request Emergency Help</a>
                <a href="{% url 'register' %}?role=provider" class="btn btn-gridx-outline btn-lg"><i class="bi bi-tools me-1"></i> Join as Service Provider</a>
                <a href="{% url 'login' %}" class="btn btn-outline-light btn-lg">Demo Login</a>
            {% endif %}
        </div>
    </div>
    <div class="col-lg-5">
        <div class="gridx-card-yellow p-4">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="badge bg-dark text-warning px-2 py-1">FROM PROBLEM TO SOLUTION</span>
                <i class="bi bi-broadcast-pin fs-3"></i>
            </div>
            <h4 class="fw-black mb-3">REQUEST → MATCH → CONNECT → SOLVE</h4>
            <div class="row g-2 small fw-bold">
                <div class="col-6"><div class="p-2 rounded bg-dark text-white"><span class="text-warning">01.</span> SELECT SERVICE</div></div>
                <div class="col-6"><div class="p-2 rounded bg-dark text-white"><span class="text-warning">02.</span> DESCRIBE ISSUE</div></div>
                <div class="col-6"><div class="p-2 rounded bg-dark text-white"><span class="text-warning">03.</span> SHARE GPS PIN</div></div>
                <div class="col-6"><div class="p-2 rounded bg-dark text-white"><span class="text-warning">04.</span> PROS ALERTED</div></div>
                <div class="col-6"><div class="p-2 rounded bg-dark text-white"><span class="text-warning">05.</span> LIVE TRACKING</div></div>
                <div class="col-6"><div class="p-2 rounded bg-dark text-white"><span class="text-warning">06.</span> COMPLETE & PAY</div></div>
            </div>
        </div>
    </div>
</div>

<div class="row g-3 my-4">
    <div class="col-md-4">
        <div class="gridx-card p-3 h-100 border-start border-4 border-warning">
            <h6 class="fw-bold text-warning mb-1"><i class="bi bi-cpu-fill me-1"></i> Smart Haversine + Skill Dispatch</h6>
            <p class="small text-secondary mb-0">Matches verified providers by skill compatibility, vehicle type, rating, and live GPS radius with atomic lock protection.</p>
        </div>
    </div>
    <div class="col-md-4">
        <div class="gridx-card p-3 h-100 border-start border-4 border-warning">
            <h6 class="fw-bold text-warning mb-1"><i class="bi bi-receipt-cutoff me-1"></i> Transparent Itemized Pricing</h6>
            <p class="small text-secondary mb-0">Database-driven base fee, per-km distance charge, and emergency surcharges calculated before you book.</p>
        </div>
    </div>
    <div class="col-md-4">
        <div class="gridx-card p-3 h-100 border-start border-4 border-warning">
            <h6 class="fw-bold text-warning mb-1"><i class="bi bi-robot me-1"></i> GRIDX AI Diagnostic Copilot</h6>
            <p class="small text-secondary mb-0">Groq-powered vehicle symptom triage, safety checklists, and context-aware booking status tracking.</p>
        </div>
    </div>
</div>

<h4 class="fw-bold mb-3"><i class="bi bi-grid-1x2-fill text-warning me-2"></i>Explore Indoor & Outdoor Grid Categories</h4>
{% include 'components/service_cards.html' %}
{% endblock %}
""",

    "templates/pages/login.html": """{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center py-4">
    <div class="col-md-6 col-lg-5">
        <div class="gridx-card p-4">
            <div class="text-center mb-3">
                <span class="badge badge-domain-outdoor mb-2">SECURE ROLE-AWARE ACCESS</span>
                <h3 class="fw-black mb-1">SIGN IN TO GRID <span class="text-warning">X</span></h3>
                <p class="small text-secondary">Automatically routes to Customer Grid or Provider Console</p>
            </div>

            <div class="p-3 rounded mb-3" style="background:#0B0E14; border:1px dashed var(--gridx-yellow);">
                <div class="small fw-bold text-warning mb-2"><i class="bi bi-lightning-fill"></i> 1-Click Instant Demo Credentials:</div>
                <div class="d-flex gap-2">
                    <button type="button" class="btn btn-sm btn-gridx flex-grow-1" onclick="fillDemo('demo_customer', 'gridxpassword123')">
                        Fill Demo Customer
                    </button>
                    <button type="button" class="btn btn-sm btn-gridx-outline flex-grow-1" onclick="fillDemo('ravi_mech', 'gridxpassword123')">
                        Fill Demo Provider
                    </button>
                </div>
            </div>

            <form method="post">
                {% csrf_token %}
                {% for field in form %}
                    <div class="mb-3">
                        <label class="form-label small fw-bold text-secondary">{{ field.label }}</label>
                        {{ field }}
                        {% if field.errors %}
                            <div class="text-danger small mt-1">{{ field.errors|striptags }}</div>
                        {% endif %}
                    </div>
                {% endfor %}
                <button type="submit" class="btn btn-gridx w-100 py-2 mt-1">ENTER DISPATCH GRID</button>
            </form>

            <div class="mt-3 text-center small text-secondary">
                New to GRIDX? <a href="{% url 'register' %}?role=customer" class="text-warning fw-bold">Create Customer Account</a> •
                <a href="{% url 'register' %}?role=provider" class="text-warning fw-bold">Register as Provider</a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
{% block scripts %}
<script>
function fillDemo(user, pass) {
    document.getElementById('id_username').value = user;
    document.getElementById('id_password').value = pass;
    showToast(`Filled ${user} credentials. Click ENTER DISPATCH GRID!`);
}
</script>
{% endblock %}
""",

    "templates/pages/register.html": """{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center py-3">
    <div class="col-lg-7">
        <div class="gridx-card p-4">
            <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 gap-2 border-bottom border-secondary pb-3">
                <div>
                    <span class="badge badge-domain-outdoor mb-1">ONBOARDING</span>
                    <h3 class="fw-black mb-0">{% if role == 'provider' %}Service Provider Registration{% else %}Customer Account Setup{% endif %}</h3>
                </div>
                <div class="btn-group">
                    <a href="{% url 'register' %}?role=customer" class="btn btn-sm {% if role != 'provider' %}btn-gridx{% else %}btn-gridx-outline{% endif %}">Customer Mode</a>
                    <a href="{% url 'register' %}?role=provider" class="btn btn-sm {% if role == 'provider' %}btn-gridx{% else %}btn-gridx-outline{% endif %}">Provider Mode</a>
                </div>
            </div>

            <form method="post">
                {% csrf_token %}
                <input type="hidden" name="role" value="{{ role }}">
                <div class="row g-3">
                    {% for field in form %}
                        <div class="{% if field.name == 'skills' %}col-12{% else %}col-md-6{% endif %}">
                            <label class="form-label small fw-bold text-warning">{{ field.label }}</label>
                            {{ field }}
                            {% if field.help_text %}<small class="d-block text-secondary" style="font-size:0.72rem;">{{ field.help_text }}</small>{% endif %}
                            {% if field.errors %}<div class="text-danger small">{{ field.errors|striptags }}</div>{% endif %}
                        </div>
                    {% endfor %}
                </div>
                <button type="submit" class="btn btn-gridx w-100 py-2 mt-4">COMPLETE REGISTRATION & LAUNCH GRID</button>
            </form>
        </div>
    </div>
</div>
{% endblock %}
""",

    "templates/pages/dashboard.html": """{% extends 'base.html' %}
{% block content %}
{% if active_booking %}
<div class="gridx-card-yellow p-3 mb-4 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-2">
    <div class="d-flex align-items-center gap-3">
        <div class="p-2 bg-dark text-warning rounded-3"><i class="bi bi-broadcast fs-4"></i></div>
        <div>
            <div class="small text-uppercase fw-black">LIVE ACTIVE DISPATCH #{{ active_booking.id }}</div>
            <div class="fw-bold">{{ active_booking.category.name }} — Status: <span class="badge bg-dark text-warning">{{ active_booking.get_status_display }}</span>
                {% if active_booking.provider %}• Assigned to <u>{{ active_booking.provider.business_name }}</u>{% endif %}
            </div>
        </div>
    </div>
    <div class="d-flex gap-2">
        <a href="{% url 'tracking' active_booking.id %}" class="btn btn-dark btn-sm fw-bold px-3"><i class="bi bi-geo-alt-fill me-1"></i> Open Live Radar</a>
        <a href="{% url 'booking_detail' active_booking.id %}" class="btn btn-outline-dark btn-sm fw-bold">Invoice / Details</a>
    </div>
</div>
{% endif %}

<div class="row g-4" id="booking-section">
    <div class="col-lg-7">
        <div class="d-flex flex-wrap justify-content-between align-items-center mb-2 gap-2">
            <h5 class="fw-bold mb-0"><span class="text-warning">01.</span> Select Service Category</h5>
            <div class="d-flex gap-1">
                <button type="button" class="btn btn-sm btn-gridx-outline" onclick="setQuickCityPreset(16.5062, 80.6480, 'Benz Circle, Vijayawada')">Vijayawada</button>
                <button type="button" class="btn btn-sm btn-gridx-outline" onclick="setQuickCityPreset(16.3067, 80.4365, 'Arundelpet, Guntur')">Guntur</button>
                <button type="button" class="btn btn-sm btn-gridx" onclick="detectBrowserGeolocation()"><i class="bi bi-crosshair"></i> Live GPS</button>
            </div>
        </div>

        {% include 'components/service_cards.html' %}

        <div class="gridx-card p-3 mt-3">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="fw-bold mb-0"><i class="bi bi-radar text-warning me-1"></i> Real-Time Service Zone Radar (Drag Yellow Pin)</h6>
                <span class="badge bg-dark border border-success text-success">{{ providers|length }} Verified Providers Online</span>
            </div>
            <div id="dashboard-map" class="map-container"></div>
        </div>

        <div class="gridx-card p-3 mt-3">
            <h6 class="fw-bold text-warning mb-2"><i class="bi bi-shield-check me-1"></i> Nearby Verified Professionals on Grid</h6>
            <div class="row g-2">
                {% for p in providers %}
                <div class="col-md-4">
                    <div class="p-2 rounded border border-secondary" style="background:#0B0E14;">
                        <div class="fw-bold small text-white text-truncate">{{ p.business_name }}</div>
                        <div class="d-flex justify-content-between small text-secondary mt-1">
                            <span class="text-warning">★ {{ p.rating_avg }}</span>
                            <span>~{{ p.dist_km }} km ({{ p.eta_mins }}m)</span>
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
                <h5 class="fw-bold mb-0"><span class="text-warning">02.</span> Dispatch Details</h5>
                <span id="selected-cat-badge" class="badge badge-domain-outdoor">{{ categories.0.name }}</span>
            </div>

            <form onsubmit="submitServiceBooking(event)">
                <input type="hidden" id="selected_category_id" value="{{ categories.0.id }}">

                <div class="mb-3">
                    <label class="form-label small fw-bold text-secondary">Select Vehicle or Home Unit</label>
                    <select id="vehicle_id" class="form-select gridx-input">
                        {% for v in vehicles %}
                            <option value="{{ v.id }}">{{ v.make_model }} — {{ v.registration_number }} ({{ v.get_vehicle_type_display }})</option>
                        {% endfor %}
                    </select>
                </div>

                <div class="row g-2 mb-3">
                    <div class="col-6">
                        <label class="form-label small text-secondary">GPS Latitude</label>
                        <input type="text" id="customer_lat" class="form-control form-control-sm" value="16.5062" readonly>
                    </div>
                    <div class="col-6">
                        <label class="form-label small text-secondary">GPS Longitude</label>
                        <input type="text" id="customer_lng" class="form-control form-control-sm" value="80.6480" readonly>
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-secondary">Exact Location / Landmark</label>
                    <input type="text" id="customer_address" class="form-control gridx-input" value="Benz Circle, NH-16, Vijayawada" required>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-secondary">Describe Symptoms / Problem</label>
                    <textarea id="issue_description" class="form-control gridx-input" rows="2" placeholder="e.g. Bike stopped suddenly, battery clicking sound, or pipe leak..." required></textarea>
                </div>

                <div class="mb-3">
                    <label class="form-label small text-secondary">Optional Issue Photo</label>
                    <input type="file" id="issue_photo" class="form-control form-control-sm" accept="image/*">
                </div>

                <div class="form-check form-switch mb-3 p-2 rounded ps-5" style="background:rgba(255,208,0,0.08); border:1px solid var(--border-grid);">
                    <input class="form-check-input" type="checkbox" id="is_emergency" checked onchange="refreshPriceEstimate()">
                    <label class="form-check-label small fw-bold text-warning" for="is_emergency">
                        HIGH URGENCY / EMERGENCY DISPATCH MODE
                    </label>
                </div>

                <div class="p-3 rounded mb-3" style="background:#080A0F; border:1px solid var(--border-grid);">
                    <div class="small fw-bold text-uppercase text-warning mb-2"><i class="bi bi-calculator"></i> Transparent Price Estimate</div>
                    <div id="estimate-breakdown">Calculating...</div>
                </div>

                <button type="submit" id="submit-booking-btn" class="btn btn-gridx w-100 py-2 fs-6">
                    <i class="bi bi-broadcast-pin me-1"></i> BROADCAST REQUEST NOW
                </button>
            </form>
        </div>

        <div class="gridx-card p-3 mt-3">
            <h6 class="fw-bold mb-2"><i class="bi bi-car-front text-warning me-1"></i> Manage Your Garage / Premises</h6>
            <form method="post" action="{% url 'add_vehicle' %}" class="row g-2 mb-2">
                {% csrf_token %}
                <div class="col-4">
                    <select name="vehicle_type" class="form-select form-select-sm">
                        <option value="CAR">Car</option>
                        <option value="BIKE">Bike</option>
                        <option value="SUV">SUV</option>
                        <option value="EV">EV</option>
                        <option value="HOME">Home</option>
                    </select>
                </div>
                <div class="col-4"><input type="text" name="make_model" class="form-control form-control-sm" placeholder="Make/Model" required></div>
                <div class="col-4"><input type="text" name="registration_number" class="form-control form-control-sm" placeholder="AP 16 ..." required></div>
                <div class="col-12"><button class="btn btn-sm btn-gridx-outline w-100">+ Add Vehicle / Home Unit</button></div>
            </form>
        </div>
    </div>
</div>

<div class="gridx-card p-4 mt-4">
    <h5 class="fw-bold mb-3"><i class="bi bi-clock-history text-warning me-2"></i>Your Dispatch & Service History</h5>
    <div class="table-responsive">
        <table class="table table-dark table-hover align-middle mb-0">
            <thead>
                <tr class="text-secondary small">
                    <th>ID</th><th>Category</th><th>Vehicle / Unit</th><th>Assigned Pro</th><th>Status</th><th>Est. Total</th><th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for b in bookings %}
                <tr>
                    <td class="fw-bold">#{{ b.id }}</td>
                    <td>{{ b.category.name }}</td>
                    <td class="small text-secondary">{{ b.vehicle.make_model|default:"Standard" }}</td>
                    <td>{{ b.provider.business_name|default:"Broadcasting..." }}</td>
                    <td><span class="badge bg-warning text-dark">{{ b.get_status_display }}</span></td>
                    <td class="text-warning fw-bold">₹{{ b.estimated_total }}</td>
                    <td>
                        <a href="{% url 'tracking' b.id %}" class="btn btn-sm btn-gridx py-1">Live Radar</a>
                        <a href="{% url 'booking_detail' b.id %}" class="btn btn-sm btn-outline-light py-1">Invoice</a>
                    </td>
                </tr>
                {% empty %}
                <tr><td colspan="7" class="text-center text-secondary py-3">No service requests yet. Select a category above to dispatch!</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
document.addEventListener('DOMContentLoaded', () => {
    const providers = [
        {% for p in providers %}
            { lat: {{ p.current_lat }}, lng: {{ p.current_lng }}, name: "{{ p.business_name|escapejs }}", rating: "{{ p.rating_avg }}" },
        {% endfor %}
    ];
    initCustomerDashboardMap(16.5062, 80.6480, providers);

    // Preselect category if ?cat=slug is present from AI Assistant
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

    "templates/pages/provider_dashboard.html": """{% extends 'base.html' %}
{% block content %}
<div class="row g-3 mb-4">
    <div class="col-md-4">
        <div class="gridx-card-yellow p-4 h-100 d-flex justify-content-between align-items-center">
            <div>
                <div class="small text-uppercase fw-black">TODAY'S / TOTAL EARNINGS</div>
                <div class="display-5 fw-black">₹{{ provider.total_earnings }}</div>
                <div class="small fw-bold">Completed Dispatches: {{ provider.completed_jobs_count }}</div>
            </div>
            <i class="bi bi-wallet2 display-4"></i>
        </div>
    </div>
    <div class="col-md-4">
        <div class="gridx-card p-4 h-100 d-flex flex-column justify-content-between">
            <div>
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="badge bg-success">VERIFIED PARTNER</span>
                    <span class="text-warning fw-bold">★ {{ provider.rating_avg }}</span>
                </div>
                <h5 class="fw-bold mb-1">{{ provider.business_name }}</h5>
                <p class="small text-secondary mb-2">Supported: {{ provider.supported_vehicles }} • Radius: {{ provider.service_radius_km }} km</p>
            </div>
            <button class="btn btn-sm {% if provider.is_available %}btn-success{% else %}btn-secondary{% endif %} w-100 fw-bold"
                    onclick="toggleProviderOnline({{ provider.is_available|yesno:'false,true' }})">
                <i class="bi bi-power me-1"></i> {% if provider.is_available %}ONLINE — RECEIVING BROADCASTS{% else %}OFFLINE — CLICK TO GO ONLINE{% endif %}
            </button>
        </div>
    </div>
    <div class="col-md-4">
        <div class="gridx-card p-4 h-100 d-flex flex-column justify-content-between">
            <div>
                <h6 class="fw-bold text-warning mb-1"><i class="bi bi-geo-alt-fill"></i> Live Telemetry Position</h6>
                <p class="small text-secondary mb-2">GPS: {{ provider.current_lat }}, {{ provider.current_lng }}</p>
            </div>
            <div class="d-flex gap-2">
                <button class="btn btn-sm btn-gridx-outline flex-grow-1" onclick="pushProviderGPS()"><i class="bi bi-crosshair"></i> Sync Browser GPS</button>
                <button class="btn btn-sm btn-gridx flex-grow-1" onclick="window.location.reload()"><i class="bi bi-arrow-clockwise"></i> Refresh Grid</button>
            </div>
        </div>
    </div>
</div>

<div class="row g-4">
    <div class="col-lg-6">
        <div class="gridx-card p-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="fw-bold text-warning mb-0"><i class="bi bi-broadcast-pin me-1"></i> Incoming Nearby Requests</h5>
                <span class="badge bg-dark border border-warning text-warning">{{ incoming_requests|length }} Active</span>
            </div>

            {% for item in incoming_requests %}
            <div class="p-3 rounded-3 mb-3" style="background:#0B0E15; border:2px solid var(--gridx-yellow);">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="badge bg-warning text-dark fw-black">
                        {% if item.booking.is_emergency %}⚡ HIGH URGENCY{% else %}STANDARD{% endif %}
                    </span>
                    <span class="small text-warning fw-bold">
                        DISTANCE: {{ item.distance_km }} km (~{{ item.eta_mins }} min) • EST. PRICE: {{ item.price_range }}
                    </span>
                </div>
                <h5 class="fw-bold mb-1">#{{ item.booking.id }} — {{ item.booking.category.name }}</h5>
                <p class="text-white mb-1">"{{ item.booking.issue_description }}"</p>
                <p class="small text-secondary mb-3">
                    <i class="bi bi-geo-alt text-warning"></i> {{ item.booking.customer_address }}
                    {% if item.booking.vehicle %} • <i class="bi bi-car-front text-warning ms-1"></i> {{ item.booking.vehicle.make_model }}{% endif %}
                </p>
                <div class="d-flex gap-2">
                    <button class="btn btn-gridx flex-grow-1" onclick="performBookingAction({{ item.booking.id }}, 'accept')">
                        <i class="bi bi-check2-circle me-1"></i> ACCEPT & NAVIGATE
                    </button>
                    <button class="btn btn-outline-secondary px-3" onclick="performBookingAction({{ item.booking.id }}, 'reject')">
                        DECLINE
                    </button>
                </div>
            </div>
            {% empty %}
            <div class="text-center py-4 text-secondary">
                <i class="bi bi-radar fs-1 d-block mb-2 text-warning"></i>
                No unassigned requests in your {{ provider.service_radius_km }} km radius right now.
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="col-lg-6">
        <div class="gridx-card p-4">
            <h5 class="fw-bold mb-3"><i class="bi bi-tools text-warning me-1"></i> Active & Assigned Dispatches</h5>
            {% for job in assigned_bookings %}
            <div class="p-3 rounded-3 mb-3 border {% if job.status != 'completed' %}border-warning{% else %}border-secondary{% endif %}" style="background:#0B0E15;">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <strong>#{{ job.id }} — {{ job.category.name }}</strong>
                    <span class="badge {% if job.status == 'completed' %}bg-success{% else %}bg-warning text-dark{% endif %}">{{ job.get_status_display }}</span>
                </div>
                <p class="small text-secondary mb-2">{{ job.customer_address }} • Customer: {{ job.customer.username }} • Est: <strong class="text-warning">₹{{ job.estimated_total }}</strong></p>

                <div class="d-flex flex-wrap gap-2 mt-2">
                    {% if job.status == 'accepted' %}
                        <button class="btn btn-sm btn-gridx" onclick="performBookingAction({{ job.id }}, 'en_route')">1. Mark En Route</button>
                    {% elif job.status == 'en_route' %}
                        <button class="btn btn-sm btn-gridx" onclick="performBookingAction({{ job.id }}, 'arrived')">2. Mark Arrived</button>
                    {% elif job.status == 'arrived' %}
                        <button class="btn btn-sm btn-gridx" onclick="performBookingAction({{ job.id }}, 'in_progress')">3. Start Service</button>
                    {% elif job.status == 'in_progress' %}
                        <button class="btn btn-sm btn-success fw-bold" onclick="performBookingAction({{ job.id }}, 'completed')">4. Complete & Issue Invoice</button>
                    {% endif %}
                    {% if job.status in 'accepted,en_route' %}
                        <button class="btn btn-sm btn-gridx-outline" onclick="performBookingAction({{ job.id }}, 'simulate_step')">
                            <i class="bi bi-cursor-fill"></i> Simulate Drive Step
                        </button>
                    {% endif %}
                    <a href="{% url 'tracking' job.id %}" class="btn btn-sm btn-outline-light">Live Radar</a>
                    <a href="{% url 'booking_detail' job.id %}" class="btn btn-sm btn-outline-warning">Invoice</a>
                </div>
            </div>
            {% empty %}
            <p class="text-secondary small mb-0">Accept an incoming broadcast request on the left to start navigating.</p>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
{% block scripts %}
<script>
async function toggleProviderOnline(state) {
    await fetch('/api/provider/status/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ is_available: state })
    });
    window.location.reload();
}
function pushProviderGPS() {
    if (!navigator.geolocation) return showToast('Geolocation unsupported', 'warning');
    navigator.geolocation.getCurrentPosition(async pos => {
        await fetch('/api/provider/status/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude })
        });
        showToast('Live GPS position updated!');
        setTimeout(() => window.location.reload(), 700);
    }, () => showToast('GPS permission denied.', 'warning'));
}
</script>
{% endblock %}
""",

    "templates/pages/tracking.html": """{% extends 'base.html' %}
{% block content %}
<div class="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
    <div>
        <span class="badge bg-warning text-dark fw-black me-2">LIVE TELEMETRY #{{ booking.id }}</span>
        <h4 class="fw-black d-inline mb-0">{{ booking.category.name }}</h4>
    </div>
    <div class="d-flex flex-wrap gap-2">
        {% if booking.provider and booking.status in 'accepted,en_route' %}
            <button class="btn btn-sm btn-gridx" onclick="performBookingAction({{ booking.id }}, 'simulate_step')">
                <i class="bi bi-cursor-fill me-1"></i> Simulate Provider Moving Closer
            </button>
        {% endif %}
        <button class="btn btn-sm btn-gridx-outline" onclick="recenterRadar()"><i class="bi bi-arrows-fullscreen"></i> Recenter</button>
        <a href="{% url 'booking_detail' booking.id %}" class="btn btn-sm btn-outline-light">Invoice & Review</a>
    </div>
</div>

<div class="stepper-wrapper mb-4">
    {% for key, label, icon in steps %}
        <div class="stepper-item {% if forloop.counter0 < current_idx %}completed{% elif forloop.counter0 == current_idx %}active{% endif %}" data-step="{{ key }}">
            <i class="bi {{ icon }} d-block fs-5 mb-1"></i>
            <div style="font-size:0.72rem;">{{ label }}</div>
        </div>
    {% endfor %}
</div>

<div class="row g-4">
    <div class="col-lg-8">
        <div class="gridx-card p-3">
            <div id="tracking-map" class="map-container" style="height:430px;"></div>
            <div class="d-flex flex-wrap justify-content-between align-items-center mt-2 small text-secondary">
                <span id="tracking-eta-banner"><span class="live-dot me-2"></span>Connecting to GRIDX GPS Telemetry...</span>
                <span id="tracking-timestamp"></span>
            </div>
        </div>
    </div>

    <div class="col-lg-4">
        <div class="gridx-card p-4 mb-3 border-top border-3 border-warning">
            <div class="small text-warning fw-bold text-uppercase">Current Dispatch State</div>
            <h3 id="live-status-label" class="fw-black mb-2">{{ booking.get_status_display }}</h3>
            <p class="small text-secondary mb-3"><i class="bi bi-geo-alt text-warning"></i> {{ booking.customer_address }}</p>

            {% if is_assigned_provider %}
                <div class="d-grid gap-2 mb-3">
                    {% if booking.status == 'accepted' %}
                        <button class="btn btn-gridx" onclick="performBookingAction({{ booking.id }}, 'en_route')">Mark En Route</button>
                    {% elif booking.status == 'en_route' %}
                        <button class="btn btn-gridx" onclick="performBookingAction({{ booking.id }}, 'arrived')">Mark Arrived at Customer</button>
                    {% elif booking.status == 'arrived' %}
                        <button class="btn btn-gridx" onclick="performBookingAction({{ booking.id }}, 'in_progress')">Start Repair Work</button>
                    {% elif booking.status == 'in_progress' %}
                        <button class="btn btn-success fw-bold" onclick="performBookingAction({{ booking.id }}, 'completed')">Complete Job & Generate Invoice</button>
                    {% endif %}
                </div>
            {% endif %}

            {% if booking.status in 'requested,searching,no_provider' and is_owner %}
                <div class="alert alert-dark border-warning small py-2">
                    Tip: Open an Incognito window and log in as <code>ravi_mech</code> / <code>gridxpassword123</code> to accept this broadcast!
                </div>
                <div class="d-grid gap-2">
                    <button class="btn btn-sm btn-gridx" onclick="performBookingAction({{ booking.id }}, 'expand_radius')">
                        <i class="bi bi-arrows-angle-expand"></i> Emergency Radius Expansion (35 km)
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="performBookingAction({{ booking.id }}, 'cancel')">
                        Cancel Service Request
                    </button>
                </div>
            {% endif %}
        </div>

        <div class="gridx-card p-4">
            <h6 class="fw-bold text-warning mb-3"><i class="bi bi-activity me-1"></i> Audit Timeline</h6>
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
const custLat = {{ booking.customer_lat }};
const custLng = {{ booking.customer_lng }};
const tMap = L.map('tracking-map').setView([custLat, custLng], 14);

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO'
}).addTo(tMap);

const cMarker = L.marker([custLat, custLng], {
    icon: createCustomIcon('#FFD000', 'bi-person-standing')
}).addTo(tMap).bindPopup('<b>Customer Breakdown Pin</b>').openPopup();

let pMarker = null;
let routeLine = null;

async function drawRoadRoute(lat1, lng1, lat2, lng2) {
    try {
        const res = await fetch(`https://router.project-osrm.org/route/v1/driving/${lng1},${lat1};${lng2},${lat2}?overview=full&geometries=geojson`);
        if (res.ok) {
            const data = await res.json();
            if (data.routes && data.routes.length > 0) {
                const coords = data.routes[0].geometry.coordinates.map(c => [c[1], c[0]]);
                if (routeLine) tMap.removeLayer(routeLine);
                routeLine = L.polyline(coords, { color: '#FFD000', weight: 4, opacity: 0.9 }).addTo(tMap);
                return;
            }
        }
    } catch (e) {}
    if (routeLine) tMap.removeLayer(routeLine);
    routeLine = L.polyline([[lat1, lng1], [lat2, lng2]], { color: '#FFD000', weight: 3, dashArray: '6, 8' }).addTo(tMap);
}

async function pollTracking() {
    try {
        const res = await fetch('/api/bookings/{{ booking.id }}/tracking/');
        if (!res.ok) return;
        const d = await res.json();
        document.getElementById('live-status-label').textContent = d.status_display;
        document.getElementById('tracking-timestamp').textContent = d.last_updated ? 'Telemetry synced: ' + new Date(d.last_updated).toLocaleTimeString() : 'Waiting for assignment';

        if (d.provider_location) {
            const pLat = d.provider_location.lat;
            const pLng = d.provider_location.lng;
            if (!pMarker) {
                pMarker = L.marker([pLat, pLng], {
                    icon: createCustomIcon('#00E676', 'bi-truck-front-fill')
                }).addTo(tMap).bindPopup(`<b>${d.provider_location.name}</b><br>Phone: ${d.provider_location.phone}`);
            } else {
                pMarker.setLatLng([pLat, pLng]);
            }
            await drawRoadRoute(pLat, pLng, custLat, custLng);
            document.getElementById('tracking-eta-banner').innerHTML = `<span class="live-dot me-2"></span><strong class="text-warning">${d.provider_location.name}</strong> (★ ${d.provider_location.rating}) • <strong>${d.distance_km} km</strong> away • Est. ETA: <strong>~${d.eta_mins} mins</strong>`;
        } else {
            document.getElementById('tracking-eta-banner').innerHTML = `<span class="live-dot me-2"></span>Broadcasting to verified providers in Vijayawada-Guntur Grid...`;
        }
    } catch (e) {}
}

function recenterRadar() {
    tMap.setView([custLat, custLng], 14);
}

pollTracking();
setInterval(pollTracking, 5000);
</script>
{% endblock %}
""",

    "templates/pages/booking_detail.html": """{% extends 'base.html' %}
{% block content %}
<div class="row g-4">
    <div class="col-lg-7">
        <div class="gridx-card p-4">
            <div class="d-flex justify-content-between align-items-center mb-3 border-bottom border-secondary pb-3">
                <div>
                    <span class="badge badge-domain-outdoor mb-1">DISPATCH RECORD #{{ booking.id }}</span>
                    <h4 class="fw-black mb-0">{{ booking.category.name }}</h4>
                </div>
                <span class="badge bg-warning text-dark fs-6">{{ booking.get_status_display }}</span>
            </div>

            <div class="row g-3 small mb-3">
                <div class="col-sm-6">
                    <div class="text-secondary">Customer</div>
                    <div class="fw-bold text-white">{{ booking.customer.username }}</div>
                </div>
                <div class="col-sm-6">
                    <div class="text-secondary">Assigned Provider</div>
                    <div class="fw-bold text-warning">{{ booking.provider.business_name|default:"Pending Assignment" }}</div>
                </div>
                <div class="col-sm-6">
                    <div class="text-secondary">Service Location</div>
                    <div class="fw-bold text-white">{{ booking.customer_address }}</div>
                </div>
                <div class="col-sm-6">
                    <div class="text-secondary">Vehicle / Unit</div>
                    <div class="fw-bold text-white">{{ booking.vehicle|default:"Standard Unit" }}</div>
                </div>
            </div>

            <div class="p-3 rounded mb-3" style="background:#0B0E14;">
                <div class="small text-secondary mb-1">Reported Problem Description:</div>
                <div class="text-white">"{{ booking.issue_description }}"</div>
                {% if booking.issue_photo %}
                    <div class="mt-2"><img src="{{ booking.issue_photo.url }}" class="img-fluid rounded border border-warning" style="max-height:180px;"></div>
                {% endif %}
            </div>

            <h6 class="fw-bold text-warning mb-2">Itemized Pricing Breakdown</h6>
            <ul class="list-group list-group-flush mb-3">
                <li class="list-group-item bg-transparent text-light d-flex justify-content-between"><span>Base Service Charge</span><span>₹{{ booking.estimated_base }}</span></li>
                <li class="list-group-item bg-transparent text-light d-flex justify-content-between"><span>Distance Fee ({{ booking.distance_km }} km)</span><span>₹{{ booking.estimated_distance_cost }}</span></li>
                <li class="list-group-item bg-transparent text-light d-flex justify-content-between"><span>Emergency Priority Surcharge</span><span>₹{{ booking.estimated_surcharge }}</span></li>
                <li class="list-group-item bg-transparent text-light d-flex justify-content-between"><span>Platform Fee & GST (18%)</span><span>₹{{ booking.estimated_tax }}</span></li>
                <li class="list-group-item bg-transparent text-warning fw-black fs-5 d-flex justify-content-between"><span>Total Estimate</span><span>₹{{ booking.estimated_total }}</span></li>
            </ul>

            <a href="{% url 'tracking' booking.id %}" class="btn btn-gridx"><i class="bi bi-radar me-1"></i> Open Live Radar Map</a>
        </div>
    </div>

    <div class="col-lg-5">
        {% if booking.invoice %}
        <div class="gridx-card p-4 mb-3 border border-2 border-warning">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h5 class="fw-black text-warning mb-0">INVOICE #INV-{{ booking.invoice.id }}</h5>
                <span class="badge {% if booking.invoice.payment_status == 'PAID' %}bg-success{% else %}bg-warning text-dark{% endif %}">
                    {{ booking.invoice.payment_status }}
                </span>
            </div>
            <div class="display-6 fw-black text-white mb-2">₹{{ booking.invoice.final_amount }}</div>
            <div class="small text-secondary mb-3">
                Provider Payout (90%): ₹{{ booking.invoice.provider_payout }} • Grid Commission (10%): ₹{{ booking.invoice.platform_commission }}
            </div>

            {% if booking.invoice.payment_status != 'PAID' %}
                <div class="d-grid gap-2">
                    <button class="btn btn-gridx" onclick="performBookingAction({{ booking.id }}, 'confirm_payment', {payment_method: 'CASH'})">
                        <i class="bi bi-cash-coin me-1"></i> Confirm Cash Payment Received
                    </button>
                    <button class="btn btn-gridx-outline" onclick="performBookingAction({{ booking.id }}, 'confirm_payment', {payment_method: 'OFFLINE_UPI'})">
                        <i class="bi bi-qr-code-scan me-1"></i> Record Direct Offline UPI Settlement
                    </button>
                </div>
            {% else %}
                <div class="alert alert-success py-2 small mb-0">
                    <i class="bi bi-patch-check-fill me-1"></i> Settled via {{ booking.invoice.payment_method }} on {{ booking.invoice.paid_at|date:"d M Y, H:i" }}
                </div>
            {% endif %}
        </div>
        {% else %}
        <div class="gridx-card p-4 mb-3 text-secondary small">
            <i class="bi bi-receipt fs-3 text-warning d-block mb-2"></i>
            Final invoice will be generated automatically once the assigned provider marks the service as <b>Completed</b>.
        </div>
        {% endif %}

        {% if booking.status == 'completed' and is_owner %}
        <div class="gridx-card p-4">
            <h5 class="fw-bold text-warning mb-2"><i class="bi bi-star-fill me-1"></i> Rate Your Service Provider</h5>
            <div class="mb-2">
                <label class="small text-secondary">Select Rating</label>
                <select id="review-rating" class="form-select gridx-input">
                    <option value="5">★★★★★ (5/5 - Outstanding Fast Response)</option>
                    <option value="4">★★★★☆ (4/5 - Good Professional Service)</option>
                    <option value="3">★★★☆☆ (3/5 - Satisfactory)</option>
                    <option value="2">★★☆☆☆ (2/5 - Delayed)</option>
                    <option value="1">★☆☆☆☆ (1/5 - Poor)</option>
                </select>
            </div>
            <div class="mb-3">
                <label class="small text-secondary">Review Comment</label>
                <textarea id="review-comment" class="form-control gridx-input" rows="2" placeholder="How was the mechanic's arrival time and repair quality?">{{ booking.review.comment }}</textarea>
            </div>
            <button class="btn btn-gridx w-100"
                    onclick="performBookingAction({{ booking.id }}, 'submit_review', {rating: document.getElementById('review-rating').value, comment: document.getElementById('review-comment').value})">
                Submit Verified Review
            </button>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}
""",

    "templates/pages/ai_assistant.html": """{% extends 'base.html' %}
{% block content %}
<div class="row g-4">
    <div class="col-lg-4">
        <div class="gridx-card p-4 h-100">
            <span class="badge badge-domain-outdoor mb-2">GROQ AI DIAGNOSTIC ENGINE</span>
            <h4 class="fw-black text-warning mb-2"><i class="bi bi-robot me-1"></i> GRIDX AI STUDIO</h4>
            <p class="small text-secondary mb-3">
                Preliminary vehicle & home emergency triage connected directly to live Vijayawada-Guntur pricing rules and your active dispatch telemetry.
            </p>
            <h6 class="small fw-bold text-uppercase text-white mb-2">One-Click Diagnostic Prompts</h6>
            <div class="d-grid gap-2">
                <button class="btn btn-sm btn-gridx-outline text-start" onclick="sendQuickPrompt('My bike stopped suddenly on the highway. What should I do?', 'studio-input', 'studio-messages')">
                    🚲 "My bike stopped suddenly. What should I do?"
                </button>
                <button class="btn btn-sm btn-gridx-outline text-start" onclick="sendQuickPrompt('My car battery is dead and clicks when turning the key.', 'studio-input', 'studio-messages')">
                    🔋 "My car battery is dead and clicks."
                </button>
                <button class="btn btn-sm btn-gridx-outline text-start" onclick="sendQuickPrompt('What might a flat tyre repair cost?', 'studio-input', 'studio-messages')">
                    🛞 "What might a flat tyre repair cost?"
                </button>
                <button class="btn btn-sm btn-gridx-outline text-start" onclick="sendQuickPrompt('Explain my current booking status and provider ETA.', 'studio-input', 'studio-messages')">
                    📍 "Explain my current booking status & ETA."
                </button>
                <button class="btn btn-sm btn-gridx-outline text-start" onclick="sendQuickPrompt('Our home main MCB keeps tripping repeatedly.', 'studio-input', 'studio-messages')">
                    ⚡ "Home main MCB keeps tripping."
                </button>
            </div>
        </div>
    </div>

    <div class="col-lg-8">
        <div class="gridx-card d-flex flex-column" style="height: 540px;">
            <div class="p-3 border-bottom border-secondary d-flex justify-content-between align-items-center">
                <div>
                    <span class="live-dot me-2"></span>
                    <strong class="text-warning">LIVE CONVERSATION</strong>
                    <small class="text-secondary ms-2">Safety-First Preliminary Guidance</small>
                </div>
                <a href="{% url 'dashboard' %}" class="btn btn-sm btn-gridx">Go to Booking Grid</a>
            </div>

            <div id="studio-messages" class="ai-messages flex-grow-1">
                <div class="msg-bubble msg-assistant">
                    ⚡ <strong class="text-warning">GRIDX AI Online.</strong> Share your vehicle symptoms, ask for live price estimates, or check your active mechanic's status.
                </div>
                {% for m in messages_history %}
                    <div class="msg-bubble {% if m.role == 'user' %}msg-user{% else %}msg-assistant{% endif %}">
                        {{ m.content|linebreaksbr }}
                    </div>
                {% endfor %}
            </div>

            <form onsubmit="sendAIMessage(event, 'studio-input', 'studio-messages')" class="p-3 border-top border-secondary d-flex gap-2">
                <input id="studio-input" type="text" class="form-control gridx-input" placeholder="Describe your vehicle breakdown or home emergency...">
                <button type="submit" class="btn btn-gridx px-4"><i class="bi bi-send-fill"></i> Send</button>
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

# Re-package the updated zip in parent directory
zip_path = PROJECT_ROOT.parent / "gridx_project_refined.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for fp in PROJECT_ROOT.rglob("*"):
        if fp.is_file() and "venv" not in fp.parts and "__pycache__" not in fp.parts and fp.name != "db.sqlite3":
            zf.write(fp, fp.relative_to(PROJECT_ROOT.parent))

print(f"\n[SUCCESS] Upgraded GRIDX v2.0 in: {PROJECT_ROOT.resolve()}")
print(f"[SUCCESS] Updated clean ZIP archive at: {zip_path.resolve()}")
