from postgres_db_admin_operator.db import create_database, drop_database

async def _db_exists(conn, name: str) -> bool:
    result = await conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
    return await result.fetchone() is not None


async def test_create_database(conn):
    await create_database(conn, "test-create-db")
    assert await _db_exists(conn, "test-create-db")
    await drop_database(conn, "test-create-db")


async def test_drop_database(conn):
    await create_database(conn, "test-drop-db")
    await drop_database(conn, "test-drop-db")
    assert not await _db_exists(conn, "test-drop-db")


async def test_drop_database_idempotent(conn):
    # dropping a non-existent database should not raise
    await drop_database(conn, "test-nonexistent-db")


async def test_create_database_with_hyphens(conn):
    await create_database(conn, "my-app-db")
    assert await _db_exists(conn, "my-app-db")
    await drop_database(conn, "my-app-db")
