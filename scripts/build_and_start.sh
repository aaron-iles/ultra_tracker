#!/usr/bin/env bash

set -e

python3 -m build --wheel

if systemctl --user list-unit-files --type=service | grep -q "^ultra-tracker.service"; then
    systemctl --user start ultra-tracker
else
    podman-compose up
fi
