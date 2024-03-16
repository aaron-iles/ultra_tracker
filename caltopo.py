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

    def __init__(self, map_id, cookie):
        self.map_id = map_id
        self.cookie = cookie
        self.features = []

        self.tracking_folder_id = None
        self.route_id = None
        self.marker_id = None
        self.route = []
        self.distances = []
        self.get_map_data()
        self.start_location = self.route[0]
        self.finish_location = self.route[-1]
        self.kdtree = KDTree(self.route)

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
            "Cookie": self.cookie,
        }
        response = requests.get(url, headers=headers, verify=True)
        return response.json()

    def extract_feature(self, feature_class: str, feature_name: str) -> dict:
        """
        Iterates through the list of map features and attempts to extract the feature matching the
        class and name provided.

        :param str feature_class: The map item class like Folder, Shape, or Marker.
        :param str feature_name: The map item's name or "title".
        :return dict: The feature dict.
        """
        return next(
            filter(
                lambda d: d.get("properties", {}).get("class") == feature_class
                and d.get("properties", {}).get("value") == feature_name,
                self.features,
            ),
            None,
        )

    def get_map_data(self):
        """
        Gets all of the data of the CalTopo map, cleans and transforms some of it, and stores it in
        the appropriate attributes.

        :reutrn None:
        """
        map_data = self.get(f"https://caltopo.com/api/v1/map/{self.map_id}/since/0")
        try:
            features = map_data["result"]["state"]["features"]
        except KeyError:
            print(f"unable to find features in {map_data}")
            return
        self.features = features
        # TODO get rid of this.
        import json

        with open("feat", "w") as f:
            json.dump(features, f)
        for feature in features:
            if (
                feature.get("properties", {}).get("class") == "Folder"
                and feature.get("properties", {}).get("title") == "Live Tracking"
            ):
                self.tracking_folder_id = feature["id"]
            elif (
                feature.get("properties", {}).get("class") == "Shape"
                and feature.get("properties", {}).get("title") == "Route"
            ):
                self.route_id = feature["id"]
                # TODO this doesn't handle 3 long lists.
                ordered_points = [[y, x] for x, y in feature["geometry"]["coordinates"]]
                self.route, self.distances = transform_path(ordered_points, 0.11)
            elif (
                feature.get("properties", {}).get("class") == "Marker"
                and feature.get("properties", {}).get("title") == "Aaron"
            ):
                self.marker_id = feature["id"]

    def move_marker(
        self, location: list, marker_course: float, description: str
    ) -> requests.Response:
        """
        Moves the tracker marker to the provided location, updates its description, and rotates it.

        :param list location: The (x, y) coordinates to which the marker should be moved.
        :param float marker_course: The heading (0 - 359) in which the marker should be rotated.
        :param str description: The description to set on the marker.
        :return requests.Reponse: A response object of the issued POST.
        """
        url = f"https://caltopo.com/api/v1/map/{self.map_id}/Marker/{self.marker_id}"
        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Cookie": self.cookie,
        }
        payload = {
            "json": {
                "type": "Feature",
                "id": self.marker_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [location[1], location[0]],
                },
                "properties": {
                    "title": "Aaron",
                    "description": description,
                    "folderId": self.tracking_folder_id,
                    "marker-size": "1.5",
                    "marker-symbol": "a:4",
                    "marker-color": "A200FF",
                    "marker-rotation": marker_course,
                    "class": "Marker",
                },
            }
        }
        result = requests.post(url, headers=headers, data=urlencode(payload), verify=True)
        print(f"marker move result {result.text}")
        return result


class CaltopoFeature:
    feature_class = "Feature"

    def __init__(self, feature_dict: dict):
        self.id = feature_dict.get("id", "")
        self.properties = feature_dict.get("properties", {})
        self.geometry = feature_dict.get("geometry", {})
        self.title = self.properties.get("title", "")
        self.folder_id = self.properties.get("folderId")
        self.description = self.properties.get("description", "")


class CaltopoMarker(CaltopoFeature):
    feature_class = "Marker"

    def __init__(self, feature_dict: dict):
        super.__init__(self, feature_dict)
        self.description = None
        self.folder = None
        self.size = self.properties.get("marker-size", "1")
        self.symbol = self.properties.get("marker-symbol")
        self.color = self.properties.get("marker-color", "FF0000")
        self.rotation = self.properties.get("marker-rotation", 0)
        # Switch x and y to more traditional (latitude, longitude) order.
        self.coordinates = self.geometry.get("coordinates", [0, 0])[:2][::-1]

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
                "folderId": self.folder,  # TODO necessary??
                "marker-size": self.size,
                "marker-symbol": self.symbol,
                "marker-color": self.color,
                "marker-rotation": self.rotation,
                "class": "Marker",
            },
        }

    def update(self) -> requests.Response:
        """
        Moves the tracker marker to the provided location, updates its description, and rotates it.

        :param list location: The (x, y) coordinates to which the marker should be moved.
        :param float marker_course: The heading (0 - 359) in which the marker should be rotated.
        :param str description: The description to set on the marker.
        :return requests.Reponse: A response object of the issued POST.
        """
        url = f"https://caltopo.com/api/v1/map/{self.caltopo_map.map_id}/Marker/{self.marker_id}"
        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Cookie": self.caltopo_map.cookie,
        }
        result = requests.post(url, headers=headers, data=urlencode(self.as_json), verify=True)
        print(f"marker update result {result.text}")
        return result


class CaltopoShape:
    feature_class = "Shape"

    def __init__(self, feature_dict: dict):
        super.__init__(self, feature_dict)
        self.pattern = self.properties.get("pattern", "stroke")
        self.stroke_width = self.properties.get("stroke-width", "solid")
        self.fill = self.properties.get("fill", "#FF0000")
        self.stroke = self.properties.get("width", "#FF0000")


class CaltopoFolder:
    feature_class = "Folder"

    def __init__(self, feature_dict: dict):
        super.__init__(self, feature_dict)























def update() -> requests.Response:
    url = f"https://caltopo.com/api/v1/map/U5P1F/Marker/723e828f-dbbd-4c7c-890a-f9884f136f57"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": 'JSESSIONID=7C40CE0B00386DDF9B41D19616729077',
    }
    foo = {
            "type": "Feature",
            "id": '723e828f-dbbd-4c7c-890a-f9884f136f57',
            "geometry": {
                "type": "Point",
                "coordinates": [36.77849, -75.97183][::-1],
            },
            "properties": {
                "title": 'testing',
                "description": '',
                "folderId": None,  
                "marker-size": '1',
                "marker-symbol": 'point',
                "marker-color": 'FF0000',
                "marker-rotation": 0,
                "class": "Marker",
            },
        }
    result = requests.post(url, headers=headers, data=urlencode(foo), verify=True)
    print(f"marker update result {result.text}")
    return result
