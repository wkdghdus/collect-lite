#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
cd "$SCRIPT_DIR"

error() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

warn() {
  printf 'Warning: %s\n' "$1" >&2
}

command -v docker >/dev/null 2>&1 || error "Docker is required to boot CollectLite."

if docker compose version >/dev/null 2>&1; then
  COMPOSE_STYLE="v2"
elif command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
  COMPOSE_STYLE="v1"
else
  error "Docker Compose is required. Install Docker Compose v2 or docker-compose v1."
fi

[ -f docker-compose.yml ] || error "docker-compose.yml was not found in $SCRIPT_DIR."

docker info >/dev/null 2>&1 || error "Docker is installed, but the Docker daemon is not available."

if [ ! -f .env ]; then
  [ -f .env.example ] || error ".env is missing and .env.example is not available."
  cp .env.example .env
  warn "Created .env from .env.example. Set COHERE_API_KEY before using model features."
elif grep -q '^COHERE_API_KEY=.*your-cohere-api-key-here' .env 2>/dev/null; then
  warn ".env still contains the placeholder COHERE_API_KEY; model features may not work."
fi

printf 'Booting CollectLite with Docker Compose...\n'
printf 'Frontend: http://localhost:3000\n'
printf 'Backend API: http://localhost:8000\n'
printf 'API Docs: http://localhost:8000/docs\n'

if [ "$COMPOSE_STYLE" = "v2" ]; then
  exec docker compose up --build
fi

exec docker-compose up --build
