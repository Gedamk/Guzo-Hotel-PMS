from __future__ import annotations

import os
import argparse
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from sqlalchemy.engine import URL


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_DB_NAME = os.getenv("GUZO_TEST_DB_NAME", "guzo_pms_test_candidate")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _env(name: str, fallback: str | None = None) -> str | None:
    return os.getenv(name) or (os.getenv(fallback) if fallback else None)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a safe local PostgreSQL test database for Guzo PMS.")
    parser.add_argument(
        "--database",
        default=DEFAULT_TEST_DB_NAME,
        help="Local test database name to create. Must contain 'test'.",
    )
    return parser.parse_args()


def _require_local_database(host: str | None, current_db: str | None, test_db_name: str) -> None:
    if host not in LOCAL_HOSTS:
        raise SystemExit(
            "Refusing to create a test database because GUZO_DB_HOST/POSTGRES_HOST "
            f"is not local: {host!r}."
        )
    if current_db and any(token in current_db.lower() for token in ("prod", "pilot", "live")):
        raise SystemExit(
            "Refusing to use production-like database settings for test setup: "
            f"{current_db!r}."
        )
    if "test" not in test_db_name.lower():
        raise SystemExit("GUZO_TEST_DB_NAME must contain 'test'.")


def main() -> None:
    args = _parse_args()
    test_db_name = str(args.database or "").strip()
    load_dotenv(ROOT / ".env", override=False)

    host = _env("GUZO_DB_HOST", "POSTGRES_HOST") or "localhost"
    port = _env("GUZO_DB_PORT", "POSTGRES_PORT") or "5432"
    user = _env("GUZO_DB_USER", "POSTGRES_USER") or "postgres"
    password = _env("GUZO_DB_PASSWORD", "POSTGRES_PASSWORD")
    current_db = _env("GUZO_DB_NAME", "POSTGRES_DB") or "postgres"

    _require_local_database(host, current_db, test_db_name)

    maintenance_db = "postgres"
    conn = psycopg2.connect(
        dbname=maintenance_db,
        user=user,
        password=password,
        host=host,
        port=port,
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (test_db_name,))
            if cursor.fetchone() is None:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_db_name)))
                print(f"Created PostgreSQL test database: {test_db_name}")
            else:
                print(f"PostgreSQL test database already exists: {test_db_name}")
    finally:
        conn.close()

    test_url = URL.create(
        "postgresql+psycopg2",
        username=user,
        password=password,
        host=host,
        port=int(port),
        database=test_db_name,
    )
    env_path = ROOT / ".env.test.local"
    env_path.write_text(
        "\n".join(
            [
                "# Local-only test database settings. Do not commit this file.",
                f"TEST_DATABASE_URL={test_url.render_as_string(hide_password=False)}",
                f"GUZO_DB_HOST={host}",
                f"GUZO_DB_PORT={port}",
                f"GUZO_DB_NAME={test_db_name}",
                f"GUZO_DB_USER={user}",
                f"GUZO_DB_PASSWORD={password or ''}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote ignored local test env file: {env_path.name}")
    print("PowerShell:")
    print(f"  $env:TEST_DATABASE_URL=(Get-Content {env_path.name} | Select-String '^TEST_DATABASE_URL=').ToString().Split('=',2)[1]")


if __name__ == "__main__":
    main()
