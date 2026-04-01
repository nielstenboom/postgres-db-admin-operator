import os
import secrets
import kopf
import psycopg
import logging
from pydantic import BaseModel

from postgres_db_admin_operator.db import (
    create_database,
    drop_database,
    test_connection,
    create_admin_role,
    setup_admin_role_privileges,
    create_readonly_role,
    setup_readonly_role_privileges,
    DatabaseNameTooLong,
)
from postgres_db_admin_operator.k8s import write_credentials_secret

logger = logging.getLogger(__name__)


class DatabaseSpec(BaseModel):
    createReadOnlyUser: bool = False


PG_HOST = os.environ["PG_HOST"]
PG_USER = os.environ["PG_USER"]
PG_PASSWORD = os.environ["PG_PASSWORD"]
PG_PORT = int(os.environ.get("PG_PORT", 5432))
CLEANUP_ON_DELETE = os.environ.get("CLEANUP_ON_DELETE", "false").lower() == "true"


def update_status(patch, phase: str, message: str | None = None) -> None:
    patch.status["phase"] = phase
    if message is not None:
        patch.status["message"] = message


def build_secret_data(
    name: str,
    admin_password: str,
    readonly_password: str | None,
) -> dict[str, str]:
    data: dict[str, str] = {
        "admin-username": f"{name}_admin",
        "admin-password": admin_password,
        "admin-database-url": f"postgresql://{name}_admin:{admin_password}@{PG_HOST}:{PG_PORT}/{name}",
        "host": PG_HOST,
        "port": str(PG_PORT),
        "dbname": name,
    }
    if readonly_password is not None:
        data["readonly-username"] = f"{name}_readonly"
        data["readonly-password"] = readonly_password
        data["readonly-database-url"] = f"postgresql://{name}_readonly:{readonly_password}@{PG_HOST}:{PG_PORT}/{name}"
    return data


def get_conn(dbname: str | None = None) -> psycopg.Connection:
    # autocommit required — CREATE/DROP DATABASE cannot run inside a transaction
    return psycopg.connect(
        host=PG_HOST, user=PG_USER, password=PG_PASSWORD, port=PG_PORT,
        dbname=dbname, autocommit=True,
    )



@kopf.on.create("postgresdatabases", errors=kopf.ErrorsMode.PERMANENT)
def create(name, spec, patch, **kwargs):
    db_spec = DatabaseSpec.model_validate(spec)
    logger.info(f"Creating database {name}")
    try:
        with get_conn() as conn:
            create_database(conn, name)
    except DatabaseNameTooLong as e:
        update_status(patch, phase="InvalidName", message=str(e))
        raise kopf.PermanentError(str(e))
    except psycopg.errors.DuplicateDatabase:
        msg = f'Database "{name}" already exists in PostgreSQL'
        update_status(patch, phase="Collision", message=msg)
        raise kopf.PermanentError(msg)

    logger.info(f"Creating admin role for database {name}")
    admin_password = secrets.token_urlsafe(32)
    with get_conn() as conn:
        create_admin_role(conn, name, admin_password)
    with get_conn(dbname=name) as db_conn:
        setup_admin_role_privileges(db_conn, name)
    logger.info(f"Admin role for database {name} created successfully")

    readonly_password = None
    if db_spec.createReadOnlyUser:
        logger.info(f"Creating readonly role for database {name}")
        readonly_password = secrets.token_urlsafe(32)
        with get_conn() as conn:
            create_readonly_role(conn, name, readonly_password)
        with get_conn(dbname=name) as db_conn:
            setup_readonly_role_privileges(db_conn, name)
        logger.info(f"Readonly role for database {name} created successfully")

    logger.info(f"Writing credentials secret for database {name}")
    write_credentials_secret(kwargs["namespace"], name, build_secret_data(name, admin_password, readonly_password))

    logger.info(f"Database {name} created successfully")
    update_status(patch, phase="Ready")


@kopf.on.delete("postgresdatabases", errors=kopf.ErrorsMode.PERMANENT)
def delete(name, spec, **kwargs):
    if not CLEANUP_ON_DELETE:
        logger.info(f"Orphaning database {name} — database will NOT be dropped since CLEANUP_ON_DELETE=false")
        return

    logger.info(f"Deleting database {name} (CLEANUP_ON_DELETE=true)")
    with get_conn() as conn:
        drop_database(conn, name)
    logger.info(f"Database {name} deleted successfully")


@kopf.on.startup()
def startup(logger, **kwargs):
    with get_conn() as conn:
        test_connection(conn)
    logger.info("Postgres connection OK")


def main():
    kopf.run(clusterwide=True)
