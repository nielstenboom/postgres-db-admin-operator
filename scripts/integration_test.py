"""
Integration test: applies a PostgresDatabase CR and verifies the database
and credentials secret were created correctly.

Requires:
  - A running kind cluster with the operator deployed (make deploy)
  - Postgres reachable via port-forward on localhost:5432
"""

import subprocess
import time
import sys
import psycopg

DB_NAME = "integration-test"
NAMESPACE = "default"
PG_HOST = "localhost"
PG_PORT = 5432
PG_USER = "postgres"
PG_PASSWORD = "devpassword"
TIMEOUT = 60


MANIFEST = f"""
apiVersion: postgresdbadminoperator.github.io/v1
kind: PostgresDatabase
metadata:
  name: {DB_NAME}
  namespace: {NAMESPACE}
spec:
  createReadOnlyUser: true
"""


def kubectl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["kubectl", *args], capture_output=True, text=True)


def apply_manifest() -> None:
    print(f"Applying PostgresDatabase '{DB_NAME}'...")
    result = subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=MANIFEST,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(1)
    print(result.stdout.strip())


def wait_for_ready() -> None:
    print(f"Waiting for '{DB_NAME}' to reach Ready phase (timeout: {TIMEOUT}s)...")
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        result = kubectl(
            "get", "postgresdatabase", DB_NAME,
            "-n", NAMESPACE,
            "-o", "jsonpath={.status.phase}",
        )
        phase = result.stdout.strip()
        if phase == "Ready":
            print(f"Phase: {phase}")
            return
        if phase in ("InvalidName", "Collision"):
            print(f"Operator reported a permanent error: {phase}")
            sys.exit(1)
        print(f"Phase: {phase or '(pending)'} — retrying...")
        time.sleep(3)
    print("Timed out waiting for Ready phase")
    sys.exit(1)


def check_database_exists() -> None:
    print(f"Checking database '{DB_NAME}' exists in Postgres...")
    with psycopg.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASSWORD, autocommit=True
    ) as conn:
        row = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,)
        ).fetchone()
        if not row:
            print(f"Database '{DB_NAME}' not found in Postgres")
            sys.exit(1)
    print(f"Database '{DB_NAME}' exists")


def check_secret_exists() -> None:
    print(f"Checking credentials secret '{DB_NAME}' exists in namespace '{NAMESPACE}'...")
    result = kubectl("get", "secret", DB_NAME, "-n", NAMESPACE)
    if result.returncode != 0:
        print(f"Secret '{DB_NAME}' not found: {result.stderr.strip()}")
        sys.exit(1)

    for key in ("admin-username", "admin-password", "admin-database-url", "readonly-username", "readonly-password"):
        result = kubectl(
            "get", "secret", DB_NAME,
            "-n", NAMESPACE,
            "-o", f"jsonpath={{.data.{key}}}",
        )
        if not result.stdout.strip():
            print(f"Secret key '{key}' is missing or empty")
            sys.exit(1)
    print(f"Secret '{DB_NAME}' exists with all expected keys")


def cleanup() -> None:
    print(f"Cleaning up PostgresDatabase '{DB_NAME}'...")
    kubectl("delete", "postgresdatabase", DB_NAME, "-n", NAMESPACE)


if __name__ == "__main__":
    try:
        apply_manifest()
        wait_for_ready()
        check_database_exists()
        check_secret_exists()
        print("\nAll checks passed.")
    finally:
        cleanup()
