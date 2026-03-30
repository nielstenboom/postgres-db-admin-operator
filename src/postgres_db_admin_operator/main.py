import os
import json
import kopf
import psycopg
import logging

from postgres_db_admin_operator.db import create_database, database_exists, drop_database, test_connection, DatabaseNameTooLong

logger = logging.getLogger(__name__)


def update_status(patch, phase: str, message: str | None = None) -> None:
    patch.status["phase"] = phase
    if message is not None:
        patch.status["message"] = message

PG_CONN = dict(
    host=os.environ["PG_HOST"],
    user=os.environ["PG_USER"],
    password=os.environ["PG_PASSWORD"],
    port=int(os.environ.get("PG_PORT", 5432)),
)

CLEANUP_ON_DELETE = os.environ.get("CLEANUP_ON_DELETE", "false").lower() == "true"


async def get_conn():
    # autocommit required — CREATE/DROP DATABASE cannot run inside a transaction
    return await psycopg.AsyncConnection.connect(**PG_CONN, autocommit=True)


@kopf.on.create("postgresdatabases")
async def create(name, spec, patch, annotations, **kwargs):
    logger.info(f"Creating database {name}")
    try:
        async with await get_conn() as conn:
            await create_database(conn, name)
    except DatabaseNameTooLong as e:
        update_status(patch, phase="InvalidName", message=str(e))
        raise kopf.PermanentError(str(e))
    except psycopg.errors.DuplicateDatabase:
        msg = f'Database "{name}" already exists in PostgreSQL'
        update_status(patch, phase="Collision", message=msg)
        raise kopf.PermanentError(msg)

    logger.info(f"Database {name} created successfully")
    update_status(patch, phase="Ready")


@kopf.on.delete("postgresdatabases")
async def delete(name, spec, **kwargs):
    if CLEANUP_ON_DELETE:
        logger.info(f"Deleting database {name} (CLEANUP_ON_DELETE=true)")
        async with await get_conn() as conn:
            await drop_database(conn, name)
        logger.info(f"Database {name} deleted successfully")
    else:
        logger.info(f"Orphaning database {name} — database will NOT be dropped since CLEANUP_ON_DELETE=false")


@kopf.on.startup()
async def startup(logger, **kwargs):
    async with await get_conn() as conn:
        await test_connection(conn)
    logger.info("Postgres connection OK")

def main():
    kopf.run(clusterwide=True)
