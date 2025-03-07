#!/usr/bin/env python3


import datetime
import json
import logging
from functools import cache

import numpy as np
import requests
from geopy.distance import geodesic
from scipy.spatial import KDTree

from ..utils import (
    detect_consecutive_sequences,
    get_gmaps_url,
    get_timezone,
    haversine_distance,
    meters_to_feet,
)
from .caltopo import CaltopoMap, CaltopoShape

logger = logging.getLogger(__name__)


def interpolate_and_filter_points(
    coordinates: np.array, min_interval_dist: float, max_interval_dist: float
):
    """
    Interpolate points between the given coordinates and filter points based on the distance
    criteria.

    :param numpy.ndarray coordinates: An array of shape (n, 2) where each row represents a point
    with latitude and longitude coordinates.
    :param float min_interval_dist: The minimum distance allowed (in feet) between two consecutive
    points. If the distance between two points is less than this value, the point will be removed.
    :param float max_interval_dist: The maximum distance allowed between two consecutive points. If
    the distance between two points is greater than this value, additional points will be
    interpolated to meet the specified interval.

    :return numpy.ndarray: An array of filtered and interpolated points with latitude and longitude
    coordinates.
    """
    interpolated_points = np.empty((0, 2), dtype=float)
    interpolated_points = np.vstack([interpolated_points, [coordinates[0, 0], coordinates[0, 1]]])
    last_point = interpolated_points[0]
    for i in range(1, len(coordinates) - 1):
        point1 = {"latitude": last_point[0], "longitude": last_point[1]}
        point2 = {"latitude": coordinates[i + 1, 0], "longitude": coordinates[i + 1, 1]}

        # Convert latitude and longitude to (lat, lon) tuples
        coords1 = (point1["latitude"], point1["longitude"])
        coords2 = (point2["latitude"], point2["longitude"])

        # Calculate the distance between consecutive points
        distance_between_points = geodesic(coords1, coords2).feet

        if distance_between_points < min_interval_dist:
            # Skip adding this point if it's too close to the previous one
            continue
        # Check if interpolation or removal is needed
        if distance_between_points > max_interval_dist:
            # Calculate the number of intervals needed
            num_intervals = int(distance_between_points / max_interval_dist)
            # Calculate the step size for latitude and longitude
            lat_step = (point2["latitude"] - point1["latitude"]) / num_intervals
            lon_step = (point2["longitude"] - point1["longitude"]) / num_intervals
            # Generate interpolated points
            intermediate_array = np.array(
                [
                    [point1["latitude"] + j * lat_step, point1["longitude"] + j * lon_step]
                    for j in range(1, num_intervals + 1)  # Include the last point
                ]
            )
            interpolated_points = np.vstack([interpolated_points, intermediate_array])
        else:
            interpolated_points = np.vstack(
                [interpolated_points, [point2["latitude"], point2["longitude"]]]
            )
        last_point = interpolated_points[-1]
    # Include the last point of the original array
    interpolated_points = np.vstack(
        [interpolated_points, [point2["latitude"], point2["longitude"]]]
    )
    return interpolated_points


def transform_path(path_data: list, min_step_size: float, max_step_size: float) -> tuple:
    """
    Takes a list of coordinate pairs (a list) and performs two operations. The first is to
    interpolate the path so that no two points are more than the `max_step_size` apart. The second
    is to calculate a cumulative sum of the distances between the points.

    :param list path_data: The list of coordinates making up the path.
    :param float min_step_size: The minumum distance allowed between points in the transformed path
    (in feet).
    :param float max_step_size: The maximum distance allowed between points in the transformed path
    (in feet).
    :return tuple: The newly interpolated path as a numpy array and the array of the cumulative
    distances.
    """
    cumulative_distance = 0
    prev_point = None
    interpolated_path_data = interpolate_and_filter_points(
        np.array(path_data), min_step_size, max_step_size
    )
    cumulative_distances_array = np.zeros(len(interpolated_path_data))

    for i, point in enumerate(interpolated_path_data):
        if prev_point is not None:
            geo = geodesic(
                (prev_point[0], prev_point[1], prev_point[2] if len(prev_point) == 3 else 0),
                (point[0], point[1], point[2] if len(point) == 3 else 0),
            )
            distance = geo.miles
            cumulative_distance += distance
        cumulative_distances_array[i] = cumulative_distance
        prev_point = point
    return interpolated_path_data, cumulative_distances_array


def find_elevations(points: np.array) -> list:
    """
    Given an array of 2D coordinates, this will append a third dimension to the coordinates
    (altitude).

    :param list points: A list of lists of 2D points.
    :return list: A list of lists of 3D points.
    """
    url = "https://caltopo.com/dem/pointstats"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "DNT": "1",
    }
    reversed_points = points[:, ::-1].tolist()
    data = {"geometry": {"type": "LineString", "coordinates": reversed_points}}
    response = requests.post(url, headers=headers, data={"json": json.dumps(data)}, timeout=60)
    if response.ok:
        try:
            new_data = np.array(response.json()["result"])[:, 2]
            # Vectorize the function
            vectorized_function = np.vectorize(meters_to_feet)
            # Apply the function to the array
            return vectorized_function(new_data)
        except (json.JSONDecodeError, KeyError):
            return []
    return []


def cumulative_altitude_changes(altitudes: np.array) -> tuple:
    """
    Calculates the cumulative gain and loss in an array of altitudes.

    :param np.array altitudes: An array of altitudes of points along a line.
    :return tuple: An array of gains, losses representing the cumulative gain and loss at each point
    along the input array.
    """
    # Calculate the differences between consecutive altitudes
    changes = np.diff(altitudes)
    # Calculate cumulative gains and losses
    gains = np.cumsum(np.where(changes > 0, changes, 0))
    losses = np.cumsum(np.where(changes < 0, -changes, 0))
    # Prepend 0 to the gains and losses arrays to align with the original altitude array
    gains = np.insert(gains, 0, 0)
    losses = np.insert(losses, 0, 0)
    return gains, losses


class Course:
    """
    A course is a representation of the race's route, aid stations, and other physical attributes.

    :param CaltopoMap caltopo_map: A CaltopoMap object containing the course and features.
    :param list aid_stations: A list of dicts of the aid stations. This should include their name
    and mile_mark.
    :param str route_name: The name of the route in the map.
    """

    def __init__(self, caltopo_map, aid_stations: list, route_name: str):
        self.route = self.extract_route(route_name, caltopo_map)
        self.course_elements = self.get_course_elements(aid_stations, caltopo_map)
        self.timezone = get_timezone(self.route.start_location)

    @property
    def aid_stations_annotations(self) -> list:
        """
        Returns a list of dicts of the aid stations to use for elevation chart annotations

        :return list: A list of simple dicts.
        """
        return [
            {"name": ce.name, "x": ce.mile_mark, "y": float(ce.altitude)}
            for ce in self.aid_stations[1:-1]
        ]

    @property
    def aid_stations(self) -> list:
        """
        The AidStation objects of this course.

        :return list: The list of only this course's aid stations.
        """
        return list(filter(lambda ce: isinstance(ce, AidStation), self.course_elements))

    def get_course_elements(self, aid_stations: list, caltopo_map: CaltopoMap) -> list:
        """
        Generates a list of `CourseElement` objects (AidStations and Legs) from the given aid
        stations and route data, alternating between `AidStation` and `Leg`.

        :param list aid_stations: A list of dicts of aid station names and mile marks.
        :param CaltopoMap caltopo_map: A CaltopoMap object.
        :return list: A list of `CourseElement` objects, including `AidStation` and `Leg`.
        """

        # Create AidStation objects, including Start and Finish
        aid_station_objects = [
            AidStation(
                asi["name"], asi["mile_mark"], asi.get("altitude", 0.0), asi.get("comments", "")
            )
            for asi in [
                {"name": "Start", "mile_mark": 0, "altitude": self.route.elevations[0]},
                {
                    "name": "Finish",
                    "mile_mark": round(float(self.route.length), 1),
                    "altitude": self.route.elevations[-1],
                },
            ]
            + aid_stations
        ]
        aid_station_objects.sort(key=lambda aso: aso.mile_mark)

        # Map marker titles to aid stations and assign Google Maps URLs
        title_to_marker = {marker.title: marker for marker in caltopo_map.markers}
        for aso in aid_station_objects[1:-1]:
            marker = title_to_marker.get(aso.name)
            if not marker:
                raise LookupError(f"aid station '{aso.name}' not found in {caltopo_map.markers}")
            aso.gmaps_url = marker.gmaps_url

        # Assign Google Maps URLs for Start and Finish separately
        aid_station_objects[0].gmaps_url = get_gmaps_url(self.route.points[0])
        aid_station_objects[-1].gmaps_url = get_gmaps_url(self.route.points[-1])

        # Create Leg objects based on AidStation mile marks and route data
        legs = []
        prev_aid = aid_station_objects[0]
        prev_gain, prev_loss = 0, 0
        for aid in aid_station_objects[1:]:
            # Get the index of the aid station's mile mark in route distances
            aid_idx = np.argmin(np.abs(self.route.distances - aid.mile_mark))

            # Calculate distances, gains, and losses between aid stations
            leg_distance = aid.mile_mark - prev_aid.mile_mark
            gain = self.route.gains[aid_idx] - prev_gain
            loss = self.route.losses[aid_idx] - prev_loss
            aid.altitude = self.route.elevations[aid_idx]
            legs.append(
                Leg(
                    f"{prev_aid.name} ➤ {aid.name}",
                    prev_aid.mile_mark,
                    aid.mile_mark,
                    leg_distance,
                    gain,
                    loss,
                )
            )

            # Update previous aid station, gain, and loss for the next iteration
            prev_aid, prev_gain, prev_loss = (
                aid,
                self.route.gains[aid_idx],
                self.route.losses[aid_idx],
            )

        # Combine AidStations and Legs, and link previous/next references
        course_elements = sorted(aid_station_objects + legs)
        for i, elem in enumerate(course_elements):
            if isinstance(elem, AidStation):
                elem.previous_leg = course_elements[i - 1] if i > 0 else None
                elem.next_leg = course_elements[i + 1] if i < len(course_elements) - 1 else None
            elif isinstance(elem, Leg):
                elem.previous_aid = course_elements[i - 1]
                elem.next_aid = course_elements[i + 1]

        return course_elements

    def extract_route(self, route_name: str, caltopo_map):
        """
        Finds the route in the map and returns the object.

        :param str route_name: The name of the route shape on the map.
        :param CaltopoMap caltopo_map: A CaltopoMap object in which to search for the route.
        :return Route: A Route object representing the course route.
        """
        for shape in caltopo_map.shapes:
            if shape.title == route_name:
                return Route(shape._feature_dict, caltopo_map.map_id, caltopo_map.session)
        raise LookupError(f"no shape called '{route_name}' found in shapes: {caltopo_map.shapes}")

    def update_course_elements(self, runner) -> None:
        """
        Loops over each course element (leg or aid station) to allow it to get updated with the
        latest information from the runner.

        :param Runner runner: The runner of the race.
        :return None:
        """
        preceding_aids = 0
        for ce in self.course_elements:
            ce.refresh(runner)
            # It is only necessary to detect the arrival and departure times of aid stations since
            # those imply the departure and arrival times of the surrounding legs.
            if isinstance(ce, AidStation):
                ce.detect_arrival_time(runner)
                ce.detect_departure_time(runner)

                if not ce.runner_has_arrived(runner):
                    miles_to_start = ce.mile_mark - runner.mile_mark
                    moving_minutes_to_start = datetime.timedelta(
                        minutes=miles_to_start * runner.average_moving_pace
                    )
                    stopping_minutes_to_start = preceding_aids * runner.average_stoppage_time
                    ce.estimated_arrival_time = (
                        runner.last_ping.timestamp
                        + moving_minutes_to_start
                        + stopping_minutes_to_start
                    )

                if not ce.runner_has_departed(runner):
                    ce.estimated_departure_time = (
                        ce.estimated_arrival_time + ce.estimate_transit_time(runner)
                    )

            if isinstance(ce, AidStation) and ce.name != "Start" and not ce.is_passed:
                preceding_aids += 1


class CourseElement:
    """
    An abstract representation of an element of the course. This can be a waypoint, aid station,
    leg, or anything else that makes up the course.

    :param str name: The name of the course element.
    :param float mile_mark: The mile mark at which this course element can be found along the route.
    """

    def __init__(self, name: str, mile_mark: float):
        self.name = name
        self.display_name = name
        self.mile_mark = mile_mark
        self.end_mile_mark = mile_mark
        self.is_passed = False
        self.associated_caltopo_marker = None

    @property
    def transit_time(self) -> datetime.timedelta:
        """
        The amount of time the runner spent on or at the course element.

        :return datetime.timedelta: The timedelta spent in transit.
        """
        if (self.departure_time != datetime.datetime.fromtimestamp(0)) and (
            self.arrival_time != datetime.datetime.fromtimestamp(0)
        ):
            return self.departure_time - self.arrival_time
        return datetime.timedelta(0)

    def is_transiting(self, runner) -> bool:
        """
        Returns True if the runner is at the aid station and False otherwise.

        :param Runner runner: The runner of the race.
        :return bool: True if the runner is transiting the aid station.
        """
        if runner.finished or not runner.started:
            return False
        return self.runner_has_arrived(runner) and not self.runner_has_departed(runner)

    def __lt__(self, other):
        # Since legs and aid stations share the same mile mark, ensure that the leg comes after.
        if isinstance(other, Leg) and self.mile_mark == other.mile_mark:
            return False
        return self.mile_mark < other.mile_mark

    def refresh(self, runner) -> None:
        """
        Updates the object with the latest ETA of the runner and the boolean to indicate if the
        runner has already passed.

        :param Runner runner: A runner object.
        :return None:
        """
        if runner.finished:
            self.is_passed = True
            return
        # The start location needs to be handled differently.
        if self.mile_mark == 0 and isinstance(self, AidStation):
            self.estimated_arrival_time = runner.race.start_time
            self.is_passed = runner.started
            self.arrival_time = runner.race.start_time
            self.departure_time = runner.race.start_time
            return

        if self.runner_has_departed(runner):
            self.is_passed = True
            self.estimated_duration = self.transit_time
            return
        self.estimated_duration = self.estimate_transit_time(runner)


class AidStation(CourseElement):
    """
    A special course element that represents an aid station on the route.

    :param str name: The name of the course element.
    :param float mile_mark: The mile mark at which this course element can be found along the route.
    """

    def __init__(
        self,
        name: str,
        mile_mark: float,
        altitude: float = 0.0,
        comments: str = "",
        prev_leg=None,
        next_leg=None,
    ):
        super().__init__(name, mile_mark)
        self.altitude = altitude
        self.gmaps_url = ""
        self.comments = comments
        self.display_name = f"{name} (mile {mile_mark})"
        self.previous_leg = prev_leg
        self.next_leg = next_leg
        self._arrival_time = datetime.datetime.fromtimestamp(0)
        self._departure_time = datetime.datetime.fromtimestamp(0)
        self._estimated_arrival_time = datetime.datetime.fromtimestamp(0)
        self._estimated_departure_time = datetime.datetime.fromtimestamp(0)

    @property
    def arrival_time(self) -> datetime.datetime:
        """
        The approximate arrival time detected.

        :return datetime.datetime:
        """
        return self._arrival_time

    @arrival_time.setter
    def arrival_time(self, value: datetime.datetime) -> None:
        """
        Setter for the approximate arrival time detected.

        :param datetime.datetime value: The approximate arrival time.
        :return None:
        """
        self._arrival_time = value

    @property
    def departure_time(self) -> datetime.datetime:
        """
        The approximate departure time detected.

        :return datetime.datetime:
        """
        return self._departure_time

    @departure_time.setter
    def departure_time(self, value: datetime.datetime) -> None:
        """
        Setter for the approximate departure time detected.

        :param datetime.datetime value: The approximate departure time.
        :return None:
        """
        self._departure_time = value

    @property
    def estimated_arrival_time(self) -> datetime.datetime:
        """
        The estimated arrival time.

        :return datetime.datetime:
        """
        return self._estimated_arrival_time

    @estimated_arrival_time.setter
    def estimated_arrival_time(self, value: datetime.datetime) -> None:
        """
        Setter for the estimated arrival time.

        :param datetime.datetime value: The ETA.
        :return None:
        """
        self._estimated_arrival_time = value

    @property
    def estimated_departure_time(self) -> datetime.datetime:
        """
        The estimated departure time.

        :return datetime.datetime:
        """
        return self._estimated_departure_time

    @estimated_departure_time.setter
    def estimated_departure_time(self, value: datetime.datetime) -> None:
        """
        Setter for the estimated departure time.

        :param datetime.datetime value: The ETD.
        :return None:
        """
        self._estimated_departure_time = value

    @property
    def stoppage_time(self) -> datetime.timedelta:
        """
        The amount of time spent stopped at this aid station.

        :return datetime.timedelta: The stoppage time.
        """
        return self.transit_time

    def runner_has_arrived(self, runner) -> bool:
        """
        A runner has arrived at an aid station if they are either at, past, or 0.11 or less miles
        away from the aid station.

        :param Runner runner: The runner of the race.
        :return bool: True if the runner has arrived at the AS and False otherwise.
        """
        return runner.mile_mark - self.mile_mark >= -0.11

    def runner_has_departed(self, runner) -> bool:
        """
        A runner has departed an aid station if they are at least 0.11 miles past it.

        :param Runner runner: The runner of the race.
        :return bool: True if the runner has departed the AS and False otherwise.
        """
        return runner.mile_mark - self.end_mile_mark > 0.11

    def estimate_transit_time(self, runner) -> datetime.timedelta:
        """
        Finds the estimated amount of time it will take to transit this AS.

        :param Runner runner: The runner of the race.
        :return datetime.timedelta: The estimated amount of time it will take to transit the AS.
        """
        return runner.average_stoppage_time

    def detect_arrival_time(self, runner) -> None:
        """
        Detects when the runner has entered the aid station. If the runner is within 0.11 miles
        or past the aid station, the runner's arrival time is recorded.

        :param Runner runner: The runner of the race.
        :return None:
        """
        # The arrival time was already detected and set by an earlier ping. Stop here.
        if self.arrival_time != datetime.datetime.fromtimestamp(0):
            return
        # If the arrival time was never set and the runner is transiting or if the runner passed
        # the course element without ever pinging inside it, set the arrival time as the ETA.
        if self.is_transiting(runner) or (
            self.runner_has_arrived(runner) and self.runner_has_departed(runner)
        ):
            self.arrival_time = self.estimated_arrival_time
            logger.info(f"runner entered {self.display_name} at {self.arrival_time}")
            return

    def detect_departure_time(self, runner) -> None:
        """
        Detects when the runner has departed the aid station. If the runner is beyond 0.11 miles
        the aid station, the runner's arrival time is recorded.

        :param Runner runner: The runner of the race.
        :return None:
        """
        # The exit time was already detected and set by an earlier ping.
        if self.departure_time != datetime.datetime.fromtimestamp(0):
            return
        if not self.is_transiting(runner) and self.runner_has_departed(runner):
            dist_traveled = runner.mile_mark - self.mile_mark
            approx_time_traveled = datetime.timedelta(
                minutes=dist_traveled * runner.average_moving_pace
            )
            self.departure_time = runner.last_ping.timestamp - approx_time_traveled
            logger.info(f"runner departed {self.display_name} at {self.departure_time}")
            return


class Leg(CourseElement):
    """
    A special course element that represents a leg of the course.

    :param str name: The name of the course element.
    :param float start_mile_mark: The mile mark at which this course element can be found along the
    route.
    :param float end_mile_mark: The mile mark at which the leg ends.
    :param float distance: The length of the leg.
    :param int gain: The amount of vertical gain (in feet) of the leg.
    :param int loss: The amount of vertical loss (in feet) of the leg.
    """

    def __init__(
        self,
        name: str,
        start_mile_mark: float,
        end_mile_mark: float,
        distance: float,
        gain: int,
        loss: int,
        prev_aid=None,
        next_aid=None,
    ):
        super().__init__(name, start_mile_mark)
        self.distance = distance
        self.end_mile_mark = end_mile_mark
        self.gain = gain
        self.loss = loss
        self.estimated_duration = datetime.timedelta(0)
        self.previous_aid = prev_aid
        self.next_aid = next_aid

    @property
    def arrival_time(self) -> datetime.datetime:
        """
        The approximate arrival time detected.

        :return datetime.datetime:
        """
        return self.previous_aid.departure_time

    @property
    def departure_time(self) -> datetime.datetime:
        """
        The approximate departure time detected.

        :return datetime.datetime:
        """
        return self.next_aid.arrival_time

    @property
    def estimated_arrival_time(self) -> datetime.datetime:
        """
        The estimated arrival time.

        :return datetime.datetime:
        """
        return self.previous_aid.estimated_departure_time

    @property
    def estimated_departure_time(self) -> datetime.datetime:
        """
        The estimated departure time.

        :return datetime.datetime:
        """
        return self.next_aid.estimated_arrival_time

    def runner_has_arrived(self, runner) -> bool:
        """
        A runner has arrived at a leg if they are more than 0.11 miles into the leg.

        :param Runner runner: The runner of the race.
        :return bool: True if the runner has started the leg.
        """
        return runner.mile_mark - self.mile_mark > 0.11

    def runner_has_departed(self, runner):
        """
        A runner has departed a leg if they have 0.11 miles or fewer to go.

        :param Runner runner: The runner of the race.
        :return bool: True if the runner has finished the leg.
        """
        return self.end_mile_mark - runner.mile_mark <= 0.11

    def estimate_transit_time(self, runner) -> datetime.timedelta:
        """
        Finds the estimated amount of time it will take to transit this leg.

        :param Runner runner: The runner of the race.
        :return datetime.timedelta: The estimated amount of time it will take to transit the leg.
        """
        return datetime.timedelta(minutes=self.distance * runner.average_moving_pace)

    def __len__(self) -> float:
        return self.distance


class Route(CaltopoShape):
    """
    This subclass of the CaltopoShape represents a race's route.
    """

    def __init__(self, feature_dict: dict, map_id: str, session: str):
        super().__init__(feature_dict, map_id, session)
        self.points, self.distances = transform_path([[y, x] for x, y in self.coordinates], 5, 75)
        logger.info(f"created route object from map ID {map_id}")
        self.elevations = find_elevations(self.points)
        logger.info(f"calculated elevations on map ID {map_id}")
        self.gains, self.losses = cumulative_altitude_changes(self.elevations)
        logger.info(f"calculated cumulative elevation changes on map ID {map_id}")
        self.length = self.distances[-1]
        self.start_location = self.points[0]
        self.finish_location = self.points[-1]
        self.kdtree = KDTree(self.points)

    @property
    def gain(self) -> float:
        """
        The total amount of elevation gain in this route.

        :return float: The total elevation loss.
        """
        return self.gains[-1]

    @property
    def loss(self) -> float:
        """
        The total amount of elevation loss in this route.

        :return float: The total elevation loss.
        """
        return self.losses[-1]

    def get_elevation_at_mile_mark(self, mile_mark: float) -> float:
        """
        Given a mile mark this will return the corresponding elevation.

        :param float mile_mark: A mile mark along the course.
        :return float: The elevation at the course's mile mark.
        """
        return self.elevations[np.where(self.distances == mile_mark)[0]].tolist()[0]

    def get_point_at_mile_mark(self, mile_mark: float) -> np.array:
        """
        Given a mile mark this will return the lat lon point at that location.

        :param float mile_mark: A mile mark along the course.
        :return np.array: A lat/lon coordinate.
        """
        return self.points[np.where(self.distances == mile_mark)[0]].tolist()[0]

    @cache
    def get_indices_within_radius(self, center_lat: float, center_lon: float, radius: int) -> tuple:
        """
        Given a center point and radius in feet, finds the indices of the route points inside said
        radius.

        :param float center_lat: The latitude of the center point.
        :param float center_lon: The longitude of the center point.
        :param int radius: The radius in feet to search from the center point for points in the
        route.
        :return tuple: An array of indices of the route ordered from closest to furthest as well as
        a bool indicating whether or not the indices are consecutive.
        """
        # Calculate distances from the center point for all points.
        distances = np.array(
            [haversine_distance([center_lat, center_lon], [lat, lon]) for lat, lon in self.points]
        )
        # Get indices of points within the radius.
        indices_within_radius = np.where(distances <= radius)[0]
        # Now get all of the segments of the route. This is used to detect loops, out-n-backs, and
        # intersections.
        route_segments = detect_consecutive_sequences(indices_within_radius)
        # Sort local indices by distance from center point.
        sorted_local_indices = np.argsort(distances[indices_within_radius])
        sorted_indices = indices_within_radius[sorted_local_indices]
        return sorted_indices, len(route_segments) == 1
