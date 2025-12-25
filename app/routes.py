from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from . import app, db
from sqlalchemy import inspect, func, or_
from .models import User, Activity, ActivityUpdate, Node, ActivityType, Status, Team
from .forms import LoginForm, ActivityForm, DummyDropdownForm, UpdateForm
from datetime import datetime, timedelta
from wtforms import SelectField, SelectMultipleField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from collections import Counter
from .remove_user_route import *

@app.route('/', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            if not user.is_active:
                flash('Your account is pending admin approval.', 'warning')
                return render_template('login.html', form=form)
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role in ['team_lead', 'super_lead']:
        return redirect(url_for('reports'))
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status = request.args.get('status')
    # Financial year filter
    fy = session.get('financial_year')
    if not fy:
        available_fys = [f for f in inject_financial_years()['available_financial_years']]
        fy = available_fys[-2] if len(available_fys) > 1 else available_fys[-1]
    start_date, end_date = get_financial_year_dates(fy)
    # Base query for activities (filtered by FY). We'll paginate for the table
    activities_query = Activity.query.join(Activity.assignees) \
        .filter(User.id == current_user.id) \
        .filter(Activity.start_date >= start_date, Activity.start_date <= end_date) \
        .order_by(Activity.start_date.desc())
    # Apply status and search filters from request (so summary links work)
    if status:
        activities_query = activities_query.filter(Activity.status == status)
    if search:
        term = f"%{search}%"
        # search across multiple activity fields and assignee username
        activities_query = activities_query.filter(or_(
            Activity.details.ilike(term),
            Activity.activity_id.ilike(term),
            Activity.node_name.ilike(term),
            Activity.activity_type.ilike(term),
            User.username.ilike(term)
        ))
    per_page = request.args.get('per_page', 10, type=int)
    activities = activities_query.paginate(page=page, per_page=per_page)
    all_activities = activities.items
    # Calculate days contributed for each activity
    for activity in activities.items:
        update_days = set(u.update_date for u in ActivityUpdate.query.filter_by(activity_id=activity.id).all())
        activity.update_days_count = len(update_days)
    # Dynamic summary: compute totals across the full FY selection (not just current page)
    statuses = Status.query.all()
    total_count = db.session.query(func.count(Activity.id)).join(Activity.assignees).filter(
        User.id == current_user.id,
        Activity.start_date >= start_date,
        Activity.start_date <= end_date
    ).scalar() or 0
    status_rows = db.session.query(Activity.status, func.count(Activity.id)).join(Activity.assignees).filter(
        User.id == current_user.id,
        Activity.start_date >= start_date,
        Activity.start_date <= end_date
    ).group_by(Activity.status).all()
    status_counter = {(s or '').strip().lower(): cnt for s, cnt in status_rows}
    summary = {'total': total_count}
    summary.update(status_counter)
    default_colors = {
        'completed': 'success',
        'in_progress': 'warning',
        'pending': 'info',
        'on_hold': 'secondary',
        'yet_to_start': 'primary',
    }
    default_icons = {
        'completed': 'fa-check',
        'in_progress': 'fa-spinner',
        'pending': 'fa-hourglass-half',
        'on_hold': 'fa-pause-circle',
        'yet_to_start': 'fa-play',
    }
    status_color_map = {s.name.lower(): getattr(s, 'color', default_colors.get(s.name.lower(), 'dark')) for s in statuses}
    status_icon_map = {s.name.lower(): getattr(s, 'icon', default_icons.get(s.name.lower(), 'fa-circle')) for s in statuses}
    return render_template(
        'dashboard.html',
        activities=activities,
        search=search,
        summary=summary,
        status_color_map=status_color_map,
        status_icon_map=status_icon_map
    )

@app.route('/add_activity', methods=['GET', 'POST'])
@login_required
def add_activity():
    form = ActivityForm()
    # Populate choices for dropdowns from persistent tables
    form.node_name.choices = [(n.name, n.name) for n in Node.query.order_by(Node.name).all()]
    form.activity_type.choices = [(t.name, t.name) for t in ActivityType.query.order_by(ActivityType.name).all()]
    form.status.choices = [(s.name, s.name.capitalize()) for s in Status.query.order_by(Status.name).all()]
    if current_user.role == 'super_lead':
        # Show all users, leads first, then members
        all_users = User.query.order_by(User.role.desc(), User.username.asc()).all()
        leads = [u for u in all_users if u.role == 'team_lead']
        members = [u for u in all_users if u.role != 'team_lead']
        form.assigned_to.choices = [(u.id, u.username + (' (Lead)' if u.role == 'team_lead' else '')) for u in leads + members]
    elif current_user.role == 'team_lead':
        team_ids = [t.id for t in current_user.teams]
        team_members = User.query.join(User.teams).filter(Team.id.in_(team_ids)).distinct().all()
        form.assigned_to.choices = [(u.id, u.username) for u in team_members]
    else:
        form.assigned_to.choices = [(current_user.id, current_user.username)]
        if not form.assigned_to.data:
            form.assigned_to.data = [current_user.id]
    # Set default values only on GET so we don't override user-submitted values on POST
    if request.method == 'GET':
        form.start_date.data = datetime.now().date()
        form.end_date.data = (datetime.now() + timedelta(days=7)).date()
    if form.validate_on_submit():
        # Generate unique activity_id: timestamp + incremental number
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        activity_count = Activity.query.count() + 1
        generated_activity_id = f"{timestamp}-{activity_count}"
        activity = Activity(
            activity_id=generated_activity_id,
            details=form.details.data,
            node_name=form.node_name.data,
            activity_type=form.activity_type.data,
            status=form.status.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            user_id=current_user.id,
            assigner_id=current_user.id
        )
        # Always assign the current user if no one is selected
        assignees = User.query.filter(User.id.in_(form.assigned_to.data)).all()
        if not assignees:
            assignees = [current_user]
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
    # Team lead or super lead can edit any activity assigned to their teams; assignee can edit their own
    if current_user.role in ['team_lead', 'super_lead']:
        team_ids = [t.id for t in current_user.teams] if current_user.role == 'team_lead' else [t.id for t in Team.query.all()]
        team_members = User.query.join(User.teams).filter(Team.id.in_(team_ids)).distinct().all()
        team_member_ids = [m.id for m in team_members]
        is_team_lead_and_on_team = any(u.id in team_member_ids for u in activity.assignees)
    else:
        is_team_lead_and_on_team = False
    is_assignee = current_user in activity.assignees
    if not (is_team_lead_and_on_team or is_assignee or current_user.role == 'super_lead'):
        flash('Not authorized', 'danger')
        return redirect(url_for('dashboard'))
    form = ActivityForm(obj=activity)
    # Populate dropdowns from persistent tables
    form.node_name.choices = [(n.name, n.name) for n in Node.query.order_by(Node.name).all()]
    form.activity_type.choices = [(t.name, t.name) for t in ActivityType.query.order_by(ActivityType.name).all()]
    form.status.choices = [(s.name, s.name.capitalize()) for s in Status.query.order_by(Status.name).all()]
    if current_user.role in ['team_lead', 'super_lead']:
        form.assigned_to.choices = [(u.id, u.username) for u in team_members]
    else:
        form.assigned_to.choices = [(current_user.id, current_user.username)]
    if request.method == 'GET':
        form.assigned_to.data = [u.id for u in activity.assignees]
    if form.validate_on_submit():
        if current_user.role in ['team_lead', 'super_lead']:
            activity.assignees = User.query.filter(User.id.in_(form.assigned_to.data)).all()
        form.populate_obj(activity)
        db.session.commit()
        flash('Activity updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_edit_activity.html', form=form, activity=activity)

@app.route('/activity/<int:activity_id>/updates')
@login_required
def view_updates(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    # Allow any assignee, team lead for their teams, or super_lead/admin to view updates
    if current_user in activity.assignees or current_user.role in ['super_lead', 'admin']:
        pass
    elif current_user.role == 'team_lead':
        team_ids = [t.id for t in current_user.teams]
        if not set(team_ids).intersection([t.id for t in activity.assignees[0].teams]):
            flash('Not authorized', 'danger')
            return redirect(url_for('dashboard'))
    else:
        flash('Not authorized', 'danger')
        return redirect(url_for('dashboard'))
    updates = ActivityUpdate.query.filter_by(activity_id=activity.id).order_by(ActivityUpdate.update_date.desc()).all()
    user_map = {u.id: u.username for u in User.query.all()}
    return render_template('view_updates.html', activity=activity, updates=updates, user_map=user_map)

@app.route('/activity/<int:activity_id>/add_update', methods=['GET', 'POST'])
@login_required
def add_update(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    # Allow any assignee, team lead, or super lead to add updates
    if current_user in activity.assignees or current_user.role in ['team_lead', 'super_lead']:
        pass
    else:
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
    from collections import Counter, defaultdict
    team_members = []
    status_summary = node_summary = type_summary = member_summary = None
    node_status_update = member_status_update = type_status_update = None
    # Financial year filter for reports
    fy = session.get('financial_year')
    if fy:
        start_date, end_date = get_financial_year_dates(fy)
    else:
        now = datetime.now()
        start_date, end_date = get_financial_year_dates(f"{str(now.year-1)[-2:]}-{str(now.year)[-2:]}")
    # Team selection for team_lead and super_lead
    if current_user.role in ['team_lead', 'super_lead']:
        # Get all teams for this user
        all_teams = current_user.teams if current_user.role == 'team_lead' else Team.query.all()
        selected_team_id = request.args.get('team_id', type=int)
        if selected_team_id:
            selected_teams = [t for t in all_teams if t.id == selected_team_id]
        else:
            selected_teams = all_teams
        team_members = User.query.join(User.teams).filter(Team.id.in_([t.id for t in selected_teams])).distinct().all()
        assignee_id = request.args.get('assignee', type=int)
        status = request.args.get('status', '')
        query = Activity.query.join(Activity.assignees).filter(User.id.in_([m.id for m in team_members]))
        query = query.filter(Activity.start_date >= start_date, Activity.start_date <= end_date)
        if assignee_id:
            query = query.filter(User.id == assignee_id)
        if status:
            query = query.filter(Activity.status == status)
        activities = query.all()
        # Build summary for all team activities (not just filtered)
        all_activities = Activity.query.join(Activity.assignees).filter(User.id.in_([m.id for m in team_members]))
        all_activities = [a for a in all_activities if start_date <= a.start_date <= end_date]
        status_summary = Counter([a.status for a in all_activities])
        node_summary = Counter([a.node_name for a in all_activities if a.node_name])
        type_summary = Counter([a.activity_type for a in all_activities if a.activity_type])
        member_summary = defaultdict(lambda: Counter())
        for a in all_activities:
            for u in a.assignees:
                if u in team_members:
                    member_summary[u.username][a.status] += 1
        node_status_update = defaultdict(lambda: {'status': Counter(), 'count': 0})
        for a in all_activities:
            if a.node_name:
                node_status_update[a.node_name]['status'][a.status] += 1
                node_status_update[a.node_name]['count'] += 1
        member_status_update = defaultdict(lambda: {'status': Counter(), 'count': 0})
        for u in team_members:
            user_activities = [a for a in all_activities if u in a.assignees]
            for a in user_activities:
                member_status_update[u.username]['status'][a.status] += 1
                member_status_update[u.username]['count'] += 1
        type_status_update = defaultdict(lambda: {'status': Counter(), 'count': 0, 'days_contributed': 0})
        for a in all_activities:
            if a.activity_type:
                type_status_update[a.activity_type]['status'][a.status] += 1
                type_status_update[a.activity_type]['count'] += 1
                days_contributed = set(u.update_date for u in ActivityUpdate.query.filter_by(activity_id=a.id).all())
                type_status_update[a.activity_type]['days_contributed'] += len(days_contributed)
        # Calculate average days contributed per type
        for t, stat in type_status_update.items():
            if stat['count'] > 0:
                stat['average_days_contributed'] = round(stat['days_contributed'] / stat['count'], 2)
            else:
                stat['average_days_contributed'] = 0
        summary = {
            'total': len(all_activities),
            'completed': sum(1 for a in all_activities if a.status == 'completed'),
            'in_progress': sum(1 for a in all_activities if a.status == 'in_progress'),
            'pending': sum(1 for a in all_activities if a.status == 'pending'),
        }
    else:
        activities = Activity.query.join(Activity.assignees).filter(User.id == current_user.id)
        activities = activities.filter(Activity.start_date >= start_date, Activity.start_date <= end_date).all()
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
    return render_template('reports.html', activities=activities, total_activities=total_activities, total_hours=total_hours, avg_daily_hours=avg_daily_hours, team_members=team_members, summary=summary, status_summary=status_summary, node_summary=node_summary, type_summary=type_summary, member_summary=member_summary, node_status_update=node_status_update, member_status_update=member_status_update, type_status_update=type_status_update, all_teams=all_teams if current_user.role in ['team_lead', 'super_lead'] else None, selected_team_id=selected_team_id if current_user.role in ['team_lead', 'super_lead'] else None)

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
        action = request.form.get('form_action')
        if action == 'edit_node':
            old_value = request.form.get('old_value')
            new_value = request.form.get('new_value')
            if old_value and new_value and old_value != new_value:
                node = Node.query.filter_by(name=old_value).first()
                if node and not Node.query.filter_by(name=new_value).first():
                    node.name = new_value
                    db.session.commit()
                    flash('Node updated.', 'success')
                else:
                    flash('Duplicate or invalid node name.', 'danger')
        elif action == 'delete_node':
            value = request.form.get('value')
            node = Node.query.filter_by(name=value).first()
            if node:
                # Safety: prevent delete if node is in use
                if Activity.query.filter_by(node_name=node.name).first():
                    flash('Cannot delete: node in use.', 'danger')
                else:
                    db.session.delete(node)
                    db.session.commit()
                    flash('Node deleted.', 'success')
        elif action == 'edit_type':
            old_value = request.form.get('old_value')
            new_value = request.form.get('new_value')
            if old_value and new_value and old_value != new_value:
                t = ActivityType.query.filter_by(name=old_value).first()
                if t and not ActivityType.query.filter_by(name=new_value).first():
                    t.name = new_value
                    db.session.commit()
                    flash('Activity type updated.', 'success')
                else:
                    flash('Duplicate or invalid activity type.', 'danger')
        elif action == 'delete_type':
            value = request.form.get('value')
            t = ActivityType.query.filter_by(name=value).first()
            if t:
                # Safety: prevent delete if type is in use
                if Activity.query.filter_by(activity_type=t.name).first():
                    flash('Cannot delete: activity type in use.', 'danger')
                else:
                    db.session.delete(t)
                    db.session.commit()
                    flash('Activity type deleted.', 'success')
        elif action == 'edit_status':
            old_value = request.form.get('old_value')
            new_value = request.form.get('new_value')
            if old_value and new_value and old_value != new_value:
                s = Status.query.filter_by(name=old_value).first()
                if s and not Status.query.filter_by(name=new_value).first():
                    s.name = new_value
                    db.session.commit()
                    flash('Status updated.', 'success')
                else:
                    flash('Duplicate or invalid status name.', 'danger')
        elif action == 'delete_status':
            value = request.form.get('value')
            s = Status.query.filter_by(name=value).first()
            if s:
                # Safety: prevent delete if status is in use
                if Activity.query.filter_by(status=s.name).first():
                    flash('Cannot delete: status in use.', 'danger')
                else:
                    db.session.delete(s)
                    db.session.commit()
                    flash('Status deleted.', 'success')
        elif action == 'add_node':
            node_name = request.form.get('node_name')
            if node_name and not Node.query.filter_by(name=node_name).first():
                db.session.add(Node(name=node_name))
                db.session.commit()
                flash('Node added successfully.', 'success')
            else:
                flash('Node already exists or invalid name.', 'danger')
        elif action == 'add_type':
            activity_type = request.form.get('activity_type')
            if activity_type and not ActivityType.query.filter_by(name=activity_type).first():
                db.session.add(ActivityType(name=activity_type))
                db.session.commit()
                flash('Activity type added successfully.', 'success')
            else:
                flash('Activity type already exists or invalid name.', 'danger')
        elif action == 'add_status':
            status = request.form.get('status')
            if status and not Status.query.filter_by(name=status).first():
                db.session.add(Status(name=status))
                db.session.commit()
                flash('Status added successfully.', 'success')
            else:
                flash('Status already exists or invalid name.', 'danger')
        else:
            # Old add logic (kept for compatibility)
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
                flash('No new value added (may already exist or be blank).', 'info')
        return redirect(url_for('manage_team_dropdowns'))
    else:
        if request.method == 'POST':
            flash('Invalid CSRF token or form data.', 'danger')
            return redirect(url_for('manage_team_dropdowns'))
    return render_template('manage_team_dropdowns.html', node_names=node_names, activity_types=activity_types, statuses=statuses, form=form)

@app.route('/team_activities')
@login_required
def team_activities():
    if current_user.role not in ['team_lead', 'super_lead']:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    # Team selection for super_lead
    all_teams = current_user.teams if current_user.role == 'team_lead' else Team.query.all()
    selected_team_id = request.args.get('team_id', type=int)
    if selected_team_id:
        selected_teams = [t for t in all_teams if t.id == selected_team_id]
    else:
        selected_teams = all_teams
    team_members = User.query.join(User.teams).filter(Team.id.in_([t.id for t in selected_teams])).distinct().all()
    team_members_map = {m.id: m.username for m in team_members}
    search = request.args.get('search', '')
    assignee = request.args.get('assignee', type=int)
    status = request.args.get('status')
    activity_type = request.args.get('activity_type')
    node_name = request.args.get('node_name')
    sort = request.args.get('sort', 'start_date')
    direction = request.args.get('direction', 'desc')
    # Financial year filter
    fy = session.get('financial_year')
    if not fy:
        available_fys = [f for f in inject_financial_years()['available_financial_years']]
        fy = available_fys[-2] if len(available_fys) > 1 else available_fys[-1]
    start_date, end_date = get_financial_year_dates(fy)
    query = Activity.query.join(Activity.assignees).filter(User.id.in_([m.id for m in team_members])).distinct()
    query = query.filter(Activity.start_date >= start_date, Activity.start_date <= end_date)
    if assignee:
        query = query.filter(User.id == assignee)
    if status:
        query = query.filter(Activity.status == status)
    if activity_type:
        query = query.filter(Activity.activity_type == activity_type)
    if node_name:
        query = query.filter(Activity.node_name == node_name)
    # Apply search filter across multiple fields
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            Activity.details.ilike(term),
            Activity.activity_id.ilike(term),
            Activity.node_name.ilike(term),
            Activity.activity_type.ilike(term),
            User.username.ilike(term)
        ))
    sort_col = getattr(Activity, sort)
    if direction == 'desc':
        sort_col = sort_col.desc()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    activities = query.order_by(sort_col).paginate(page=page, per_page=per_page)
    for activity in activities.items:
        update_days = set(u.update_date for u in ActivityUpdate.query.filter_by(activity_id=activity.id).all())
        activity.update_days_count = len(update_days)
    all_activities = Activity.query.join(Activity.assignees).filter(User.id.in_([m.id for m in team_members])).distinct()
    all_activities = all_activities.filter(Activity.start_date >= start_date, Activity.start_date <= end_date).all()
    summary = {
        'total': len(all_activities),
        'completed': sum(1 for a in all_activities if a.status == 'completed'),
        'in_progress': sum(1 for a in all_activities if a.status == 'in_progress'),
        'pending': sum(1 for a in all_activities if a.status == 'pending'),
        'on_hold': sum(1 for a in all_activities if a.status == 'on_hold'),
        'yet_to_start': sum(1 for a in all_activities if a.status == 'yet_to_start'),
    }
    # Dynamic summary: count all statuses
    statuses = Status.query.all()
    status_counter = Counter((a.status or '').strip().lower() for a in all_activities)
    summary = {'total': len(all_activities)}
    summary.update(status_counter)
    default_colors = {
        'completed': 'success',
        'in_progress': 'warning',
        'pending': 'info',
        'on_hold': 'secondary',
        'yet_to_start': 'primary',
    }
    default_icons = {
        'completed': 'fa-check',
        'in_progress': 'fa-spinner',
        'pending': 'fa-hourglass-half',
        'on_hold': 'fa-pause-circle',
        'yet_to_start': 'fa-play',
    }
    status_color_map = {s.name.lower(): getattr(s, 'color', default_colors.get(s.name.lower(), 'dark')) for s in statuses}
    status_icon_map = {s.name.lower(): getattr(s, 'icon', default_icons.get(s.name.lower(), 'fa-circle')) for s in statuses}
    return render_template('team_activities.html', activities=activities, team_members=team_members, team_members_map=team_members_map, summary=summary, all_teams=all_teams, selected_team_id=selected_team_id, status_color_map=status_color_map, status_icon_map=status_icon_map)

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

@app.route('/admin_users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    from .models import User, Team
    users = User.query.all()
    teams = Team.query.order_by(Team.name).all()
    if request.method == 'POST' and request.form.get('form_type') == 'add_team':
        new_team = request.form.get('new_team')
        if new_team and not Team.query.filter_by(name=new_team).first():
            db.session.add(Team(name=new_team))
            db.session.commit()
            flash(f'Team "{new_team}" added (users can now be assigned to this team).', 'success')
        else:
            flash('Team already exists or invalid.', 'danger')
        teams = Team.query.order_by(Team.name).all()
        pending_users = User.query.filter_by(is_active=False).all()
        return render_template('admin_users.html', users=users, teams=teams, pending_users=pending_users)
    if request.method == 'POST' and request.form.get('form_type') == 'add_user':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        team_id = request.form.get('team')
        if username and password and role and team_id:
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'danger')
            else:
                from werkzeug.security import generate_password_hash
                user = User(username=username, password_hash=generate_password_hash(password), role=role, is_active=True)
                team = Team.query.get(int(team_id))
                if team:
                    user.teams.append(team)
                db.session.add(user)
                db.session.commit()
                flash('User added successfully!', 'success')
            return redirect(url_for('admin_users'))
    if request.args.get('approve'):
        user = User.query.get(int(request.args.get('approve')))
        if user:
            user.is_active = True
            db.session.commit()
            flash('User approved and activated.', 'success')
        return redirect(url_for('admin_users'))
    if request.args.get('delete'):
        user = User.query.get(int(request.args.get('delete')))
        if user:
            db.session.delete(user)
            db.session.commit()
            flash('User deleted.', 'success')
        return redirect(url_for('admin_users'))
    pending_users = User.query.filter_by(is_active=False).all()
    return render_template('admin_users.html', users=users, teams=teams, pending_users=pending_users)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    from .models import User, Team
    from . import db
    from flask import render_template, request, redirect, url_for, flash
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        team_id = request.form.get('team')
        if not username or not password or not role or not team_id:
            flash('All fields are required.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
        else:
            from werkzeug.security import generate_password_hash
            user = User(username=username, password_hash=generate_password_hash(password), role=role, is_active=False)
            team = Team.query.get(int(team_id))
            if team:
                user.teams.append(team)
            db.session.add(user)
            db.session.commit()
            flash('Signup successful! Awaiting admin approval.', 'success')
            return redirect(url_for('index'))
    teams = Team.query.order_by(Team.name).all()
    return render_template('signup.html', teams=teams)



@app.route('/team_management', methods=['GET', 'POST'])
@login_required
def team_management():
    from .models import User, Team
    # Determine which users and teams the current user can manage
    if current_user.role == 'super_lead':
        managed_users = User.query.all()
        all_teams = Team.query.all()
    elif current_user.role == 'team_lead':
        all_teams = current_user.teams
        managed_users = []
        for team in all_teams:
            managed_users.extend(team.users)
        # Remove duplicates
        managed_users = list(set(managed_users))
    else:
        managed_users = [current_user]
        all_teams = current_user.teams

    # Handle add member
    if request.method == 'POST' and request.form.get('form_action') == 'add_member':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'member')
        team_ids = request.form.getlist('teams')
        if not username or not password or not team_ids:
            flash('All fields are required.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
        else:
            user = User(username=username, password_hash=password, role=role, is_active=True)
            for tid in team_ids:
                team = Team.query.get(int(tid))
                if team:
                    user.teams.append(team)
            db.session.add(user)
            db.session.commit()
            flash('User added successfully!', 'success')
        return redirect(url_for('team_management'))

    # Handle add team (super_lead/admin only)
    if request.method == 'POST' and request.form.get('form_action') == 'add_team' and current_user.role in ['super_lead', 'admin']:
        team_name = request.form.get('team_name')
        if team_name and not Team.query.filter_by(name=team_name).first():
            db.session.add(Team(name=team_name))
            db.session.commit()
            flash('Team added successfully!', 'success')
        else:
            flash('Team already exists or invalid.', 'danger')
        return redirect(url_for('team_management'))

    # Handle edit team name (super_lead only)
    if request.method == 'POST' and request.form.get('form_action') == 'edit_team_name' and current_user.role == 'super_lead':
        team_id = request.form.get('team_id')
        new_team_name = request.form.get('new_team_name', '').strip()
        if team_id and new_team_name:
            team = Team.query.get(int(team_id))
            if team and not Team.query.filter(Team.name == new_team_name, Team.id != team.id).first():
                team.name = new_team_name
                db.session.commit()
                flash('Team name updated.', 'success')
            else:
                flash('Invalid or duplicate team name.', 'danger')
        else:
            flash('Team name cannot be blank.', 'danger')
        return redirect(url_for('team_management'))

    # Handle delete team (super_lead only)
    if request.method == 'POST' and request.form.get('form_action') == 'delete_team' and current_user.role == 'super_lead':
        team_id = request.form.get('team_id')
        team = Team.query.get(int(team_id))
        if team and team.name != 'Default':
            has_users = len(team.users) > 0
            has_activities = False
            for user in team.users:
                if Activity.query.join(Activity.assignees).filter(Activity.assignees.any(id=user.id)).count() > 0:
                    has_activities = True
                    break
            if has_users or has_activities:
                flash('Cannot delete team: team has users or activities.', 'danger')
            else:
                db.session.delete(team)
                db.session.commit()
                flash('Team deleted.', 'success')
        else:
            flash('Cannot delete this team.', 'danger')
        return redirect(url_for('team_management'))

    # Handle edit user (super_lead/team_lead)
    if request.method == 'POST' and request.form.get('form_action') == 'edit_user':
        user_id = request.form.get('user_id')
        user = User.query.get(int(user_id))
        if user:
            user.username = request.form.get('username')
            user.role = request.form.get('role')
            # Update teams
            team_ids = request.form.getlist('teams')
            user.teams = [Team.query.get(int(tid)) for tid in team_ids if Team.query.get(int(tid))]
            # Update active status
            user.is_active = bool(request.form.get('is_active'))
            db.session.commit()
            flash('User updated successfully!', 'success')
        else:
            flash('User not found.', 'danger')
        return redirect(url_for('team_management'))

    # --- FY filter logic ---
    fy = session.get('financial_year')
    if fy:
        start_date, end_date = get_financial_year_dates(fy)
    else:
        now = datetime.now()
        start_date, end_date = get_financial_year_dates(f"{str(now.year-1)[-2:]}-{str(now.year)[-2:]}")
    # --- END FY filter logic ---
    # For each managed user, set has_activities flag for template
    for u in managed_users:
        u.has_activities = Activity.query.join(Activity.assignees)\
            .filter(Activity.assignees.any(id=u.id))\
            .filter(Activity.start_date >= start_date, Activity.start_date <= end_date).count() > 0
    # Build team activity summary for the team management page
    team_summaries = {}
    all_statuses = set()
    for team in all_teams:
        team_members = team.users
        activities = Activity.query.join(Activity.assignees)\
            .filter(User.id.in_([m.id for m in team_members]))\
            .filter(Activity.start_date >= start_date, Activity.start_date <= end_date).distinct().all()
        status_counts = {}
        for a in activities:
            status_counts[a.status] = status_counts.get(a.status, 0) + 1
            all_statuses.add(a.status)
        team_summaries[team.id] = {
            'total': len(activities),
            'status_counts': status_counts,
            'num_members': len(team_members),
        }
    # Attach summary to each team for template
    for team in all_teams:
        team.summary = team_summaries.get(team.id, {'total': 0, 'status_counts': {}, 'num_members': 0})
    # Order managed_users: super_lead first, then team_lead, then member, then admin (if present)
    role_order = {'super_lead': 0, 'team_lead': 1, 'member': 2, 'admin': 3}
    managed_users = sorted(managed_users, key=lambda u: (role_order.get(u.role, 99), u.username.lower()))
    return render_template('pending_approvals.html', managed_users=managed_users, all_teams=all_teams)

@app.route('/approve_user/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    # Only allow approval if current_user is a team lead for a member, or super lead/admin
    if user.role == 'member' and current_user.role == 'team_lead':
        if not set([t.id for t in current_user.teams]).intersection([t.id for t in user.teams]):
            flash('Not authorized to approve this user.', 'danger')
            return redirect(url_for('team_management'))
    elif current_user.role not in ['super_lead', 'admin']:
        flash('Not authorized to approve this user.', 'danger')
        return redirect(url_for('team_management'))
    user.is_active = True
    db.session.commit()
    flash('User approved.', 'success')
    return redirect(url_for('team_management'))

def get_financial_year_dates(fy_str):
    # fy_str: e.g. '23-24' or '24-25'
    start_year = int('20' + fy_str.split('-')[0])
    start_date = datetime(start_year, 4, 1)
    end_date = datetime(start_year + 1, 3, 31, 23, 59, 59)
    return start_date, end_date

@app.route('/set_financial_year', methods=['POST'])
def set_financial_year():
    fy = request.form.get('financial_year')
    session['financial_year'] = fy
    return redirect(request.referrer or url_for('dashboard'))

@app.context_processor
def inject_financial_years():
    # Debug: print DB file and tables
    print('DB file in use:', db.engine.url)
    inspector = inspect(db.engine)
    print('Tables:', inspector.get_table_names())
    # Find min and max years from Activity data, fallback to current year
    min_year = db.session.query(db.func.min(Activity.start_date)).scalar()
    max_year = db.session.query(db.func.max(Activity.start_date)).scalar()
    if min_year and max_year:
        min_fy = min_year.year if min_year.month >= 4 else min_year.year - 1
        max_fy = max_year.year if max_year.month >= 4 else max_year.year - 1
        years = list(range(min_fy, max_fy + 1))  # +1, not +2
    else:
        now = datetime.now()
        years = [now.year - 1, now.year]
    available_fys = [f"{str(y)[-2:]}-{str(y+1)[-2:]}" for y in years]
    selected_fy = session.get('financial_year', available_fys[-1])
    return dict(
        available_financial_years=available_fys,
        selected_financial_year=selected_fy
    )