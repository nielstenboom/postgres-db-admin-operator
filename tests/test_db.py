import pytest
import psycopg.errors

from postgres_db_admin_operator.db import create_database, database_exists, drop_database, DatabaseNameTooLong


async def test_create_database(conn):
    await create_database(conn, "test-create-db")
    assert await database_exists(conn, "test-create-db")
    await drop_database(conn, "test-create-db")


async def test_drop_database(conn):
    await create_database(conn, "test-drop-db")
    await drop_database(conn, "test-drop-db")
    assert not await database_exists(conn, "test-drop-db")


async def test_drop_database_idempotent(conn):
    # dropping a non-existent database should not raise
    await drop_database(conn, "test-nonexistent-db")


async def test_create_database_with_hyphens(conn):
    await create_database(conn, "my-app-db")
    assert await database_exists(conn, "my-app-db")
    await drop_database(conn, "my-app-db")


async def test_database_exists_false(conn):
    assert not await database_exists(conn, "definitely-does-not-exist-xyz")


async def test_create_database_name_too_long(conn):
    long_name = "a" * 70
    with pytest.raises(DatabaseNameTooLong):
        await create_database(conn, long_name)


async def test_create_database_collision(conn):
    await create_database(conn, "test-collision-db")
    try:
        with pytest.raises(psycopg.errors.DuplicateDatabase):
            await create_database(conn, "test-collision-db")
    finally:
        await drop_database(conn, "test-collision-db")
