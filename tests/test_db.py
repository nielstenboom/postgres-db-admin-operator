import pytest
import psycopg.errors

from postgres_db_admin_operator.db import create_database, database_exists, drop_database, DatabaseNameTooLong


def test_create_database(conn):
    create_database(conn, "test-create-db")
    assert database_exists(conn, "test-create-db")
    drop_database(conn, "test-create-db")


def test_drop_database(conn):
    create_database(conn, "test-drop-db")
    drop_database(conn, "test-drop-db")
    assert not database_exists(conn, "test-drop-db")


def test_drop_database_idempotent(conn):
    # dropping a non-existent database should not raise
    drop_database(conn, "test-nonexistent-db")


def test_create_database_with_hyphens(conn):
    create_database(conn, "my-app-db")
    assert database_exists(conn, "my-app-db")
    drop_database(conn, "my-app-db")


def test_database_exists_false(conn):
    assert not database_exists(conn, "definitely-does-not-exist-xyz")


def test_create_database_name_too_long(conn):
    long_name = "a" * 70
    with pytest.raises(DatabaseNameTooLong):
        create_database(conn, long_name)


def test_create_database_collision(conn):
    create_database(conn, "test-collision-db")
    try:
        with pytest.raises(psycopg.errors.DuplicateDatabase):
            create_database(conn, "test-collision-db")
    finally:
        drop_database(conn, "test-collision-db")
