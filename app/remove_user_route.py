from flask import redirect, url_for, flash
from flask_login import login_required, current_user
from . import app, db
from .models import User, Activity

@app.route('/remove_user/<int:user_id>', methods=['POST'])
@login_required
def remove_user(user_id):
    user = User.query.get_or_404(user_id)
    # Only allow removal if current_user is a team lead for a member, or super lead/admin
    if user.role == 'member' and current_user.role == 'team_lead':
        if not set([t.id for t in current_user.teams]).intersection([t.id for t in user.teams]):
            flash('Not authorized to remove this user.', 'danger')
            return redirect(url_for('team_management'))
    elif current_user.role not in ['super_lead', 'admin']:
        flash('Not authorized to remove this user.', 'danger')
        return redirect(url_for('team_management'))
    # Only remove if user has no assigned activities
    assigned_activities = Activity.query.join(Activity.assignees).filter(Activity.assignees.any(id=user.id)).count()
    if assigned_activities > 0:
        flash('Cannot remove user: user has assigned activities.', 'danger')
        return redirect(url_for('team_management'))
    db.session.delete(user)
    db.session.commit()
    flash('User removed.', 'success')
    return redirect(url_for('team_management'))
