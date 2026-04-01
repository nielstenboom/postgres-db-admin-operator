import pytest
import psycopg
import psycopg.errors

from postgres_db_admin_operator.db import (
    create_admin_role,
    setup_admin_role_privileges,
    create_readonly_role,
    setup_readonly_role_privileges,
    drop_role,
)

POSTGRES_PORT = 5433
POSTGRES_PASSWORD = "testpassword"
ROLE_PASSWORD = "roletestpassword"


def connect_as(role: str, dbname: str) -> psycopg.Connection:
    return psycopg.connect(
        host="localhost",
        port=POSTGRES_PORT,
        user=role,
        password=ROLE_PASSWORD,
        dbname=dbname,
        autocommit=True,
    )


def role_exists(conn: psycopg.Connection, name: str) -> bool:
    result = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (name,))
    return result.fetchone() is not None


def test_create_admin_role(conn, role_db):
    db = role_db.info.dbname
    create_admin_role(conn, db, ROLE_PASSWORD)
    assert role_exists(conn, f"{db}_admin")


def test_admin_role_can_create_table_and_insert(conn, role_db):
    db = role_db.info.dbname
    create_admin_role(conn, db, ROLE_PASSWORD)
    setup_admin_role_privileges(role_db, db)

    with connect_as(f"{db}_admin", db) as admin_conn:
        admin_conn.execute("CREATE TABLE test_admin (id int)")
        admin_conn.execute("INSERT INTO test_admin VALUES (1)")
        result = admin_conn.execute("SELECT * FROM test_admin").fetchall()
        assert result == [(1,)]


def test_admin_role_default_privileges_apply_to_new_tables(conn, role_db):
    """Tables created after setup_admin_role_privileges should also be accessible."""
    db = role_db.info.dbname
    create_admin_role(conn, db, ROLE_PASSWORD)
    setup_admin_role_privileges(role_db, db)

    role_db.execute("CREATE TABLE test_new_table (id int)")
    role_db.execute("INSERT INTO test_new_table VALUES (42)")

    with connect_as(f"{db}_admin", db) as admin_conn:
        result = admin_conn.execute("SELECT * FROM test_new_table").fetchall()
        assert result == [(42,)]


def test_create_readonly_role(conn, role_db):
    db = role_db.info.dbname
    create_readonly_role(conn, db, ROLE_PASSWORD)
    assert role_exists(conn, f"{db}_readonly")


def test_readonly_role_can_select(conn, role_db):
    db = role_db.info.dbname
    create_readonly_role(conn, db, ROLE_PASSWORD)
    setup_readonly_role_privileges(role_db, db)

    role_db.execute("CREATE TABLE test_readonly (id int)")
    role_db.execute("INSERT INTO test_readonly VALUES (1)")

    with connect_as(f"{db}_readonly", db) as ro_conn:
        result = ro_conn.execute("SELECT * FROM test_readonly").fetchall()
        assert result == [(1,)]


def test_readonly_role_cannot_insert(conn, role_db):
    db = role_db.info.dbname
    create_readonly_role(conn, db, ROLE_PASSWORD)
    setup_readonly_role_privileges(role_db, db)

    role_db.execute("CREATE TABLE test_readonly_insert (id int)")

    with connect_as(f"{db}_readonly", db) as ro_conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            ro_conn.execute("INSERT INTO test_readonly_insert VALUES (1)")


def test_readonly_role_default_privileges_apply_to_new_tables(conn, role_db):
    """Tables created after setup_readonly_role_privileges should also be selectable."""
    db = role_db.info.dbname
    create_readonly_role(conn, db, ROLE_PASSWORD)
    setup_readonly_role_privileges(role_db, db)

    role_db.execute("CREATE TABLE test_later_table (id int)")
    role_db.execute("INSERT INTO test_later_table VALUES (99)")

    with connect_as(f"{db}_readonly", db) as ro_conn:
        result = ro_conn.execute("SELECT * FROM test_later_table").fetchall()
        assert result == [(99,)]


def test_drop_role(conn, role_db):
    db = role_db.info.dbname
    create_readonly_role(conn, db, ROLE_PASSWORD)
    role_db.execute(f'DROP OWNED BY "{db}_readonly"')
    drop_role(conn, f"{db}_readonly")
    assert not role_exists(conn, f"{db}_readonly")


def test_drop_role_idempotent(conn):
    drop_role(conn, "definitely-does-not-exist-role")
