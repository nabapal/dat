# Team Portal (Django)

This is a Django-based team activity tracker and daily team management app, migrated from Flask.

## Apps
- `users`: User authentication, registration, roles
- `teams`: Team management
- `activities`: Activity tracking, updates
- `attributes`: Nodes, activity types, statuses, color badges
- `dashboard`: Dashboards and reporting

## Setup
1. Create and activate a virtual environment
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Create a superuser: `python manage.py createsuperuser`
5. Start the server: `python manage.py runserver`

## Migration Plan
- Models, forms, views, templates, and static files are being migrated from the Flask project to Django apps.
- See `.github/copilot-instructions.md` for workspace-specific Copilot guidance.

## Features
- User registration, login, logout (custom forms, Django best practices)
- Team management (CRUD)
- Activity tracking (CRUD, updates, assignees, status)
- Attribute management (Nodes, Activity Types, Statuses with color badges)
- Dashboard with summary stats
- Django admin for all models

## Testing
Run all tests:
```
python manage.py test
```
All core features are covered by basic tests.

## Deployment Checklist
- Set `DEBUG = False` in `team_portal/settings.py`
- Set `ALLOWED_HOSTS` to your domain or server IP
- Collect static files:
  ```
  python manage.py collectstatic
  ```
- Use a production server (e.g., Gunicorn):
  ```
  gunicorn team_portal.wsgi:application --bind 0.0.0.0:8000
  ```
- Use Nginx or Apache as a reverse proxy
- Set up HTTPS (Let's Encrypt recommended)
- Use a production database (PostgreSQL/MySQL) for scale
- Configure environment variables for secrets

## Example Gunicorn + Nginx
- Gunicorn: `gunicorn team_portal.wsgi:application --bind 127.0.0.1:8000`
- Nginx site config (sample):
  ```
  server {
      listen 80;
      server_name yourdomain.com;
      location /static/ {
          alias /path/to/static/;
      }
      location / {
          proxy_pass http://127.0.0.1:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
      }
  }
  ```

## Further Customization
- Add user profile management, notifications, or reporting as needed.
- See each app's `views.py` and `templates/` for extension points.

---
For questions or contributions, see the project issues or contact the maintainer.
