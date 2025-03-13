#!/usr/bin/env python3


import numpy as np
import pytest
import pytz
from ultra_tracker_fixtures import *
from test_race_01 import caltopo_map_01, race_01_config, course_01, race_01_path

from ultra_tracker.models import course


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


@pytest.fixture
def figure_8_course():
    return np.array(
        [
            [39.23211507705254, -76.73341015455956],
            [39.232921186097386, -76.73378566382165],
            [39.234483515404605, -76.73405388472314],
            [39.23655271716178, -76.73461178419824],
            [39.23743356364831, -76.73396805403466],
            [39.2396064870435, -76.73494437811608],
            [39.24123514248017, -76.73174718497033],
            [39.24071995964499, -76.72769168493981],
            [39.23895833813752, -76.72696212408776],
            [39.2364820217905, -76.72704795477624],
            [39.23520228042921, -76.7283568727755],
            [39.23563441770786, -76.73419335959191],
            [39.2356842778908, -76.73483708975549],
            [39.23531863572639, -76.7378840791964],
            [39.23337405220233, -76.74103835699792],
            [39.22981715316172, -76.74269059775109],
            [39.22823809814144, -76.73957923529382],
            [39.22815498899829, -76.73636058447595],
            [39.22862039893231, -76.73337796805139],
            [39.23074794789731, -76.73299172995324],
            [39.231944665845056, -76.73337796805139],
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


def test_course_creation_timezone(course_01):
    assert course_01.timezone == pytz.timezone("America/New_York")


def test_course_creation_course_elements(course_01, race_01_config):
    assert len(course_01.course_elements) == (len(race_01_config["aid_stations"]) + 2) * 2 - 1


def test_course_creation_route(course_01):
    assert bool(course_01.route)


def test_course_creation_aid_not_found(caltopo_map_01, race_01_config):
    aid_stations_map_01 = race_01_config["aid_stations"]
    aid_stations_map_01.append({"name": "Non-existent Aid", "mile_mark": 10})
    with pytest.raises(LookupError):
        course_01 = course.Course(caltopo_map_01, aid_stations_map_01, "Route 01")


def test_course_creation_route_not_found(caltopo_map_01, race_01_config):
    with pytest.raises(LookupError):
        course_01 = course.Course(
            caltopo_map_01, race_01_config["aid_stations"], "Non-existent Route"
        )


def test_route_gain(course_01):
    assert course_01.route.gain == np.float64(1140.5008234795741)


def test_route_loss(course_01):
    assert course_01.route.loss == np.float64(1194.7701806399723)


def test_route_get_elevation_at_mile_mark(course_01):
    assert (
        course_01.route.get_elevation_at_mile_mark(course_01.route.distances[100])
        == 479.00262467000005
    )


def test_route_get_point_at_mile_mark(course_01):
    np.testing.assert_array_equal(
        course_01.route.get_point_at_mile_mark(course_01.route.distances[100]),
        np.array([39.26911502211737, -76.73395001678226]),
    )


def test_route_get_indices_within_radius_overlap(course_01):
    result = course_01.route.get_indices_within_radius(39.27470, -76.72012, 100)
    np.testing.assert_array_equal(result[0], np.array([30, 13, 14, 29]))
    assert result[1] == False


def test_route_get_indices_within_radius_no_overlap(course_01):
    result = course_01.route.get_indices_within_radius(39.27407, -76.72289, 100)
    np.testing.assert_array_equal(result[0], np.array([38]))
    assert result[1] == True


def test_find_closest_index_basic(short_2d_points_array_very_far):
    interpolated_array, distances = course.transform_path(short_2d_points_array_very_far, 5, 25)
    coordinates = [39.22138, -76.71350]
    assert course.find_closest_index(4, coordinates, distances, interpolated_array) == 881


def test_find_closest_index_figure_8(figure_8_course):
    interpolated_array, distances = course.transform_path(figure_8_course, 5, 25)
    coordinates = [39.23561, -76.73431]
    assert course.find_closest_index(1.7, coordinates, distances, interpolated_array) == 353


def test_align_known_mile_marks(figure_8_course):
    interpolated_array, distances = course.transform_path(figure_8_course, 10, 75)
    known_mile_marks = [
        {"coordinates": [39.23204, -76.73340], "mile_mark": 0, "name": "Start"},
        {"coordinates": [39.23559, -76.73442], "mile_mark": 0.34, "name": "AS1"},
        {"coordinates": [39.24002, -76.73533], "mile_mark": 0.67, "name": "AS2"},
        {"coordinates": [39.23559, -76.73442], "mile_mark": 2, "name": "AS3"},
        {"coordinates": [39.22814, -76.73900], "mile_mark": 2.8, "name": "AS4"},
        {"coordinates": [39.23204, -76.73340], "mile_mark": 3.4, "name": "Finish"},
    ]
    modified_distances = course.align_known_mile_marks(
        distances, interpolated_array, known_mile_marks
    )
    expected_modified_distances = np.array(
        [
            0.0,
            0.015454545454545455,
            0.03090909090909091,
            0.046363636363636364,
            0.06181818181818182,
            0.07727272727272727,
            0.09272727272727273,
            0.10818181818181818,
            0.12363636363636364,
            0.1390909090909091,
            0.15454545454545454,
            0.17,
            0.18545454545454546,
            0.20090909090909093,
            0.21636363636363637,
            0.23181818181818184,
            0.24727272727272728,
            0.26272727272727275,
            0.2781818181818182,
            0.29363636363636364,
            0.3090909090909091,
            0.3245454545454546,
            0.34,
            0.35500000000000004,
            0.37000000000000005,
            0.385,
            0.4,
            0.41500000000000004,
            0.43000000000000005,
            0.44500000000000006,
            0.46,
            0.47500000000000003,
            0.49000000000000005,
            0.505,
            0.52,
            0.535,
            0.55,
            0.5650000000000001,
            0.5800000000000001,
            0.595,
            0.6100000000000001,
            0.625,
            0.6400000000000001,
            0.655,
            0.67,
            0.6847777777777778,
            0.6995555555555556,
            0.7143333333333334,
            0.7291111111111112,
            0.7438888888888889,
            0.7586666666666667,
            0.7734444444444445,
            0.7882222222222223,
            0.803,
            0.8177777777777778,
            0.8325555555555556,
            0.8473333333333334,
            0.8621111111111112,
            0.8768888888888889,
            0.8916666666666667,
            0.9064444444444445,
            0.9212222222222223,
            0.936,
            0.9507777777777778,
            0.9655555555555556,
            0.9803333333333334,
            0.9951111111111112,
            1.0098888888888888,
            1.0246666666666666,
            1.0394444444444444,
            1.0542222222222222,
            1.069,
            1.0837777777777777,
            1.0985555555555555,
            1.1133333333333333,
            1.128111111111111,
            1.1428888888888888,
            1.1576666666666666,
            1.1724444444444444,
            1.1872222222222222,
            1.202,
            1.2167777777777777,
            1.2315555555555555,
            1.2463333333333333,
            1.261111111111111,
            1.2758888888888889,
            1.2906666666666666,
            1.3054444444444444,
            1.3202222222222222,
            1.335,
            1.3497777777777777,
            1.3645555555555555,
            1.3793333333333333,
            1.394111111111111,
            1.4088888888888889,
            1.4236666666666666,
            1.4384444444444444,
            1.4532222222222222,
            1.468,
            1.4827777777777778,
            1.4975555555555555,
            1.5123333333333333,
            1.527111111111111,
            1.5418888888888889,
            1.5566666666666666,
            1.5714444444444444,
            1.5862222222222222,
            1.601,
            1.6157777777777778,
            1.6305555555555555,
            1.6453333333333333,
            1.660111111111111,
            1.6748888888888889,
            1.6896666666666667,
            1.7044444444444444,
            1.7192222222222222,
            1.734,
            1.7487777777777778,
            1.7635555555555555,
            1.7783333333333333,
            1.793111111111111,
            1.8078888888888889,
            1.8226666666666667,
            1.8374444444444444,
            1.8522222222222222,
            1.867,
            1.8817777777777778,
            1.8965555555555556,
            1.9113333333333333,
            1.926111111111111,
            1.9408888888888889,
            1.9556666666666667,
            1.9704444444444444,
            1.9852222222222222,
            2.0,
            2.0145454545454546,
            2.0290909090909093,
            2.0436363636363635,
            2.058181818181818,
            2.0727272727272728,
            2.0872727272727274,
            2.1018181818181816,
            2.1163636363636362,
            2.130909090909091,
            2.1454545454545455,
            2.16,
            2.1745454545454543,
            2.189090909090909,
            2.2036363636363636,
            2.2181818181818183,
            2.2327272727272724,
            2.247272727272727,
            2.2618181818181817,
            2.2763636363636364,
            2.290909090909091,
            2.305454545454545,
            2.32,
            2.3345454545454545,
            2.349090909090909,
            2.3636363636363633,
            2.378181818181818,
            2.3927272727272726,
            2.4072727272727272,
            2.421818181818182,
            2.4363636363636365,
            2.4509090909090907,
            2.4654545454545453,
            2.48,
            2.494545454545454,
            2.509090909090909,
            2.5236363636363635,
            2.538181818181818,
            2.5527272727272727,
            2.5672727272727274,
            2.5818181818181816,
            2.596363636363636,
            2.610909090909091,
            2.625454545454545,
            2.6399999999999997,
            2.6545454545454543,
            2.669090909090909,
            2.6836363636363636,
            2.6981818181818182,
            2.7127272727272724,
            2.727272727272727,
            2.7418181818181817,
            2.8,
            2.823076923076923,
            2.846153846153846,
            2.8692307692307693,
            2.8923076923076922,
            2.9153846153846152,
            2.9384615384615382,
            2.9615384615384612,
            2.9846153846153847,
            3.0076923076923077,
            3.0307692307692307,
            3.0538461538461537,
            3.0769230769230766,
            3.0999999999999996,
            3.123076923076923,
            3.146153846153846,
            3.169230769230769,
            3.192307692307692,
            3.2153846153846155,
            3.2384615384615385,
            3.2615384615384615,
            3.2846153846153845,
            3.3076923076923075,
            3.3307692307692305,
            3.353846153846154,
            3.376923076923077,
            3.4,
            3.4,
        ]
    )
    np.testing.assert_array_equal(modified_distances, expected_modified_distances)
