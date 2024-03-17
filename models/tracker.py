#!/usr/bin/env python3


import datetime


class Ping:
    """
    Represents a single ping payload from the tracker.

    :param dict ping_data: The raw tracker payload.
    """
    __slots__ = {"_event", "altitude", "heading", "imei", "latitude", "longitude", "message_code", "speed", "timestamp"}
    def __init__(self, ping_data: dict):
        self._event = ping_data.get("Events", [{}])[0]
        self.altitude = self._event.get("point", {}).get("altitude", 0.0)
        self.heading = self._event.get("point", {}).get("course", 0)
        self.imei = self._event.get("imei")
        self.latitude = self._event.get("point", {}).get("latitude", 0.0)
        self.longitude = self._event.get("point", {}).get("longitude", 0.0)
        self.message_code = self._event.get("messageCode")
        self.speed = self._event.get("point", {}).get("speed", 0.0)
        self.timestamp = self.extract_timestamp()

    @property
    def latlon(self) -> tuple:
        return (self.latitude, self.longitude)

    @property
    def lonlat(self) -> tuple:
        return (self.latitude, self.longitude)


    def extract_timestamp(self):
        """
        Extracts the timestamp from the event.

        :return datetime.datetime: A datetime object representing the timestamp.
        """
        ts = self._event.get("timeStamp", 0)
        try:
            return datetime.datetime.fromtimestamp(ts)
        except ValueError:
            return datetime.datetime.fromtimestamp(ts // 1000)






