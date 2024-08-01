#!/usr/bin/env python3


import datetime
import logging

import pytz
from timezonefinder import TimezoneFinder

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


def get_timezone(latlon: list):
    """
    Given a location by coordinates, returns the timezone.

    :param list latlon: The latitude, longitude of the location.
    :return pytz: A timezone object.
    """
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=latlon[0], lng=latlon[1])
    if timezone_str:
        logger.info(f"determined {latlon} to be in timezone {timezone_str}")
        return pytz.timezone(timezone_str)
    else:
        return None


def get_gmaps_url(latlon: list) -> str:
    """
    Given a latitude and longitude, returns the associated Google Maps URL.

    :param list latlon: The latitude, longitude.
    :return str: The URL of the lat lon in Gmaps.
    """
    return f"http://maps.google.com/maps?z=12&t=m&q=loc:{latlon[0]}+{latlon[1]}"
