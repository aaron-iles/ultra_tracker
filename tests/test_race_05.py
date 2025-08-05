#!/usr/bin/env python3

import datetime
import json
import os

import pytest
import requests_mock
import yaml
from ultra_tracker_fixtures import *

from ultra_tracker.models import caltopo, course, race
from ultra_tracker import database, ut_socket, application


@pytest.fixture
def caltopo_session():
    return caltopo.CaltopoSession("testcredid", "dGVzdGtleQ==")


@pytest.fixture
def race_05_path():
    return os.path.join(os.path.dirname(__file__), "test_data", "05")


@pytest.fixture
def race_05_config(race_05_path):
    race_config_file = os.path.join(race_05_path, "race_config.yml")
    with open(race_config_file, "r") as file:
        config_05 = yaml.safe_load(file)
    return config_05


@pytest.fixture
def caltopo_map_05(caltopo_session, requests_mock, race_05_path):
    map_id = "05"
    data_file = os.path.join(race_05_path, "map_data.json")
    with open(data_file, "r") as f:
        map_mock_response = json.loads(f.read())
    requests_mock.get(f"https://caltopo.com/api/v1/map/{map_id}/since/0", json=map_mock_response)

    requests_mock.real_http = True
    # elevation_data_file = os.path.join(race_05_path, "elevation_data.json")
    # with open(elevation_data_file, "r") as f:
    #    elev_mock_response = json.loads(f.read())
    # requests_mock.post("https://caltopo.com/dem/pointstats", json=elev_mock_response)
    return caltopo.CaltopoMap(map_id, caltopo_session)


@pytest.fixture
def course_05(caltopo_map_05, race_05_config):
    return course.Course(
        caltopo_map_05, race_05_config["aid_stations"], "Route 05", race_05_config["route_distance"]
    )


@pytest.fixture
def runner_05(caltopo_map_05, race_05_path, requests_mock):
    data_file = os.path.join(race_05_path, "map_data.json")
    with open(data_file, "r") as f:
        map_mock_response = json.loads(f.read())
    for marker_id in map_mock_response["result"]["ids"]["Marker"]:
        requests_mock.post(
            f"https://caltopo.com/api/v1/map/05/Marker/{marker_id}",
            json={"result": {}, "status": "ok"},
        )
    return race.Runner(caltopo_map_05, "Runner", [0, 0], None, False)


@pytest.fixture
def race_05(race_05_path, caltopo_map_05, course_05, runner_05):
    race_config_file = os.path.join(race_05_path, "race_config.yml")
    with open(race_config_file, "r") as file:
        config_data = yaml.safe_load(file)

    if os.path.exists("/tmp/data_store.json"):
        os.remove("/tmp/data_store.json")

    return race.Race(
        config_data["race_name"],
        caltopo_map_05,
        course_05.timezone.localize(
            datetime.datetime.strptime(config_data["start_time"], "%Y-%m-%dT%H:%M:%S")
        ),
        "/tmp/data_store.json",
        course_05,
        runner_05,
    )


@pytest.fixture
def race_05_post_log(race_05_path):
    post_log_file = os.path.join(race_05_path, "post_log.json")
    with open(post_log_file, "r") as f:
        post_log = json.loads(f.read())
    return post_log


@pytest.fixture
def race_05_expected_mile_marks(race_05_path):
    emm = os.path.join(race_05_path, "expected_mile_marks.json")
    with open(emm, "r") as f:
        expected_mile_marks = json.loads(f.read())
    return expected_mile_marks


def test_race_05_full(race_05, race_05_post_log, race_05_expected_mile_marks):
    mile_mark_progression = []
    race_05.runner.race = race_05
    database.connect("sqlite:////tmp/ut_datastore.db")
    socketio = ut_socket.socketio
    app = application.create_app()
    for ping_data in race_05_post_log:
        race_05.ingest_ping(ping_data)
        mile_mark_progression.append(float(round(race_05.runner.mile_mark, 2)))
    assert_lists_equal_with_percentage(mile_mark_progression, race_05_expected_mile_marks)
