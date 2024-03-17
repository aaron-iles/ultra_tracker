#!/usr/bin/env python3


from scipy.spatial import KDTree
from urllib.parse import urlencode
import requests

from geo_utils import interpolate_between_points, transform_path


class CaltopoMap:
    """
    An instance of a CalTopo map from https://caltopo.com/. This represents a single map with 0 or
    more map objects.
    """

    def __init__(self, map_id, session_id):
        self.folders = set()
        self.map_id = map_id
        self.markers = set()
        self.session_id = session_id
        self.shapes = set()
        self.get_map_features()

    def get(self, url: str) -> dict:
        """
        Perform a GET to the CalTopo API.

        :param str url: The URL on which to issue the GET.
        :return dict: The response dict.
        """
        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Cookie": f"JSESSIONID={self.session_id}",
        }
        response = requests.get(url, headers=headers, verify=True)
        return response.json()

    def get_map_features(self) -> None:
        """
        Gets all of the features from the map, converts them to objects, and stores them in the
        appropriate attributes.

        :reutrn None:
        """
        map_data = self.get(f"https://caltopo.com/api/v1/map/{self.map_id}/since/0")
        try:
            features = map_data["result"]["state"]["features"]
        except KeyError:
            raise LookupError(f"unable to find features in {map_data}")
        for feature in features:
            feature_class = feature.get("properties", {}).get("class")
            if feature_class == "Folder":
                self.folders.add(CaltopoFolder(feature))
            elif feature_class == "Shape":
                self.shapes.add(CaltopoShape(feature))
            elif feature_class == "Marker":
                self.markers.add(CaltopoMarker(feature))
            else:
                print(f"Unknown feature found: {feature}")


class CaltopoFeature:
    feature_class = "Feature"

    def __init__(self, feature_dict: dict):
        self._feature_dict = feature_dict
        self.description = self.properties.get("description", "")
        self.folder_id = self.properties.get("folderId")
        self.geometry = feature_dict.get("geometry", {})
        self.id = feature_dict.get("id", "")
        self.properties = feature_dict.get("properties", {})
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
    feature_class = "Marker"

    def __init__(self, feature_dict: dict):
        super().__init__(feature_dict)
        self.color = self.properties.get("marker-color", "FF0000")
        # Switch x and y to more traditional (latitude, longitude) order.
        self.coordinates = self.geometry.get("coordinates", [0, 0])[:2][::-1]
        self.description = None
        self.folder = None
        self.rotation = self.properties.get("marker-rotation", 0)
        self.size = self.properties.get("marker-size", "1")
        self.symbol = self.properties.get("marker-symbol")

    @property
    def as_json(self) -> dict:
        """ """
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
                "folderId": self.folder,
                "marker-size": self.size,
                "marker-symbol": self.symbol,
                "marker-color": self.color,
                "marker-rotation": self.rotation,
                "class": "Marker",
            },
        }

    def update(self) -> requests.Response:
        """
        Moves the marker to the provided location, updates its description, and rotates it.

        :param list location: The (x, y) coordinates to which the marker should be moved.
        :param float marker_heading: The heading (0 - 359) in which the marker should be rotated.
        :param str description: The description to set on the marker.
        :return requests.Reponse: A response object of the issued POST.
        """
        url = f"https://caltopo.com/api/v1/map/{self.caltopo_map.map_id}/Marker/{self.marker_id}"
        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Cookie": f"JSESSIONID={self.caltopo_map.session_id}",
        }
        result = requests.post(
            url, headers=headers, data=urlencode({"json": self.as_json}), verify=True
        )
        print(f"marker update result {result.text}")
        return result


class CaltopoShape(CaltopoFeature):
    feature_class = "Shape"

    def __init__(self, feature_dict: dict):
        super().__init__(feature_dict)
        self.pattern = self.properties.get("pattern", "stroke")
        self.stroke_width = self.properties.get("stroke-width", "solid")
        self.fill = self.properties.get("fill", "#FF0000")
        self.stroke = self.properties.get("width", "#FF0000")
        # Warning! This could be a 3-deep list: [[[-75.8..., 32.1...]]]
        self.coordinates = self.geometry.get("coordinates", [])


class CaltopoFolder(CaltopoFeature):
    feature_class = "Folder"

    def __init__(self, feature_dict: dict):
        super().__init__(feature_dict)
