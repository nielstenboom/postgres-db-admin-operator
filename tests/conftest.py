import pytest
import psycopg


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
async def conn(postgres_service):
    async with await psycopg.AsyncConnection.connect(
        host="localhost",
        port=POSTGRES_PORT,
        user="postgres",
        password=POSTGRES_PASSWORD,
        autocommit=True,
    ) as c:
        yield c
