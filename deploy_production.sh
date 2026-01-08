#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ENV_FILE="$PROJECT_ROOT/infra/.env.production"
ENV_TEMPLATE="$PROJECT_ROOT/infra/.env.production.example"
DB_DIR="$PROJECT_ROOT/infra/db"
USER_DATA_DIR="$PROJECT_ROOT/user_data"
SEED=0

usage() {
  cat <<'EOF'
Usage: ./deploy_production.sh [--seed]

Options:
  --seed    Run seed_demo.py inside the container after the stack is up
  -h,--help Show this help text
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --seed)
      SEED=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! -f "$ENV_TEMPLATE" ]]; then
  echo "Missing template file at $ENV_TEMPLATE" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ENV_TEMPLATE" "$ENV_FILE"
  echo "Created $ENV_FILE from template. Update the values (especially SECRET_KEY) and re-run." >&2
  exit 1
fi

if grep -q "SECRET_KEY=change-me" "$ENV_FILE"; then
  echo "Set a strong SECRET_KEY in $ENV_FILE before deploying." >&2
  exit 1
fi

mkdir -p "$DB_DIR" "$USER_DATA_DIR"

# create backups dir and backup local SQLite DB if present
BACKUP_DIR="$PROJECT_ROOT/infra/backups"
mkdir -p "$BACKUP_DIR"
if [[ -f "$PROJECT_ROOT/app/activity_tracker.db" ]]; then
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  cp "$PROJECT_ROOT/app/activity_tracker.db" "$BACKUP_DIR/activity_tracker-${ts}.db"
  echo "Backed up SQLite DB -> $BACKUP_DIR/activity_tracker-${ts}.db"
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "Docker Compose v1 or v2 is required." >&2
  exit 1
fi

# By default pull immutable images and start containers. Set FORCE_BUILD=1 to build on host.
if [[ "${FORCE_BUILD:-0}" == "1" ]]; then
  echo "Building images on host (FORCE_BUILD=1)."
  "${COMPOSE[@]}" --env-file "$ENV_FILE" up -d --build
else
  echo "Pulling images (recommended for production)..."
  "${COMPOSE[@]}" --env-file "$ENV_FILE" pull --ignore-pull-failures || true
  echo "Starting containers..."
  "${COMPOSE[@]}" --env-file "$ENV_FILE" up -d
fi

echo "Containers started. Running DB migrations (if any)..."
# attempt to run migrations inside the web container; tolerant to missing tools
set +e
"${COMPOSE[@]}" --env-file "$ENV_FILE" run --rm web bash -lc 'if command -v flask >/dev/null 2>&1; then flask db upgrade --no-input; elif command -v alembic >/dev/null 2>&1; then alembic upgrade head; fi'
set -e

# Determine app port for healthcheck
APP_PORT=$(grep -E '^APP_PORT=' "$ENV_FILE" | cut -d'=' -f2)
if [[ -z "${APP_PORT:-}" ]]; then APP_PORT=8000; fi

# wait for a healthy responsive app
MAX_WAIT=${MAX_WAIT:-60}
n=0
until curl -fsS --max-time 3 "http://127.0.0.1:${APP_PORT}/" >/dev/null 2>&1 || [[ $n -ge $MAX_WAIT ]]; do
  sleep 1; n=$((n+1)); echo "Waiting for app to respond... ${n}s"
done

if [[ $n -ge $MAX_WAIT ]]; then
  echo "ERROR: healthcheck failed after ${MAX_WAIT}s. Dumping last logs for debugging:" >&2
  "${COMPOSE[@]}" --env-file "$ENV_FILE" logs --no-color --timestamps --tail=200 web || true
  exit 1
fi

echo "Deployment complete. Application is available on port $APP_PORT"

# Run optional seed after the app is healthy
if [[ $SEED -eq 1 ]]; then
  echo "Running seed_demo.py inside the web container..."
  "${COMPOSE[@]}" --env-file "$ENV_FILE" exec -T web python seed_demo.py
fi
