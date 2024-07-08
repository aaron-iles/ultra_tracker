#!/usr/bin/env python3


import datetime
import json
import logging
import os
from math import atan2, cos, radians, sin, sqrt

import numpy as np
import pytz
from scipy.stats import norm

from .caltopo import CaltopoMarker
from .course import Route
from .tracker import Ping

logger = logging.getLogger(__name__)


def format_duration(duration: datetime.timedelta) -> str:
    """
    Formats a duration object as HH:mm'ss"

    :param datetime.timedelta duration: A time duration.
    :return str: The formatted duration.
    """
    total_hours = duration.total_seconds() / 3600
    hours, remainder = divmod(total_hours, 1)
    minutes, remainder = divmod(remainder * 60, 1)
    seconds, _ = divmod(remainder * 60, 1)
    return f"{int(hours)}:{int(minutes):02}'{int(seconds):02}\""


def format_distance(distance_ft: float) -> str:
    """
    Format a distance in feet into a human-readable format.

    :param float distance_ft: The distance in feet.

    :return str: A human-readable representation of the distance. If the distance is over 5280 feet,
    it will be converted to miles with one decimal point, otherwise, it will be displayed in feet
    with one decimal point.
    """
    if distance_ft >= 5280:
        distance_mi = distance_ft / 5280
        return f"{distance_mi:.1f} mi"
    else:
        return f"{distance_ft:.1f} ft"


def convert_decimal_pace_to_pretty_format(decimal_pace: float) -> str:
    """
    Formats a running pace in a traditional human format.

    :param float decimal_pace: A running pace in minutes per mile.
    :return str: The formatted pace as mm'ss".
    """
    total_seconds = int(decimal_pace * 60)  # Convert pace to total seconds
    minutes, remainder = divmod(total_seconds, 60)
    seconds, _ = divmod(remainder, 1)
    return f"{minutes}'{seconds:02d}\""


def kph_to_min_per_mi(kph: float) -> float:
    """
    Convert kilometers per hour (kph) to minutes per mile (min/mi).

    Parameters:
    :param float kph: Speed in kilometers per hour.
    :return float: Speed in minutes per mile.
    """
    miles_per_hour = kph / 1.60934
    return 60 / miles_per_hour if miles_per_hour != 0 else 0.0


def calculate_most_probable_mile_mark(
    mile_marks: list, elapsed_time: float, average_pace: float
) -> float:
    """
    Given a list of mile marks, calculates the most likely mile mark given the average pace and
    elapsed time.

    :param list mile_marks: A list of mile markers to test.
    :param float elapsed_time: The elapsed time in minutes.
    :param float average_pace: The average pace in minutes per mile.
    :return float: One of the mile marks from the provided list.
    """
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


def haversine_distance(coord1: list, coord2: list) -> float:
    """
    Calculate the Haversine distance between two points specified by their latitude and longitude coordinates.

    :param list coord1: Latitude and longitude coordinates of the first point in the format
    [latitude, longitude].
    :param list coord2: Latitude and longitude coordinates of the second point in the format
    [latitude, longitude].
    :return float: The distance between the two points in feet.
    """
    # Radius of the Earth in kilometers
    R = 6371.0
    # Convert latitude and longitude from degrees to radians
    lat1 = radians(coord1[0])
    lon1 = radians(coord1[1])
    lat2 = radians(coord2[0])
    lon2 = radians(coord2[1])
    # Compute the differences between latitudes and longitudes
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    # Haversine formula
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance_km = R * c
    # Convert kilometers to feet (1 km = 3280.84 feet)
    return distance_km * 3280.84


class Race:
    """
    This object orchestrates a race.

    :param str name: The name of the race. This is to be used in the web application.
    :param CaltopoMap caltopo_map: The Caltopo map object that is associated with the course.
    :param datetime.datetime start_time: The start time of the race.
    :param str data_store: The filepath in which to store data.
    :param Course course: A course object representing the race.
    :param Runner runner: The runner in the race.
    """

    def __init__(
        self,
        name,
        caltopo_map,
        start_time,
        data_store,
        course,
        runner,
    ):
        self.course = course
        self.runner = runner
        self.data_store = data_store
        self.start_time = start_time
        self.started = False
        self.last_ping_raw = {}
        self.map_url = caltopo_map.url
        self.restore()
        logger.info(f"race at {self.start_time} of {self.course.route.length} mi")

    @property
    def stats(self) -> dict:
        """
        The race statistics to be saved.

        :return dict: The race stats for saving including ping count, runner's pace, and last ping
        data.
        """
        return {
            "average_pace": self.runner.average_pace,
            "pings": self.runner.pings,
            "last_ping": self.last_ping_raw,
        }

    @property
    def html_stats(self) -> dict:
        """
        Returns generic runner and race stats to be used for a webpage.

        :return dict: Runner and race stats.
        """
        return {
            "x_data": json.dumps(self.course.route.distances.tolist()),
            "y_data": json.dumps(self.course.route.elevations.tolist()),
            "runner_x": self.runner.mile_mark,
            "runner_y": self.runner.elevation,
            "avg_pace": convert_decimal_pace_to_pretty_format(self.runner.average_pace),
            "altitude": format_distance(self.runner.last_ping.altitude),
            "current_pace": convert_decimal_pace_to_pretty_format(self.runner.current_pace),
            "mile_mark": round(self.runner.mile_mark, 2),
            "elapsed_time": format_duration(self.runner.elapsed_time),
            "last_update": self.runner.last_ping.timestamp.strftime("%m-%d %H:%M"),
            "est_finish_date": self.runner.estimated_finish_date.strftime("%m-%d %H:%M"),
            "est_finish_time": format_duration(self.runner.estimated_finish_time),
            "start_time": self.start_time.strftime("%m-%d %H:%M"),
            "map_url": self.map_url,
            "aid_stations": self.course.aid_stations,
            "course_deviation": format_distance(self.runner.course_deviation),
            "deviation_background_color": "#90EE90"
            if self.runner.course_deviation < 100
            else "#FAFAD2"
            if 100 <= self.runner.course_deviation <= 150
            else "#FFD700"
            if 151 <= self.runner.course_deviation <= 200
            else "#FFC0CB",
            "debug_data": {
                "course_deviation": format_distance(self.runner.course_deviation),
                "last_ping": self.runner.last_ping.as_json,
                "estimated_course_location": self.runner.estimate_marker.coordinates[::-1],
                "pings": self.runner.pings,
                "track_interval": self.runner.track_interval,
                "low_battery": self.runner.low_battery,
                "course": {
                    "distance": self.course.route.length,
                    "aid_stations": len(self.course.aid_stations),
                    "timezone": str(self.course.timezone),
                    "points": len(self.course.route.points),
                },
            },
        }

    def save(self) -> None:
        """
        Saves the race stats to a file.

        :return None:
        """
        with open(self.data_store, "w") as f:
            f.write(json.dumps(self.stats))

    def restore(self) -> None:
        """
        Restores the race state from a file.

        :return None:
        """
        if os.path.exists(self.data_store):
            with open(self.data_store, "r") as f:
                data = json.load(f)
                self.runner.average_pace = data.get("average_pace", 10)
                self.runner.pings = data.get("pings", 0)
                ping = Ping(data.get("last_ping", {}), self.course.timezone)
                self.runner.check_in(ping, self.start_time, self.course.route)
                self.course.update_aid_stations(self.runner)
                logger.info(f"restore success: {self.runner.last_ping}")

    def ingest_ping(self, ping_data: dict) -> None:
        """
        Takes a raw ping payload and updates the race and runner with the information.

        :param dict ping_data: The raw data from a tracker ping.
        :return None:
        """
        self.last_ping_raw = ping_data
        ping = Ping(ping_data, self.course.timezone)
        logger.info(ping)
        if ping.gps_fix == 0 or ping.latlon == [0, 0]:
            logger.info("ping does not contain GPS coordinates, skipping")
            return
        # Don't do anything if the race hasn't started yet.
        if ping.timestamp < self.start_time:
            logger.info(
                f"incoming timestamp {ping.timestamp} before race start time {self.start_time}"
            )
            return
        # Don't do anything if the runner has already finished.
        if self.runner.finished:
            logger.info("runner already finished; ignoring ping")
            return
        self.runner.check_in(ping, self.start_time, self.course.route)
        self.course.update_aid_stations(self.runner)
        self.save()


class Runner:
    """
    This represents a single runner of the race.

    :param CaltopoMap caltopo_map: The Caltopo map object that is associated with the course.
    :param str marker_name: The name of the marker representing the runner.
    """

    def __init__(self, caltopo_map, marker_name: str):
        self.average_pace = 10
        self.current_pace = 10
        self.elapsed_time = datetime.timedelta(0)
        self.elevation = 0
        self.estimated_finish_date = datetime.datetime.fromtimestamp(0)
        self.estimated_finish_time = datetime.timedelta(0)
        self.finished = False
        self.last_ping = Ping({}, pytz.timezone("Etc/GMT"))
        self.low_battery = False
        self.marker, self.estimate_marker = self.extract_marker(marker_name, caltopo_map)
        self.mile_mark = 0
        self.pings = 0
        self.started = False
        self.track_interval = 300

    def extract_marker(self, marker_name: str, caltopo_map) -> CaltopoMarker:
        """
        Given a marker name, extracts the marker from the map object to associate with the runner.

        :param str marker_name: The marker name or title.
        :param CaltopoMap caltopo_map: The map object containing the markers.
        :return CaltopoMarker: The marker representing the runner.
        """
        estimate_marker = None
        true_marker = None
        for marker in caltopo_map.markers:
            if marker.title == f"{marker_name} (estimated)":
                estimate_marker = marker
            elif marker.title == marker_name:
                true_marker = marker

        if estimate_marker and true_marker:
            return true_marker, estimate_marker
        raise LookupError(
            f"no marker called '{marker_name}' found in markers: {caltopo_map.markers}"
        )

    def calculate_pace(self) -> float:
        """
        Calculates the average pace of the runner.
        :return float: The pace in minutes per mile.
        """
        return (
            (self.elapsed_time.total_seconds() / 60.0) / self.mile_mark if self.mile_mark else 10.0
        )

    def check_if_started(self) -> None:
        """
        Checks if the runner has started the race yet or not. This can only be triggered if the
        race is ongoing and the runner has progressed more than 100 yards down the course.

        :return None:
        """
        self.started = self.mile_mark > 0.11

    @property
    def course_deviation(self) -> float:
        """
        The difference (in feet) between the runner's true location and the course estimate.

        :return float: The uncertainty in the location calculation.
        """
        return abs(
            haversine_distance(
                self.marker.coordinates[::-1], self.estimate_marker.coordinates[::-1]
            )
        )

    def check_if_finished(self, route) -> None:
        """
        Checks if the runner has finished the race. This will trigger if the runner is within 100
        yards of the finish line.

        :return None:
        """
        if not self.started:
            self.finished = False
        self.finished = abs(route.length - self.mile_mark) < 0.11

    @property
    def in_progress(self) -> bool:
        """
        Returns a bool to indicate if the runner is still on the course

        :return bool: True if the runner is still on the course and False otherwise.
        """
        return self.started and not self.finished

    @property
    def marker_description(self) -> str:
        """
        A nicely formatted string for the runner's map marker.

        :return str: The runner's map marker description.
        """
        return (
            f"𝗹𝗮𝘀𝘁 𝘂𝗽𝗱𝗮𝘁𝗲: {self.last_ping.timestamp.strftime('%m-%d %H:%M')}\n"
            f"𝗺𝗶𝗹𝗲 𝗺𝗮𝗿𝗸: {round(self.mile_mark, 2)}\n"
            f"𝗲𝗹𝗮𝗽𝘀𝗲𝗱 𝘁𝗶𝗺𝗲: {format_duration(self.elapsed_time)}\n"
            f"𝗮𝘃𝗴 𝗽𝗮𝗰𝗲: {convert_decimal_pace_to_pretty_format(self.average_pace)}\n"
            f"𝗽𝗶𝗻𝗴𝘀: {self.pings}\n"
            f"𝗘𝗙𝗗: {self.estimated_finish_date.strftime('%m-%d %H:%M')}\n"
            f"𝗘𝗙𝗧: {format_duration(self.estimated_finish_time)}"
        )

    def calculate_mile_mark(self, route) -> tuple:
        """
        Calculates the most likely mile mark of the runner. This is based on the runner's location
        and pace. This will grab the 100 closest points on the course to the runner's ping and 
        return the closest point if it is within 0.25 mi of the anticipated mile mark of the runner.
        If no point matches that criteria, this will calculate the probability (given the last pace) 
        that the runner is at one of those points, then return the point with the highest 
        probability.

        :param Route route: The route of the course.
        :return tuple: The most probable mile mark and the coordinates of that mile mark on the
        course.
        """
        _, matched_indices = route.kdtree.query(self.last_ping.latlon, k=100)
        mile_marks = [route.distances[i] for i in matched_indices]
        expected_mile_mark = (self.elapsed_time.total_seconds() / 60) * (1 / self.average_pace)
        for mm in mile_marks:
            if abs(mm - expected_mile_mark) < 0.25:
                return mm, route.points[np.where(route.distances == mm)[0]].tolist()[0], route.elevations[np.where(route.distances == mm)[0]].tolist()[0]
        # If there was no mile mark found within a quarter mile of the anticipated mile mark, use
        # a different method for guessing the mile mark.
        mile_mark = calculate_most_probable_mile_mark(
            [route.distances[i] for i in matched_indices],
            self.elapsed_time.total_seconds() / 60,
            self.average_pace,
        )
        coords = route.points[np.where(route.distances == mile_mark)[0]].tolist()[0]
        elevation = route.elevations[np.where(route.distances == mile_mark)[0]].tolist()[0]
        return mile_mark, coords, elevation

    def check_in(self, ping: Ping, start_time: datetime.datetime, route: Route) -> None:
        """
        This method is called when a runner pings. This will update all of the runner's statistics
        as well as update the map.

        :param Ping ping: The runner's ping payload object.
        :param datetime.datetime start_time: The race start time.
        :param Route route: The route of the race.
        :return None:
        """
        last_timestamp = self.last_ping.timestamp
        self.pings += 1
        self.low_battery = ping.low_battery == 1
        if ping.interval_change:
            self.track_interval = ping.interval_change

        # Don't update if latest point is older than current point
        if last_timestamp > ping.timestamp:
            logger.info(
                f"incoming timestamp {ping.timestamp} older than last timestamp {last_timestamp}"
            )
            return
        # At this point the race has started and this is a new ping.
        self.last_ping = ping
        self.current_pace = kph_to_min_per_mi(self.last_ping.speed)
        self.elapsed_time = ping.timestamp - start_time
        self.mile_mark, coords, self.elevation = self.calculate_mile_mark(route)
        self.average_pace = self.calculate_pace()
        self.check_if_started()
        if not self.in_progress:
            logger.info(f"race not in progress; started: {self.started} finished: {self.finished}")
            return
        self.estimated_finish_time = datetime.timedelta(minutes=self.average_pace * route.length)
        self.estimated_finish_date = start_time + self.estimated_finish_time
        # Now update the marker attributes.
        self.marker.description = self.marker_description
        self.marker.coordinates = ping.lonlat
        self.marker.rotation = round(ping.heading)
        # Update the estimate marker coordinates.
        self.estimate_marker.coordinates = coords[::-1]
        self.estimate_marker.rotation = round(ping.heading)
        self.estimate_marker.description = ""
        # Issue the POST to update the estimate marker.
        CaltopoMarker.update(self.estimate_marker)
        # Issue the POST to update the marker. This must be called this way to work with the uwsgi
        # thread decorator.
        CaltopoMarker.update(self.marker)
        self.check_if_finished(route)
        logger.info(self)

    def __str__(self):
        return f"RUNNER {round(self.mile_mark, 2)} mi @ {convert_decimal_pace_to_pretty_format(self.average_pace)} ({format_duration(self.elapsed_time)})"
