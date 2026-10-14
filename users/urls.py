from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('vehicles/add/', views.add_vehicle_view, name='add_vehicle'),
    path('vehicles/<int:vehicle_id>/delete/', views.delete_vehicle_view, name='delete_vehicle'),
]
