from django.test import TestCase
from django.urls import reverse
from .models import Activity, ActivityUpdate
from users.models import User, Team
from attributes.models import Node, ActivityType, Status
from datetime import datetime
from datetime import date, timedelta

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

    def test_age_days_with_end_and_without_end(self):
        # With explicit end_date
        start = datetime(2025, 12, 20)
        end = datetime(2025, 12, 25)
        activity = Activity.objects.create(
            activity_id='A2', details='AgingTest', node_name=self.node, activity_type=self.type,
            status=self.status, start_date=start, end_date=end, user=self.user, assigner=self.user, team=self.team
        )
        self.assertEqual(activity.age_days, 5)

        # Without end_date should use today's date
        today = date.today()
        start_date = datetime.combine(today - timedelta(days=3), datetime.min.time())
        activity2 = Activity.objects.create(
            activity_id='A3', details='AgingTest2', node_name=self.node, activity_type=self.type,
            status=self.status, start_date=start_date, user=self.user, assigner=self.user, team=self.team
        )
        self.assertEqual(activity2.age_days, 3)
