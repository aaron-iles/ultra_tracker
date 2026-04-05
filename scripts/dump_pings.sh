#!/usr/bin/env bash

set -e

podman exec ultra-tracker-postgres \
  psql -U tracker -d ultra-tracker \
  -t -A -c "SELECT raw FROM pings ORDER BY created_at;"
