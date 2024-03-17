#!/usr/bin/env python3


from models.caltopo import CaltopoMap, CaltopoMarker, CaltopoShape


class Course:
    def __init__(self, caltopo_map, aid_stations: list, route_name: str):
        self.aid_stations = self.extract_aid_stations(aid_stations, caltopo_map)
        self.route = self.extract_route(route_name, caltopo_map)

    def extract_aid_stations(self, aid_stations: list, caltopo_map):
        # Map each marker's title to the object.
        title_to_marker = {marker.title: marker for marker in caltopo_map.markers}
        try:
            return [
                AidStation(
                    title_to_marker[aid_station["name"]]._feature_dict, aid_station["mile_mark"]
                )
                for aid_station in aid_stations
            ]
        except KeyError as err:
            raise KeyError(f"aid station '{err.args[0]}' not found in {caltopo_map.markers}")

    def extract_route(self, route_name: str, caltopo_map):
        for shape in caltopo_map.shapes:
            if shape.title == route_name:
                return Route(shape._feature_dict)
        raise LookupError(f"no shape called '{route_name}' found in shapes: {caltopo_map.shapes}")


class AidStation(CaltopoMarker):
    def __init__(self, feature_dict, mile_mark):
        super().__init__(feature_dict)
        self.mile_mark = mile_mark


class Route(CaltopoShape):
    def __init__(self, feature_dict):
        super().__init__(feature_dict)
        # TODO this doesn't handle 3 long lists.
        self.points, self.distances = transform_path([[y, x] for x, y in self.coordinates], 0.11)
        self.length = self.distances[-1]
        self.start_location = self.points[0]
        self.finish_location = self.points[-1]
        self.kdtree = KDTree(self.points)
