import argparse
import sqlite3
import sys


def init_db(db_path: str, schema_path: str = "schema.sql") -> None:
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
    except FileNotFoundError:
        print(f"Schema file not found: {schema_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executescript(schema_sql)
    finally:
        conn.close()

    print(f"Initialized database at {db_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the job database schema")
    parser.add_argument("--db", default="jobs.db", help="Path to the SQLite database file (default: jobs.db)")
    parser.add_argument("--schema", default="schema.sql", help="Path to the SQL schema file (default: schema.sql)")
    args = parser.parse_args()

    init_db(args.db, args.schema)