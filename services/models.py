from decimal import Decimal
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
