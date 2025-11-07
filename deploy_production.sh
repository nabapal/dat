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

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "Docker Compose v1 or v2 is required." >&2
  exit 1
fi

"${COMPOSE[@]}" --env-file "$ENV_FILE" up -d --build

echo "Deployment started. Containers are running in the background."

if [[ $SEED -eq 1 ]]; then
  echo "Running seed_demo.py inside the web container..."
  "${COMPOSE[@]}" --env-file "$ENV_FILE" exec -T web python seed_demo.py
fi

APP_PORT=$(grep -E '^APP_PORT=' "$ENV_FILE" | cut -d'=' -f2)
if [[ -z "${APP_PORT:-}" ]]; then
  APP_PORT=8000
fi

echo "Deployment complete. Application is available on port $APP_PORT."
