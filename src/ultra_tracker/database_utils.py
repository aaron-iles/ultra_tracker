#!/usr/bin/env python3


import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import requests
from psycopg2.extras import execute_values

from .models.course import AidStation, Leg
from .models.race import Race, Runner
from .models.tracker import Ping

log = logging.getLogger(__name__)
#  host=PGHOST, port=PGPORT, dbname=PGDATABASE, user=PGUSER, password=PGPASSWORD

# TODO should we use TIMESTAMPTZ or TIMESTAMPTZTZ

# TODO what do we need in the postgres?
# stats: start time, update, moving time, elapsed time,mile mark,altitud, pace, est fin
# TODO map_url?
# TODO course profile?

runners_table_create_sql = """
    CREATE TABLE IF NOT EXISTS runners (
        name TEXT PRIMARY KEY,
        mile_mark DOUBLE PRECISION,
        altitude DOUBLE PRECISION,
        average_overall_pace DOUBLE PRECISION,
        average_moving_pace DOUBLE PRECISION,
        elapsed_time DOUBLE PRECISION,
        stoppage_time DOUBLE PRECISION,
        moving_time DOUBLE PRECISION,
        last_update TIMESTAMPTZ,
        est_finish_date TIMESTAMPTZ,
        est_finish_time DOUBLE PRECISION,
        course_deviation DOUBLE PRECISION
    );
    """


race_table_create_sql = """
    CREATE TABLE IF NOT EXISTS race (
        name TEXT PRIMARY KEY,
        start_time TIMESTAMPTZ,
        timezone TEXT,
        started BOOLEAN,
        map_url TEXT,
        distance DOUBLE PRECISION,
        distances JSONB,
        elevations JSONB
    );
    """

race_upsert_sql = """
    INSERT INTO race (
        name,
        start_time,
        timezone,
        started,
        map_url,
        distance,
        distances,
        elevations
    ) VALUES (
        %(name)s,
        %(start_time)s,
        %(timezone)s,
        %(started)s,
        %(map_url)s,
        %(distance)s,
        %(distances)s::jsonb,
        %(elevations)s::jsonb
    )
    ON CONFLICT (name) DO UPDATE SET
        start_time = EXCLUDED.start_time,
        timezone = EXCLUDED.timezone,
        started = EXCLUDED.started,
        map_url = EXCLUDED.map_url,
        distance = EXCLUDED.distance,
        distances = EXCLUDED.distances,
        elevations = EXCLUDED.elevations;
    """

runner_upsert_sql = """
    INSERT INTO runners (
        name,
        mile_mark,
        altitude,
        average_overall_pace,
        average_moving_pace,
        elapsed_time,
        stoppage_time,
        moving_time,
        last_update,
        est_finish_date,
        est_finish_time,
        course_deviation
    ) VALUES (
        %(name)s,
        %(mile_mark)s,
        %(altitude)s,
        %(average_overall_pace)s,
        %(average_moving_pace)s,
        %(elapsed_time)s,
        %(stoppage_time)s,
        %(moving_time)s,
        %(last_update)s,
        %(est_finish_date)s,
        %(est_finish_time)s,
        %(course_deviation)s
    )
    ON CONFLICT (name) DO UPDATE SET
        mile_mark = EXCLUDED.mile_mark,
        altitude = EXCLUDED.altitude,
        average_overall_pace = EXCLUDED.average_overall_pace,
        average_moving_pace = EXCLUDED.average_moving_pace,
        elapsed_time = EXCLUDED.elapsed_time,
        stoppage_time = EXCLUDED.stoppage_time,
        moving_time = EXCLUDED.moving_time,
        last_update = EXCLUDED.last_update,
        est_finish_date = EXCLUDED.est_finish_date,
        est_finish_time = EXCLUDED.est_finish_time,
        course_deviation = EXCLUDED.course_deviation;
"""

pings_table_create_sql = """
    CREATE TABLE IF NOT EXISTS pings (
        timestamp TIMESTAMPTZ,
        timestamp_raw BIGINT PRIMARY KEY,
        status JSONB,
        heading DOUBLE PRECISION,
        latlon JSONB,
        altitude DOUBLE PRECISION,
        gps_fix TEXT,
        message_code TEXT,
        speed DOUBLE PRECISION
    );
    """

ping_upsert_sql = """
    INSERT INTO pings (
        timestamp,
        timestamp_raw,
        status,
        heading,
        latlon,
        altitude,
        gps_fix,
        message_code,
        speed
    ) VALUES (
        %(timestamp)s,
        %(timestamp_raw)s,
        %(status)s,
        %(heading)s,
        %(latlon)s::jsonb,
        %(altitude)s,
        %(gps_fix)s,
        %(message_code)s,
        %(speed)s
    )
    ON CONFLICT (timestamp_raw) DO UPDATE SET
        timestamp = EXCLUDED.timestamp,
        status = EXCLUDED.status,
        heading = EXCLUDED.heading,
        latlon = EXCLUDED.latlon,
        altitude = EXCLUDED.altitude,
        gps_fix = EXCLUDED.gps_fix,
        message_code = EXCLUDED.message_code,
        speed = EXCLUDED.speed;
    """


legs_table_create_sql = """
    CREATE TABLE IF NOT EXISTS legs (
        name TEXT PRIMARY KEY,
        display_name TEXT,
        mile_mark DOUBLE PRECISION,
        end_mile_mark DOUBLE PRECISION,
        distance DOUBLE PRECISION,
        gain DOUBLE PRECISION,
        loss DOUBLE PRECISION,
        estimated_duration DOUBLE PRECISION,
        arrival_time TIMESTAMPTZ,
        departure_time TIMESTAMPTZ,
        estimated_arrival_time TIMESTAMPTZ,
        estimated_departure_time TIMESTAMPTZ,
        is_passed BOOLEAN
    );
    """

leg_upsert_sql = """
    INSERT INTO legs (
        name,
        display_name,
        mile_mark,
        end_mile_mark,
        distance,
        gain,
        loss,
        estimated_duration,
        arrival_time,
        departure_time,
        estimated_arrival_time,
        estimated_departure_time,
        is_passed
    ) VALUES (
        %(name)s,
        %(display_name)s,
        %(mile_mark)s,
        %(end_mile_mark)s,
        %(distance)s,
        %(gain)s,
        %(loss)s,
        %(estimated_duration)s,
        %(arrival_time)s,
        %(departure_time)s,
        %(estimated_arrival_time)s,
        %(estimated_departure_time)s,
        %(is_passed)s
    )
    ON CONFLICT (name) DO UPDATE SET
        display_name = EXCLUDED.display_name,
        mile_mark = EXCLUDED.mile_mark,
        end_mile_mark = EXCLUDED.end_mile_mark,
        distance = EXCLUDED.distance,
        gain = EXCLUDED.gain,
        loss = EXCLUDED.loss,
        estimated_duration = EXCLUDED.estimated_duration,
        arrival_time = EXCLUDED.arrival_time,
        departure_time = EXCLUDED.departure_time,
        estimated_arrival_time = EXCLUDED.estimated_arrival_time,
        estimated_departure_time = EXCLUDED.estimated_departure_time,
        is_passed = EXCLUDED.is_passed;
    """

aid_stations_table_create_sql = """
    CREATE TABLE IF NOT EXISTS aidstations (
        name TEXT PRIMARY KEY,
        display_name TEXT,
        mile_mark DOUBLE PRECISION,
        end_mile_mark DOUBLE PRECISION,
        altitude DOUBLE PRECISION,
        gmaps_url TEXT,
        comments TEXT,
        coordinates JSONB,
        estimated_duration DOUBLE PRECISION,
        arrival_time TIMESTAMPTZ,
        departure_time TIMESTAMPTZ,
        estimated_arrival_time TIMESTAMPTZ,
        estimated_departure_time TIMESTAMPTZ,
        is_passed BOOLEAN,
        stoppage_time DOUBLE PRECISION
    );
    """


aid_station_upsert_sql = """
    INSERT INTO aidstations (
        name,
        display_name,
        mile_mark,
        end_mile_mark,
        altitude,
        gmaps_url,
        comments,
        coordinates,
        estimated_duration,
        arrival_time,
        departure_time,
        estimated_arrival_time,
        estimated_departure_time,
        is_passed,
        stoppage_time
    ) VALUES (
        %(name)s,
        %(display_name)s,
        %(mile_mark)s,
        %(end_mile_mark)s,
        %(altitude)s,
        %(gmaps_url)s,
        %(comments)s,
        %(coordinates)s::jsonb,
        %(estimated_duration)s,
        %(arrival_time)s,
        %(departure_time)s,
        %(estimated_arrival_time)s,
        %(estimated_departure_time)s,
        %(is_passed)s,
        %(stoppage_time)s
    )
    ON CONFLICT (name) DO UPDATE SET
        display_name = EXCLUDED.display_name,
        mile_mark = EXCLUDED.mile_mark,
        end_mile_mark = EXCLUDED.end_mile_mark,
        altitude = EXCLUDED.altitude,
        gmaps_url = EXCLUDED.gmaps_url,
        comments = EXCLUDED.comments,
        coordinates = EXCLUDED.coordinates,
        estimated_duration = EXCLUDED.estimated_duration,
        arrival_time = EXCLUDED.arrival_time,
        departure_time = EXCLUDED.departure_time,
        estimated_arrival_time = EXCLUDED.estimated_arrival_time,
        estimated_departure_time = EXCLUDED.estimated_departure_time,
        is_passed = EXCLUDED.is_passed,
        stoppage_time = EXCLUDED.stoppage_time;
    """


######################################


class Database:
    def __init__(self, host, port, dbname, user, password):
        """
        Initialize a Database connection.

        :param str dsn: PostgreSQL DSN string
        """
        self.conn = psycopg2.connect(
            host=host, port=port, dbname=dbname, user=user, password=password
        )
        self.cursor = self.conn.cursor()
        self.cursor.execute(race_table_create_sql)
        self.cursor.execute(runners_table_create_sql)
        self.cursor.execute(pings_table_create_sql)
        self.cursor.execute(aid_stations_table_create_sql)
        self.cursor.execute(legs_table_create_sql)
        self.conn.commit()

    def save(self, object_):
        """ """
        if isinstance(object_, AidStation):
            upsert_sql = aid_station_upsert_sql
        elif isinstance(object_, Leg):
            upsert_sql = leg_upsert_sql
        elif isinstance(object_, Runner):
            upsert_sql = runner_upsert_sql
        elif isinstance(object_, Ping):
            upsert_sql = ping_upsert_sql
        elif isinstance(object_, Race):
            upsert_sql = race_upsert_sql
        # log.info(object_.database_record)
        self.cursor.execute(upsert_sql, object_.database_record)
        self.conn.commit()


# TODO cursor.close() and conn.close()
