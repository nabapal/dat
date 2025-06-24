from django.test import TestCase
from django.urls import reverse
from .models import Activity, ActivityUpdate
from users.models import User, Team
from attributes.models import Node, ActivityType, Status
from datetime import datetime

class ActivityModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='pass')
        self.team = Team.objects.create(name='Team1')
        self.node = Node.objects.create(name='Node1')
        self.type = ActivityType.objects.create(name='Type1')
        self.status = Status.objects.create(name='Open', color='success')

    def test_create_activity(self):
        activity = Activity.objects.create(
            activity_id='A1', details='Test', node_name=self.node, activity_type=self.type,
            status=self.status, start_date=datetime.now(), user=self.user, assigner=self.user, team=self.team
        )
        self.assertEqual(str(activity), 'A1')
