#!/usr/bin/env python3


import datetime
import logging
from math import atan2, cos, radians, sin, sqrt

import numpy as np
import pytz
from timezonefinder import TimezoneFinder
from lxml import etree


logger = logging.getLogger(__name__)


def export_to_gpx(coordinates: np.ndarray, filename: str) -> None:
    """
    Export a NumPy array of coordinates to a GPX file.

    :param np.ndarray coordinates: An array of coordinates with shape (n, 2) or (n, 3). Each
    coordinate should be in the form [latitude, longitude] or [latitude, longitude, elevation].
    :param str filename: The name of the output GPX file.
    :return None:
    """
    # Create the root element
    gpx = etree.Element("gpx", version="1.1", creator="export_to_gpx_function")
    trk = etree.SubElement(gpx, "trk")
    trkseg = etree.SubElement(trk, "trkseg")
    # Add coordinates to the GPX file
    for coord in coordinates:
        trkpt = etree.SubElement(trkseg, "trkpt", lat=str(coord[0]), lon=str(coord[1]))
        if len(coord) == 3:
            ele = etree.SubElement(trkpt, "ele")
            ele.text = str(coord[2])
    # Create a tree and write to a file
    tree = etree.ElementTree(gpx)
    tree.write(filename, pretty_print=True, xml_declaration=True, encoding="UTF-8")


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


def format_distance(distance_ft: float, force_ft: bool = False) -> str:
    """
    Format a distance in feet into a human-readable format.

    :param float distance_ft: The distance in feet.
    :param bool force_ft: True if the formatter should always return feet and False otherwise.

    :return str: A human-readable representation of the distance. If the distance is over 5280 feet,
    it will be converted to miles with one decimal point, otherwise, it will be displayed in feet
    with one decimal point.
    """
    if distance_ft >= 5280 and not force_ft:
        distance_mi = distance_ft / 5280
        return f"{distance_mi:.1f} mi"
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


def get_timezone(latlon: list):
    """
    Given a location by coordinates, returns the timezone.

    :param list latlon: The latitude, longitude of the location.
    :return pytz: A timezone object.
    """
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=latlon[0], lng=latlon[1])
    if timezone_str:
        logger.debug(f"determined {latlon} to be in timezone {timezone_str}")
        return pytz.timezone(timezone_str)
    return None


def get_gmaps_url(latlon: list) -> str:
    """
    Given a latitude and longitude, returns the associated Google Maps URL.

    :param list latlon: The latitude, longitude.
    :return str: The URL of the lat lon in Gmaps.
    """
    return f"https://www.google.com/maps/search/?api=1&query={latlon[0]},{latlon[1]}"


def meters_to_feet(meters: float) -> float:
    """
    Convert meters to feet.

    :param float meters: A distance in meters.
    :return float: The distance in feet.
    """
    return meters * 3.280839895


def feet_to_meters(feet: float) -> float:
    """
    Convert feet to meters.

    :param float feet: A distance in feet.
    :return float: The distance in meters.
    """
    return feet / 3.280839895


def haversine_distance(coord1: list, coord2: list) -> float:
    """
    Calculate the Haversine distance between two points specified by their latitude and longitude
    coordinates.

    :param list coord1: Latitude and longitude coordinates of the first point in the format
    [latitude, longitude].
    :param list coord2: Latitude and longitude coordinates of the second point in the format
    [latitude, longitude].
    :return float: The distance between the two points in feet.
    """
    # Radius of the Earth in kilometers
    radius = 6371.0
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
    distance_km = radius * c
    # Convert kilometers to feet (1 km = 3280.84 feet)
    return meters_to_feet(distance_km * 1000)


def detect_consecutive_sequences(integers: list) -> list:
    """
    Detects consecutive sequences of integers in a list of integers.
    This function sorts the input integers and then identifies groups of consecutive integers
    by checking for breaks (gaps) in the sequence. It returns a list of lists, where each inner
    list contains a sequence of consecutive integers.

    :param integers: A list or array of integers representing the integers to be checked.
    :type integers: list or ndarray
    :return list: A list of lists, where each inner list contains consecutive integers from the
    input list, sorted in ascending order.
    """
    sorted_integers = np.sort(integers)
    diffs = np.diff(sorted_integers)
    # Identify where the break occurs (diff > 1)
    break_points = np.where(diffs > 1)[0] + 1
    # Add the start and end integers of the split sequences
    sequences = np.split(sorted_integers, break_points)
    return [seq.tolist() for seq in sequences]
