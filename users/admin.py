from django.contrib import admin
from .models import CustomerProfile, ProviderProfile, Vehicle
admin.site.register(CustomerProfile)
admin.site.register(ProviderProfile)
admin.site.register(Vehicle)
