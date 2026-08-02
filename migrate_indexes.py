"""Apply model indexes to an EXISTING database without downtime.

Run once against your production PostgreSQL database:

    DATABASE_URL=postgresql://... python migrate_indexes.py

How it works
------------
* Derives every index declared in models.py (via SQLAlchemy metadata), so it
  stays in sync when models change.
* On PostgreSQL it issues `CREATE INDEX CONCURRENTLY IF NOT EXISTS ...` using
  an AUTOCOMMIT connection. CONCURRENTLY builds the index without taking a
  table lock, so reads and writes continue uninterrupted (no downtime).
* It skips any index whose columns are already covered by an existing index,
  which avoids creating redundant duplicate indexes (e.g. when a UNIQUE
  constraint already created one).
* On SQLite (dev/local) it falls back to plain `CREATE INDEX IF NOT EXISTS`
  (CONCURRENTLY is not supported there).

Note: `db.create_all()` on a fresh database already creates all of these
indexes, so this script is only needed for databases that were created
before the indexes were added to models.py.
"""

import sys

from app import app, db
from sqlalchemy import text


def _existing_indexes(inspector, table_name):
    result = {}
    for idx in inspector.get_indexes(table_name):
        cols = tuple(sorted(c['name'] for c in idx['column_names']))
        result.setdefault(cols, idx['name'])
    return result


def main():
    with app.app_context():
        engine = db.engine
        inspector = db.inspect(engine)
        tables = set(inspector.get_table_names())
        is_postgres = engine.dialect.name == 'postgresql'

        created = 0
        skipped = 0

        with engine.connect() as conn:
            if is_postgres:
                conn = conn.execution_options(isolation_level="AUTOCOMMIT")

            for table in db.metadata.sorted_tables:
                if table.name not in tables:
                    continue
                existing = _existing_indexes(inspector, table.name)
                for index in table.indexes:
                    cols = tuple(sorted(c.name for c in index.columns))
                    if cols in existing:
                        skipped += 1
                        continue
                    col_list = ', '.join(c.name for c in index.columns)
                    if is_postgres:
                        sql = f'CREATE INDEX CONCURRENTLY IF NOT EXISTS {index.name} ON {table.name} ({col_list})'
                    else:
                        sql = f'CREATE INDEX IF NOT EXISTS {index.name} ON {table.name} ({col_list})'
                    print(f'[create] {index.name} ON {table.name} ({col_list})')
                    conn.execute(text(sql))
                    created += 1

        print(f'Done. Created {created} index(es), skipped {skipped} already covered.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'[error] {exc}', file=sys.stderr)
        sys.exit(1)
