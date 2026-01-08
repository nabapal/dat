# Daily Activity Tracker

This is an enterprise-grade daily activity tracker for teams. Team members can add and update their daily activities, while team leads can view dashboards, assign activities, and generate reports.

## Features
- User authentication (login)
- Add, edit, and update activities
- Team dashboard for leads
- Activity updates and logs
- Activity reports with summary stats
- Demo data seeding

## Setup
1. **Install dependencies** (in a virtual environment):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install flask flask_sqlalchemy flask_login flask_wtf wtforms
   ```

2. **Seed demo data**:
   ```bash
   flask seed_demo
   ```

3. **Run the app**:
   ```bash
   ./run.sh
   ```

4. **Login with demo users**:
   - Team Lead: `alice` / `alice`
   - Member: `bob` / `bob`, `carol` / `carol`

## File Structure
- `app/` - Main Flask app (models, routes, templates)
- `seed_demo.py` - Script to seed demo data
- `run.sh` - Shell script to run the app

## Notes
- For production, update the `SECRET_KEY` and use hashed passwords.

---

## Development deployment ✅
- Quick run (local development):
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  # create a local env file if needed
  cp .env.example .env
  ./run.sh
  ```
- Use `flask` or `run.sh` for iterative development; templates and static assets are served from source.
- For debugging: enable the Flask debug mode (`FLASK_ENV=development`) and check logs.

## Production deployment 🔒
- This project includes a helper script `deploy_production.sh` that performs safe deploy steps: backup (SQLite), optional git update, pull or build images, optional DB migrations and healthcheck.

### Basic usage
- Deploy the latest `origin/main` (default):
  ```bash
  ./deploy_production.sh
  ```
- Deploy a specific ref or tag (useful for releases):
  ```bash
  DEPLOY_REF=origin/main ./deploy_production.sh
  DEPLOY_REF=v1.2.3 ./deploy_production.sh
  ```

### Useful environment flags
- `FORCE_BUILD=1` — build images on the host (`docker compose up -d --build`) instead of pulling images (useful for quick deploys but CI-built images are recommended for production).
- `SKIP_GIT_UPDATE=1` — do not reset the repo (deploy whatever is checked out).
- `AUTO_STASH=1` and `AUTO_STASH_POP=1` — stash local changes before updating and optionally pop them after a successful deploy.
- `DEPLOY_REF` — git ref to deploy (branch, tag or commit SHA).

### Safety & rollback
- The script **backs up** the SQLite DB (if present) into `infra/backups/` before deploy.
- If healthcheck fails, the script prints logs and exits; perform rollback by restoring the previous image or checkout.

---

## Importing user Excel data 📥
User activity is imported from Excel spreadsheets placed in the `user_data/` directory. Filenames should be `username.xlsx` (case-insensitive). The importer expects the header row to be the 3rd row and uses the first 7 columns for activity metadata, with subsequent date columns treated as per-day updates.

### CLI usage (import specific files or all)
- Import all Excel files in `user_data/`:
  ```bash
  python inspect_excel.py
  ```
- Import one or more specific users (pass usernames without extension or filenames):
  ```bash
  python inspect_excel.py -f alice
  python inspect_excel.py -f alice bob.xlsx
  # enable verbose logging to see created/updated records per file
  python inspect_excel.py -f Sumit --verbose
  ```
- Use a custom directory:
  ```bash
  python inspect_excel.py -d /path/to/user_data -f alice
  ```

Notes:
- The importer will create a `User` entry if the username does not exist, with a default password of `username@123` and role `member`. Assign teams/roles through the UI if needed.
- `seed_demo.py` performs a full reset (drops and recreates tables) and then imports all Excel files; use it only when you want a fresh demo dataset.

---

If you want, I can also add a sample Excel template to `docs/` to help your team prepare files that import cleanly.
