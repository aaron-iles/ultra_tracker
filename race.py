#!/usr/bin/env python3


from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from scipy.stats import norm
import argparse
import datetime
import json
import numpy as np
import os
import requests
import yaml
from jinja2 import Environment, FileSystemLoader

from caltopo import CaltopoMap

class Race:
    def __init__(
        self,
        start_time,
        data_store,
        caltopo_map_id,
        caltopo_cookies,
    ):
        self.started = False
        self.finished = False
        self.caltopo_map = CaltopoMap(caltopo_map_id, caltopo_cookies)
        self.total_distance = self.caltopo_map.distances[-1]
        self.start_time = start_time
        self.last_mile_mark = 0
        self.pace = 10
        self.pings = 0
        self.last_ping = {}
        self.last_timestamp = datetime.datetime.fromtimestamp(0)
        self.elapsed_time = datetime.timedelta(0)
        self.estimated_finish_time = datetime.timedelta(0)
        self.estimated_finish_date = datetime.datetime.fromtimestamp(0)
        self.last_location = (0, 0)
        self.course = 0
        self.data_store = data_store
        self.restore()

    @staticmethod
    def extract_timestamp(ping_data: dict):
        ts = ping_data.get("Events", [{}])[0].get("timeStamp", "0")
        try:
            return datetime.datetime.fromtimestamp(ts)
        except ValueError:
            return datetime.datetime.fromtimestamp(ts // 1000)

    @staticmethod
    def extract_point(ping_data: dict):
        return ping_data.get("Events", [{}])[0].get("point", {})

    @staticmethod
    def extract_course(ping_data: dict):
        return int(Race.extract_point(ping_data).get("course", 0))

    @staticmethod
    def extract_location(ping_data: dict):
        point = Race.extract_point(ping_data)
        return (point.get("latitude", 0), point.get("longitude", 0))

    def _check_if_started(self):
        if self.start_time > datetime.datetime.now():
            self.started = False
        self.started = self.last_mile_mark > 0.11

    def _check_if_finished(self):
        if not self.started:
            self.finished = False
        self.finished = abs(self.total_distance - self.last_mile_mark) < 0.11

    @property
    def in_progress(self):
        return self.started and not self.finished

    @property
    def stats(self):
        return {"pace": self.pace, "pings": self.pings, "last_ping": self.last_ping}

    @property
    def html_stats(self):
        return {
            "avg_pace": convert_decimal_pace_to_pretty_format(self.pace),
            "mile_mark": round(self.last_mile_mark, 2),
            "elapsed_time": format_duration(self.elapsed_time),
            "last_update": self.last_timestamp.strftime("%m-%d %H:%M"),
            "pings": self.pings,
            "est_finish_date": self.estimated_finish_date.strftime("%m-%d %H:%M"),
            "est_finish_time": format_duration(self.estimated_finish_time),
            "start_time": self.start_time.strftime("%m-%d %H:%M"),
        }

    @property
    def marker_description(self):
        return (
            f"last update: {self.last_timestamp.strftime('%m-%d %H:%M')}\n"
            f"mile mark: {round(self.last_mile_mark, 2)}\n"
            f"elapsed time: {format_duration(self.elapsed_time)}\n"
            f"avg pace: {convert_decimal_pace_to_pretty_format(self.pace)}\n"
            f"pings: {self.pings}\n"
            f"EFD: {self.estimated_finish_date.strftime('%m-%d %H:%M')}\n"
            f"EFT: {format_duration(self.estimated_finish_time)}"
        )

    def _calculate_last_mile_mark(self):
        _, matched_indices = self.caltopo_map.kdtree.query(self.last_location, k=5)
        return calculate_most_probable_mile_mark(
            [self.caltopo_map.distances[i] for i in matched_indices],
            self.elapsed_time.total_seconds() / 60,
            self.pace,
        )

    def _calculate_pace(self):
        return (
            (self.elapsed_time.total_seconds() / 60.0) / self.last_mile_mark
            if self.last_mile_mark
            else 10
        )

    def save(self):
        with open(self.data_store, "w") as f:
            f.write(json.dumps(self.stats))
        return

    def restore(self):
        if os.path.exists(self.data_store):
            with open(self.data_store, "r") as f:
                data = json.load(f)
                self.pace = data.get("pace", 10)
                self.pings = data.get("pings", 0)
                self.last_ping = data.get("last_ping", {})
        return

    def update(self, ping_data):
        self.pings += 1
        self.last_ping = ping_data
        # Don't update if latest point is older than current point
        if self.last_timestamp > (new_timestamp := self.extract_timestamp(ping_data)):
            print(
                f"incoming timestamp {new_timestamp} older than last timestamp {self.last_timestamp}"
            )
            return
        elif new_timestamp < self.start_time:
            print(f"incoming timestamp {new_timestamp} before race start time {self.start_time}")
            return
        self.last_timestamp = new_timestamp
        self.course = self.extract_course(ping_data)
        self.last_location = self.extract_location(ping_data)
        self.elapsed_time = self.last_timestamp - self.start_time
        self.last_mile_mark = self._calculate_last_mile_mark()
        self._check_if_started()
        if not self.in_progress:
            print(f"race not in progress started: {self.started} finished: {self.finished}")
            return
        self.pace = self._calculate_pace()
        self.estimated_finish_time = datetime.timedelta(minutes=self.pace * self.total_distance)
        self.estimated_finish_date = self.start_time + self.estimated_finish_time
        self.save()
        self.caltopo_map.move_marker(self.last_location, self.course, self.marker_description)
        self._check_if_finished()


class AidStation(CaltopoMarker):
    def __init__(self, name: str, mile_mark: float, marker_id: str, caltopo_map):
        super().__init__(name, caltopo_map)
        self.name = name
        self.mile_mark = mile_mark
        self.marker_id = marker_id

