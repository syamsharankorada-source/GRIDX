from django.urls import path
from . import views

urlpatterns = [
    path('api/map-tiles/<int:z>/<int:x>/<int:y>.png', views.map_tile_proxy, name='map_tile_proxy'),
    path('', views.home_view, name='home'),
    path('dashboard/', views.customer_dashboard_view, name='dashboard'),
    path('provider/', views.provider_dashboard_view, name='provider_dashboard'),
    path('bookings/<int:booking_id>/', views.booking_detail_view, name='booking_detail'),
    path('bookings/<int:booking_id>/tracking/', views.tracking_view, name='tracking'),
    path('ai-assistant/', views.ai_assistant_page_view, name='ai_assistant'),

    path('api/catalog/', views.ServiceCatalogAPIView.as_view(), name='api_catalog'),
    path('api/pricing/estimate/', views.PriceEstimateAPIView.as_view(), name='api_price_estimate'),
    path('api/bookings/', views.BookingListCreateAPIView.as_view(), name='api_bookings'),
    path('api/bookings/<int:booking_id>/action/', views.BookingActionAPIView.as_view(), name='api_booking_action'),
    path('api/bookings/<int:booking_id>/tracking/', views.LiveTrackingAPIView.as_view(), name='api_live_tracking'),
    path('api/provider/status/', views.ProviderLocationUpdateAPIView.as_view(), name='api_provider_status'),
    path('api/ai/chat/', views.AIAssistantAPIView.as_view(), name='api_ai_chat'),
]
