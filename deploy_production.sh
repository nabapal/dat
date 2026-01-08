#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ENV_FILE="$PROJECT_ROOT/infra/.env.production"
ENV_TEMPLATE="$PROJECT_ROOT/infra/.env.production.example"
DB_DIR="$PROJECT_ROOT/infra/db"
USER_DATA_DIR="$PROJECT_ROOT/user_data"
SEED=0
# Auto-stash behavior: set AUTO_STASH=1 to stash local changes before updating, and
# AUTO_STASH_POP=1 to automatically pop them back after a successful deploy.
AUTO_STASH=0
AUTO_STASH_POP=0
STASH_CREATED=0
STASH_REF=""

usage() {
  cat <<'EOF'
Usage: ./deploy_production.sh [--seed] [--auto-stash] [--auto-stash-pop]

Options:
  --seed            Run seed_demo.py inside the container after the stack is up
  --auto-stash      Automatically stash local changes before updating the repo
  --auto-stash-pop  Pop the stash after a successful deploy (use with caution)
  -h,--help         Show this help text
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --seed)
      SEED=1
      shift
      ;;
    --auto-stash)
      AUTO_STASH=1
      shift
      ;;
    --auto-stash-pop)
      AUTO_STASH=1
      AUTO_STASH_POP=1
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

# Optionally update the checked-out code to the desired ref before deploying.
# Set DEPLOY_REF (e.g. 'origin/main' or a tag/sha) to control what gets deployed.
DEPLOY_REF="${DEPLOY_REF:-origin/main}"
if [[ "${SKIP_GIT_UPDATE:-0}" != "1" ]]; then
  if command -v git >/dev/null 2>&1 && [[ -d "$PROJECT_ROOT/.git" ]]; then
    echo "Updating repository to '$DEPLOY_REF'..."
    pushd "$PROJECT_ROOT" >/dev/null
    if [[ -n "$(git status --porcelain)" ]]; then
      if [[ "${AUTO_STASH:-0}" == "1" ]]; then
        echo "Auto-stashing local changes..."
        STASH_NAME=$(git stash push -m "deploy_autostash_$(date -u +%Y%m%dT%H%M%SZ)")
        if [[ "$STASH_NAME" == "No local changes to save" || -z "$STASH_NAME" ]]; then
          STASH_CREATED=0
          echo "No local changes detected to stash."
        else
          STASH_CREATED=1
          STASH_REF=$(git rev-parse --short refs/stash || true)
          echo "Stashed changes -> ${STASH_REF}"
        fi
      else
        echo "Error: working tree has uncommitted changes in $PROJECT_ROOT. Commit/stash or set SKIP_GIT_UPDATE=1 or use --auto-stash to stash automatically." >&2
        popd >/dev/null
        exit 1
      fi
    fi
    git fetch --all --prune
    git reset --hard "$DEPLOY_REF"
    echo "Repository updated to $(git rev-parse --short HEAD)"
    popd >/dev/null
  else
    echo "Git not available or not a git repository; skipping code update." >&2
  fi
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
  if [[ "${STASH_CREATED:-0}" == "1" ]]; then
    echo "Note: local changes were stashed as ${STASH_REF}. You can restore them later with 'git stash pop' in $PROJECT_ROOT." >&2
  fi
  exit 1
fi

echo "Deployment complete. Application is available on port $APP_PORT"

# Restore stashed changes if requested
if [[ "${AUTO_STASH_POP:-0}" == "1" && "${STASH_CREATED:-0}" == "1" ]]; then
  echo "Restoring stashed changes..."
  pushd "$PROJECT_ROOT" >/dev/null
  set +e
  git stash pop
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    echo "Warning: git stash pop reported conflicts or failed to apply. Inspect and resolve manually; check 'git stash list'." >&2
  else
    echo "Stashed changes restored."
  fi
  popd >/dev/null
else
  if [[ "${STASH_CREATED:-0}" == "1" ]]; then
    echo "Note: local changes were stashed as ${STASH_REF}; to restore them run 'git stash pop' in $PROJECT_ROOT or run with --auto-stash-pop next time." >&2
  fi
fi

# Run optional seed after the app is healthy
if [[ $SEED -eq 1 ]]; then
  echo "Running seed_demo.py inside the web container..."
  "${COMPOSE[@]}" --env-file "$ENV_FILE" exec -T web python seed_demo.py
fi
