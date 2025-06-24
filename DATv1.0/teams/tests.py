from django.test import TestCase
from django.urls import reverse
from users.models import Team

class TeamModelTest(TestCase):
    def test_create_team(self):
        team = Team.objects.create(name='Alpha')
        self.assertEqual(str(team), 'Alpha')

class TeamViewTest(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name='Beta')

    def test_team_list_view(self):
        response = self.client.get(reverse('team_list'))
        self.assertEqual(response.status_code, 302)  # Redirects to login if not authenticated
