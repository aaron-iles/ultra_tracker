#!/usr/bin/env python3


from ultra_tracker.models import course
import numpy as np
import pytz
import pytest

from ultra_tracker_fixtures import *


@pytest.fixture
def short_2d_points_array_far():
    return np.array([[39.25694, -76.77481], [39.25633, -76.77265], [39.25491, -76.77048]])


@pytest.fixture
def short_2d_points_array_close():
    return np.array(
        [
            [39.25690, -76.77449],
            [39.25688, -76.77442],
            [39.25685, -76.77434],
            [39.25682, -76.77414],
            [39.25677, -76.77403],
            [39.25674, -76.77393],
        ]
    )


@pytest.fixture
def short_2d_points_array_very_far():
    return np.array(
        [[39.25696, -76.77645], [39.23546, -76.74214], [39.22207, -76.71278], [39.22978, -76.66696]]
    )


@pytest.fixture
def short_2d_points_array_various_elevations():
    return np.array(
        [
            [39.44828, -77.62682],
            [39.25616, -76.61029],
            [27.98881, 86.92545],
        ]
    )


def test_interpolate_and_filter_points_far_interpolation_tight(short_2d_points_array_far):
    interpolated_array = course.interpolate_and_filter_points(short_2d_points_array_far, 1, 10)
    assert len(interpolated_array) == 145


def test_interpolate_and_filter_points_far_interpolation_loose(short_2d_points_array_far):
    interpolated_array = course.interpolate_and_filter_points(short_2d_points_array_far, 5, 75)
    assert len(interpolated_array) == 21


def test_interpolate_and_filter_points_close_filter(short_2d_points_array_close):
    interpolated_array = course.interpolate_and_filter_points(short_2d_points_array_close, 50, 100)
    assert len(interpolated_array) == 4


def test_transform_path_very_far(short_2d_points_array_very_far):
    interpolated_array, cum_distances = course.transform_path(short_2d_points_array_very_far, 5, 75)
    assert cum_distances[-1] == 6.693805083466609


def test_transform_path_far(short_2d_points_array_far):
    interpolated_array, cum_distances = course.transform_path(short_2d_points_array_far, 1, 10)
    assert cum_distances[-1] == 0.2711855245038631


def test_transform_path_short(short_2d_points_array_close):
    interpolated_array, cum_distances = course.transform_path(short_2d_points_array_close, 5, 10)
    assert cum_distances[-1] == 0.03225980102383289


def test_find_elevations(short_2d_points_array_various_elevations):
    elevations = course.find_elevations(short_2d_points_array_various_elevations)
    np.testing.assert_array_equal(
        elevations, np.array([1755.249343825, 3.780463716217651, 28738.682053815093])
    )


def test_cumulative_altitude_changes():
    cum_changes = course.cumulative_altitude_changes(np.array([1, 3, 5, 7]))
    np.testing.assert_array_equal(cum_changes[0], np.array([0, 2, 4, 6]))
    np.testing.assert_array_equal(cum_changes[1], np.array([0, 0, 0, 0]))

    cum_changes = course.cumulative_altitude_changes(np.array([7, 5, 3, 1]))
    np.testing.assert_array_equal(cum_changes[0], np.array([0, 0, 0, 0]))
    np.testing.assert_array_equal(cum_changes[1], np.array([0, 2, 4, 6]))

    cum_changes = course.cumulative_altitude_changes(np.array([5, 11, 19, 4, 7, 12, 3, 1]))
    np.testing.assert_array_equal(cum_changes[0], np.array([0, 6, 14, 14, 17, 22, 22, 22]))
    np.testing.assert_array_equal(cum_changes[1], np.array([0, 0, 0, 15, 15, 15, 24, 26]))


def test_course_creation_timezone(caltopo_map_01, aid_stations_map_01):
    course_01 = course.Course(caltopo_map_01, aid_stations_map_01, "Route 01")
    assert course_01.timezone == pytz.timezone("America/New_York")


def test_course_creation_course_elements(caltopo_map_01, aid_stations_map_01):
    course_01 = course.Course(caltopo_map_01, aid_stations_map_01, "Route 01")
    print(course_01.course_elements)
    assert len(course_01.course_elements) == (len(aid_stations_map_01) + 2) * 2 - 1


def test_course_creation_route(caltopo_map_01, aid_stations_map_01):
    course_01 = course.Course(caltopo_map_01, aid_stations_map_01, "Route 01")
    assert bool(course_01.route)


def test_course_creation_aid_not_found(caltopo_map_01, aid_stations_map_01):
    aid_stations_map_01.append({"name": "Non-existent Aid", "mile_mark": 10})
    with pytest.raises(LookupError):
        course_01 = course.Course(caltopo_map_01, aid_stations_map_01, "Route 01")


def test_course_creation_route_not_found(caltopo_map_01, aid_stations_map_01):
    with pytest.raises(LookupError):
        course_01 = course.Course(caltopo_map_01, aid_stations_map_01, "Non-existent Route")


def test_route_gain(caltopo_map_01, aid_stations_map_01):
    course_01 = course.Course(caltopo_map_01, aid_stations_map_01, "Route 01")
    assert course_01.route.gain == np.float64(1140.5008234795741)


def test_route_loss(caltopo_map_01, aid_stations_map_01):
    course_01 = course.Course(caltopo_map_01, aid_stations_map_01, "Route 01")
    assert course_01.route.loss == np.float64(1194.7701806399723)


def test_route_get_elevation_at_mile_mark(caltopo_map_01, aid_stations_map_01):
    course_01 = course.Course(caltopo_map_01, aid_stations_map_01, "Route 01")
    assert (
        course_01.route.get_elevation_at_mile_mark(course_01.route.distances[100])
        == 479.00262467000005
    )


def test_route_get_point_at_mile_mark(caltopo_map_01, aid_stations_map_01):
    course_01 = course.Course(caltopo_map_01, aid_stations_map_01, "Route 01")
    np.testing.assert_array_equal(
        course_01.route.get_point_at_mile_mark(course_01.route.distances[100]),
        np.array([39.26911502211737, -76.73395001678226]),
    )
