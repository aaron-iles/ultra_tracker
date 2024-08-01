#!/usr/bin/env python3


import datetime
import json
import logging

import numpy as np
import requests
from geopy.distance import geodesic
from scipy.spatial import KDTree

from .caltopo import CaltopoMap, CaltopoShape
from .tracker import meters_to_feet
from .utils import format_duration, get_gmaps_url, get_timezone

logger = logging.getLogger(__name__)


def interpolate_and_filter_points(
    coordinates: np.array, min_interval_dist: float, max_interval_dist: float
):
    """
    Interpolate points between the given coordinates and filter points based on the distance criteria.

    :param numpy.ndarray coordinates: An array of shape (n, 2) where each row represents a point with
    latitude and longitude coordinates.
    :param float min_interval_dist: The minimum distance allowed (in feet) between two consecutive
    points. If the distance between two points is less than this value, the point will be removed.
    :param float max_interval_dist: The maximum distance allowed between two consecutive points. If
    the distance between two points is greater than this value, additional points will be
    interpolated to meet the specified interval.

    :return numpy.ndarray: An array of filtered and interpolated points with latitude and longitude coordinates.
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
        elif distance_between_points > max_interval_dist:
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
    response = requests.post(url, headers=headers, data={"json": json.dumps(data)})
    if response.ok:
        try:
            new_data = np.array(response.json()["result"])[:, 2]
            # Vectorize the function
            vectorized_function = np.vectorize(meters_to_feet)
            # Apply the function to the array
            return vectorized_function(new_data)
        except (json.JSONDecodeError, KeyError):
            return


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

    def get_course_elements(self, aid_stations: list, caltopo_map: CaltopoMap) -> list:
        """
        Searches the provided list of aid stations and route to generate all `AidStation` and `Leg`
        objects.

        :param list aid_stations: A list of dicts of aid station names and mile marks.
        :param CaltopoMap caltopo_map: A CaltopoMap object.
        :return list: A list of `CourseElement` objects alternating between `AidStation` and `Leg`.
        """
        # First create each of the AidStation objects. This also includes the start and finish even
        # though they are not technically aid stations.
        aid_station_objects = sorted(
            [
                AidStation(asi["name"], asi["mile_mark"])
                for asi in [
                    {"name": "Start", "mile_mark": 0},
                    {"name": "Finish", "mile_mark": round(self.route.length, 1)},
                ]
                + aid_stations
            ]
        )

        # Map each marker's title to the object.
        title_to_marker = {marker.title: marker for marker in caltopo_map.markers}
        # Now take each marker and get the Google Maps URL associated with it. We do this by finding
        # the marker in the list of markers parsed from Caltopo and associating them based on name.
        for aso in aid_station_objects[1:-1]:
            try:
                aso.gmaps_url = title_to_marker[aso.name].gmaps_url
            except KeyError as err:
                raise KeyError(f"aid station '{err.args[0]}' not found in {caltopo_map.markers}")
        # Since the start and finish aren't markers on the map, we do them separately.
        aid_station_objects[0].gmaps_url = get_gmaps_url(self.route.points[0])
        aid_station_objects[-1].gmaps_url = get_gmaps_url(self.route.points[-1])

        leg_objects = []
        prev_aid = aid_station_objects[0]
        prev_gain = 0
        prev_loss = 0
        for aso in aid_station_objects[1:]:
            # This is the index in the big array of where the aid station lies. It calculates
            # the closest mile mark to the reported mile mark and gets the index in that array.
            aso_index = np.argmin(np.abs(self.route.distances - aso.mile_mark))

            total_gain_at_aso = self.route.gains[aso_index]
            total_loss_at_aso = self.route.losses[aso_index]
            distance_to_aso = aso.mile_mark - prev_aid.mile_mark
            gain_to_aso = total_gain_at_aso - prev_gain
            loss_to_aso = total_loss_at_aso - prev_loss
            prev_gain = total_gain_at_aso
            prev_loss = total_loss_at_aso

            leg_objects.append(
                Leg(
                    f"{prev_aid.name} ➤ {aso.name}",
                    prev_aid.mile_mark,
                    distance_to_aso,
                    gain_to_aso,
                    loss_to_aso,
                )
            )
            prev_aid = aso
        return sorted(aid_station_objects + leg_objects)

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
        # TODO: Deprecate this in favor of calculating these for any runner upon request.
        for ce in self.course_elements:
            ce.refresh(runner)


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
        self.is_passed = False
        self.distance_to = 0
        self.estimated_arrival_time = datetime.datetime.fromtimestamp(0)
        self.associated_caltopo_marker = None

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
        # TODO: Deprecate this in favor of methods that allow any runner to ask for an ETA, etc.
        miles_to_me = self.mile_mark - runner.mile_mark
        if miles_to_me < 0:
            # The runner has already passed this course element.
            # TODO: This only works for a single runner using this application.
            self.is_passed = True
            return
        # It may be necessary to set this back to False if the tracker momentarily thought the
        # runner passed the aid (and changed the bool above) but then corrected itself.
        self.is_passed = False
        minutes_to_me = datetime.timedelta(minutes=miles_to_me * runner.average_pace)
        self.estimated_arrival_time = runner.last_ping.timestamp + minutes_to_me

    def get_eta(self, runner) -> datetime.datetime:
        """
        Given a `Runner`, calculates the ETA of the runner to the mile mark. If the runner has
        already passed the mile mark, this function returns None.

        :param Runner runner: A runner in the race.
        :return datetime.datetime: The time and date of the runner's ETA.
        """
        miles_to_me = self.mile_mark - runner.mile_mark
        if miles_to_me < 0:
            # The runner has already passed this aid station.
            return
        minutes_to_me = datetime.timedelta(minutes=miles_to_me * runner.average_pace)
        return runner.last_ping.timestamp + minutes_to_me


class AidStation(CourseElement):
    """
    A special course element that represents an aid station on the route.

    :param str name: The name of the course element.
    :param float mile_mark: The mile mark at which this course element can be found along the route.
    """

    def __init__(self, name: str, mile_mark: float):
        super().__init__(name, mile_mark)
        self.display_name = f"✚ {name}"
        self.gmaps_url = ""


class Leg(CourseElement):
    """
    A special course element that represents a leg of the course.

    :param str name: The name of the course element.
    :param float mile_mark: The mile mark at which this course element can be found along the route.
    :param float distance: The length of the leg.
    :param int gain: The amount of vertical gain (in feet) of the leg.
    :param int loss: The amount of vertical loss (in feet) of the leg.
    """

    def __init__(self, name: str, mile_mark: float, distance: float, gain: int, loss: int):
        super().__init__(name, mile_mark)
        self.distance = distance
        self.gain = gain
        self.loss = loss
        self.estimated_duration = datetime.timedelta(0)

    @property
    def estimated_duration_str(self) -> str:
        """
        The pretty string representation of the estimated duration.

        :return str: A human-friendly representation of the duration.
        """
        return format_duration(self.estimated_duration)

    def refresh(self, runner) -> None:
        """
        Refreshes the estimated duration of the leg based on the runner's average pace.

        :param Runner runner: The runner in the race.
        :return None:
        """
        super().refresh(runner)
        # TODO This should be calculated based on moving pace and exclude stoppage time.
        self.estimated_duration = datetime.timedelta(minutes=self.distance * runner.average_pace)
        return


class Route(CaltopoShape):
    """
    This subclass of the CaltopoShape represents a race's route.
    """

    def __init__(self, feature_dict: dict, map_id: str, session: str):
        super().__init__(feature_dict, map_id, session)
        self.points, self.distances = transform_path([[y, x] for x, y in self.coordinates], 5, 100)
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
