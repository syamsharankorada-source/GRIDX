from django.contrib import admin
from .models import ServiceCategory, PricingRule, Booking, BookingStatusHistory, ProviderLocation, Invoice, Review, Notification
admin.site.register(ServiceCategory)
admin.site.register(PricingRule)
admin.site.register(Booking)
admin.site.register(BookingStatusHistory)
admin.site.register(ProviderLocation)
admin.site.register(Invoice)
admin.site.register(Review)
admin.site.register(Notification)
