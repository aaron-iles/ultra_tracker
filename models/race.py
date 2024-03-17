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

from models.caltopo import CaltopoMap, CaltopoMarker, CaltopoShape
from models.tracker import Ping


def format_duration(duration):
    total_hours = duration.total_seconds() / 3600
    hours, remainder = divmod(total_hours, 1)
    minutes, remainder = divmod(remainder * 60, 1)
    seconds, _ = divmod(remainder * 60, 1)
    return f"{int(hours)}:{int(minutes):02}'{int(seconds):02}\""


def convert_decimal_pace_to_pretty_format(decimal_pace):
    total_seconds = int(decimal_pace * 60)  # Convert pace to total seconds
    minutes, remainder = divmod(total_seconds, 60)
    seconds, _ = divmod(remainder, 1)
    pretty_format = f"{minutes}'{seconds:02d}\""
    return pretty_format


def calculate_most_probable_mile_mark(mile_marks, elapsed_time, average_pace):
    # Constants
    if not average_pace:
        average_speed = 1 / 10
    else:
        average_speed = 1 / average_pace  # Speed in miles per minute
    # Calculate expected distance based on elapsed time and average speed
    expected_distance = elapsed_time * average_speed
    # Calculate standard deviation based on average pace
    standard_deviation = average_pace / 3  # Adjust for variability in pace
    # Calculate probabilities for each mile mark
    probabilities = norm.pdf(mile_marks, loc=expected_distance, scale=standard_deviation)
    # Find the mile mark with the highest probability
    most_probable_mile_mark = mile_marks[np.argmax(probabilities)]
    return most_probable_mile_mark


class Race:
    def __init__(
        self,
        start_time,
        data_store,
        course,
        runner,
    ):
        self.data_store = data_store
        self.start_time = start_time
        self.started = False
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
    def extract_heading(ping_data: dict):
        return int(Race.extract_point(ping_data).get("heading", 0))

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
        self.finished = abs(self.course.route.length - self.last_mile_mark) < 0.11

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
        _, matched_indices = self.course.route.kdtree.query(self.runner.last_location, k=5)
        return calculate_most_probable_mile_mark(
            [self.course.route.distances[i] for i in matched_indices],
            self.elapsed_time.total_seconds() / 60,
            self.runner.pace,
        )


    def save(self):
        with open(self.data_store, "w") as f:
            f.write(json.dumps(self.stats))
        return

    def restore(self):
        if os.path.exists(self.data_store):
            with open(self.data_store, "r") as f:
                data = json.load(f)
                self.runner.pace = data.get("pace", 10)
                self.runner.pings = data.get("pings", 0)
                self.runner.last_ping = data.get("last_ping", {})
        return

    def ingest_ping(self, ping_data):
        ping = Ping(ping_data)
        self.runner.pings += 1
        # Don't update if latest point is older than current point
        if self.runner.last_ping.timestamp > ping.timestamp:
            print(
                f"incoming timestamp {ping.timestamp} older than last timestamp {self.runner.last_ping.timestamp}"
            )
            return
        elif new_timestamp < self.start_time:
            print(f"incoming timestamp {new_timestamp} before race start time {self.start_time}")
            return
        self.runner.update(ping)
       # self.runner.last_ping = ping
       # self.runner.last_timestamp = new_timestamp
       # self.runner.heading = self.extract_heading(ping_data)
       # self.runner.last_location = self.extract_location(ping_data)
       # self.runner.elapsed_time = self.runner.last_timestamp - self.start_time
       # self.runner.last_mile_mark = self._calculate_last_mile_mark()
       # self._check_if_started()
       # if not self.in_progress:
       #     print(f"race not in progress started: {self.started} finished: {self.finished}")
       #     return
       # self.runner.pace = self.runner._calculate_pace()
       # self.runner.estimated_finish_time = datetime.timedelta(
       #     minutes=self.runner.pace * self.course.route.length
       # )
       # self.runner.estimated_finish_date = self.start_time + self.runner.estimated_finish_time
       # self.save() # TODO
       # self.caltopo_map.move_marker(
       #     self.last_location, self.heading, self.marker_description
       # )  # TODO
       # self._check_if_finished()


class Runner:
    def __init__(self, marker_name: str, caltopo_map):
        self.elapsed_time = datetime.timedelta(0)
        self.estimated_finish_date = datetime.datetime.fromtimestamp(0)
        self.estimated_finish_time = datetime.timedelta(0)
        self.finished = False
        self.heading = 0
        self.last_location = (0, 0)
        self.last_mile_mark = 0
        self.last_ping = Ping({})
        self.last_timestamp = datetime.datetime.fromtimestamp(0)
        self.marker = self.extract_marker(marker_name, caltopo_map)
        self.pace = 10
        self.pings = 0
        self.started = False

    def extract_marker(self, marker_name: str, caltopo_map):
        for marker in caltopo_map.markers:
            if marker.title == marker_name:
                return marker
        raise LookupError(f"no marker called '{marker_name}' found in markers: {caltopo_map.markers}")

    def _calculate_pace(self) -> float:
        return (
            (self.elapsed_time.total_seconds() / 60.0) / self.last_mile_mark
            if self.last_mile_mark
            else 10.0
        )

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

    def update(ping: Ping):
        self.last_ping = ping
        self.last_timestamp = ping.timestamp # TODO necessary?
        self.heading = ping.heading # TODO necessary?
        self.last_location = ping.latlon # TODO necessary?
        self.elapsed_time = self.ping.timestamp - self.start_time # TODO dont have start time
        self.last_mile_mark = self._calculate_last_mile_mark() # TODO runner doesnt know course information
        self._check_if_started()
        if not self.in_progress:
            print(f"race not in progress started: {self.started} finished: {self.finished}")
            return
        self.runner.pace = self.runner._calculate_pace()
        self.runner.estimated_finish_time = datetime.timedelta(
            minutes=self.runner.pace * self.course.route.length
        )
        self.runner.estimated_finish_date = self.start_time + self.runner.estimated_finish_time
        self.save() # TODO
        self.caltopo_map.move_marker(
            self.last_location, self.heading, self.marker_description
        )  # TODO
        self._check_if_finished()


