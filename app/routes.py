from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from . import app, db
from .models import User, Activity, ActivityUpdate, Node, ActivityType, Status
from .forms import LoginForm, ActivityForm, DummyDropdownForm, UpdateForm
from datetime import datetime
from wtforms import SelectField, SelectMultipleField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo

@app.route('/', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password_hash == form.password.data:  # Replace with hash check
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'team_lead':
        return redirect(url_for('reports'))
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status = request.args.get('status')
    # Get all activities for summary
    all_activities = Activity.query.join(Activity.assignees).filter(User.id == current_user.id).order_by(Activity.start_date.desc()).all()
    # Build summary dict
    summary = {
        'total': len(all_activities),
        'completed': sum(1 for a in all_activities if a.status == 'completed'),
        'in_progress': sum(1 for a in all_activities if a.status == 'in_progress'),
        'pending': sum(1 for a in all_activities if a.status == 'pending'),
    }
    # Filtered query for table
    query = Activity.query.join(Activity.assignees).filter(User.id == current_user.id)
    if status:
        query = query.filter(Activity.status == status)
    elif search:
        status_list = ['pending', 'in_progress', 'completed', 'on_hold']
        if search.lower() in status_list:
            query = query.filter(Activity.status == search.lower())
        else:
            query = query.filter(
                (Activity.activity_id.ilike(f'%{search}%')) |
                (Activity.details.ilike(f'%{search}%')) |
                (Activity.node_name.ilike(f'%{search}%')) |
                (Activity.activity_type.ilike(f'%{search}%'))
            )
    per_page = request.args.get('per_page', 10, type=int)
    activities = query.order_by(Activity.start_date.desc()).paginate(page=page, per_page=per_page)
    # Add update_days_count for each activity (member dashboard)
    for activity in activities.items:
        update_days = set(u.update_date for u in ActivityUpdate.query.filter_by(activity_id=activity.id).all())
        activity.update_days_count = len(update_days)
    return render_template('dashboard.html', activities=activities, search=search, summary=summary)

@app.route('/add_activity', methods=['GET', 'POST'])
@login_required
def add_activity():
    form = ActivityForm()
    # Populate choices for dropdowns from persistent tables
    form.node_name.choices = [(n.name, n.name) for n in Node.query.order_by(Node.name).all()]
    form.activity_type.choices = [(t.name, t.name) for t in ActivityType.query.order_by(ActivityType.name).all()]
    form.status.choices = [(s.name, s.name.capitalize()) for s in Status.query.order_by(Status.name).all()]
    if current_user.role == 'team_lead':
        form.assigned_to.choices = [(u.id, u.username) for u in User.query.filter_by(team=current_user.team).all()]
    else:
        form.assigned_to.choices = [(current_user.id, current_user.username)]
        form.assigned_to.data = [current_user.id]
    if form.validate_on_submit():
        activity = Activity(
            activity_id=f"ACT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            details=form.details.data,
            node_name=form.node_name.data,
            activity_type=form.activity_type.data,
            status=form.status.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            user_id=current_user.id,
            assigner_id=current_user.id
        )
        # Assign multiple users
        assignees = User.query.filter(User.id.in_(form.assigned_to.data)).all()
        activity.assignees.extend(assignees)
        db.session.add(activity)
        db.session.commit()
        flash('Activity created successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_edit_activity.html', form=form)

@app.route('/edit_activity/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_activity(id):
    activity = Activity.query.get_or_404(id)
    # Team lead can edit any activity assigned to a member of their team; assignee can edit their own
    team_members = User.query.filter_by(team=current_user.team).all() if current_user.role == 'team_lead' else []
    team_member_ids = [m.id for m in team_members]
    is_team_lead_and_on_team = current_user.role == 'team_lead' and any(u.id in team_member_ids for u in activity.assignees)
    is_assignee = current_user in activity.assignees
    if not (is_team_lead_and_on_team or is_assignee):
        flash('Not authorized', 'danger')
        return redirect(url_for('dashboard'))
    form = ActivityForm(obj=activity)
    # Populate dropdowns from persistent tables
    form.node_name.choices = [(n.name, n.name) for n in Node.query.order_by(Node.name).all()]
    form.activity_type.choices = [(t.name, t.name) for t in ActivityType.query.order_by(ActivityType.name).all()]
    form.status.choices = [(s.name, s.name.capitalize()) for s in Status.query.order_by(Status.name).all()]
    if current_user.role == 'team_lead':
        form.assigned_to.choices = [(u.id, u.username) for u in User.query.filter_by(team=current_user.team).all()]
    else:
        form.assigned_to.choices = [(current_user.id, current_user.username)]
    if request.method == 'GET':
        form.assigned_to.data = [u.id for u in activity.assignees]
    if form.validate_on_submit():
        if current_user.role == 'team_lead':
            # Only team lead can update assignees
            activity.assignees = User.query.filter(User.id.in_(form.assigned_to.data)).all()
        # Always update other fields
        form.populate_obj(activity)
        db.session.commit()
        flash('Activity updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_edit_activity.html', form=form, activity=activity)

@app.route('/team_dashboard')
@login_required
def team_dashboard():
    if current_user.role != 'team_lead':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    team_members = User.query.filter_by(team=current_user.team).all()
    activities = Activity.query.filter(Activity.assigned_to.in_([m.id for m in team_members])).all()
    return render_template('team_dashboard.html', activities=activities, team_members=team_members)

@app.route('/activity/<int:activity_id>/updates')
@login_required
def view_updates(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    # Allow any assignee to view updates
    if current_user not in activity.assignees and current_user.role != 'team_lead':
        flash('Not authorized', 'danger')
        return redirect(url_for('dashboard'))
    updates = ActivityUpdate.query.filter_by(activity_id=activity.id).order_by(ActivityUpdate.update_date.desc()).all()
    # Fetch user info for each update
    user_map = {u.id: u.username for u in User.query.all()}
    return render_template('view_updates.html', activity=activity, updates=updates, user_map=user_map)

@app.route('/activity/<int:activity_id>/add_update', methods=['GET', 'POST'])
@login_required
def add_update(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    # Allow any assignee to add updates
    if current_user not in activity.assignees and current_user.role != 'team_lead':
        flash('Not authorized', 'danger')
        return redirect(url_for('dashboard'))
    form = UpdateForm()
    if form.validate_on_submit():
        update = ActivityUpdate(
            activity_id=activity.id,
            update_text=form.update_text.data,
            update_date=form.update_date.data,
            updated_by=current_user.id
        )
        db.session.add(update)
        db.session.commit()
        flash('Update added successfully.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_update.html', activity=activity, form=form)

@app.route('/edit_update/<int:update_id>', methods=['GET', 'POST'])
@login_required
def edit_update(update_id):
    update = ActivityUpdate.query.get_or_404(update_id)
    activity = Activity.query.get_or_404(update.activity_id)
    # Only updater or team lead can edit
    if not (current_user.id == update.updated_by or current_user.role == 'team_lead'):
        flash('Not authorized to edit this update.', 'danger')
        return redirect(url_for('view_updates', activity_id=activity.id))
    form = UpdateForm(obj=update)
    if form.validate_on_submit():
        update.update_text = form.update_text.data
        update.update_date = form.update_date.data
        db.session.commit()
        flash('Update edited successfully.', 'success')
        return redirect(url_for('view_updates', activity_id=activity.id))
    return render_template('add_update.html', activity=activity, form=form, edit_mode=True)

@app.route('/delete_update/<int:update_id>', methods=['POST'])
@login_required
def delete_update(update_id):
    update = ActivityUpdate.query.get_or_404(update_id)
    activity_id = update.activity_id
    # Only updater or team lead can delete
    if not (current_user.id == update.updated_by or current_user.role == 'team_lead'):
        flash('Not authorized to delete this update.', 'danger')
        return redirect(url_for('view_updates', activity_id=activity_id))
    db.session.delete(update)
    db.session.commit()
    flash('Update deleted successfully.', 'success')
    return redirect(url_for('view_updates', activity_id=activity_id))

@app.route('/reports')
@login_required
def reports():
    team_members = []
    status_summary = node_summary = type_summary = member_summary = None
    node_status_update = member_status_update = type_status_update = None
    if current_user.role == 'team_lead':
        team_members = User.query.filter_by(team=current_user.team).all()
        assignee_id = request.args.get('assignee', type=int)
        status = request.args.get('status', '')
        query = Activity.query.join(Activity.assignees).filter(User.id.in_([m.id for m in team_members]))
        if assignee_id:
            query = query.filter(User.id == assignee_id)
        if status:
            query = query.filter(Activity.status == status)
        activities = query.all()
        # Build summary for all team activities (not just filtered)
        all_activities = Activity.query.join(Activity.assignees).filter(User.id.in_([m.id for m in team_members])).all()
        from collections import Counter, defaultdict
        status_summary = Counter([a.status for a in all_activities])
        node_summary = Counter([a.node_name for a in all_activities if a.node_name])
        type_summary = Counter([a.activity_type for a in all_activities if a.activity_type])
        member_summary = defaultdict(lambda: Counter())
        for a in all_activities:
            for u in a.assignees:
                if u in team_members:
                    member_summary[u.username][a.status] += 1
        # Node status (no update days)
        node_status_update = defaultdict(lambda: {'status': Counter(), 'count': 0})
        for a in all_activities:
            if a.node_name:
                node_status_update[a.node_name]['status'][a.status] += 1
                node_status_update[a.node_name]['count'] += 1
        # Member status (no update days)
        member_status_update = defaultdict(lambda: {'status': Counter(), 'count': 0})
        for u in team_members:
            user_activities = [a for a in all_activities if u in a.assignees]
            for a in user_activities:
                member_status_update[u.username]['status'][a.status] += 1
                member_status_update[u.username]['count'] += 1
        # Type status and days contributed
        type_status_update = defaultdict(lambda: {'status': Counter(), 'count': 0, 'days_contributed': 0})
        for a in all_activities:
            if a.activity_type:
                type_status_update[a.activity_type]['status'][a.status] += 1
                type_status_update[a.activity_type]['count'] += 1
                days_contributed = set(u.update_date for u in ActivityUpdate.query.filter_by(activity_id=a.id).all())
                type_status_update[a.activity_type]['days_contributed'] += len(days_contributed)
        summary = {
            'total': len(all_activities),
            'completed': sum(1 for a in all_activities if a.status == 'completed'),
            'in_progress': sum(1 for a in all_activities if a.status == 'in_progress'),
            'pending': sum(1 for a in all_activities if a.status == 'pending'),
        }
    else:
        activities = Activity.query.join(Activity.assignees).filter(User.id == current_user.id).all()
        summary = {
            'total': len(activities),
            'completed': sum(1 for a in activities if a.status == 'completed'),
            'in_progress': sum(1 for a in activities if a.status == 'in_progress'),
            'pending': sum(1 for a in activities if a.status == 'pending'),
        }
        status_summary = node_summary = type_summary = member_summary = node_status_update = member_status_update = None
    total_activities = len(activities)
    total_hours = sum([a.duration or 0 for a in activities])
    avg_daily_hours = total_hours / 7 if total_activities else 0
    return render_template('reports.html', activities=activities, total_activities=total_activities, total_hours=total_hours, avg_daily_hours=avg_daily_hours, team_members=team_members, summary=summary, status_summary=status_summary, node_summary=node_summary, type_summary=type_summary, member_summary=member_summary, node_status_update=node_status_update, member_status_update=member_status_update, type_status_update=type_status_update)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/manage_team_dropdowns', methods=['GET', 'POST'])
@login_required
def manage_team_dropdowns():
    if current_user.role != 'team_lead':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    form = DummyDropdownForm()
    node_names = [n.name for n in Node.query.order_by(Node.name).all()]
    activity_types = [t.name for t in ActivityType.query.order_by(ActivityType.name).all()]
    statuses = [s.name for s in Status.query.order_by(Status.name).all()]
    if form.validate_on_submit():
        added = False
        if form.node_name.data and not Node.query.filter_by(name=form.node_name.data).first():
            db.session.add(Node(name=form.node_name.data))
            added = True
        if form.activity_type.data and not ActivityType.query.filter_by(name=form.activity_type.data).first():
            db.session.add(ActivityType(name=form.activity_type.data))
            added = True
        if form.status.data and not Status.query.filter_by(name=form.status.data).first():
            db.session.add(Status(name=form.status.data))
            added = True
        if added:
            db.session.commit()
            flash('Dropdown option added!', 'success')
        else:
            flash('No new value added (may already exist or empty).', 'warning')
        return redirect(url_for('manage_team_dropdowns'))
    return render_template('manage_team_dropdowns.html', node_names=node_names, activity_types=activity_types, statuses=statuses, form=form)

@app.route('/team_activities')
@login_required
def team_activities():
    if current_user.role != 'team_lead':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    team_members = User.query.filter_by(team=current_user.team).all()
    team_members_map = {m.id: m.username for m in team_members}
    search = request.args.get('search', '')
    assignee = request.args.get('assignee', type=int)
    status = request.args.get('status')
    activity_type = request.args.get('activity_type')
    node_name = request.args.get('node_name')
    sort = request.args.get('sort', 'start_date')
    direction = request.args.get('direction', 'desc')
    query = Activity.query.join(Activity.assignees).filter(User.id.in_([m.id for m in team_members]))
    if assignee:
        query = query.filter(User.id == assignee)
    if status:
        query = query.filter(Activity.status == status)
    if activity_type:
        query = query.filter(Activity.activity_type == activity_type)
    if node_name:
        query = query.filter(Activity.node_name == node_name)
    if search:
        query = query.filter(
            (Activity.activity_id.ilike(f'%{search}%')) |
            (Activity.details.ilike(f'%{search}%')) |
            (Activity.node_name.ilike(f'%{search}%')) |
            (Activity.activity_type.ilike(f'%{search}%'))
        )
    sort_map = {
        'activity_id': Activity.activity_id,
        'details': Activity.details,
        'status': Activity.status,
        'node_name': Activity.node_name,
        'activity_type': Activity.activity_type,
        'start_date': Activity.start_date,
        'end_date': Activity.end_date,
    }
    sort_col = sort_map.get(sort, Activity.start_date)
    if direction == 'desc':
        sort_col = sort_col.desc()
    else:
        sort_col = sort_col.asc()
    per_page = request.args.get('per_page', 10, type=int)
    page = request.args.get('page', 1, type=int)
    activities = query.order_by(sort_col).paginate(page=page, per_page=per_page)
    # Add update_days_count for each activity in the current page
    for activity in activities.items:
        update_days = set(u.update_date for u in ActivityUpdate.query.filter_by(activity_id=activity.id).all())
        activity.update_days_count = len(update_days)
    # Build summary for all team activities (not just filtered)
    all_activities = Activity.query.join(Activity.assignees).filter(User.id.in_([m.id for m in team_members])).all()
    summary = {
        'total': len(all_activities),
        'completed': sum(1 for a in all_activities if a.status == 'completed'),
        'in_progress': sum(1 for a in all_activities if a.status == 'in_progress'),
        'pending': sum(1 for a in all_activities if a.status == 'pending'),
    }
    return render_template('team_activities.html', activities=activities, team_members=team_members, team_members_map=team_members_map, summary=summary)

@app.route('/delete_activity/<int:id>', methods=['POST'])
@login_required
def delete_activity(id):
    activity = Activity.query.get_or_404(id)
    # Only allow team lead of the team or assignee to delete
    team_members = User.query.filter_by(team=current_user.team).all() if current_user.role == 'team_lead' else []
    team_member_ids = [m.id for m in team_members]
    is_team_lead_and_on_team = current_user.role == 'team_lead' and any(u.id in team_member_ids for u in activity.assignees)
    is_assignee = current_user in activity.assignees
    if not (is_team_lead_and_on_team or is_assignee):
        flash('Not authorized to delete this activity.', 'danger')
        return redirect(url_for('dashboard'))
    db.session.delete(activity)
    db.session.commit()
    flash('Activity deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])
    submit = SubmitField('Change Password')

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        user = User.query.get(current_user.id)
        if user.password_hash != form.old_password.data:
            flash('Current password is incorrect.', 'danger')
        else:
            user.password_hash = form.new_password.data
            db.session.commit()
            flash('Password changed successfully.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('change_password.html', form=form)
