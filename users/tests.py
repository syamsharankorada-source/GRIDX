from django.test import TestCase
from django.contrib.auth.models import User
from .models import CustomerProfile, Vehicle

class UserAuthTests(TestCase):
    def test_customer_and_vehicle(self):
        u = User.objects.create_user(username='c1', password='pw123456')
        CustomerProfile.objects.create(user=u, phone='9000000001')
        Vehicle.objects.create(owner=u, vehicle_type='CAR', make_model='Swift', registration_number='AP16AA1111')
        self.assertEqual(u.vehicles.count(), 1)
