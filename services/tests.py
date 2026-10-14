from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from users.models import CustomerProfile, ProviderProfile, Vehicle
from .models import ServiceCategory, PricingRule, Booking
from .dispatch import accept_booking_atomic, find_ranked_eligible_providers
from .pricing import calculate_itemized_estimate

class GridXSystemTests(TestCase):
    def setUp(self):
        self.cat = ServiceCategory.objects.create(slug='battery-ev', name='Battery & EV Assistance', domain='OUTDOOR')
        PricingRule.objects.create(category=self.cat, base_charge=Decimal('220.00'), per_km_charge=Decimal('20.00'), emergency_surcharge=Decimal('100.00'))
        self.cust = User.objects.create_user(username='syam', password='pw123456')
        CustomerProfile.objects.create(user=self.cust, phone='9999999991')
        self.veh = Vehicle.objects.create(owner=self.cust, vehicle_type='CAR', make_model='Nexon EV', registration_number='AP16EV2026')
        self.other = User.objects.create_user(username='other', password='pw123456')

        self.p1_user = User.objects.create_user(username='p1', password='pw123456')
        self.p1 = ProviderProfile.objects.create(user=self.p1_user, phone='8888888881', business_name='Vijayawada Pro', is_verified=True, is_available=True, current_lat=16.51, current_lng=80.645)
        self.p1.skills.add(self.cat)

        self.p2_user = User.objects.create_user(username='p2', password='pw123456')
        self.p2 = ProviderProfile.objects.create(user=self.p2_user, phone='8888888882', business_name='Guntur Pro', is_verified=True, is_available=True, current_lat=16.512, current_lng=80.649)
        self.p2.skills.add(self.cat)

    def test_pricing_and_atomic_dispatch(self):
        est = calculate_itemized_estimate(self.cat, distance_km=4.0, is_emergency=True)
        self.assertEqual(est['base_charge'], '220.00')
        b = Booking.objects.create(customer=self.cust, vehicle=self.veh, category=self.cat, issue_description='Dead battery', customer_lat=16.5062, customer_lng=80.6480, estimated_total=Decimal('500.00'))
        self.assertEqual(len(find_ranked_eligible_providers(b)), 2)
        accept_booking_atomic(b.id, self.p1)
        with self.assertRaises(ValueError):
            accept_booking_atomic(b.id, self.p2)

    def test_isolation_and_ai(self):
        c = APIClient()
        c.force_authenticate(user=self.cust)
        res = c.post('/api/bookings/', {'category_id': self.cat.id, 'vehicle_id': self.veh.id, 'issue_description': 'Engine wont crank', 'customer_lat': 16.5062, 'customer_lng': 80.6480})
        self.assertEqual(res.status_code, 201)
        b_id = res.data['booking']['id']

        c2 = APIClient()
        c2.force_authenticate(user=self.other)
        self.assertEqual(c2.get(f'/api/bookings/{b_id}/tracking/').status_code, 403)
