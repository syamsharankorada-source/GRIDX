from django.db import models
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
