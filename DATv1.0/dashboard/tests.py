from django.test import TestCase
from django.urls import reverse
from users.models import User

class DashboardViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dash', password='pass', is_active=True)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirects to login
        self.client.login(username='dash', password='pass')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
