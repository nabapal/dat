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
