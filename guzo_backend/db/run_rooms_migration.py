# guzo_backend/db/run_rooms_migration.py
#
# Run the rooms table migration using the existing DB connection helper.

from pathlib import Path

from guzo_backend.dependencies import get_db_connection


def run_sql_file(path: str) -> None:
    sql_path = Path(path)
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    sql = sql_path.read_text(encoding="utf-8")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()

    print(f"✅ Applied SQL file: {sql_path}")


if __name__ == "__main__":
    run_sql_file("guzo_backend/db/sql/2025_11_24_add_rooms_table.sql")
