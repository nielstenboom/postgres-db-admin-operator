import psycopg


async def test_connection(conn: psycopg.AsyncConnection) -> None:
    await conn.execute("SELECT 1")


async def create_database(conn: psycopg.AsyncConnection, name: str) -> None:
    await conn.execute(f'CREATE DATABASE "{name}"')


async def drop_database(conn: psycopg.AsyncConnection, name: str) -> None:
    # force-disconnect existing sessions so the drop doesn't hang
    await conn.execute(
        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{name}'"
    )
    await conn.execute(f'DROP DATABASE IF EXISTS "{name}"')
