#!/usr/bin/env bash

# Use this entrypoint script for testing and debugging on the cli without having to run in a 
# container.

#uwsgi uwsgi.ini --honour-stdin --pyargv '-c data/race_config.yml -d data/ --disable-marker-updates'
uwsgi uwsgi.ini --honour-stdin --pyargv '-c data/race_config.yml -d data/ -v'
