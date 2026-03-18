#!/usr/bin/env bash

docker compose down
docker rmi ultra_tracker:latest
rm -rf dist
python3 -m build --wheel
sudo rm -rf pgdata/
rm -f data/post_log.txt data/data_store.json data/ut_datastore.db
docker compose up
