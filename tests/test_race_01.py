#!/usr/bin/env python3


import datetime
import json
import os

import pytest
import requests_mock
import yaml
from ultra_tracker_fixtures import *

from ultra_tracker import application, database, ut_socket
from ultra_tracker.models import caltopo, course, race


@pytest.fixture
def race_01_path():
    return os.path.join(os.path.dirname(__file__), "test_data", "01")


@pytest.fixture
def race_01_config(race_01_path):
    race_config_file = os.path.join(race_01_path, "race_config.yml")
    with open(race_config_file, "r") as file:
        config_01 = yaml.safe_load(file)
    return config_01


@pytest.fixture
def caltopo_map_01(caltopo_session, requests_mock, race_01_path):
    map_id = "01"
    data_file = os.path.join(race_01_path, "map_data.json")
    with open(data_file, "r") as f:
        map_mock_response = json.loads(f.read())
    requests_mock.get(f"https://caltopo.com/api/v1/map/{map_id}/since/0", json=map_mock_response)

    requests_mock.real_http = True
    # elevation_data_file = os.path.join(race_01_path, "elevation_data.json")
    # with open(elevation_data_file, "r") as f:
    #    elev_mock_response = json.loads(f.read())

    # requests_mock.post("https://caltopo.com/dem/pointstats", json=elev_mock_response)
    return caltopo.CaltopoMap(map_id, caltopo_session)


@pytest.fixture
def course_01(caltopo_map_01, race_01_config):
    return course.Course(
        caltopo_map_01, race_01_config["aid_stations"], "Route 01", race_01_config["route_distance"]
    )


@pytest.fixture
def runner_01(caltopo_map_01, race_01_path, requests_mock):
    data_file = os.path.join(race_01_path, "map_data.json")
    with open(data_file, "r") as f:
        map_mock_response = json.loads(f.read())
    for marker_id in map_mock_response["result"]["ids"]["Marker"]:
        requests_mock.post(
            f"https://caltopo.com/api/v1/map/01/Marker/{marker_id}",
            json={"result": {}, "status": "ok"},
        )
    return race.Runner(caltopo_map_01, "Runner", [0, 0], None, True)


@pytest.fixture
def race_01(race_01_path, caltopo_map_01, course_01, runner_01, race_01_config):

    if os.path.exists("/tmp/data_store.json"):
        os.remove("/tmp/data_store.json")

    return race.Race(
        race_01_config["race_name"],
        caltopo_map_01,
        course_01.timezone.localize(
            datetime.datetime.strptime(race_01_config["start_time"], "%Y-%m-%dT%H:%M:%S")
        ),
        "/tmp/data_store.json",
        course_01,
        runner_01,
    )


@pytest.fixture
def race_01_post_log(race_01_path):
    post_log_file = os.path.join(race_01_path, "post_log.json")
    with open(post_log_file, "r") as f:
        post_log = json.loads(f.read())
    return post_log


@pytest.fixture
def race_01_expected_mile_marks(race_01_path):
    emm = os.path.join(race_01_path, "expected_mile_marks.json")
    with open(emm, "r") as f:
        expected_mile_marks = json.loads(f.read())
    return expected_mile_marks


def test_race_01_full(race_01, race_01_post_log, race_01_expected_mile_marks):
    mile_mark_progression = []
    race_01.runner.race = race_01

    database.connect("sqlite:////tmp/ut_datastore.db")
    socketio = ut_socket.socketio
    app = application.create_app()

    for ping_data in race_01_post_log:
        race_01.ingest_ping(ping_data)
        mile_mark_progression.append(float(round(race_01.runner.mile_mark, 2)))
    # with open('/tmp/mi', 'w') as f:
    #    f.write(json.dumps(mile_mark_progression))
    assert_lists_equal_with_percentage(mile_mark_progression, race_01_expected_mile_marks)
