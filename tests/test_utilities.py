#!/usr/bin/env python3


from ultra_tracker import utils


def test_format_duration():
    duration = utils.datetime.timedelta(seconds=0)
    assert utils.format_duration(duration) == "0:00'00\""
    duration = utils.datetime.timedelta(seconds=10)
    assert utils.format_duration(duration) == "0:00'10\""
    duration = utils.datetime.timedelta(seconds=10, minutes=9)
    assert utils.format_duration(duration) == "0:09'10\""
    duration = utils.datetime.timedelta(seconds=10, minutes=9, hours=8)
    assert utils.format_duration(duration) == "8:09'10\""
    duration = utils.datetime.timedelta(seconds=10, minutes=9, hours=8, days=2)
    assert utils.format_duration(duration) == "56:09'10\""


def test_format_distance():
    assert utils.format_distance(0) == "0.0 ft"
    assert utils.format_distance(0, force_ft=True) == "0.0 ft"
    assert utils.format_distance(1234.567) == "1234.6 ft"
    assert utils.format_distance(5280) == "1.0 mi"
    assert utils.format_distance(6000) == "1.1 mi"
    assert utils.format_distance(6000, force_ft=True) == "6000.0 ft"


def test_convert_decimal_pace_to_pretty_format():
    assert utils.convert_decimal_pace_to_pretty_format(10.0) == "10'00\""
    assert utils.convert_decimal_pace_to_pretty_format(63) == "63'00\""
    assert utils.convert_decimal_pace_to_pretty_format(7.63) == "7'37\""


def test_kph_to_min_per_mi():
    assert utils.kph_to_min_per_mi(0) == 0.0
    assert utils.kph_to_min_per_mi(1) == 96.5604
    assert utils.kph_to_min_per_mi(10) == 9.656039999999999
    assert utils.kph_to_min_per_mi(13.65) == 7.074021978021977


def test_get_timezone():
    assert utils.get_timezone([-54.94069, -67.62175]) == utils.pytz.timezone("America/Punta_Arenas")
    assert utils.get_timezone([40.72559, -74.01534]) == utils.pytz.timezone("America/New_York")
    assert utils.get_timezone([51.46344, 0.04811]) == utils.pytz.timezone("Europe/London")
    assert utils.get_timezone([-23.58080, 133.89616]) == utils.pytz.timezone("Australia/Darwin")


def test_get_gmaps_url():
    assert (
        utils.get_gmaps_url([-23.58080, 133.89616])
        == "https://www.google.com/maps/search/?api=1&query=-23.5808,133.89616"
    )


def test_meters_to_feet():
    assert utils.meters_to_feet(1) == 3.280839895


def test_feet_to_meters():
    assert utils.feet_to_meters(1) == 1 / 3.280839895


def test_haversine_distance():
    assert (
        utils.haversine_distance([39.34239, -77.72800], [39.33950, -77.70603]) == 6287.673243369766
    )
    assert (
        utils.haversine_distance([39.23690, -79.48623], [38.89637, -77.02599]) == 707814.8813412233
    )


def test_detect_consecutive_sequences():
    assert utils.detect_consecutive_sequences([]) == [[]]
    assert utils.detect_consecutive_sequences([1]) == [[1]]
    assert utils.detect_consecutive_sequences([1, 2, 3]) == [[1, 2, 3]]
    assert utils.detect_consecutive_sequences([1, 3, 5]) == [[1], [3], [5]]
    assert utils.detect_consecutive_sequences([1, 3, 2, 5, 4, 6]) == [[1, 2, 3, 4, 5, 6]]
    assert utils.detect_consecutive_sequences([1, 2, 5, 4, 9]) == [[1, 2], [4, 5], [9]]
