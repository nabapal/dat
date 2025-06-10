import click
from app import app, db
from app.models import User, Activity, ActivityUpdate, Node, ActivityType, Status
from datetime import datetime, timedelta

@app.cli.command('seed_demo')
def seed_demo():
    """Seed the database with demo users and activities."""
    db.drop_all()
    db.create_all()
    # Create users
    u1 = User(username='alice', password_hash='alice', team='A', role='team_lead')
    u2 = User(username='bob', password_hash='bob', team='A', role='member')
    u3 = User(username='carol', password_hash='carol', team='A', role='member')
    db.session.add_all([u1, u2, u3])
    db.session.commit()
    # Create activities and assign to multiple users
    for i in range(1, 6):
        a = Activity(
            activity_id=f'ACT-A-{i:03d}',
            details=f'Activity #{i} for Alice team',
            node_name='Node1',
            activity_type='Type1',
            status='pending',
            start_date=datetime.utcnow() - timedelta(days=i),
            end_date=None,
            user_id=u1.id,
            assigner_id=u1.id
        )
        a.assignees.append(u2)
        a.assignees.append(u3)
        db.session.add(a)
    db.session.commit()
    print('Demo data seeded.')
