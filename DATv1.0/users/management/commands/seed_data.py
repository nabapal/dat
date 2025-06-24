from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Team
from activities.models import Activity, ActivityUpdate
from attributes.models import Node, ActivityType, Status

class Command(BaseCommand):
    help = 'Seed the database with demo data.'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        # Remove all data
        ActivityUpdate.objects.all().delete()
        Activity.objects.all().delete()
        User.objects.all().delete()
        Team.objects.all().delete()
        Node.objects.all().delete()
        ActivityType.objects.all().delete()
        Status.objects.all().delete()

        # Create teams
        team_ipse = Team.objects.create(name='IPSE', description='IPSE Team')
        team_telco = Team.objects.create(name='Teclo', description='Teclo Team')

        # Create users
        naba = User.objects.create_user(username='naba', password='password', role='team_lead', is_active=True)
        anup = User.objects.create_user(username='anup', password='password', role='super_lead', is_active=True)
        admin = User.objects.create_superuser(username='admin', password='admin', email='admin@example.com', role='admin', is_active=True)
        naba.teams.add(team_ipse, team_telco)
        anup.teams.add(team_ipse, team_telco)
        admin.teams.add(team_ipse, team_telco)

        # Add demo members
        member_names = [
            'Abhijeet', 'Shweta', 'Gurkirat', 'Konda', 'Sairam',
            'Kazi', 'Sumit', 'Neelmani', 'Dilpreet', 'Ronak'
        ]
        members = []
        for i, name in enumerate(member_names):
            user = User.objects.create_user(username=name, password=name, role='member', is_active=True)
            if i < 5:
                user.teams.add(team_ipse)
            else:
                user.teams.add(team_telco)
            members.append(user)

        # Create nodes
        node_names = [
            'ACI', 'NXOS', 'DCNM', 'NDO', 'CGNAT', 'CPNR', 'CLMS', 'TWAMP', 'Splunk', 'DNS', 'SSM', 'ISE',
            'Arbor', 'CGNAT LC', 'Telemetry', 'DCNM/NXOS', 'ACI/NXOS', 'Other Domain'
        ]
        for n in node_names:
            Node.objects.create(name=n)

        # Create activity types
        activity_types = [
            'New Product Validation', 'Pluggables Testing', 'Regression Testing', 'MoP Validation', 'Solution Testing',
            'Feature Testing', 'Provisioning and Configuration', 'Issue Analysis & Testing', 'Infosec Testing',
            'Audit and Analysis', 'Support Activity', 'Documentation', 'ATP 1A', 'ATP 1B', 'Other',
            'Release Testing', 'Lab Troubleshooting', 'Production Troubleshooting'
        ]
        for t in activity_types:
            ActivityType.objects.create(name=t)

        # Create statuses
        statuses = ['In Progress', 'Completed', 'Yet to start', 'On Hold']
        for s in statuses:
            Status.objects.create(name=s)

        self.stdout.write(self.style.SUCCESS('All data removed. Teams, users (including naba and anup), nodes, activity types, and statuses seeded.'))
