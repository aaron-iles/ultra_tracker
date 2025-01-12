#!/usr/bin/env python3


import datetime

from ..utils import meters_to_feet, get_timezone

GPS_FIX_MAP = {0: "No Fix", 1: "2D Fix", 2: "3D Fix", 3: "3D Fix+", None: "unknown"}


class Ping:
    """
    Represents a single ping payload from the tracker.
    See https://developer.garmin.com/inReach/IPC_Outbound.pdf

    :param dict ping_data: The raw tracker payload.
    """

    __slots__ = {
        "_event",
        "altitude",
        "gps_fix",
        "heading",
        "imei",
        "latitude",
        "longitude",
        "message_code",
        "speed",
        "timestamp",
        "low_battery",
        "interval_change",
    }

    def __init__(self, ping_data: dict):
        self._event = ping_data.get("Events", [{}])[0]
        self.altitude = meters_to_feet(self._event.get("point", {}).get("altitude", 0.0))
        self.gps_fix = GPS_FIX_MAP.get(self._event.get("point", {}).get("gpsFix"))
        self.heading = self._event.get("point", {}).get("course", 0)
        self.imei = self._event.get("imei")
        self.latitude = self._event.get("point", {}).get("latitude", 0.0)
        self.longitude = self._event.get("point", {}).get("longitude", 0.0)
        self.message_code = self._event.get("messageCode")
        self.speed = self._event.get("point", {}).get("speed", 0.0)
        self.low_battery = self._event.get("status", {}).get("lowBattery", 0)
        self.interval_change = self._event.get("status", {}).get("intervalChange", 0)
        self.timestamp = self.extract_timestamp(
            self._event.get("timeStamp", 0), get_timezone([self.latitude, self.longitude])
        )

    @property
    def latlon(self) -> list:
        """
        The coordinates in (latitude, longitude) order.

        :return list: The coordinates in (latitude, longitude) order.
        """
        return [self.latitude, self.longitude]

    @property
    def lonlat(self) -> list:
        """
        The coordinates in (longitude, latitude) order.

        :return list: The coordinates in (longitude, latitude) order.
        """
        return [self.longitude, self.latitude]

    @property
    def latlonalt(self) -> list:
        """
        The coordinates and altitude of the ping in (latitude, longitude, altitude) order.

        :return list: The coordinates in (x, y, z) order.
        """
        return [self.latitude, self.longitude, self.altitude]

    @staticmethod
    def extract_timestamp(timestamp: int or float, timezone) -> datetime.datetime:
        """
        Extracts the timestamp from the event.

        :param int or float timestamp: The unix timestamp.
        :param timezone: A pytz timezone object in which to normalize the timestamp.
        :return datetime.datetime: A datetime object representing the timestamp.
        """
        try:
            return datetime.datetime.fromtimestamp(timestamp, timezone)
        except ValueError:
            return datetime.datetime.fromtimestamp(timestamp // 1000, timezone)

    def __str__(self):
        return f"PING {self.timestamp} | {self.heading}° | {self.latlon}"

    @property
    def as_json(self) -> dict:
        """
        A json representation of the ping object.

        :return dict: The dict of the ping object.
        """
        return {
            "status": self._event.get("status", {}),
            "timestamp": self.timestamp,
            "timestamp_raw": self._event.get("timeStamp", 0),
            "heading": self.heading,
            "latlon": self.latlon,
            "lonlat": self.lonlat,
            "altitude": self.altitude,
            "gps_fix": self.gps_fix,
            "message_code": self.message_code,
            "speed": self.speed,
        }
