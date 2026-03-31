import psycopg
from psycopg import sql

PG_MAX_NAME_LENGTH = 63


class DatabaseNameTooLong(Exception):
    pass


def test_connection(conn: psycopg.Connection) -> None:
    conn.execute("SELECT 1")


def database_exists(conn: psycopg.Connection, name: str) -> bool:
    result = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
    return result.fetchone() is not None


def create_database(conn: psycopg.Connection, name: str) -> None:
    if len(name) > PG_MAX_NAME_LENGTH:
        raise DatabaseNameTooLong(f'Database name "{name}" exceeds PostgreSQL\'s 63-byte limit')
    conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


def drop_database(conn: psycopg.Connection, name: str) -> None:
    # force-disconnect existing sessions so the drop doesn't hang
    conn.execute(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
        (name,),
    )
    conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name)))


def create_admin_role(conn: psycopg.Connection, db_name: str, password: str) -> None:
    """Server-level: create login role and grant full database access."""
    name = f"{db_name}_admin"
    conn.execute(
        sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(
            sql.Identifier(name), sql.Literal(password)
        )
    )
    conn.execute(
        sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
            sql.Identifier(db_name), sql.Identifier(name)
        )
    )


def setup_admin_role_privileges(conn: psycopg.Connection, db_name: str) -> None:
    """Database-level: grant schema and table privileges. conn must be connected to db_name."""
    name = f"{db_name}_admin"
    conn.execute(sql.SQL("GRANT ALL ON SCHEMA public TO {}").format(sql.Identifier(name)))
    conn.execute(
        sql.SQL("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(name))
    )
    conn.execute(
        sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {}").format(sql.Identifier(name))
    )


def create_readonly_role(conn: psycopg.Connection, db_name: str, password: str) -> None:
    """Server-level: create login role and grant connect access."""
    name = f"{db_name}_readonly"
    conn.execute(
        sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(
            sql.Identifier(name), sql.Literal(password)
        )
    )
    conn.execute(
        sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
            sql.Identifier(db_name), sql.Identifier(name)
        )
    )


def setup_readonly_role_privileges(conn: psycopg.Connection, db_name: str) -> None:
    """Database-level: grant read-only privileges. conn must be connected to db_name."""
    name = f"{db_name}_readonly"
    conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(name)))
    conn.execute(
        sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(name))
    )
    conn.execute(
        sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {}").format(sql.Identifier(name))
    )


def drop_role(conn: psycopg.Connection, name: str) -> None:
    conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(name)))
