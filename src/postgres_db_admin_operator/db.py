import psycopg

PG_MAX_NAME_LENGTH = 63


class DatabaseNameTooLong(Exception):
    pass


async def test_connection(conn: psycopg.AsyncConnection) -> None:
    await conn.execute("SELECT 1")


async def database_exists(conn: psycopg.AsyncConnection, name: str) -> bool:
    result = await conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
    return await result.fetchone() is not None


async def create_database(conn: psycopg.AsyncConnection, name: str) -> None:
    if len(name) > PG_MAX_NAME_LENGTH:
        raise DatabaseNameTooLong(f'Database name "{name}" exceeds PostgreSQL\'s 63-byte limit')
    await conn.execute(f'CREATE DATABASE "{name}"')


async def drop_database(conn: psycopg.AsyncConnection, name: str) -> None:
    # force-disconnect existing sessions so the drop doesn't hang
    await conn.execute(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
        (name,),
    )
    await conn.execute(f'DROP DATABASE IF EXISTS "{name}"')
