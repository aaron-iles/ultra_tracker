#!/usr/bin/env bash

# Use this entrypoint script for testing and debugging on the cli without having to run in a 
# container.

# First rebuild the package
python3 -m build --wheel
# Install it (preferably in a venv)
python3 -m pip install --force-reinstall --no-deps dist/ultra_tracker-*.whl

#uwsgi uwsgi.ini --honour-stdin --pyargv '-c data/race_config.yml -d data/ --disable-marker-updates'
uwsgi uwsgi.ini --honour-stdin --pyargv '-c data/race_config.yml -d data/'
