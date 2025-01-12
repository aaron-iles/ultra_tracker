#!/usr/bin/env python3


from ultra_tracker.models import course
import numpy as np
import pytest


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
