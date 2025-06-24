from app import app, db
from app.models import Activity

with app.app_context():
    activities = Activity.query.all()
    for activity in activities:
        if activity.status:
            normalized = activity.status.strip().lower().replace(' ', '_')
            if activity.status != normalized:
                print(f"Updating '{activity.status}' to '{normalized}' for activity_id {activity.activity_id}")
                activity.status = normalized
    db.session.commit()
print("All activity statuses normalized.")
