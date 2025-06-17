import click
from app import app, db
from app.models import User, Node, ActivityType, Status, Team

@app.cli.command('seed_demo')
def seed_demo():
    """Remove all data, then seed the database with teams, users, nodes, activity types, and statuses."""
    # Remove all data
    User.query.delete()
    Team.query.delete()
    Node.query.delete()
    ActivityType.query.delete()
    Status.query.delete()
    db.session.commit()

    # Create teams
    team_admin = Team(name='Admin')
    team_ipse = Team(name='IPSE')
    team_telco = Team(name='Telco')
    db.session.add_all([team_admin, team_ipse, team_telco])
    db.session.commit()

    # Create users
    users = [
        User(username='admin', password_hash='admin', team=team_admin, role='admin', is_active=True),
        User(username='Abhijeet', password_hash='Abhijeet', team=team_ipse, role='member', is_active=True),
        User(username='Shweta', password_hash='Shweta', team=team_ipse, role='member', is_active=True),
        User(username='Gurkirat', password_hash='Gurkirat', team=team_ipse, role='member', is_active=True),
        User(username='Konda', password_hash='Konda', team=team_ipse, role='member', is_active=True),
        User(username='Sairam', password_hash='Sairam', team=team_ipse, role='member', is_active=True),
        User(username='Kazi', password_hash='Kazi', team=team_telco, role='member', is_active=True),
        User(username='Sumit', password_hash='Sumit', team=team_telco, role='member', is_active=True),
        User(username='Neelmani', password_hash='Neelmani', team=team_telco, role='member', is_active=True),
        User(username='Dilpreet', password_hash='Dilpreet', team=team_telco, role='member', is_active=True),
        User(username='Ronak', password_hash='Ronak', team=team_telco, role='member', is_active=True),
    ]
    db.session.add_all(users)
    db.session.commit()

    # Create nodes
    nodes = [
        'ACI', 'NXOS', 'DCNM', 'NDO', 'CGNAT', 'CPNR', 'CLMS', 'TWAMP', 'Splunk', 'DNS', 'SSM', 'ISE',
        'Arbor', 'CGNAT LC', 'Telemetry', 'DCNM/NXOS', 'ACI/NXOS', 'Other Domain'
    ]
    for n in nodes:
        db.session.add(Node(name=n))
    db.session.commit()

    # Create activity types
    activity_types = [
        'New Product Validation', 'Pluggables Testing', 'Regression Testing', 'MoP Validation', 'Solution Testing',
        'Feature Testing', 'Provisioning and Configuration', 'Issue Analysis & Testing', 'Infosec Testing',
        'Audit and Analysis', 'Support Activity', 'Documentation', 'ATP 1A', 'ATP 1B', 'Other',
        'Release Testing', 'Lab Troubleshooting', 'Production Troubleshooting'
    ]
    for t in activity_types:
        db.session.add(ActivityType(name=t))
    db.session.commit()

    # Create statuses
    statuses = ['In Progress', 'Completed', 'Yet to start', 'On Hold']
    for s in statuses:
        db.session.add(Status(name=s))
    db.session.commit()

    print('All data removed. Teams, users, nodes, activity types, and statuses seeded.')
