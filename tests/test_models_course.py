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
    assert len(course_01.course_elements) == len(race_01_config["aid_stations"]) * 2 - 1


def test_course_creation_route(course_01):
    assert bool(course_01.route)


def test_course_creation_aid_not_found(caltopo_map_01, race_01_config):
    aid_stations_map_01 = race_01_config["aid_stations"]
    aid_stations_map_01.append({"name": "Non-existent Aid", "mile_mark": 10})
    with pytest.raises(LookupError):
        course_01 = course.Course(
            caltopo_map_01, aid_stations_map_01, "Route 01", race_01_config["route_distance"]
        )


def test_course_creation_route_not_found(caltopo_map_01, race_01_config):
    with pytest.raises(LookupError):
        course_01 = course.Course(
            caltopo_map_01,
            race_01_config["aid_stations"],
            "Non-existent Route",
            race_01_config["route_distance"],
        )


def test_route_gain(course_01):
    assert course_01.route.gain == np.float64(1274.3555896371147)


def test_route_loss(course_01):
    assert course_01.route.loss == np.float64(1328.6249467975144)


def test_route_get_elevation_at_mile_mark(course_01):
    assert (
        course_01.route.get_elevation_at_mile_mark(course_01.route.distances[100])
        == 407.5355502215759
    )


def test_route_get_point_at_mile_mark(course_01):
    np.testing.assert_array_equal(
        course_01.route.get_point_at_mile_mark(course_01.route.distances[100]),
        np.array([39.27446818400414, -76.7205454570135]),
    )


def test_route_get_indices_within_radius_overlap(course_01):
    result = course_01.route.get_indices_within_radius(39.27470, -76.72012, 100)
    np.testing.assert_array_equal(
        result[0], np.array([95, 94, 43, 96, 42, 44, 93, 45, 41, 97, 92, 46, 40, 98])
    )
    assert result[1] == False


def test_route_get_indices_within_radius_no_overlap(course_01):
    result = course_01.route.get_indices_within_radius(39.27407, -76.72289, 100)
    np.testing.assert_array_equal(result[0], np.array([125, 126, 124, 127, 123, 128]))
    assert result[1] == True


def test_find_closest_index_basic(short_2d_points_array_very_far):
    interpolated_array, distances = course.transform_path(short_2d_points_array_very_far, 5, 25)
    coordinates = [39.22220, -76.71303]
    assert course.find_closest_index(4, coordinates, distances, interpolated_array) == 879


def test_find_closest_index_figure_8(figure_8_course):
    interpolated_array, distances = course.transform_path(figure_8_course, 5, 25)
    coordinates = [39.23561, -76.73431]
    assert course.find_closest_index(1.7, coordinates, distances, interpolated_array) == 353


def test_align_known_mile_marks(figure_8_course):
    interpolated_array, distances = course.transform_path(figure_8_course, 10, 75)
    known_mile_marks = [
        {"coordinates": [39.23204, -76.73340], "mile_mark": 0, "name": "Start"},
        {"coordinates": [39.23559, -76.73442], "mile_mark": 0.34, "name": "AS1"},
        {"coordinates": [39.23960, -76.73503], "mile_mark": 0.67, "name": "AS2"},
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
            0.02125,
            0.0425,
            0.06375,
            0.085,
            0.10625000000000001,
            0.1275,
            0.14875000000000002,
            0.17,
            0.19125,
            0.21250000000000002,
            0.23375,
            0.255,
            0.27625,
            0.29750000000000004,
            0.31875000000000003,
            0.34,
            0.35650000000000004,
            0.373,
            0.3895,
            0.406,
            0.42250000000000004,
            0.43900000000000006,
            0.4555,
            0.47200000000000003,
            0.48850000000000005,
            0.505,
            0.5215000000000001,
            0.538,
            0.5545,
            0.5710000000000001,
            0.5875,
            0.6040000000000001,
            0.6205,
            0.637,
            0.6535,
            0.67,
            0.6868354430379747,
            0.7036708860759494,
            0.7205063291139241,
            0.7373417721518988,
            0.7541772151898735,
            0.7710126582278481,
            0.7878481012658228,
            0.8046835443037975,
            0.8215189873417722,
            0.8383544303797469,
            0.8551898734177216,
            0.8720253164556963,
            0.8888607594936709,
            0.9056962025316456,
            0.9225316455696203,
            0.939367088607595,
            0.9562025316455697,
            0.9730379746835444,
            0.989873417721519,
            1.0067088607594936,
            1.0235443037974683,
            1.040379746835443,
            1.0572151898734177,
            1.0740506329113924,
            1.090886075949367,
            1.1077215189873417,
            1.1245569620253164,
            1.141392405063291,
            1.1582278481012658,
            1.1750632911392405,
            1.1918987341772151,
            1.2087341772151898,
            1.2255696202531645,
            1.2424050632911392,
            1.2592405063291139,
            1.2760759493670886,
            1.2929113924050633,
            1.309746835443038,
            1.3265822784810126,
            1.3434177215189873,
            1.360253164556962,
            1.3770886075949367,
            1.3939240506329114,
            1.410759493670886,
            1.4275949367088607,
            1.4444303797468354,
            1.46126582278481,
            1.4781012658227848,
            1.4949367088607595,
            1.5117721518987342,
            1.5286075949367088,
            1.5454430379746835,
            1.5622784810126582,
            1.5791139240506329,
            1.5959493670886076,
            1.6127848101265823,
            1.629620253164557,
            1.6464556962025316,
            1.6632911392405063,
            1.680126582278481,
            1.6969620253164557,
            1.7137974683544304,
            1.730632911392405,
            1.7474683544303797,
            1.7643037974683544,
            1.781139240506329,
            1.7979746835443038,
            1.8148101265822785,
            1.8316455696202532,
            1.8484810126582278,
            1.8653164556962025,
            1.8821518987341772,
            1.898987341772152,
            1.9158227848101266,
            1.9326582278481013,
            1.949493670886076,
            1.9663291139240506,
            1.9831645569620253,
            2.0,
            2.0131147540983605,
            2.0262295081967214,
            2.039344262295082,
            2.0524590163934424,
            2.0655737704918034,
            2.078688524590164,
            2.0918032786885243,
            2.1049180327868853,
            2.1180327868852458,
            2.1311475409836067,
            2.144262295081967,
            2.1573770491803277,
            2.1704918032786886,
            2.183606557377049,
            2.1967213114754096,
            2.2098360655737705,
            2.222950819672131,
            2.2360655737704915,
            2.2491803278688525,
            2.262295081967213,
            2.275409836065574,
            2.2885245901639344,
            2.301639344262295,
            2.314754098360656,
            2.3278688524590163,
            2.340983606557377,
            2.3540983606557377,
            2.3672131147540982,
            2.3803278688524587,
            2.3934426229508197,
            2.40655737704918,
            2.419672131147541,
            2.4327868852459016,
            2.445901639344262,
            2.459016393442623,
            2.4721311475409835,
            2.485245901639344,
            2.498360655737705,
            2.5114754098360654,
            2.524590163934426,
            2.537704918032787,
            2.5508196721311474,
            2.5639344262295083,
            2.577049180327869,
            2.5901639344262293,
            2.6032786885245898,
            2.6163934426229507,
            2.629508196721311,
            2.642622950819672,
            2.6557377049180326,
            2.668852459016393,
            2.681967213114754,
            2.6950819672131145,
            2.7081967213114755,
            2.721311475409836,
            2.7344262295081965,
            2.747540983606557,
            2.760655737704918,
            2.7737704918032784,
            2.7868852459016393,
            2.8,
            2.8166666666666664,
            2.833333333333333,
            2.8499999999999996,
            2.8666666666666667,
            2.8833333333333333,
            2.9,
            2.9166666666666665,
            2.933333333333333,
            2.9499999999999997,
            2.9666666666666663,
            2.9833333333333334,
            3.0,
            3.0166666666666666,
            3.033333333333333,
            3.05,
            3.0666666666666664,
            3.083333333333333,
            3.0999999999999996,
            3.1166666666666667,
            3.1333333333333333,
            3.15,
            3.1666666666666665,
            3.183333333333333,
            3.1999999999999997,
            3.216666666666667,
            3.2333333333333334,
            3.25,
            3.2666666666666666,
            3.283333333333333,
            3.3,
            3.3166666666666664,
            3.333333333333333,
            3.35,
            3.3666666666666667,
            3.3833333333333333,
            3.4,
            3.4,
        ]
    )
    np.testing.assert_array_equal(modified_distances, expected_modified_distances)
