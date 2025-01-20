#!/usr/bin/env python3


from ultra_tracker_fixtures import *


def test_race_01_full(race_01, race_01_post_log, race_01_expected_mile_marks):
    mile_mark_progression = []
    for ping_data in race_01_post_log:
        race_01.ingest_ping(ping_data)
        mile_mark_progression.append(float(round(race_01.runner.mile_mark, 2)))
    assert mile_mark_progression == race_01_expected_mile_marks
