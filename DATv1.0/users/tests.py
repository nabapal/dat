from django.test import TestCase
from django.urls import reverse
from .models import User, Team

class UserModelTest(TestCase):
    def test_create_user(self):
        team = Team.objects.create(name='Test Team')
        user = User.objects.create_user(username='testuser', password='testpass')
        user.teams.add(team)
        self.assertEqual(user.username, 'testuser')
        self.assertIn(team, user.teams.all())

class UserAuthTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass', is_active=True)

    def test_login(self):
        logged_in = self.client.login(username='testuser', password='testpass')
        self.assertTrue(logged_in)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_register(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser', 'password1': 'newpass123', 'password2': 'newpass123', 'email': 'a@b.com', 'role': 'member'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())
