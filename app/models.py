from datetime import datetime
from . import db

activity_assignees = db.Table('activity_assignees',
    db.Column('activity_id', db.Integer, db.ForeignKey('activity.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

user_teams = db.Table('user_teams',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(32), default='member')
    is_active = db.Column(db.Boolean, default=False)
    activities = db.relationship('Activity', backref='user', lazy='dynamic', foreign_keys='Activity.user_id')
    assigned_by_me = db.relationship('Activity', foreign_keys='Activity.assigner_id', backref='assigner', lazy='dynamic')
    teams = db.relationship('Team', secondary='user_teams', back_populates='users')

    # Flask-Login integration
    def is_authenticated(self):
        return True
    def is_anonymous(self):
        return False
    def get_id(self):
        return str(self.id)

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.String(20), unique=True, nullable=False)
    details = db.Column(db.Text, nullable=False)
    node_name = db.Column(db.String(50))
    activity_type = db.Column(db.String(50))
    status = db.Column(db.String(50), default='pending')
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    duration = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assignees = db.relationship('User', secondary=activity_assignees, backref='activities_assigned_to', lazy='dynamic')

class ActivityUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)
    update_date = db.Column(db.Date, nullable=False)
    update_text = db.Column(db.Text, nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Node(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class ActivityType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    users = db.relationship('User', secondary='user_teams', back_populates='teams')
