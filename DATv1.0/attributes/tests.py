from django.test import TestCase
from .models import Node, ActivityType, Status

class AttributeModelTest(TestCase):
    def test_create_node(self):
        node = Node.objects.create(name='NodeX')
        self.assertEqual(str(node), 'NodeX')

    def test_create_activitytype(self):
        atype = ActivityType.objects.create(name='TypeX')
        self.assertEqual(str(atype), 'TypeX')

    def test_create_status(self):
        status = Status.objects.create(name='Closed', color='danger')
        self.assertEqual(str(status), 'Closed')
        self.assertEqual(status.color, 'danger')
