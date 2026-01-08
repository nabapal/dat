import os
import pandas as pd
from app import app, db
from app.models import Activity, ActivityUpdate, Node, ActivityType, Status, User
from datetime import datetime
import traceback

# Helper: try to detect which row contains the proper header by scanning first N rows
def detect_header_row(file_path, sheet_name, max_scan_rows=5, engine='openpyxl'):
    """Try reading the sheet with header rows 0..max_scan_rows-1 and return the first header row
    whose column names contain any of the expected header keywords. Returns an integer header
    index or None if nothing suitable is found."""
    expected_keywords = ['activity', 'activity id', 'start', 'start date', 'activity id', 'activityid']
    try:
        for header_row in range(0, max_scan_rows):
            try:
                df_try = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine, header=header_row, nrows=1)
            except Exception:
                continue
            cols = [str(c).strip().lower() for c in list(df_try.columns) if isinstance(c, (str,))]
            for kw in expected_keywords:
                for c in cols:
                    if kw in c:
                        return header_row
        return None
    except Exception:
        return None

def _series_lookup(series, candidates, default=None):
    """Return the first non-null value for the provided candidate column names."""
    for name in candidates:
        if name in series and series[name] is not None and not pd.isna(series[name]):
            return series[name]
    return default


def import_user_excels(user_data_dir='user_data', files=None, verbose=False):
    """Import Excel files from ``user_data_dir`` into the database.

    If ``files`` is provided, it should be an iterable of filenames (relative to
    ``user_data_dir``) or absolute paths; only those files will be imported. If
    ``files`` is None, all `*.xlsx` files in the directory will be imported.
    """
    with app.app_context():
        # Build list of files to process
        to_process = []
        print(f"Starting import_user_excels(user_data_dir={user_data_dir}, files={files}, verbose={verbose})")
        try:
            cwd = os.getcwd()
            print(f"CWD: {cwd}")
            ud_abs = os.path.abspath(user_data_dir) if not os.path.isabs(user_data_dir) else user_data_dir
            print(f"user_data_dir resolved: {ud_abs}")
            if os.path.exists(ud_abs):
                print(f"user_data_dir contents: {os.listdir(ud_abs)}")
            else:
                print(f"user_data_dir does not exist: {ud_abs}")
        except Exception as e:
            print(f"Error inspecting user_data_dir: {e}")
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

        if verbose:
            print('Files to process:', to_process)

        for file_path in to_process:
            filename = os.path.basename(file_path)
            print(f"Importing {filename}... (path={file_path})")
            try:
                print(f"  file size: {os.path.getsize(file_path)} bytes")
            except Exception:
                pass
            # per-file counters
            created_activities = 0
            created_updates = 0
            skipped_rows = 0
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
                if verbose: print(f"Created user: {user.username} (id={user.id})")
            else:
                if verbose: print(f"Found existing user: {user.username} (id={user.id})")

            # Inspect workbook and available sheets (helpful in container)
            try:
                xl = pd.ExcelFile(file_path, engine='openpyxl')
                print(f"  Available sheets: {xl.sheet_names}")
            except Exception as e:
                print(f"  Could not open workbook for {filename}: {e}")
                if verbose:
                    traceback.print_exc()
                continue

            # Build candidate sheet names and try to locate match (more flexible)
            candidates = [
                username.capitalize(),
                username.capitalize() + ' ',
                username.title(),
                username.upper(),
                username
            ]
            matched_sheet = None
            for c in candidates:
                if c in xl.sheet_names:
                    matched_sheet = c
                    break
            if not matched_sheet:
                # try stripped/lower matching
                for s in xl.sheet_names:
                    if isinstance(s, str) and s.strip().lower() == username:
                        matched_sheet = s
                        break
            if not matched_sheet:
                # fallback to first sheet but warn
                matched_sheet = xl.sheet_names[0] if xl.sheet_names else None
                print(f"  Warning: no sheet explicitly matching {username}; falling back to first sheet: {matched_sheet}")

            if not matched_sheet:
                print(f"  No usable sheet found in {filename}; skipping file")
                continue

            # Try to detect header row automatically (scan first few rows)
            header_row = None
            header_row = detect_header_row(file_path, matched_sheet, max_scan_rows=6)
            if header_row is None:
                header_row = 2  # fall back to previous default
                print(f"  Could not auto-detect header row for {matched_sheet}; falling back to header={header_row}")
            else:
                if verbose:
                    print(f"  Detected header row: {header_row} for sheet {matched_sheet}")
            try:
                df_full = pd.read_excel(file_path, sheet_name=matched_sheet, engine='openpyxl', header=header_row)
            except Exception as e:
                print(f"  Error reading sheet {matched_sheet} from {filename}: {e}")
                if verbose:
                    traceback.print_exc()
                continue

            # Normalize string column headers (strip whitespace, preserve datetime headings)
            df_full.rename(columns=lambda c: c.strip() if isinstance(c, str) else c, inplace=True)
            df_main = df_full.iloc[:, 0:7]
            df_updates = df_full.iloc[:, 7:]
            if verbose:
                print(f"  df_main.shape={df_main.shape}, df_updates.shape={df_updates.shape}")
                print(f"  df_main.columns={list(df_main.columns)}")
                print(f"  df_main.head(3)=\n{df_main.head(3)}")

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
                    skipped_rows += 1
                    if verbose:
                        reasons = []
                        if not activity_id or activity_id.lower() == 'nan':
                            reasons.append('missing Activity ID')
                        if not details or details.lower() == 'nan':
                            reasons.append('missing Activity details')
                        if pd.isnull(start_date):
                            reasons.append('missing or invalid Start date')
                        print(f"    Skipping row idx={idx}: {', '.join(reasons)}")
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
                    created_activities += 1
                    if verbose: print(f"  Created activity {activity.activity_id} for user {user.username}")
                else:
                    if verbose: print(f"  Found existing activity {activity.activity_id} for user {user.username}")
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
                                    if verbose: print(f"    Updated existing update for {activity.activity_id} on {update_date}")
                                    created_updates += 1
                            else:
                                update = ActivityUpdate(
                                    activity_id=activity.id,
                                    update_text=normalized_text,
                                    update_date=update_date,
                                    updated_by=user.id
                                )
                                db.session.add(update)
                                created_updates += 1
                                if verbose: print(f"    Added update for {activity.activity_id} on {update_date}")
                db.session.commit()
            if verbose:
                print(f"Finished {filename}: created_activities={created_activities}, created_updates={created_updates}, skipped_rows={skipped_rows}")
            else:
                print(f"Finished {filename}: created_activities={created_activities}, created_updates={created_updates}, skipped_rows={skipped_rows}")
        print('All user Excel files imported.')
    # keep return for programmatic use
    return True


def delete_user_and_related(username, yes=False, verbose=False):
    """Delete a user (case-insensitive) and their activities and updates.

    This function is destructive and will prompt for confirmation unless `yes` is True.
    Returns True on success, False otherwise.
    """
    with app.app_context():
        user = User.query.filter(db.func.lower(User.username) == username.lower()).first()
        if not user:
            print(f"User '{username}' not found.")
            return False
        # gather counts
        activity_q = Activity.query.filter_by(user_id=user.id)
        activity_ids = [a.id for a in activity_q.all()]
        activity_count = len(activity_ids)
        updates_on_owned = ActivityUpdate.query.filter(ActivityUpdate.activity_id.in_(activity_ids)).count() if activity_count else 0
        updates_by_user = ActivityUpdate.query.filter_by(updated_by=user.id).count()
        assigned_activities = Activity.query.filter(Activity.assignees.any(id=user.id)).all()
        assigned_count = len(assigned_activities)

        print(f"About to delete user: {user.username} (id={user.id})")
        print(f"  Activities owned: {activity_count}")
        print(f"  Activity updates on owned activities: {updates_on_owned}")
        print(f"  Activity updates authored by user: {updates_by_user}")
        print(f"  Activities where user is an assignee: {assigned_count}")

        if not yes:
            confirm = input("Type 'DELETE' to confirm deletion of the user and all related data: ")
            if confirm != 'DELETE':
                print('Aborted by user.')
                return False

        try:
            # Remove assignee relationships
            for act in assigned_activities:
                if user in act.assignees:
                    act.assignees.remove(user)
            db.session.commit()

            # Delete activity updates on owned activities
            if activity_ids:
                deleted_updates_owned = db.session.query(ActivityUpdate).filter(ActivityUpdate.activity_id.in_(activity_ids)).delete(synchronize_session=False)
                if verbose: print(f"Deleted {deleted_updates_owned} updates on owned activities")

            # Delete activities owned by user
            deleted_activities = db.session.query(Activity).filter(Activity.user_id == user.id).delete(synchronize_session=False)
            if verbose: print(f"Deleted {deleted_activities} activities owned by user")

            # Delete activity updates authored by user on other activities
            deleted_updates_by_user = db.session.query(ActivityUpdate).filter(ActivityUpdate.updated_by == user.id).delete(synchronize_session=False)
            if verbose: print(f"Deleted {deleted_updates_by_user} activity updates authored by user")

            # Finally delete the user record
            db.session.delete(user)
            db.session.commit()
            print(f"Deleted user '{username}' and related data (activities: {deleted_activities}, updates_on_owned: {deleted_updates_owned if activity_ids else 0}, updates_by_user: {deleted_updates_by_user})")
            return True
        except Exception as e:
            print(f"Error while deleting user {username}: {e}")
            traceback.print_exc()
            db.session.rollback()
            return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Import user Excel files into DAT or perform user maintenance')
    parser.add_argument('-d', '--dir', default='user_data', help='Directory containing Excel files (default: user_data)')
    parser.add_argument('-f', '--files', nargs='+', help='Specific Excel filenames or usernames to import (without extension)')
    parser.add_argument('--delete-user', nargs='+', help='Username(s) to delete along with their activities (destructive)')
    parser.add_argument('--yes', action='store_true', help='Confirm destructive actions without prompting')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging during import or delete')
    args = parser.parse_args()

    # Handle destructive delete option first
    if args.delete_user:
        for username in args.delete_user:
            ok = delete_user_and_related(username, yes=args.yes, verbose=args.verbose)
            if not ok:
                print(f"Failed to delete user {username}")
        # exit after delete operations
        import sys
        sys.exit(0)

    files = None
    if args.files:
        files = args.files
    import_user_excels(user_data_dir=args.dir, files=files, verbose=args.verbose)
