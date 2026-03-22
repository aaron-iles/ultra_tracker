#!/usr/bin/env bash

docker compose down
docker rmi ultra_tracker:latest
rm -rf dist
python3 -m build --wheel
rm -f data/post_log.txt data/data_store.json
docker compose up
