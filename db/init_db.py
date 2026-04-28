"""
Job Search Pipeline — Database initialization
Applies any pending migrations from migrations/ to pipeline.db.
Safe to run repeatedly: already-applied migrations are skipped.

Idiom preserved from v0.1.0: `python3 db/init_db.py` is the bootstrap command.
"""

import os
import sqlite3
import sys

# When run as `python3 db/init_db.py`, Python prepends db/ to sys.path,
# which shadows the `db` package. Reorder so the repo root wins.
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if HERE in sys.path:
    sys.path.remove(HERE)
sys.path.insert(0, REPO_ROOT)

from db.db import _apply_migrations, _current_schema_version, DB_PATH


def init():
    """Apply pending migrations and report final state."""
    _apply_migrations(verbose=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        version = _current_schema_version(conn)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()]
        views = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
        ).fetchall()]
    finally:
        conn.close()

    print(f"\n✓ Database ready: {DB_PATH}")
    print(f"  Schema version: {version}")
    print(f"  Tables: {', '.join(tables)}")
    print(f"  Views:  {', '.join(views)}")


if __name__ == "__main__":
    init()
