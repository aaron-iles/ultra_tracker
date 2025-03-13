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
def race_03_path():
    return os.path.join(os.path.dirname(__file__), "test_data", "03")


@pytest.fixture
def aid_stations_map_03(race_03_path):
    race_config_file = os.path.join(race_03_path, "race_config.yml")
    with open(race_config_file, "r") as file:
        config_data = yaml.safe_load(file)
    return config_data["aid_stations"]


@pytest.fixture
def caltopo_map_03(caltopo_session, requests_mock, race_03_path):
    map_id = "03"
    data_file = os.path.join(race_03_path, "map_data.json")
    with open(data_file, "r") as f:
        map_mock_response = json.loads(f.read())
    requests_mock.get(f"https://caltopo.com/api/v1/map/{map_id}/since/0", json=map_mock_response)

    elevation_data_file = os.path.join(race_03_path, "elevation_data.json")
    with open(elevation_data_file, "r") as f:
        elev_mock_response = json.loads(f.read())

    requests_mock.post("https://caltopo.com/dem/pointstats", json=elev_mock_response)

    return caltopo.CaltopoMap(map_id, caltopo_session)


@pytest.fixture
def course_03(caltopo_map_03, aid_stations_map_03):
    return course.Course(caltopo_map_03, aid_stations_map_03, "Route 03")


@pytest.fixture
def runner_03(caltopo_map_03, race_03_path, requests_mock):
    data_file = os.path.join(race_03_path, "map_data.json")
    with open(data_file, "r") as f:
        map_mock_response = json.loads(f.read())
    for marker_id in map_mock_response["result"]["ids"]["Marker"]:
        requests_mock.post(
            f"https://caltopo.com/api/v1/map/03/Marker/{marker_id}",
            json={"result": {}, "status": "ok"},
        )
    return race.Runner(caltopo_map_03, "Runner", [0, 0], None, False)


@pytest.fixture
def race_03(race_03_path, caltopo_map_03, course_03, runner_03):
    race_config_file = os.path.join(race_03_path, "race_config.yml")
    with open(race_config_file, "r") as file:
        config_data = yaml.safe_load(file)

    if os.path.exists("/tmp/data_store.json"):
        os.remove("/tmp/data_store.json")

    return race.Race(
        config_data["race_name"],
        caltopo_map_03,
        course_03.timezone.localize(
            datetime.datetime.strptime(config_data["start_time"], "%Y-%m-%dT%H:%M:%S")
        ),
        "/tmp/data_store.json",
        course_03,
        runner_03,
    )


@pytest.fixture
def race_03_post_log(race_03_path):
    post_log_file = os.path.join(race_03_path, "post_log.json")
    with open(post_log_file, "r") as f:
        post_log = json.loads(f.read())
    return post_log


@pytest.fixture
def race_03_expected_mile_marks(race_03_path):
    emm = os.path.join(race_03_path, "expected_mile_marks.json")
    with open(emm, "r") as f:
        expected_mile_marks = json.loads(f.read())
    return expected_mile_marks


def test_race_03_full(race_03, race_03_post_log, race_03_expected_mile_marks):
    mile_mark_progression = []
    race_03.runner.race = race_03
    for ping_data in race_03_post_log:
        race_03.ingest_ping(ping_data)
        mile_mark_progression.append(float(round(race_03.runner.mile_mark, 2)))
    assert_lists_equal_with_percentage(mile_mark_progression, race_03_expected_mile_marks)
