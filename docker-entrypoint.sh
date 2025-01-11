#!/usr/bin/env bash
uwsgi uwsgi.ini --pyargv '-c /app/data/race_config.yml -d /app/data/'
