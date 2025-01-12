#!/usr/bin/env python3


from ultra_tracker.models import race





def test_calculate_most_probable_mile_mark_single():
    assert race.calculate_most_probable_mile_mark([1.3], 10.21, 8.06) == 1.3


def test_calculate_most_probable_mile_mark_large_spread():
    assert race.calculate_most_probable_mile_mark([1.1, 5.1, 10.1, 19.1], 30, 7) == 5.1


def test_calculate_most_probable_mile_mark_long_list():
    assert race.calculate_most_probable_mile_mark(range(1,1000), 60, 12.56) == 5
