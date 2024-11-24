#!/usr/bin/env python3


import base64
import hmac
import json
import logging
import time
import uuid

import requests

# import uwsgidecorators

from .utils import get_gmaps_url

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

        :param str url_endpoint: The URL endpoint to which to issue the GET.
        :return requests.Response: The raw response object from the GET.
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

    def delete(self, url_endpoint: str) -> requests.Response:
        """
        Issue a DELETE request to Caltopo and reutrn the response.

        :param str url_endpoint: The URL endpoint to which to issue the DELETE.
        :return requests.Response: The raw response object from the DELETE.
        """
        expires = int(time.time() * 1000) + 120000  # 2 minutes from current time, in milliseconds
        data = f"DELETE {url_endpoint}\n{expires}\n"
        params = {}
        params["id"] = self.credential_id
        params["expires"] = expires
        params["signature"] = self._get_token(data)
        params["json"] = ""
        return requests.delete(
            f"{self.url_prefix}{url_endpoint}",
            params=params,
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
        self.url = f"https://caltopo.com/m/{map_id}"
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
                new_folder = CaltopoFolder(feature, self.map_id, self.session)
                if new_folder in self.folders:
                    raise ValueError(f"folder names must be unique: {new_folder}")
                self.folders.add(new_folder)
            elif feature_class == "Shape":
                new_shape = CaltopoShape(feature, self.map_id, self.session)
                if new_shape in self.shapes:
                    raise ValueError(f"shape names must be unique: {new_shape}")
                self.shapes.add(new_shape)
            elif feature_class == "Marker":
                new_marker = CaltopoMarker(feature, self.map_id, self.session)
                if new_marker in self.markers:
                    raise ValueError(f"marker names must be unique: {new_marker}")
                self.markers.add(new_marker)
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
        response = self.session.delete(url)
        if not response.ok:
            logger.info(f"WARNING: unable to delete test folder: {response.text}")
            return False
        logger.info(f"authentication test passed for map ID {self.map_id}")
        return True

    def get_or_create_folder(self, title: str):
        """
        Gets a folder from the map. If it does not exist, the folder is created.

        :param str title: The title of the folder.
        :return CaltopoFolder: The folder object.
        """
        folder_feature_dict = {
            "properties": {"title": title, "visible": True, "labelVisible": True},
            "id": None,
        }
        new_folder = CaltopoFolder(folder_feature_dict, self.map_id, self.session)
        if new_folder in self.folders:
            logger.info(f"INFO: folder '{title}' already exists")
            return next((obj for obj in self.folders if obj.title == title))
        logger.info(f"INFO: folder '{title}' not found; creating folder")
        self.folders.add(new_folder)
        url = f"/api/v1/map/{self.map_id}/Folder/"
        response = self.session.post(url, new_folder.as_json)
        import ipdb; ipdb.set_trace()
        if not response.ok:
            logger.info(f"WARNING: unable to create folder: {response.text}")
        new_folder.id = response.json()['result']['id']
        return new_folder

    def get_or_create_marker(
        self,
        title: str,
        folder_name: str,
        marker_size: int,
        marker_symbol: str,
        marker_color: str,
        coordinates: list,
    ):
        """ """
        folder = self.get_or_create_folder(folder_name)
        import ipdb; ipdb.set_trace()

        feature_dict = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": coordinates,
            },
            "properties": {
                "title": title,
                "description": "",
                "folderId": folder_id,
                "marker-size": marker_size,
                "marker-symbol": marker_symbol,
                "marker-color": marker_color,
                "marker-rotation": 0,
                "class": "Marker",
            },
        }

        assert new_marker not in self.markers


class CaltopoFeature:
    """
    This represents a single feature object in Caltopo.

    :param dict feature_dict: The raw dict of features from Caltopo.
    :param str map_id: The map ID (UUID-like) from Caltopo.
    :param CaltopoSession session: The session to use to update Caltopo.
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
        return hash(self.title)

    # Caltopo allows features with the same title, but this application does not and will treat the
    # titles as the unique identifiers.
    def __eq__(self, other):
        return self.title == other.title

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
        self.gmaps_url = get_gmaps_url(self.coordinates[::-1])

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

    # @uwsgidecorators.thread
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

    @property
    def as_json(self) -> dict:
        """
        Converts the folder to a dict.

        :return dict: A dict representation of the folder object.
        """
        return {"properties":{"title":self.title,"visible":True,"labelVisible":True},"id":self.id}
