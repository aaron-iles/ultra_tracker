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


#  host=PGHOST, port=PGPORT, dbname=PGDATABASE, user=PGUSER, password=PGPASSWORD


# TODO what do we need in the postgres?
# stats: start time, update, moving time, elapsed time,mile mark,altitud, pace, est fin
# TODO map_url?

CREATE TABLE IF NOT EXISTS runners (
    name TEXT PRIMARY KEY,
    mile_mark DOUBLE PRECISION,
    altitude DOUBLE PRECISION,
    average_overall_pace TEXT,
    average_moving_pace TEXT,
    elapsed_time DOUBLE PRECISION,
    stoppage_time DOUBLE PRECISION,
    moving_time DOUBLE PRECISION,
    last_update TIMESTAMP,
    est_finish_date TIMESTAMP,
    est_finish_time DOUBLE PRECISION,
    start_time TIMESTAMP,
    course_deviation DOUBLE PRECISION,
    pings BIGINT,
);





##############


CREATE TABLE IF NOT EXISTS pings (
    timestamp TIMESTAMP,
    timestamp_raw BIGINT,
    status JSONB,
    heading DOUBLE PRECISION,
    latlon JSONB,
    altitude DOUBLE PRECISION,
    gps_fix TEXT,
    message_code TEXT,
    speed DOUBLE PRECISION
);

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
    arrival_time TIMESTAMP,
    departure_time TIMESTAMP,
    estimated_arrival_time TIMESTAMP,
    estimated_departure_time TIMESTAMP,
    is_passed BOOLEAN,
    stoppage_time DOUBLE PRECISION
);


CREATE TABLE IF NOT EXISTS legs (
    name TEXT PRIMARY KEY,
    display_name TEXT,
    mile_mark DOUBLE PRECISION,
    end_mile_mark DOUBLE PRECISION,
    distance DOUBLE PRECISION,
    gain DOUBLE PRECISION,
    loss DOUBLE PRECISION,
    estimated_duration DOUBLE PRECISION,
    arrival_time TIMESTAMP,
    departure_time TIMESTAMP,
    estimated_arrival_time TIMESTAMP,
    estimated_departure_time TIMESTAMP,
    is_passed BOOLEAN,
);




























######################################

import psycopg2
from psycopg2.extras import execute_values

class Database:
    def __init__(self, dsn):
        """
        Initialize a Database connection.

        :param str dsn: PostgreSQL DSN string
        """
        self.conn = psycopg2.connect(dsn)
        self.cursor = self.conn.cursor()

        # Prepare the upsert SQL
        self.upsert_sql = """
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
            previous_leg,
            next_leg,
            arrival_time,
            departure_time,
            estimated_arrival_time,
            estimated_departure_time,
            is_passed,
            associated_caltopo_marker,
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
            %(previous_leg)s,
            %(next_leg)s,
            %(arrival_time)s,
            %(departure_time)s,
            %(estimated_arrival_time)s,
            %(estimated_departure_time)s,
            %(is_passed)s,
            %(associated_caltopo_marker)s,
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
            previous_leg = EXCLUDED.previous_leg,
            next_leg = EXCLUDED.next_leg,
            arrival_time = EXCLUDED.arrival_time,
            departure_time = EXCLUDED.departure_time,
            estimated_arrival_time = EXCLUDED.estimated_arrival_time,
            estimated_departure_time = EXCLUDED.estimated_departure_time,
            is_passed = EXCLUDED.is_passed,
            associated_caltopo_marker = EXCLUDED.associated_caltopo_marker,
            stoppage_time = EXCLUDED.stoppage_time;
        """

    def save(self, record: dict):
        """
        Upsert a single record into the aidstations table.

        :param dict record: A dict containing all required fields (like `db_dict` from your AidStation)
        """
        self.cursor.execute(self.upsert_sql, record)
        self.conn.commit()

    def close(self):
        """Close the database connection."""
        self.cursor.close()
        self.conn.close()







# Initialize
database = Database(dsn="postgres://user:password@localhost:5432/race")

# Save all aid stations
for aid_station in aid_stations:
    database.save(aid_station.db_dict)  # <- your @property called db_dict

# Close connection
database.close()


















def ensure_schema_and_upsert(rows: List[Tuple]) -> int:
    """Create table if needed and upsert rows by activity id."""
    if not rows:
        return 0

    conn = psycopg2.connect(
        host=PGHOST, port=PGPORT, dbname=PGDATABASE, user=PGUSER, password=PGPASSWORD
    )
    cur = conn.cursor()
    cur.execute(
        """
      CREATE TABLE IF NOT EXISTS  (
        start_time TIMESTAMP WITHOUT TIME ZONE PRIMARY KEY,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        duration_min DOUBLE PRECISION,
        distance_mi DOUBLE PRECISION,
        pace_min_per_mile DOUBLE PRECISION,
        gain_ft INTEGER,
        average_hr_bpm DOUBLE PRECISION,
        average_temp_f DOUBLE PRECISION,
        notes TEXT,
        raw_json JSONB
      );
    """
    )
    # Upsert
    sql = """
    INSERT INTO activities
        (start_time, latitude, longitude, duration_min, distance_mi, pace_min_per_mile,
         gain_ft, average_hr_bpm, average_temp_f, notes, raw_json)
    VALUES %s
    ON CONFLICT (start_time) DO UPDATE SET
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        duration_min = EXCLUDED.duration_min,
        distance_mi = EXCLUDED.distance_mi,
        pace_min_per_mile = EXCLUDED.pace_min_per_mile,
        gain_ft = EXCLUDED.gain_ft,
        average_hr_bpm = EXCLUDED.average_hr_bpm,
        average_temp_f = EXCLUDED.average_temp_f,
        notes = EXCLUDED.notes,
        raw_json = EXCLUDED.raw_json;
    """
    execute_values(cur, sql, rows, page_size=500)
    n = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return n
