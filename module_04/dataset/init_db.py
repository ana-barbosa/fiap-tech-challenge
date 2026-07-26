"""Initialize the shared SQLite database from db/schema.sql.

Safe to re-run - schema.sql uses CREATE TABLE IF NOT EXISTS throughout, so this never
drops or overwrites existing data. Each service writes its own table(s); only the
aggregation service reads across tables, and no service imports another's code -
sqlite3 is the only cross-service dependency.

Runs as the first step of `make generate-dataset`, and is also called directly by
dataset/seed_patients.py and every service's run.py.
"""

import argparse
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = REPO_ROOT / "db" / "hospital.sqlite"
SCHEMA_PATH = REPO_ROOT / "db" / "schema.sql"


def init_db(db_path=DEFAULT_DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()
    return db_path


def get_connection(db_path=DEFAULT_DB_PATH):
    """Open a connection with foreign-key enforcement on (off by default in sqlite3)."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    path = init_db(args.db_path)
    print(f"initialized database at {path}")


if __name__ == "__main__":
    main()
