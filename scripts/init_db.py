"""
scripts/init_db.py — run once to create the users and scan_logs tables
in your MySQL database, using the models defined in app/db/models.py.

Usage:
    python scripts/init_db.py

Make sure .env is filled in and the target MySQL database (DB_NAME) already
exists (this script creates TABLES, not the database itself).
"""

import sys
import os
import traceback

# Allow running this script directly from the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Step 1/4: Importing dependencies (this can take 10-20s the first time "
      "because it also imports Streamlit)...", flush=True)

try:
    from app.db.database import get_engine, Base, DB_HOST, DB_PORT, DB_NAME, DB_USER
    from app.db import models  # noqa: F401 -- import so models register with Base
except Exception:
    print("FAILED during import. Full error below:", flush=True)
    traceback.print_exc()
    sys.exit(1)

print("Step 2/4: Imports OK.", flush=True)
print(f"Step 3/4: Will connect to host={DB_HOST} port={DB_PORT} db={DB_NAME} user={DB_USER}", flush=True)


def main():
    try:
        engine = get_engine()
        print("Step 4/4: Connecting and creating tables (if they don't already exist)...", flush=True)
        Base.metadata.create_all(engine)
        print("SUCCESS. Tables ready: users, scan_logs", flush=True)
    except Exception:
        print("FAILED while connecting/creating tables. Full error below:", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()