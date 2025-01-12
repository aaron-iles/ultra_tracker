#!/usr/bin/env python3




from ultra_tracker.models import caltopo
import pytest


@pytest.fixture
def caltopo_sessison():
    return caltopo.CaltopoSession("test_cred_id", "test_key")


@pytest.fixture
def caltopo_map(caltopo_sessison, requests_mock):
    map_id = "test_map_id"
    response = {} # TODO
    requests_mock.get(f"https://caltopo.com/m/{map_id}")
    return caltopo.CaltopoMap(map_id, caltopo_session)

