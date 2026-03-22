#!/usr/bin/env bash

set -e

SERVICE_NAME="ultra-tracker"

if systemctl list-unit-files --type=service | grep -q "^${SERVICE_NAME}.service"; then
    sudo systemctl stop "$SERVICE_NAME"
else
    docker compose down
fi

docker rmi ultra_tracker:latest || true
docker volume rm ultra-tracker_postgres-data
rm -rf dist
rm -f data/post_log.txt data/data_store.json
python3 -m build --wheel

if systemctl list-unit-files --type=service | grep -q "^${SERVICE_NAME}.service"; then
    sudo systemctl start "$SERVICE_NAME"
else
    docker compose up
fi

