from app import app, db
from app.models import User, Activity, Node, ActivityType, Status, Team
from datetime import datetime, timedelta

@app.cli.command('seed_demo')
def seed_demo():
    """Seed the database with demo users and activities."""
    # Create teams if not present
    team_ipse = Team.query.filter_by(name='IPSE').first()
    if not team_ipse:
        team_ipse = Team(name='IPSE')
        db.session.add(team_ipse)
    team_telco = Team.query.filter_by(name='TELCO').first()
    if not team_telco:
        team_telco = Team(name='TELCO')
        db.session.add(team_telco)
    db.session.commit()

    # Add admin user if not present
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(username='admin', password_hash='admin', team=team_ipse, role='admin')
        db.session.add(admin_user)
        db.session.commit()

    # Add demo users for each team if not present
    if not User.query.filter_by(username='alice').first():
        u1 = User(username='alice', password_hash='alice', team=team_ipse, role='team_lead')
        u2 = User(username='bob', password_hash='bob', team=team_ipse, role='member')
        db.session.add_all([u1, u2])
    if not User.query.filter_by(username='carol').first():
        u3 = User(username='carol', password_hash='carol', team=team_telco, role='team_lead')
        u4 = User(username='dave', password_hash='dave', team=team_telco, role='member')
        db.session.add_all([u3, u4])
    db.session.commit()

    print('Demo teams (IPSE, TELCO) and admin user seeded.')

@app.cli.command('init_dropdowns')
def init_dropdowns():
    """Initialize default dropdown values for Node, ActivityType, and Status."""
    nodes = ['Node1', 'Node2']
    types = ['Type1', 'Type2']
    statuses = ['pending', 'in_progress', 'completed', 'on_hold']
    for n in nodes:
        if not Node.query.filter_by(name=n).first():
            db.session.add(Node(name=n))
    for t in types:
        if not ActivityType.query.filter_by(name=t).first():
            db.session.add(ActivityType(name=t))
    for s in statuses:
        if not Status.query.filter_by(name=s).first():
            db.session.add(Status(name=s))
    db.session.commit()
    print('Dropdown tables initialized.')
