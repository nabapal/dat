from app import app, db
from app.models import User, Node, ActivityType, Status, Team
import click

@app.cli.command('seed_demo')
def seed_demo():
    """Drop all tables, recreate them, then seed the database with teams, users, nodes, activity types, and statuses."""
    # Drop and recreate all tables
    db.drop_all()
    db.create_all()

    # Create teams
    team_ipse = Team(name='IPSE')
    team_telco = Team(name='Telco')
    db.session.add_all([team_ipse, team_telco])
    db.session.commit()

    # Create users
    naba = User(username='naba', password_hash='password', role='team_lead', is_active=True)
    anup = User(username='anup', password_hash='password', role='super_lead', is_active=True)
    admin = User(username='admin', password_hash='admin', role='admin', is_active=True)
    naba.teams.extend([team_ipse, team_telco])
    db.session.add_all([naba, anup, admin])
    db.session.commit()

    # Add some members to teams for demo
    members = [
        User(username='Abhijeet', password_hash='Abhijeet', role='member', is_active=True),
        User(username='Shweta', password_hash='Shweta', role='member', is_active=True),
        User(username='Gurkirat', password_hash='Gurkirat', role='member', is_active=True),
        User(username='Konda', password_hash='Konda', role='member', is_active=True),
        User(username='Sairam', password_hash='Sairam', role='member', is_active=True),
        User(username='Kazi', password_hash='Kazi', role='member', is_active=True),
        User(username='Sumit', password_hash='Sumit', role='member', is_active=True),
        User(username='Neelmani', password_hash='Neelmani', role='member', is_active=True),
        User(username='Dilpreet', password_hash='Dilpreet', role='member', is_active=True),
        User(username='Ronak', password_hash='Ronak', role='member', is_active=True),
    ]
    # Assign first 5 to IPSE, rest to Telco
    for m in members[:5]:
        m.teams.append(team_ipse)
    for m in members[5:]:
        m.teams.append(team_telco)
    db.session.add_all(members)
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

    print('All tables dropped and recreated. Teams, users (including naba and anup), nodes, activity types, and statuses seeded.')
