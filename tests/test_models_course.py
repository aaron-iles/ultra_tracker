#!/usr/bin/env python3


from ultra_tracker.models import course
import numpy as np
import pytest


@pytest.fixture
def widely_spaced_2d_points_short():
    return np.array([[39.25694, -76.77481], [39.25633, -76.77265], [39.25491, -76.77048]])





def test_interpolate_and_filter_points_wide(widely_spaced_2d_points_short):
    interpolated_array = course.interpolate_and_filter_points(widely_spaced_2d_points_short, 5, 75)
    good_array = np.array(
        [
            [39.25694, -76.77481],
            [39.25683316, -76.77458211],
            [39.25672632, -76.77435421],
            [39.25661947, -76.77412632],
            [39.25651263, -76.77389842],
            [39.25640579, -76.77367053],
            [39.25629895, -76.77344263],
            [39.25619211, -76.77321474],
            [39.25608526, -76.77298684],
            [39.25597842, -76.77275895],
            [39.25587158, -76.77253105],
            [39.25576474, -76.77230316],
            [39.25565789, -76.77207526],
            [39.25555105, -76.77184737],
            [39.25544421, -76.77161947],
            [39.25533737, -76.77139158],
            [39.25523053, -76.77116368],
            [39.25512368, -76.77093579],
            [39.25501684, -76.77070789],
            [39.25491, -76.77048],
            [39.25491, -76.77048],
        ]
    )
    assert np.testing.assert_array_equal(interpolated_array, good_array)
