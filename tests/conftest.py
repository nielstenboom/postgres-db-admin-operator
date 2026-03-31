import pytest
import psycopg
from psycopg import sql

from postgres_db_admin_operator.db import create_database, drop_database


POSTGRES_PORT = 5433  # avoid clashing with any local postgres on 5432
POSTGRES_PASSWORD = "testpassword"


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    return str(pytestconfig.rootdir / "docker-compose.yml")


@pytest.fixture(scope="session")
def postgres_service(docker_services):
    docker_services.wait_until_responsive(
        timeout=30,
        pause=0.5,
        check=lambda: _is_postgres_ready(),
    )


def _is_postgres_ready() -> bool:
    try:
        psycopg.connect(
            host="localhost",
            port=POSTGRES_PORT,
            user="postgres",
            password=POSTGRES_PASSWORD,
            autocommit=True,
        ).close()
        return True
    except Exception:
        return False


@pytest.fixture
def conn(postgres_service):
    with psycopg.connect(
        host="localhost",
        port=POSTGRES_PORT,
        user="postgres",
        password=POSTGRES_PASSWORD,
        autocommit=True,
    ) as c:
        yield c


@pytest.fixture
def role_db(conn):
    """Creates a temporary database for role tests, yields a connection to it, drops it on teardown."""
    name = "test-roles-db"
    drop_database(conn, name)  # clean up from any previous failed run
    create_database(conn, name)
    with psycopg.connect(
        host="localhost",
        port=POSTGRES_PORT,
        user="postgres",
        password=POSTGRES_PASSWORD,
        dbname=name,
        autocommit=True,
    ) as db_conn:
        yield db_conn
        # DROP OWNED BY revokes all grants (including GRANT ON DATABASE) so DROP ROLE can succeed
        for role in [f"{name}_admin", f"{name}_readonly"]:
            if conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
                db_conn.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(role)))
                conn.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
    drop_database(conn, name)
