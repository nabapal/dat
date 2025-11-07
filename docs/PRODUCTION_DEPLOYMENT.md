# Production Deployment with Docker

This guide describes how to run the DAT Flask application in a production-like environment using Docker while persisting the SQLite database and the `user_data/` directory on the host operating system.

## Deployment Plan Overview

1. **Containerized application runtime**
   - Build an image from the project `Dockerfile` based on `python:3.10-slim`.
   - Run the Flask application behind Gunicorn (`gunicorn --bind 0.0.0.0:8000 run:app`).
   - Expose the host port defined in `APP_PORT` (we use `8009` in production; change as needed).

2. **Persistent host storage**
   - Mount `./infra/db` from the host into `/data` in the container so the SQLite file (`activity_tracker.db`) lives on the host.
   - Mount the existing `./user_data` directory into `/app/user_data` to share uploads/data with the host.

3. **Configuration management**
   - Use `infra/.env.production` (not committed) for secrets and runtime overrides.
   - `SECRET_KEY` **must** be changed before deploying; `DATABASE_URL` defaults to the mounted SQLite file `sqlite:////data/activity_tracker.db`.

4. **Orchestration**
   - `docker-compose.yml` defines a single `web` service.
   - `deploy_production.sh` prepares directories, validates config, builds the image, and starts the stack.
   - Optional `--seed` flag executes `seed_demo.py` inside the running container.

5. **Ongoing operations**
   - `docker compose logs web -f` to follow logs.
   - `docker compose restart web` for zero-downtime config tweaks.
   - Back up `infra/db/activity_tracker.db` and `user_data/` regularly with host tooling.

## Prerequisites

- Docker Engine 20.10+ and Docker Compose v2 (or legacy `docker-compose`) installed on the host.
- Port `8000` (or custom `APP_PORT`) available on the host.
- Excel source files required by `inspect_excel.py` accessible within the repository structure before seeding.

## One-Time Setup

1. **Clone the repository** on the deployment host and change into the repo directory.
2. **Create the environment file**:

   ```bash
   cp infra/.env.production.example infra/.env.production
   ```

   Edit `infra/.env.production` and set:

   - `SECRET_KEY` to a long random string (use `python -c 'import secrets; print(secrets.token_urlsafe(32))'`).
   - Adjust `APP_PORT` to the host port you want to expose (set it to `8009` in production or any free port).
   - Leave `DATABASE_URL=sqlite:////data/activity_tracker.db` unless you are pointing to an external database.

3. **Verify host directories** (the deployment script will also create them):

   ```bash
   mkdir -p infra/db
   mkdir -p user_data
   ```

## Deploying the Stack

Run the helper script from the repository root:

```bash
./deploy_production.sh
```

The script will:

1. Validate that `infra/.env.production` exists and contains a non-placeholder `SECRET_KEY`.
2. Ensure `infra/db/` and `user_data/` directories exist for bind-mounting.
3. Detect Docker Compose (v2 plugin or legacy binary).
4. Build the image defined in the `Dockerfile` and start the `web` service in detached mode.
5. Print the port where the application is exposed (the value of `APP_PORT`, e.g. `8009`).

### Seeding Data

To rebuild and seed the database in one step, append `--seed`:

```bash
./deploy_production.sh --seed
```

After the container is running, the script invokes `python seed_demo.py` inside the container. The script drops and recreates all tables, imports Excel data via `inspect_excel.py`, and normalizes statuses.

You can re-run the seeding command manually later:

```bash
docker compose --env-file infra/.env.production exec -T web python seed_demo.py
```

## Updating an Existing Deployment

When fresh changes land in `main`, pull them onto the server and redeploy:

```bash
cd /home/naba/prepod/dat
git fetch origin
git pull --ff-only origin main
sudo docker compose --env-file infra/.env.production up -d --build
sudo docker compose --env-file infra/.env.production exec -T web python seed_demo.py  # optional reseed
```

Always rerun the seeding step if the source Excel files have changed or you need a clean activity dataset.

## Routine Operations

- **View logs**: `docker compose --env-file infra/.env.production logs -f web`
- **Restart service**: `docker compose --env-file infra/.env.production restart web`
- **Stop stack**: `docker compose --env-file infra/.env.production down`
- **Update image**: pull latest code, then `./deploy_production.sh` (Compose rebuilds incrementally).
- **Clear activity data**: `sqlite3 infra/db/activity_tracker.db "DELETE FROM activity_update; DELETE FROM activity;"`

## Backup and Restore

- **Database**: Back up `infra/db/activity_tracker.db` with your preferred file backup solution.
- **User data**: Back up the `user_data/` directory.
- To restore, stop the stack, replace the files, and run `docker compose up -d` to bring the container back online.

## Rollback Strategy

1. Keep previous application image tags by using Git tags or branches and rebuilding as needed.
2. Maintain dated snapshots of `infra/db/activity_tracker.db` and `user_data/` to roll back data changes.
3. To revert quickly, check out the previous Git commit, restore the matching backups, and run `./deploy_production.sh` again.
