#!/usr/bin/env python3


import datetime
import json
import os

import pytest
import requests_mock
import yaml
from ultra_tracker_fixtures import *

from ultra_tracker import application, ut_socket
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
    return race.Runner(caltopo_map_01, "Runner", [0, 0], None, False)


@pytest.fixture
def race_01(race_01_path, caltopo_map_01, course_01, runner_01, race_01_config, database):

    return race.Race(
        race_01_config["race_name"],
        caltopo_map_01,
        course_01.timezone.localize(
            datetime.datetime.strptime(race_01_config["start_time"], "%Y-%m-%dT%H:%M:%S")
        ),
        course_01,
        runner_01,
        database,
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


def test_race_01_full(race_01, race_01_post_log, race_01_expected_mile_marks, subtests):
    mile_mark_progression = []
    race_01.runner.race = race_01

    socketio = ut_socket.socketio
    app = application.create_app()

    for ping_data in race_01_post_log:
        race_01.ingest_ping(ping_data)
        mile_mark_progression.append(float(round(race_01.runner.mile_mark, 2)))

    with subtests.test(name="test_mile_marks"):
        assert_lists_equal_with_percentage(mile_mark_progression, race_01_expected_mile_marks)

    with subtests.test(name="test_total_ping_count"):
        database_ping_count = race_01.database.fetch_one("SELECT COUNT(*) FROM pings")[0]
        count = len({item["Events"][0]["timeStamp"] for item in race_01_post_log})
        assert database_ping_count == count

    with subtests.test(name="test_position_report_ping_count"):
        database_ping_count = race_01.database.fetch_one(
            "SELECT COUNT(*) FROM pings WHERE message_code = 'Position Report'"
        )[0]
        count = len(
            {
                item["Events"][0]["timeStamp"]
                for item in race_01_post_log
                if item["Events"][0]["messageCode"] == 0
            }
        )
        assert database_ping_count == count

    with subtests.test(name="test_aid_station_stoppage_time"):
        stoppage_times = race_01.database.fetch_all(
            "SELECT stoppage_time FROM aidstations ORDER BY mile_mark"
        )
        assert stoppage_times == [
            (0.0,),
            (258.884758,),
            (441.718517,),
            (276.376519,),
            (0.0,),
            (0.0,),
            (0.0,),
        ]

    with subtests.test(name="test_aid_station_arrival_time"):
        arrival_times = race_01.database.fetch_all(
            "SELECT arrival_time FROM aidstations ORDER BY mile_mark"
        )
        assert arrival_times == [
            (datetime.datetime(2024, 12, 30, 20, 30, tzinfo=datetime.timezone.utc),),
            (datetime.datetime(2024, 12, 30, 20, 35, 30, tzinfo=datetime.timezone.utc),),
            (datetime.datetime(2024, 12, 30, 21, 3, 51, 560408, tzinfo=datetime.timezone.utc),),
            (datetime.datetime(2024, 12, 30, 22, 37, 30, 27904, tzinfo=datetime.timezone.utc),),
            (datetime.datetime(1970, 1, 1, 0, 0, tzinfo=datetime.timezone.utc),),
            (datetime.datetime(1970, 1, 1, 0, 0, tzinfo=datetime.timezone.utc),),
            (datetime.datetime(1970, 1, 1, 0, 0, tzinfo=datetime.timezone.utc),),
        ]

    # leg duration
    # leg pace
    # aid station departure time
    # overall pace
    # avg pace
    # avg update interval
    # finish time == elapsed time
