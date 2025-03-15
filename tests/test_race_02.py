#!/usr/bin/env python3

import datetime
import json
import os

import pytest
import requests_mock
import yaml
from ultra_tracker_fixtures import *

from ultra_tracker.models import caltopo, course, race


@pytest.fixture
def caltopo_session():
    return caltopo.CaltopoSession("testcredid", "dGVzdGtleQ==")


@pytest.fixture
def race_02_path():
    return os.path.join(os.path.dirname(__file__), "test_data", "02")


@pytest.fixture
def race_02_config(race_02_path):
    race_config_file = os.path.join(race_02_path, "race_config.yml")
    with open(race_config_file, "r") as file:
        config_02 = yaml.safe_load(file)
    return config_02


@pytest.fixture
def caltopo_map_02(caltopo_session, requests_mock, race_02_path):
    map_id = "02"
    data_file = os.path.join(race_02_path, "map_data.json")
    with open(data_file, "r") as f:
        map_mock_response = json.loads(f.read())
    requests_mock.get(f"https://caltopo.com/api/v1/map/{map_id}/since/0", json=map_mock_response)

    requests_mock.real_http = True
    # elevation_data_file = os.path.join(race_02_path, "elevation_data.json")
    # with open(elevation_data_file, "r") as f:
    #    elev_mock_response = json.loads(f.read())
    # requests_mock.post("https://caltopo.com/dem/pointstats", json=elev_mock_response)
    return caltopo.CaltopoMap(map_id, caltopo_session)


@pytest.fixture
def course_02(caltopo_map_02, race_02_config):
    return course.Course(
        caltopo_map_02, race_02_config["aid_stations"], "Route 02", race_02_config["route_distance"]
    )


@pytest.fixture
def runner_02(caltopo_map_02, race_02_path, requests_mock):
    data_file = os.path.join(race_02_path, "map_data.json")
    with open(data_file, "r") as f:
        map_mock_response = json.loads(f.read())
    for marker_id in map_mock_response["result"]["ids"]["Marker"]:
        requests_mock.post(
            f"https://caltopo.com/api/v1/map/02/Marker/{marker_id}",
            json={"result": {}, "status": "ok"},
        )
    return race.Runner(caltopo_map_02, "Runner", [0, 0], None, False)


@pytest.fixture
def race_02(race_02_path, caltopo_map_02, course_02, runner_02):
    race_config_file = os.path.join(race_02_path, "race_config.yml")
    with open(race_config_file, "r") as file:
        config_data = yaml.safe_load(file)

    if os.path.exists("/tmp/data_store.json"):
        os.remove("/tmp/data_store.json")

    return race.Race(
        config_data["race_name"],
        caltopo_map_02,
        course_02.timezone.localize(
            datetime.datetime.strptime(config_data["start_time"], "%Y-%m-%dT%H:%M:%S")
        ),
        "/tmp/data_store.json",
        course_02,
        runner_02,
    )


@pytest.fixture
def race_02_post_log(race_02_path):
    post_log_file = os.path.join(race_02_path, "post_log.json")
    with open(post_log_file, "r") as f:
        post_log = json.loads(f.read())
    return post_log


@pytest.fixture
def race_02_expected_mile_marks(race_02_path):
    emm = os.path.join(race_02_path, "expected_mile_marks.json")
    with open(emm, "r") as f:
        expected_mile_marks = json.loads(f.read())
    return expected_mile_marks


def test_race_02_full(race_02, race_02_post_log, race_02_expected_mile_marks):
    mile_mark_progression = []
    race_02.runner.race = race_02
    for ping_data in race_02_post_log:
        race_02.ingest_ping(ping_data)
        mile_mark_progression.append(float(round(race_02.runner.mile_mark, 2)))
    assert_lists_equal_with_percentage(mile_mark_progression, race_02_expected_mile_marks)
