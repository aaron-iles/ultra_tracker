#!/usr/bin/env python3


import base64
import hmac
import json
import logging
import time
import uuid
from urllib.parse import urlencode

import pytz
import requests
import uwsgidecorators
from timezonefinder import TimezoneFinder

logger = logging.getLogger(__name__)


class CaltopoSession:
    """
    A session object to use to issue GETs and POSTs to Caltopo.

    :param str credential_id: The 12-character credential ID from the Caltopo user page.
    :param str key: The base-64 encoded key associated with the credential ID.
    """

    def __init__(self, credential_id: str, key: str):
        self.url_prefix = "https://caltopo.com"
        self.credential_id = credential_id
        self.key = key

    def _get_token(self, data: str) -> str:
        """
        Internal method to get the token needed for signed requests.

        :param str data: Data to be signed
        :return str: Signed token
        """
        token = hmac.new(base64.b64decode(self.key), data.encode(), "sha256").digest()
        return base64.b64encode(token).decode()

    def get(self, url_endpoint: str) -> requests.Response:
        """
        Issue a GET request to Caltopo and reutrn the response.

        :param str url_endpoint: The URL endpoint to which to issue the POST.
        :param dict payload: The payload data to send.
        :return requests.Response: The raw response object from the POST.
        """
        expires = int(time.time() * 1000) + 120000  # 2 minutes from current time, in milliseconds
        data = f"GET {url_endpoint}\n{expires}\n"
        params = {}
        params["id"] = self.credential_id
        params["expires"] = expires
        params["signature"] = self._get_token(data)
        return requests.get(
            f"{self.url_prefix}{url_endpoint}",
            data=params,
            verify=True,
            timeout=60,
        )

    def post(self, url_endpoint: str, payload: dict) -> requests.Response:
        """
        Issue a POST request to Caltopo and reutrn the response.

        :param str url_endpoint: The URL endpoint to which to issue the POST.
        :param dict payload: The payload data to send.
        :return requests.Response: The raw response object from the POST.
        """
        expires = int(time.time() * 1000) + 120000  # 2 minutes from current time, in milliseconds
        data = f"POST {url_endpoint}\n{expires}\n{json.dumps(payload)}"
        params = {}
        params["id"] = self.credential_id
        params["expires"] = expires
        params["signature"] = self._get_token(data)
        params["json"] = json.dumps(payload)
        return requests.post(
            f"{self.url_prefix}{url_endpoint}",
            data=params,
            verify=True,
            timeout=60,
        )


    def delete(self, url_endpoint: str, payload: dict) -> requests.Response:
        """
        Issue a DELETE request to Caltopo and reutrn the response.

        :param str url_endpoint: The URL endpoint to which to issue the POST.
        :param dict payload: The payload data to send.
        :return requests.Response: The raw response object from the POST.
        """
        expires = int(time.time() * 1000) + 120000  # 2 minutes from current time, in milliseconds
        data = f"DELETE {url_endpoint}\n{expires}\n{json.dumps(payload)}"
        params = {}
        params["id"] = self.credential_id
        params["expires"] = expires
        params["signature"] = self._get_token(data)
        params["json"] = json.dumps(payload)
        return requests.delete(
            f"{self.url_prefix}{url_endpoint}",
            data=params,
            verify=True,
            timeout=60,
        )





class CaltopoMap:
    """
    An instance of a CalTopo map from https://caltopo.com/. This represents a single map with 0 or
    more map objects.
    """

    def __init__(self, map_id: str, session: CaltopoSession):
        self.folders = set()
        self.map_id = map_id
        self.markers = set()
        self.session = session
        self.shapes = set()
        self.get_map_features()

    def get(self, url: str) -> dict:
        """
        Perform a GET to the CalTopo API.

        :param str url: The URL on which to issue the GET.
        :return dict: The response dict.
        """
        response = self.session.get(url)
        return response.json()

    def get_map_features(self) -> None:
        """
        Gets all of the features from the map, converts them to objects, and stores them in the
        appropriate attributes.

        :reutrn None:
        """
        map_data = self.get(f"/api/v1/map/{self.map_id}/since/0")
        try:
            features = map_data["result"]["state"]["features"]
        except KeyError:
            raise LookupError(f"unable to find features in {map_data}")
        for feature in features:
            feature_class = feature.get("properties", {}).get("class")
            if feature_class == "Folder":
                # TODO
                self.folders.add(CaltopoFolder(feature, self.map_id, self.session))
            elif feature_class == "Shape":
                self.shapes.add(CaltopoShape(feature, self.map_id, self.session))
            elif feature_class == "Marker":
                self.markers.add(CaltopoMarker(feature, self.map_id, self.session))
            else:
                logger.info(f"Unknown feature found: {feature}")

    def test_authentication(self) -> bool:
        """
        Attempts to create and delete a folder to ensure authentication is working.

        :return bool: True if the auth test passed and False otherwise.
        """
        url = f"/api/v1/map/{self.map_id}/Folder"
        params = {
            "properties": {
                "title": str(uuid.uuid1()),
                "visible": False,
                "labelVisible": False,
            },
            "id": None,
        }
        response = self.session.post(url, params)
        if not response.ok:
            logger.info(f"WARNING: unable to create test folder: {response.text}")
            return False
        url = f"/api/v1/map/{self.map_id}/Folder/{response.json()['result']['id']}"
        self.session.delete(url, {})
        logger.info(f"authentication test passed for map ID {self.map_id}")
        return True


class CaltopoFeature:
    """
    This represents a single feature object in Caltopo.

    :param dict feature_dict: The raw dict of features from Caltopo.
    :param str map_id: The map ID (UUID-like) from Caltopo.
    :param str session_id: The auth token for Caltopo.
    """

    feature_class = "Feature"

    def __init__(self, feature_dict: dict, map_id: str, session: CaltopoSession):
        self._feature_dict = feature_dict
        self.map_id = map_id
        self.session = session
        self.properties = feature_dict.get("properties", {})
        self.description = self.properties.get("description", "")
        self.folder_id = self.properties.get("folderId")
        self.geometry = feature_dict.get("geometry", {})
        self.id = feature_dict.get("id", "")
        self.title = self.properties.get("title", "")

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return f"{self.title} ({self.id})"

    def __str__(self):
        return f"{self.title} ({self.id})"


class CaltopoMarker(CaltopoFeature):
    """
    A Caltopo marker object.
    """

    feature_class = "Marker"

    def __init__(self, feature_dict: dict, map_id: str, session: CaltopoSession):
        super().__init__(feature_dict, map_id, session)
        self.color = self.properties.get("marker-color", "FF0000")
        # This comes in as longitude, latitude.
        self.coordinates = self.geometry.get("coordinates", [0, 0])[:2]
        self.description = ""
        self.rotation = self.properties.get("marker-rotation", 0)
        self.size = self.properties.get("marker-size", "1")
        self.symbol = self.properties.get("marker-symbol")
        self.gmaps_url = f"http://maps.google.com/maps?z=12&t=m&q=loc:{self.coordinates[1]}+{self.coordinates[0]}"

    @property
    def as_json(self) -> dict:
        """
        Converts the marker to a dict.

        :return dict: A dict representation of the marker object.
        """
        return {
            "type": "Feature",
            "id": self.id,
            "geometry": {
                "type": "Point",
                "coordinates": self.coordinates,
            },
            "properties": {
                "title": self.title,
                "description": self.description,
                "folderId": self.folder_id,
                "marker-size": self.size,
                "marker-symbol": self.symbol,
                "marker-color": self.color,
                "marker-rotation": self.rotation,
                "class": "Marker",
            },
        }

    @uwsgidecorators.thread
    def update(self) -> requests.Response:
        """
        Moves the marker to the provided location, updates its description, and rotates it.

        :return requests.Reponse: A response object of the issued POST.
        """
        url = f"/api/v1/map/{self.map_id}/Marker/{self.id}"
        response = self.session.post(url, self.as_json)
        if not response.ok:
            logger.info(f"WARNING: unable to update marker: {response.text}")
        return


class CaltopoShape(CaltopoFeature):
    """
    A Caltopo shape object. This includes lines, areas, and more.
    """

    feature_class = "Shape"

    def __init__(self, feature_dict: dict, map_id: str, session: CaltopoSession):
        super().__init__(feature_dict, map_id, session)
        self.pattern = self.properties.get("pattern", "stroke")
        self.stroke_width = self.properties.get("stroke-width", "solid")
        self.fill = self.properties.get("fill", "#FF0000")
        self.stroke = self.properties.get("width", "#FF0000")
        # Warning! This could be a 3-deep list: [[[-75.8..., 32.1...]]]
        self.coordinates = [point[:2] for point in self.geometry.get("coordinates", [])]


class CaltopoFolder(CaltopoFeature):
    """
    A Caltopo folder object.
    """

    feature_class = "Folder"

    def __init__(self, feature_dict: dict, map_id: str, session: CaltopoSession):
        super().__init__(feature_dict, map_id, session)


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
