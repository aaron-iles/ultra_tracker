#!/usr/bin/env python3


from ultra_tracker.models import race


def test_calculate_most_probable_mile_mark_single():
    assert race.calculate_most_probable_mile_mark([1.3], 10.21, 8.06) == 1.3


def test_calculate_most_probable_mile_mark_large_spread():
    assert race.calculate_most_probable_mile_mark([1.1, 5.1, 10.1, 19.1], 30, 7) == 5.1


def test_calculate_most_probable_mile_mark_long_list():
    assert race.calculate_most_probable_mile_mark(range(1, 1000), 60, 12.56) == 5


def test_sanity_check_mile_mark_no_movement_short_time():
    last_mile_mark = 1
    last_check_in_time = datetime.datetime(2025, 12, 27, 14, 30, 0)
    new_check_in_time = datetime.datetime(2025, 12, 27, 14, 50, 0)
    new_mile_mark = 1.04
    assert race.sanity_check_mile_mark(
        last_mile_mark,
        last_check_in_time,
        new_check_in_time,
        new_mile_mark,
    )


def test_sanity_check_mile_mark_no_movement_long_time():
    last_mile_mark = 19.3
    last_check_in_time = datetime.datetime(2025, 12, 27, 14, 30, 0)
    new_check_in_time = datetime.datetime(2025, 12, 27, 15, 50, 0)
    new_mile_mark = 19.26
    assert race.sanity_check_mile_mark(
        last_mile_mark,
        last_check_in_time,
        new_check_in_time,
        new_mile_mark,
    )


def test_sanity_check_mile_mark_backward_movement():
    last_mile_mark = 19.3
    last_check_in_time = datetime.datetime(2025, 12, 27, 14, 30, 0)
    new_check_in_time = datetime.datetime(2025, 12, 27, 15, 50, 0)
    new_mile_mark = 18.6
    assert not race.sanity_check_mile_mark(
        last_mile_mark,
        last_check_in_time,
        new_check_in_time,
        new_mile_mark,
    )


def test_sanity_check_mile_mark_sub4_pace():
    last_mile_mark = 19.3
    last_check_in_time = datetime.datetime(2025, 12, 27, 14, 30, 0)
    new_check_in_time = datetime.datetime(2025, 12, 27, 14, 35, 0)
    new_mile_mark = 20.57
    assert not race.sanity_check_mile_mark(
        last_mile_mark,
        last_check_in_time,
        new_check_in_time,
        new_mile_mark,
    )


def test_sanity_check_mile_mark_reasonable_pace():
    last_mile_mark = 19.3
    last_check_in_time = datetime.datetime(2025, 12, 27, 14, 30, 0)
    new_check_in_time = datetime.datetime(2025, 12, 27, 14, 35, 0)
    new_mile_mark = 19.8
    assert race.sanity_check_mile_mark(
        last_mile_mark,
        last_check_in_time,
        new_check_in_time,
        new_mile_mark,
    )
