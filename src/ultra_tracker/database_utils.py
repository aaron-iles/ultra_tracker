#!/usr/bin/env python3


import logging

import psycopg2
from psycopg2.pool import SimpleConnectionPool

from .models.course import AidStation, Leg
from .models.race import Race, Runner
from .models.tracker import Ping

logger = logging.getLogger(__name__)

RUNNER_TABLE_CREATE_SQL = """
    CREATE TABLE IF NOT EXISTS runner (
        name TEXT,
        mile_mark DOUBLE PRECISION,
        altitude DOUBLE PRECISION,
        average_overall_pace DOUBLE PRECISION,
        average_moving_pace DOUBLE PRECISION,
        elapsed_time DOUBLE PRECISION,
        stoppage_time DOUBLE PRECISION,
        moving_time DOUBLE PRECISION,
        last_update TIMESTAMPTZ PRIMARY KEY,
        est_finish_date TIMESTAMPTZ,
        est_finish_time DOUBLE PRECISION,
        course_deviation DOUBLE PRECISION,
        cumulative_gain DOUBLE PRECISION
    );
    """


RACE_TABLE_CREATE_SQL = """
    CREATE TABLE IF NOT EXISTS race (
        name TEXT PRIMARY KEY,
        start_time TIMESTAMPTZ,
        timezone TEXT,
        started BOOLEAN,
        map_url TEXT,
        distance DOUBLE PRECISION,
        gain BIGINT,
        loss BIGINT,
        distances JSONB,
        elevations JSONB
    );
    """

RACE_UPSERT_SQL = """
    INSERT INTO race (
        name,
        start_time,
        timezone,
        started,
        map_url,
        distance,
        gain,
        loss,
        distances,
        elevations
    ) VALUES (
        %(name)s,
        %(start_time)s,
        %(timezone)s,
        %(started)s,
        %(map_url)s,
        %(distance)s,
        %(gain)s,
        %(loss)s,
        %(distances)s,
        %(elevations)s
    )
    ON CONFLICT (name) DO UPDATE SET
        start_time = EXCLUDED.start_time,
        timezone = EXCLUDED.timezone,
        started = EXCLUDED.started,
        map_url = EXCLUDED.map_url,
        distance = EXCLUDED.distance,
        gain = EXCLUDED.gain,
        loss = EXCLUDED.loss,
        distances = EXCLUDED.distances,
        elevations = EXCLUDED.elevations;
    """

RUNNER_UPSERT_SQL = """
    INSERT INTO runner (
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
        course_deviation,
        cumulative_gain
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
        %(course_deviation)s,
        %(cumulative_gain)s
    )
    ON CONFLICT (last_update) DO UPDATE SET
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
        course_deviation = EXCLUDED.course_deviation,
        cumulative_gain = EXCLUDED.cumulative_gain;
"""

PINGS_TABLE_CREATE_SQL = """
    CREATE TABLE IF NOT EXISTS pings (
        created_at TIMESTAMP DEFAULT NOW(),
        timestamp TIMESTAMPTZ,
        timestamp_raw BIGINT PRIMARY KEY,
        imei TEXT,
        status JSONB,
        heading DOUBLE PRECISION,
        latlon JSONB,
        altitude DOUBLE PRECISION,
        gps_fix TEXT,
        message_code TEXT,
        speed DOUBLE PRECISION,
        raw JSONB
    );
    """

PING_UPSERT_SQL = """
    INSERT INTO pings (
        timestamp,
        timestamp_raw,
        imei,
        status,
        heading,
        latlon,
        altitude,
        gps_fix,
        message_code,
        speed,
        raw
    ) VALUES (
        %(timestamp)s,
        %(timestamp_raw)s,
        %(imei)s,
        %(status)s,
        %(heading)s,
        %(latlon)s,
        %(altitude)s,
        %(gps_fix)s,
        %(message_code)s,
        %(speed)s,
        %(raw)s
    )
    ON CONFLICT (timestamp_raw) DO UPDATE SET
        timestamp = EXCLUDED.timestamp,
        imei = EXCLUDED.imei,
        status = EXCLUDED.status,
        heading = EXCLUDED.heading,
        latlon = EXCLUDED.latlon,
        altitude = EXCLUDED.altitude,
        gps_fix = EXCLUDED.gps_fix,
        message_code = EXCLUDED.message_code,
        speed = EXCLUDED.speed,
        raw = EXCLUDED.raw;
    """


LEGS_TABLE_CREATE_SQL = """
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

LEG_UPSERT_SQL = """
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

AID_STATIONS_TABLE_CREATE_SQL = """
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


AID_STATION_UPSERT_SQL = """
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
        %(coordinates)s,
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


class Database:
    def __init__(self, host, port, dbname, user, password):
        """
        Initialize a Database connection.

        :param str dsn: PostgreSQL DSN string
        """
        self.conn = psycopg2.connect(
            host=host, port=port, dbname=dbname, user=user, password=password
        )
        self.pool = SimpleConnectionPool(
            minconn=1,
            maxconn=300,
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
        )
        # Instantiate the database
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(RACE_TABLE_CREATE_SQL)
                cur.execute(RUNNER_TABLE_CREATE_SQL)
                cur.execute(PINGS_TABLE_CREATE_SQL)
                cur.execute(AID_STATIONS_TABLE_CREATE_SQL)
                cur.execute(LEGS_TABLE_CREATE_SQL)
            conn.commit()
        finally:
            self.pool.putconn(conn)

    @property
    def contains_data(self) -> bool:
        """
        Returns True if at least one runner exists in the database.
        """
        row = self.fetch_one(
            """
            SELECT EXISTS (
                SELECT 1 FROM runner LIMIT 1
            )
        """
        )
        return row[0]

    def execute(self, query, params=None, conn=None):
        """ """
        owns_conn = conn is None
        if owns_conn:
            conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
            if owns_conn:
                conn.commit()
        except Exception:
            if owns_conn:
                conn.rollback()
            raise
        finally:
            if owns_conn:
                self.pool.putconn(conn)

    def fetch_one(self, query, params=None, conn=None):
        owns_conn = conn is None
        if owns_conn:
            conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                result = cur.fetchone()
            return result
        finally:
            if owns_conn:
                self.pool.putconn(conn)

    def fetch_all(self, query, params=None, conn=None):
        owns_conn = conn is None
        if owns_conn:
            conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                results = cur.fetchall()
            return results
        finally:
            if owns_conn:
                self.pool.putconn(conn)


    def save(self, object_, conn=None):
        """ """
        upsert_map = {
            AidStation: AID_STATION_UPSERT_SQL,
            Leg: LEG_UPSERT_SQL,
            Runner: RUNNER_UPSERT_SQL,
            Ping: PING_UPSERT_SQL,
            Race: RACE_UPSERT_SQL,
        }
        try:
            upsert_sql = upsert_map[type(object_)]
        except KeyError as err:
            raise ValueError(f"unsupported object type: {type(object_)}") from err
        self.execute(upsert_sql, object_.database_record, conn=conn)

    def restore(self, object_) -> None:
        """ """
        if isinstance(object_, AidStation):
            self._restore_aidstation(object_)
        elif isinstance(object_, Runner):
            self._restore_runner(object_)
        else:
            raise ValueError(f"unsupported object type: {type(object_)}")

    def _restore_aidstation(self, object_):
        """
        Restore a single AidStation from the database using its name.
        """
        row = self.fetch_one(
            """
            SELECT
                arrival_time,
                estimated_arrival_time,
                departure_time,
                estimated_departure_time,
                is_passed
            FROM aidstations
            WHERE name = %s
            """,
            (object_.name,),
        )

        if row is None:
            return

        object_.arrival_time = row[0]
        object_.estimated_arrival_time = row[1]
        object_.departure_time = row[2]
        object_.estimated_departure_time = row[3]
        object_.is_passed = row[4]

    def _restore_runner(self, runner):
        """
        Restore a single AidStation from the database using its name.
        """
        row = self.fetch_one(
            """
            SELECT mile_mark
            FROM runner
            WHERE name = %s
            ORDER BY last_update DESC
            LIMIT 1
            """,
            (runner.name,),
        )
        if row:
            runner.mile_mark = row[0]
        row = self.fetch_one(
            """
            SELECT raw
            FROM pings
            WHERE message_code = 'Position Report'
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )
        if row:
            ping = Ping(row[0], runner.race.course.timezone)
            runner.last_ping = ping
