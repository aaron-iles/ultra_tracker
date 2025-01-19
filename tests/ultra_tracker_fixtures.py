#!/usr/bin/env python3


import os
import json
from ultra_tracker.models import caltopo
import pytest
import requests_mock


@pytest.fixture
def map_01_path():
    return os.path.join(os.path.dirname(__file__), "test_data", "01")


@pytest.fixture
def caltopo_session():
    return caltopo.CaltopoSession("testcredid", "dGVzdGtleQ==")


@pytest.fixture
def caltopo_line_no_coords():
    return {
        "geometry": {"coordinates": [[]], "type": "LineString"},
        "id": "e26810c4-d12c-11ef-9d17-b6c8914f6ecb",
        "type": "Feature",
        "properties": {
            "stroke-opacity": 1,
            "creator": "XXXXXX",
            "pattern": "solid",
            "description": "",
            "stroke-width": 2,
            "title": "Route",
            "fill": "#FF0000",
            "stroke": "#FF0000",
            "class": "Shape",
            "updated": 1736269309737,
            "folderId": "ead94520-d12c-11ef-9d17-b6c8914f6ecb",
        },
    }


@pytest.fixture
def caltopo_folder():
    return {
        "id": "ead94520-d12c-11ef-9d17-b6c8914f6ecb",
        "type": "Feature",
        "properties": {
            "creator": "XXXXXX",
            "visible": True,
            "title": "Test Folder",
            "class": "Folder",
            "updated": 1736269324716,
            "labelVisible": True,
        },
    }


@pytest.fixture
def aid_stations_map_01():
    return [
        {"name": "01 Aid", "mile_mark": 0.35},
        {"name": "02 Aid", "mile_mark": 1.46},
        {"name": "03 Aid", "mile_mark": 9.8},
        {"name": "04 Aid", "mile_mark": 13.2},
        {"name": "05 Aid", "mile_mark": 13.7},
    ]


@pytest.fixture
def caltopo_map_01(caltopo_session, requests_mock, map_01_path):
    map_id = "01"
    data_file = os.path.join(map_01_path, "map_data.json")
    with open(data_file, "r") as f:
        mock_response = json.loads(f.read())
    requests_mock.get(f"https://caltopo.com/api/v1/map/{map_id}/since/0", json=mock_response)

    elevation_data_file = os.path.join(map_01_path, "elevation_data.json")
    with open(elevation_data_file, "r") as f:
        mock_response = json.loads(f.read())

    requests_mock.post("https://caltopo.com/dem/pointstats", json=mock_response)

    return caltopo.CaltopoMap(map_id, caltopo_session)
