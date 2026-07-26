#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

docker compose down
git pull origin prod
docker compose build
docker compose up -d
docker image prune -f