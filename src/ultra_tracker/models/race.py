#!/usr/bin/env python3


import datetime
import json
import logging
import os

import numpy as np
import pytz
from scipy.stats import norm

from .caltopo import CaltopoMarker
from .course import Route
from .tracker import Ping
from ..utils import (
    convert_decimal_pace_to_pretty_format,
    format_distance,
    format_duration,
    haversine_distance,
    kph_to_min_per_mi,
)

logger = logging.getLogger(__name__)


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
        self.name = name
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
            "distances": json.dumps(self.course.route.distances.tolist()),
            "elevations": json.dumps(self.course.route.elevations.tolist()),
            "runner_x": self.runner.mile_mark,
            "runner_y": self.runner.elevation,
            "runner_name": self.runner.marker.title,
            "avg_pace": convert_decimal_pace_to_pretty_format(self.runner.average_pace),
            "altitude": format_distance(self.runner.last_ping.altitude, True),
            "current_pace": convert_decimal_pace_to_pretty_format(self.runner.current_pace),
            "mile_mark": round(self.runner.mile_mark, 2),
            "elapsed_time": format_duration(self.runner.elapsed_time),
            "last_update": self.runner.last_ping.timestamp.strftime("%m/%d %H:%M"),
            "est_finish_date": self.runner.estimated_finish_date.strftime("%m/%d %H:%M"),
            "est_finish_time": format_duration(self.runner.estimated_finish_time),
            "start_time": self.start_time.strftime("%m/%d %H:%M"),
            "map_url": self.map_url,
            "course_elements": self.course.course_elements,
            "course_deviation": format_distance(self.runner.course_deviation),
            "deviation_background_color": (
                "#90EE90"
                if self.runner.course_deviation < 100
                else (
                    "#FAFAD2"
                    if 100 <= self.runner.course_deviation <= 150
                    else "#FFD700" if 151 <= self.runner.course_deviation <= 200 else "#FFC0CB"
                )
            ),
            "debug_data": {
                "course_deviation": format_distance(self.runner.course_deviation),
                "last_ping": self.runner.last_ping.as_json,
                "estimated_course_location": self.runner.estimate_marker.coordinates[::-1],
                "pings": self.runner.pings,
                "track_interval": self.runner.track_interval,
                "low_battery": self.runner.low_battery,
                "course": {
                    "distance": self.course.route.length,
                    "gain": self.course.route.gain,
                    "loss": self.course.route.loss,
                    "course_elements": len(self.course.course_elements),
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
                ping = Ping(data.get("last_ping", {}))
                self.runner.check_in(ping, self.start_time, self.course.route)
                self.course.update_course_elements(self.runner, self.start_time)
                logger.info(f"restore success: {self.runner.last_ping}")
        else:
            self.runner.mile_mark = 0
            self.runner.elevation = self.course.route.elevations[0]

    def ingest_ping(self, ping_data: dict) -> None:
        """
        Takes a raw ping payload and updates the race and runner with the information.

        :param dict ping_data: The raw data from a tracker ping.
        :return None:
        """
        self.last_ping_raw = ping_data
        ping = Ping(ping_data)
        logger.info(ping)
        if ping.gps_fix == 0 or ping.latlon == [0, 0]:
            logger.info("ping does not contain GPS coordinates, skipping")
            self.runner.pings += 1
            return
        # Don't do anything if the race hasn't started yet.
        if ping.timestamp < self.start_time:
            logger.info(
                f"incoming timestamp {ping.timestamp} before race start time {self.start_time}"
            )
            self.runner.pings += 1
            return
        # Don't do anything if the runner has already finished.
        if self.runner.finished:
            logger.info("runner already finished; ignoring ping")
            return
        self.runner.check_in(ping, self.start_time, self.course.route)
        self.course.update_course_elements(self.runner, self.start_time)
        self.save()


class Runner:
    """
    This represents a single runner of the race.

    :param CaltopoMap caltopo_map: The Caltopo map object that is associated with the course.
    :param str marker_name: The name of the marker representing the runner.
    :param list default_start_location: The lat/lon coordinates of where to place the runner marker
    if not found before race start.
    """

    def __init__(self, caltopo_map, marker_name: str, default_start_location: list = [0, 0]):
        self.average_pace = 10
        self.current_pace = 10
        self.elapsed_time = datetime.timedelta(0)
        self.elevation = 0
        self.estimated_finish_date = datetime.datetime.fromtimestamp(0)
        self.estimated_finish_time = datetime.timedelta(0)
        self.finished = False
        self.last_ping = Ping({})
        self.low_battery = False
        self.marker, self.estimate_marker = self.extract_marker(
            marker_name, caltopo_map, default_start_location
        )
        self.mile_mark = 0
        self.pings = 0
        self.started = False
        self.track_interval = 300

    def extract_marker(self, marker_name: str, caltopo_map, default_start_location: list) -> tuple:
        """
        Given a marker name, extracts the marker from the map object to associate with the runner.
        This also includes the estimate marker for troubleshooting.

        :param str marker_name: The marker name or title.
        :param CaltopoMap caltopo_map: The map object containing the markers.
        :param list default_start_location: The lat/lon coordinates of where to place the runner
        marker if not found before race start.
        :return tuple: The marker representing the runner and the runner's estimated location.
        """
        true_marker = caltopo_map.get_or_create_marker(
            marker_name, "Live Tracking", "1", "a:4", "A200FF", default_start_location
        )
        estimate_marker = caltopo_map.get_or_create_marker(
            f"{marker_name} (estimated)",
            "Backend",
            "0.5",
            "point",
            "FFFFFF",
            default_start_location,
            False,
        )
        return true_marker, estimate_marker

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

    def calculate_mile_mark(self, route, latlon: list) -> tuple:
        """
        Calculates the most likely mile mark of the runner. This is based on the runner's location
        and pace. This will grab the 100 closest points on the course to the runner's ping and
        return the closest point if it is within 0.25 mi of the anticipated mile mark of the runner.
        If no point matches that criteria, this will calculate the probability (given the last pace)
        that the runner is at one of those points, then return the point with the highest
        probability.

        :param Route route: The route of the course.
        :param list latlon: The latitude/longitude of the runner on the course.
        :return tuple: The most probable mile mark and the coordinates of that mile mark on the
        course.
        """
        # TODO: Should we allow the mile marker to move backward? There are some legitimate times
        # when it happens but usually only a small amount.

        # This step right here has been found to result in better estimates. Rather than performing
        # the math based on the actual location of the runner, we "snap to" the closest point on the
        # course and THEN perform the math. This helps account for satellite reception issues,
        # course redirections, and incorrectly drawn maps.
        # Get the closest 1 point to the latlon.
        _, matched_indices = route.kdtree.query(latlon, k=1)
        latlon = route.points[matched_indices]

        # First, grab all of the points within 100 feet. This returns the points in order from
        # closest to furthest.
        indices_within_radius, are_consecutive = route.get_indices_within_radius(
            latlon[0], latlon[1], 100
        )
        logger.debug(f"found {len(indices_within_radius)} points within 100 ft of {latlon}")
        logger.debug(f"points are consecutive? {are_consecutive}")

        # Case 1: When there are course points close to the ping and they are all consecutive,
        # the true location is the closest course point to the ping. This is the easiest case.
        if len(indices_within_radius) > 0 and are_consecutive:
            mile_mark = route.distances[indices_within_radius[0]]
            elevation = route.elevations[indices_within_radius[0]]
            point = route.points[indices_within_radius[0]]
            return mile_mark, point.tolist(), elevation

        # Case 2: When there are course points close to the ping and they are not consecutive, then
        # the runner must be either on an out and back, loop, or intersection. This is trickier.
        if len(indices_within_radius) > 0 and not are_consecutive:
            mile_marks = [route.distances[i] for i in indices_within_radius]
            mile_mark = calculate_most_probable_mile_mark(
                mile_marks, self.elapsed_time.total_seconds() / 60, self.average_pace
            )
            coords = route.get_point_at_mile_mark(mile_mark)
            elevation = route.get_elevation_at_mile_mark(mile_mark)
            # TODO maybe check here if the mile mark moved backward more than X miles and do a
            # different calculation if so.
            return mile_mark, coords, elevation

        # Case 3: This should only occur if the latlon is more than 100 ft from the closest course
        # point. This is impossible because above we "snapped to" the closest course point, but
        # keeping this here in case that changes in the future.
        logger.warning(f"unable to find mile mark given point {latlon}")
        return 0, [0, 0], 0

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
        last_mile_mark = self.mile_mark
        self.mile_mark, coords, self.elevation = self.calculate_mile_mark(
            route, self.last_ping.latlon
        )
        # If the runner is seen to move backward by more than 1/10th of a mile, print a warning.
        # Sometimes this is valid, but it may indicate the previous or current mile mark estimates
        # are wrong. Movements of less than 1/10th of a mile can be ignored since they could be
        # seen frequently at aid stations.
        if (self.mile_mark - last_mile_mark) < -0.1:
            logger.warning(f"runner has moved backward from {last_mile_mark} to {self.mile_mark}")
        self.average_pace = self.calculate_pace()
        self.check_if_started()
        if not self.in_progress:
            logger.info(f"race not in progress; started: {self.started} finished: {self.finished}")
            return
        self.estimated_finish_time = datetime.timedelta(minutes=self.average_pace * route.length)
        self.estimated_finish_date = start_time + self.estimated_finish_time
        # Now update the marker attributes.
        self.marker.coordinates = ping.lonlat
        self.marker.rotation = round(ping.heading)
        # Update the estimate marker coordinates.
        self.estimate_marker.coordinates = coords[::-1]
        self.estimate_marker.rotation = round(ping.heading)
        # Issue the POST to update the estimate marker.
        CaltopoMarker.update(self.estimate_marker)
        # Issue the POST to update the marker. This must be called this way to work with the uwsgi
        # thread decorator.
        CaltopoMarker.update(self.marker)
        self.check_if_finished(route)
        logger.info(self)

    def __str__(self):
        return f"RUNNER {round(self.mile_mark, 2)} mi @ {convert_decimal_pace_to_pretty_format(self.average_pace)} ({format_duration(self.elapsed_time)})"
