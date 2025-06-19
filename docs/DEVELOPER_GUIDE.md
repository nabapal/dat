# Daily Activity Tracker – User & Developer Guide

## Project Overview
The Daily Activity Tracker is a web application for teams to log, manage, and report daily activities. Team members can add and update their activities, while team leads and super leads can assign, review, and report on team progress. The app supports user authentication, team management, activity dashboards, and flexible attribute management.

## Technology Stack
- **Backend:** Python, Flask, SQLAlchemy
- **Frontend:** HTML, Bootstrap (SB Admin 2), Jinja2 templates
- **Database:** SQLite (default), supports PostgreSQL/MySQL with config
- **Dev Tools:** Visual Studio Code, GitHub Copilot, Git
- **CI/CD:** GitHub Actions (example), supports Jenkins, ArgoCD, Azure DevOps
- **Containerization/Deployment:** Docker, Kubernetes, Helm

## Codebase Structure
```
app/
  __init__.py         # Flask app factory
  models.py           # SQLAlchemy ORM models
  routes.py           # Flask routes (views/controllers)
  forms.py            # WTForms for input validation
  templates/          # Jinja2 HTML templates
  static/             # CSS, JS, images
  activity_tracker.db # SQLite DB (dev only)
run.sh                # Shell script to run the app
seed_demo.py          # Demo data seeding script
migrations/           # Alembic DB migrations
k8s/                  # Kubernetes manifests (if present)
helm-chart/           # Helm chart for deployment (if present)
```

## Key Function/Component Descriptions
- **User Authentication:** Login/logout, password change, role-based access (member, team_lead, super_lead, admin)
- **Activity Management:** Add, edit, assign, and update activities; supports multiple assignees
- **Team Management:** Add/edit/remove teams and members, assign roles, manage team attributes
- **Attribute Management:** Manage Nodes, Activity Types, and Statuses (team lead only)
- **Dashboards & Reports:** Team and individual dashboards, activity summaries, status breakdowns
- **CI/CD Pipeline:** Automated build, test, and deploy (see below)

## Setup Instructions
1. **Clone the repository:**
   ```bash
   git clone https://github.com/nabapal/dat.git
   cd dat
   ```
2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   # Or manually:
   pip install flask flask_sqlalchemy flask_login flask_wtf wtforms
   ```
4. **Seed demo data (optional):**
   ```bash
   flask seed_demo
   ```
5. **Run the app locally:**
   ```bash
   ./run.sh
   # or
   flask run
   ```
6. **Login with demo users:**
   - Team Lead: `alice` / `alice`
   - Member: `bob` / `bob`, `carol` / `carol`

## Testing
- **Run tests:**
  ```bash
  pytest
  # or
  python -m unittest discover
  ```
- **Test Coverage:**
  Use `pytest --cov=app` for coverage reports. Ensure all major routes and models are covered.

## CI/CD Pipeline
- **Tools:** GitHub Actions (default), Jenkins, ArgoCD supported
- **Pipeline Steps:**
  1. Checkout code
  2. Install dependencies
  3. Run tests (unit/integration)
  4. Build Docker image
  5. Push image to registry
  6. Deploy to Kubernetes (staging)
  7. (Optional) Run integration tests
  8. Promote to production
- **Example:** See `.github/workflows/deploy.yml` in the repo for a full pipeline.

## Deployment Guide
### Docker
```bash
docker build -t <your-registry>/dat-app:latest .
docker run -d -p 5000:5000 <your-registry>/dat-app:latest
```
### Kubernetes (with Helm)
1. Edit `values.yaml` for your environment
2. Deploy:
   ```bash
   helm install dat-app ./helm-chart -f values.yaml
   ```
### Kubernetes (raw manifests)
```bash
kubectl apply -f k8s/
```
### Secrets & DB
- Store secrets in Kubernetes Secrets or environment variables
- Use managed DB (Cloud SQL, RDS) or persistent volume for SQLite/Postgres
### Ingress & TLS
- Use NGINX Ingress, cert-manager for TLS
### Monitoring
- Integrate with Prometheus, Grafana, ELK/Loki for logs

## Common Issues & Debugging Tips
- **Flask-Login Import Error:** Ensure `flask_login` is installed (`pip install flask_login`)
- **DB Connection Issues:** Check DB URI and credentials in environment/config
- **Static Files Not Loading:** Ensure `static/` is correctly mapped and Flask is not in debug mode for production
- **Kubernetes Deploy Fails:** Check pod logs (`kubectl logs <pod>`), image pull secrets, and resource limits
- **CI/CD Fails:** Review pipeline logs, ensure secrets are set in CI/CD environment

## Contribution Guidelines
- Fork the repo and create a feature branch
- Write clear, tested code and add/modify tests as needed
- Run all tests before submitting a PR
- Follow PEP8 and project code style
- Submit a pull request with a clear description of your changes

## License & Contact
- **License:** MIT (see LICENSE file)
- **Maintainer:** Naba Pal (<nabapal.pal@gmail.com>)
- For issues, open a GitHub issue or contact the maintainer
