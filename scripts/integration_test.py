"""
Integration test: applies a PostgresDatabase CR and verifies the database
and credentials secret were created correctly.

Requires:
  - A running kind cluster with the operator deployed (make deploy)
  - Postgres reachable via port-forward on localhost:5432
"""

import time
import psycopg
from kubernetes import client, config
from kubernetes.client.rest import ApiException

DB_NAME = "integration-test"
SECRET_NAME = f"{DB_NAME}-credentials"
NAMESPACE = "default"
PG_HOST = "localhost"
PG_PORT = 5432
PG_USER = "postgres"
PG_PASSWORD = "devpassword"
TIMEOUT = 60
GROUP = "postgresdbadminoperator.github.io"
VERSION = "v1"
PLURAL = "postgresdatabases"


def get_clients() -> tuple[client.CustomObjectsApi, client.CoreV1Api]:
    config.load_kube_config()
    return client.CustomObjectsApi(), client.CoreV1Api()


def apply_manifest(custom: client.CustomObjectsApi) -> None:
    print(f"Applying PostgresDatabase '{DB_NAME}'...")
    manifest = {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": "PostgresDatabase",
        "metadata": {"name": DB_NAME, "namespace": NAMESPACE},
        "spec": {"createReadOnlyUser": True},
    }
    try:
        custom.create_namespaced_custom_object(GROUP, VERSION, NAMESPACE, PLURAL, manifest)
    except ApiException as e:
        if e.status == 409:
            print("Resource already exists, continuing...")
        else:
            raise
    print(f"PostgresDatabase '{DB_NAME}' created")


def wait_for_ready(custom: client.CustomObjectsApi) -> None:
    print(f"Waiting for '{DB_NAME}' to reach Ready phase (timeout: {TIMEOUT}s)...")
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        obj = custom.get_namespaced_custom_object(GROUP, VERSION, NAMESPACE, PLURAL, DB_NAME)
        phase = obj.get("status", {}).get("phase", "")
        if phase == "Ready":
            print(f"Phase: {phase}")
            return
        if phase in ("InvalidName", "Collision"):
            raise RuntimeError(f"Operator reported a permanent error: {phase}")
        print(f"Phase: {phase or '(pending)'} — retrying...")
        time.sleep(3)
    raise TimeoutError(f"Timed out after {TIMEOUT}s waiting for Ready phase")


def check_database_exists() -> None:
    print(f"Checking database '{DB_NAME}' exists in Postgres...")
    with psycopg.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASSWORD, autocommit=True
    ) as conn:
        row = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,)
        ).fetchone()
        if not row:
            raise AssertionError(f"Database '{DB_NAME}' not found in Postgres")
    print(f"Database '{DB_NAME}' exists")


def check_secret_exists(core: client.CoreV1Api) -> None:
    print(f"Checking credentials secret '{SECRET_NAME}' exists in namespace '{NAMESPACE}'...")
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        try:
            secret = core.read_namespaced_secret(SECRET_NAME, NAMESPACE)
            break
        except ApiException as e:
            if e.status == 404:
                print("Secret not found yet — retrying...")
                time.sleep(3)
            else:
                raise
    else:
        raise TimeoutError(f"Timed out waiting for secret '{SECRET_NAME}' to appear")

    expected_keys = ("admin-username", "admin-password", "admin-database-url", "readonly-username", "readonly-password")
    for key in expected_keys:
        if not secret.data or not secret.data.get(key):
            raise AssertionError(f"Secret key '{key}' is missing or empty")
    print(f"Secret '{SECRET_NAME}' exists with all expected keys")


if __name__ == "__main__":
    custom, core = get_clients()
    apply_manifest(custom)
    wait_for_ready(custom)
    check_database_exists()
    check_secret_exists(core)
    print("\nAll checks passed.")

