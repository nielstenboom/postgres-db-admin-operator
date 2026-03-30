import os
import kopf
import psycopg
import logging

from postgres_db_admin_operator.db import create_database, drop_database, test_connection

logger = logging.getLogger(__name__)

PG_CONN = dict(
    host=os.environ["PG_HOST"],
    user=os.environ["PG_USER"],
    password=os.environ["PG_PASSWORD"],
    port=int(os.environ.get("PG_PORT", 5432)),
)


async def get_conn():
    # autocommit required — CREATE/DROP DATABASE cannot run inside a transaction
    return await psycopg.AsyncConnection.connect(**PG_CONN, autocommit=True)


@kopf.on.create("postgresdatabases")
async def create(name, spec, **kwargs):
    logger.info(f"Creating database {name}")
    async with await get_conn() as conn:
        await create_database(conn, name)
    logger.info(f"Database {name} created successfully")


@kopf.on.delete("postgresdatabases")
async def delete(name, spec, **kwargs):
    logger.info(f"Deleting database {name}")
    async with await get_conn() as conn:
        await drop_database(conn, name)
    logger.info(f"Database {name} deleted successfully")


@kopf.on.startup()
async def startup(logger, **kwargs):
    async with await get_conn() as conn:
        await test_connection(conn)
    logger.info("Postgres connection OK")

def main():
    kopf.run(clusterwide=True)
