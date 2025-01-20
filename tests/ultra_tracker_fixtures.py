#!/usr/bin/env python3

import pytest

from ultra_tracker.models import caltopo


def assert_lists_equal_with_percentage(list1, list2):
    if len(list1) != len(list2):
        pytest.fail(f"Lists have different lengths: {len(list1)} != {len(list2)}")

    unequal_indices = []
    for i, (el1, el2) in enumerate(zip(list1, list2)):
        if el1 != el2:
            unequal_indices.append(i)

    unequal_count = len(unequal_indices)
    total_count = len(list1)

    if unequal_count > 0:
        percentage_not_equal = (unequal_count / total_count) * 100
        unequal_values = [f"index {i}: {list1[i]} != {list2[i]}" for i in unequal_indices]

        pytest.fail(
            f"Lists differ by {percentage_not_equal:.2f}% "
            f"({unequal_count} unequal elements out of {total_count}). "
            f"Unequal values:\n{'\n'.join(unequal_values)}"
        )


@pytest.fixture
def caltopo_session():
    return caltopo.CaltopoSession("testcredid", "dGVzdGtleQ==")
