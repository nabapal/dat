import os
import pandas as pd
from app import app, db
from app.models import Activity, ActivityUpdate, Node, ActivityType, Status, User
from datetime import datetime

def import_user_excels(user_data_dir='user_data'):
    """Import all Excel files found in ``user_data_dir`` into the database."""
    with app.app_context():
        for filename in os.listdir(user_data_dir):
            if not filename.endswith('.xlsx'):
                continue
            username = filename.replace('.xlsx', '').lower()
            file_path = os.path.join(user_data_dir, filename)
            user = User.query.filter(db.func.lower(User.username) == username).first()
            if not user:
                user = User(
                    username=username.capitalize(),
                    password_hash=username + '@123',
                    role='member',
                    is_active=True
                )
                db.session.add(user)
                db.session.commit()
            for sheet_name in [username.capitalize(), username.capitalize() + ' ']:
                try:
                    df_full = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl', header=2)
                    break
                except Exception:
                    continue
            else:
                try:
                    xl = pd.ExcelFile(file_path, engine='openpyxl')
                    print(f"Sheet not found for {username} in {filename}. Available sheets: {xl.sheet_names}")
                except Exception as e:
                    print(f"Sheet not found for {username} in {filename}. Could not read sheet names: {e}")
                continue
            df_main = df_full.iloc[:, 0:7]
            df_updates = df_full.iloc[:, 7:]
            for idx, row in df_main.iterrows():
                activity_id = str(row['Activity ID']).strip()
                details = str(row['Activity ']).strip()
                node_name = str(row['Node Name']).strip()
                activity_type = str(row['Activity Type']).strip()
                status = str(row['Status']).strip()
                start_date = pd.to_datetime(row['Start date'], errors='coerce')
                if not activity_id or activity_id.lower() == 'nan' or not details or details.lower() == 'nan' or pd.isnull(start_date):
                    continue
                end_date = None
                if 'End Date' in df_updates.columns:
                    end_date_val = pd.to_datetime(df_updates.loc[idx, 'End Date'], errors='coerce')
                    if not (pd.isnull(end_date_val) or str(end_date_val).lower() == 'nat'):
                        end_date = end_date_val
                duration = None
                if 'Duration' in df_main.columns:
                    duration_val = row.get('Duration', None)
                    if not pd.isnull(duration_val):
                        duration = duration_val
                node = Node.query.filter_by(name=node_name).first()
                if not node and node_name:
                    node = Node(name=node_name)
                    db.session.add(node)
                atype = ActivityType.query.filter_by(name=activity_type).first()
                if not atype and activity_type:
                    atype = ActivityType(name=activity_type)
                    db.session.add(atype)
                stat = Status.query.filter_by(name=status).first()
                if not stat and status:
                    stat = Status(name=status)
                    db.session.add(stat)
                db.session.commit()
                activity = Activity.query.filter_by(activity_id=activity_id).first()
                if not activity:
                    activity = Activity(
                        activity_id=activity_id,
                        details=details,
                        node_name=node_name,
                        activity_type=activity_type,
                        status=status,
                        start_date=start_date,
                        end_date=end_date,
                        duration=duration,
                        user_id=user.id,
                        assigner_id=user.id
                    )
                    db.session.add(activity)
                    db.session.commit()
                if hasattr(activity, 'assignees') and user not in activity.assignees:
                    activity.assignees.append(user)
                    db.session.commit()
                for col in df_updates.columns:
                    if isinstance(col, datetime):
                        update_text = df_updates.loc[idx, col]
                        if pd.notnull(update_text):
                            existing_update = ActivityUpdate.query.filter_by(
                                activity_id=activity.id,
                                update_date=col,
                                updated_by=user.id
                            ).first()
                            if not existing_update:
                                update = ActivityUpdate(
                                    activity_id=activity.id,
                                    update_text=str(update_text),
                                    update_date=col,
                                    updated_by=user.id
                                )
                                db.session.add(update)
                db.session.commit()
    print('All user Excel files imported.')


if __name__ == '__main__':
    import_user_excels()
