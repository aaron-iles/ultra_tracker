#!/usr/bin/env python3

import pytest

from ultra_tracker.models import caltopo
from ultra_tracker.database_utils import Database
from testcontainers.postgres import PostgresContainer
import psycopg2


@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:15", username="test", password="test", dbname="testdb") as pg:
        yield pg


@pytest.fixture()
def database(postgres):
    db = Database(
        host=postgres.get_container_host_ip(),
        port=postgres.get_exposed_port(5432),
        dbname=postgres.dbname,
        user=postgres.username,
        password=postgres.password,
    )

    # clean schema per test
    db.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    db = Database(
        host=postgres.get_container_host_ip(),
        port=postgres.get_exposed_port(5432),
        dbname=postgres.dbname,
        user=postgres.username,
        password=postgres.password,
    )
    return db


def assert_lists_equal_with_percentage(list1, list2):
    if len(list1) != len(list2):
        pytest.fail(f"Lists have different lengths: {len(list1)} != {len(list2)}")
        return

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
