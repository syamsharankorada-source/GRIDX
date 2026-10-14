from rest_framework import serializers
from .models import ServiceCategory, Booking, BookingStatusHistory
from users.models import ProviderProfile

class ServiceCategorySerializer(serializers.ModelSerializer):
    base_price = serializers.SerializerMethodField()
    class Meta:
        model = ServiceCategory
        fields = ['id', 'slug', 'name', 'domain', 'icon', 'description', 'base_price']
    def get_base_price(self, obj):
        return str(obj.pricing_rule.base_charge) if hasattr(obj, 'pricing_rule') else "250.00"

class ProviderPublicSerializer(serializers.ModelSerializer):
    skills = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    class Meta:
        model = ProviderProfile
        fields = ['id', 'business_name', 'phone', 'is_verified', 'is_available', 'service_radius_km', 'supported_vehicles', 'current_lat', 'current_lng', 'rating_avg', 'completed_jobs_count', 'skills', 'last_location_update']

class BookingStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingStatusHistory
        fields = ['from_status', 'to_status', 'note', 'timestamp']

class BookingSerializer(serializers.ModelSerializer):
    category_detail = ServiceCategorySerializer(source='category', read_only=True)
    provider_detail = ProviderPublicSerializer(source='provider', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    status_history = BookingStatusHistorySerializer(many=True, read_only=True)
    class Meta:
        model = Booking
        fields = '__all__'
