#!/usr/bin/env python3


from ultra_tracker.models import tracker
import pytz
import pytest
import datetime


@pytest.fixture
def raw_ping_data():
    return {
        "Version": "3.0",
        "Events": [
            {
                "addresses": [],
                "transportMode": "Satellite",
                "imei": "123456789012345",
                "messageCode": 0,
                "freeText": "",
                "timeStamp": 1721571300000,
                "point": {
                    "latitude": 38.04270386695862,
                    "longitude": -107.66809701919556,
                    "altitude": 2887.2566,
                    "gpsFix": 2,
                    "course": 225.0,
                    "speed": 3.003,
                },
                "status": {
                    "autonomous": 0,
                    "lowBattery": 0,
                    "intervalChange": 0,
                    "resetDetected": 0,
                },
            }
        ],
    }


@pytest.fixture
def raw_ping_data_no_loc():
    return {
        "Version": "3.0",
        "Events": [
            {
                "addresses": [],
                "transportMode": "Satellite",
                "imei": "123456789012345",
                "messageCode": 1,
                "freeText": "",
                "timeStamp": 1721551474166,
                "point": {
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "altitude": -422.0,
                    "gpsFix": 0,
                    "course": 0.0,
                    "speed": 0.0,
                },
                "status": {
                    "autonomous": 0,
                    "lowBattery": 2,
                    "intervalChange": 0,
                    "resetDetected": 0,
                },
            }
        ],
    }


@pytest.fixture
def basic_ping(raw_ping_data):
    return tracker.Ping(raw_ping_data)


@pytest.fixture
def ping_without_location(raw_ping_data_no_loc):
    return tracker.Ping(raw_ping_data_no_loc)


def test_ping__str__(basic_ping):
    assert (
        str(basic_ping)
        == "PING 2024-07-21 08:15:00-06:00 | 225.0° | [38.04270386695862, -107.66809701919556]"
    )


def test_ping_no_loc__str__(ping_without_location):
    assert str(ping_without_location) == "PING 2024-07-21 08:44:34+00:00 | 0.0° | [0.0, 0.0]"


def test_ping_latlon(basic_ping):
    assert basic_ping.latlon == [38.04270386695862, -107.66809701919556]


def test_ping_lonlat(basic_ping):
    assert basic_ping.lonlat == [-107.66809701919556, 38.04270386695862]


def test_ping_latlonalt(basic_ping):
    assert basic_ping.latlonalt == [38.04270386695862, -107.66809701919556, 9472.626640382057]


def test_extract_timestamp():
    assert tracker.Ping.extract_timestamp(
        1721571300000, pytz.timezone("America/New_York")
    ) == datetime.datetime.fromtimestamp(1721571300, pytz.timezone("America/New_York"))
    assert tracker.Ping.extract_timestamp(
        1721571300, pytz.timezone("America/New_York")
    ) == datetime.datetime.fromtimestamp(1721571300, pytz.timezone("America/New_York"))


def test_ping_as_json(basic_ping):
    assert basic_ping.as_json == {
        "altitude": 9472.626640382057,
        "gps_fix": "3D Fix",
        "heading": 225.0,
        "latlon": [38.04270386695862, -107.66809701919556],
        "lonlat": [-107.66809701919556, 38.04270386695862],
        "message_code": 0,
        "speed": 3.003,
        "status": {"autonomous": 0, "intervalChange": 0, "lowBattery": 0, "resetDetected": 0},
        "timestamp": datetime.datetime.fromtimestamp(1721571300, pytz.timezone("America/Denver")),
        "timestamp_raw": 1721571300000,
    }
