#!/usr/bin/env bash

if systemctl --user list-unit-files --type=service | grep -q "^ultra-tracker.service"; then
    systemctl --user stop ultra-tracker
else
    podman-compose down
fi

podman rmi ultra_tracker:latest || true
podman volume prune --force
podman system prune --force --all
rm -rf dist build
rm -f data/post_log.txt data/data_store.json
