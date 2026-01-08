import os
import pandas as pd
from app import app, db
from app.models import Activity, ActivityUpdate, Node, ActivityType, Status, User
from datetime import datetime

def _series_lookup(series, candidates, default=None):
    """Return the first non-null value for the provided candidate column names."""
    for name in candidates:
        if name in series and series[name] is not None and not pd.isna(series[name]):
            return series[name]
    return default


def import_user_excels(user_data_dir='user_data', files=None):
    """Import Excel files from ``user_data_dir`` into the database.

    If ``files`` is provided, it should be an iterable of filenames (relative to
    ``user_data_dir``) or absolute paths; only those files will be imported. If
    ``files`` is None, all `*.xlsx` files in the directory will be imported.
    """
    with app.app_context():
        # Build list of files to process
        to_process = []
        if files:
            if isinstance(files, str):
                files = [files]
            for f in files:
                original_f = f
                # normalize filename: add .xlsx if missing and user passed a bare username
                if not f.endswith('.xlsx') and os.path.basename(f) == f:
                    f = f + '.xlsx'
                # 1) if absolute path given and exists, use it
                if os.path.isabs(f) and os.path.exists(f):
                    to_process.append(f)
                    continue
                # 2) if relative path provided and exists (e.g., user_data/Sumit.xlsx), use it
                if os.path.exists(f):
                    to_process.append(os.path.abspath(f))
                    continue
                # 3) otherwise try relative to user_data_dir
                p = os.path.join(user_data_dir, f)
                if os.path.exists(p):
                    to_process.append(p)
                    continue
                # not found in any of the above locations
                print(f"Warning: specified file {original_f} not found (checked as absolute, relative and under {user_data_dir}); skipping.")
        else:
            for filename in os.listdir(user_data_dir):
                if filename.endswith('.xlsx'):
                    to_process.append(os.path.join(user_data_dir, filename))

        if not to_process:
            print('No Excel files to import.')
            return

        for file_path in to_process:
            filename = os.path.basename(file_path)
            print(f"Importing {filename}...")
            if not filename.endswith('.xlsx'):
                print(f"Skipping non-xlsx file: {filename}")
                continue
            username = filename.replace('.xlsx', '').lower()
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
            # find sheet containing user data
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

            # Normalize string column headers (strip whitespace, preserve datetime headings)
            df_full.rename(columns=lambda c: c.strip() if isinstance(c, str) else c, inplace=True)
            df_main = df_full.iloc[:, 0:7]
            df_updates = df_full.iloc[:, 7:]
            for idx, row in df_main.iterrows():
                activity_id = str(_series_lookup(row, ['Activity ID', 'ActivityID', 'Activity_Id'], '')).strip()
                details = str(_series_lookup(row, ['Activity', 'Activity Details', 'Activity Description', 'Activity '], '')).strip()
                node_name = str(_series_lookup(row, ['Node Name', 'Node'], '')).strip()
                activity_type = str(_series_lookup(row, ['Activity Type', 'Type'], '')).strip()
                status_raw = _series_lookup(row, ['Status', 'Current Status', 'Activity Status'], '')
                status = str(status_raw).strip() if status_raw is not None else ''
                start_raw = _series_lookup(row, ['Start date', 'Start Date', 'Start'], None)
                start_date = pd.to_datetime(start_raw, errors='coerce', dayfirst=True)
                if not activity_id or activity_id.lower() == 'nan' or not details or details.lower() == 'nan' or pd.isnull(start_date):
                    continue
                end_date = None
                update_row = df_updates.loc[idx] if idx in df_updates.index else pd.Series(dtype='object')
                end_raw = _series_lookup(update_row, ['End Date', 'End date', 'End'], None)
                if end_raw is not None:
                    end_date_val = pd.to_datetime(end_raw, errors='coerce', dayfirst=True)
                    if not (pd.isnull(end_date_val) or str(end_date_val).lower() == 'nat'):
                        end_date = end_date_val
                duration = None
                if 'Duration' in df_main.columns:
                    duration_val = row.get('Duration', None)
                    if not pd.isnull(duration_val):
                        duration = duration_val
                normalized_status = status if status else 'pending'
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
                        status=normalized_status,
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
                            update_date = col.date()
                            normalized_text = str(update_text).strip()
                            existing_update = ActivityUpdate.query.filter_by(
                                activity_id=activity.id,
                                update_date=update_date,
                                updated_by=user.id
                            ).first()
                            if existing_update:
                                if existing_update.update_text != normalized_text:
                                    existing_update.update_text = normalized_text
                            else:
                                update = ActivityUpdate(
                                    activity_id=activity.id,
                                    update_text=normalized_text,
                                    update_date=update_date,
                                    updated_by=user.id
                                )
                                db.session.add(update)
                db.session.commit()
        print('All user Excel files imported.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Import user Excel files into DAT')
    parser.add_argument('-d', '--dir', default='user_data', help='Directory containing Excel files (default: user_data)')
    parser.add_argument('-f', '--files', nargs='+', help='Specific Excel filenames or usernames to import (without extension)')
    args = parser.parse_args()

    files = None
    if args.files:
        files = args.files
    import_user_excels(user_data_dir=args.dir, files=files)
