from sqlalchemy import inspect
from app import app, db
from app.models import User, Node, ActivityType, Status, Team
from werkzeug.security import generate_password_hash
from inspect_excel import import_user_excels
from normalize_statuses import normalize_statuses

def seed_demo():
    """Drop and recreate tables, then seed base data before importing user activity."""
    db.drop_all()
    db.create_all()
    inspector = inspect(db.engine)
    print('Tables after create_all:', inspector.get_table_names())

    # Create teams
    team_ipse = Team(name='IPSE')
    team_telco = Team(name='Telco')
    db.session.add_all([team_ipse, team_telco])
    db.session.commit()

    # Create users (with hashed passwords)
    naba = User(username='Naba', password_hash=generate_password_hash('password'), role='team_lead', is_active=True)
    anup = User(username='Anup', password_hash=generate_password_hash('password'), role='super_lead', is_active=True)
    admin = User(username='admin', password_hash=generate_password_hash('admin'), role='admin', is_active=True)
    naba.teams.extend([team_ipse, team_telco])
    db.session.add_all([naba, anup, admin])
    db.session.commit()

    # Add some members to teams for demo
    members = [
        User(username='Abhijeet', password_hash=generate_password_hash('Abhijeet'), role='member', is_active=True),
        User(username='Shweta', password_hash=generate_password_hash('Shweta'), role='member', is_active=True),
        User(username='Gurkirat', password_hash=generate_password_hash('Gurkirat'), role='member', is_active=True),
        User(username='Konda', password_hash=generate_password_hash('Konda'), role='member', is_active=True),
        User(username='Sairam', password_hash=generate_password_hash('Sairam'), role='member', is_active=True),
        User(username='Kazi', password_hash=generate_password_hash('Kazi'), role='member', is_active=True),
        User(username='Sumit', password_hash=generate_password_hash('Sumit'), role='member', is_active=True),
        User(username='Neelmani', password_hash=generate_password_hash('Neelmani'), role='member', is_active=True),
        User(username='Dilpreet', password_hash=generate_password_hash('Dilpreet'), role='member', is_active=True),
        User(username='Ronak', password_hash=generate_password_hash('Ronak'), role='member', is_active=True),
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

    # Import user Excel data after base seeding
    import_user_excels()

    # Normalize statuses to ensure consistent casing
    normalize_statuses()

if __name__ == '__main__':
    with app.app_context():
        seed_demo()
