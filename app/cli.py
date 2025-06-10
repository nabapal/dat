from app import app, db
from app.models import User, Activity, Node, ActivityType, Status
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
    # Create activities
    for i in range(1, 6):
        a = Activity(
            activity_id=f'ACT-A-{i:03d}',
            details=f'Activity #{i} for Alice team',
            node_name='Node1',
            activity_type='Type1',
            status='pending',
            start_date=datetime.utcnow() - timedelta(days=i),
            end_date=None,
            user_id=u1.id,  # team lead is the creator/owner
            assigner_id=u1.id
        )
        a.assignees.append(u2)
        a.assignees.append(u3)
        db.session.add(a)
    db.session.commit()
    print('Demo data seeded.')

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
