"""Apply multi-campus constraints to an EXISTING database without downtime.

Run once against your production PostgreSQL database (after the app has booted
at least once so `_ensure_campus_columns()` has backfilled all rows to the
'MAIN' campus):

    DATABASE_URL=postgresql://... python migrate_campuses.py

What it does
------------
1. Ensures a 'MAIN' campus exists.
2. Adds a `campus_id` column to every campus-scoped table if missing.
3. Backfills any NULL `campus_id` rows to the MAIN campus.
4. Adds a FOREIGN KEY from each table's `campus_id` to `campuses.id`
   (NOT VALID, then validated — this avoids taking a full table lock).
5. Adds an index on `campus_id` where not already covered.
6. Drops the old global UNIQUE constraints that per-campus unique
   constraints replace:
     * subjects:      uq_subjects (on code)            -> uq_subjects_campus_code
     * fee_settings:  uq_fee_settings (on form)        -> uq_fee_settings_campus_form
7. Creates the per-campus UNIQUE constraints (CONCURRENTLY is not possible
   for UNIQUE, so it uses NOT VALID which avoids the long table lock; the
   constraint is still enforced for new writes and validated at the end).

On SQLite (local dev) it skips the FK/constraint work and only ensures the
columns + MAIN backfill, which the app's `_ensure_campus_columns()` already
handles at boot.
"""

import sys

from app import app, db
from sqlalchemy import text

CAMPUS_SCOPED_TABLES = [
    'users', 'students', 'subjects', 'monthly_tests', 'exam_marks',
    'principal_comments', 'fee_accounts', 'payments', 'fee_settings',
    'teacher_remarks', 'timetables', 'exam_timetables', 'activity_logs',
    'activities', 'staff_leaves',
]

OLD_UNIQUE_CONSTRAINTS = [
    ('subjects', 'uq_subjects', 'code'),
    ('fee_settings', 'uq_fee_settings', 'form'),
]

NEW_UNIQUE_CONSTRAINTS = [
    ('subjects', 'uq_subjects_campus_code', 'campus_id, code'),
    ('fee_settings', 'uq_fee_settings_campus_form', 'campus_id, form'),
]


def main():
    with app.app_context():
        engine = db.engine
        inspector = db.inspect(engine)
        tables = set(inspector.get_table_names())
        is_postgres = engine.dialect.name == 'postgresql'

        if 'campuses' not in tables:
            print('[error] campuses table missing; boot the app once first so db.create_all() runs.')
            sys.exit(1)

        with engine.begin() as conn:
            main_id = None
            row = conn.execute(text("SELECT id FROM campuses WHERE code = 'MAIN' LIMIT 1")).fetchone()
            if row:
                main_id = row[0]
            else:
                result = conn.execute(
                    text("INSERT INTO campuses (name, code, address, created_at) "
                         "VALUES ('Main Campus', 'MAIN', '', now()) RETURNING id"))
                main_id = result.scalar()
                print(f'[create] MAIN campus id={main_id}')
            if not main_id:
                print('[error] could not determine MAIN campus id.')
                sys.exit(1)

            for table in CAMPUS_SCOPED_TABLES:
                if table not in tables:
                    print(f'[skip] {table} not present')
                    continue
                cols = {c['name'] for c in inspector.get_columns(table)}
                if 'campus_id' not in cols:
                    print(f'[alter] {table}: ADD COLUMN campus_id INTEGER')
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN campus_id INTEGER'))
                    cols.add('campus_id')
                print(f'[update] {table}: backfill NULL campus_id -> MAIN')
                conn.execute(text(f'UPDATE {table} SET campus_id = :cid WHERE campus_id IS NULL'),
                             {'cid': main_id})
                if is_postgres:
                    fk_name = f'fk_{table}_campus'
                    fk_exists = any(
                        fk.get('name') == fk_name
                        for fk in inspector.get_foreign_keys(table)
                    )
                    if not fk_exists:
                        print(f'[fk] {table}: ADD CONSTRAINT {fk_name} NOT VALID')
                        conn.execute(text(
                            f'ALTER TABLE {table} ADD CONSTRAINT {fk_name} '
                            f'FOREIGN KEY (campus_id) REFERENCES campuses(id) NOT VALID'))
                    idx_name = f'ix_{table}_campus_id'
                    covered = False
                    for idx in inspector.get_indexes(table):
                        names = [c['name'] for c in idx['column_names']]
                        if 'campus_id' in names:
                            covered = True
                            break
                    if not covered:
                        print(f'[index] {table}: CREATE INDEX {idx_name}')
                        conn.execute(text(
                            f'CREATE INDEX CONCURRENTLY IF NOT EXISTS {idx_name} '
                            f'ON {table} (campus_id)').execution_options(isolation_level='AUTOCOMMIT'))

            if is_postgres:
                for table, old_name, _cols in OLD_UNIQUE_CONSTRAINTS:
                    existing = [c['name'] for c in inspector.get_unique_constraints(table)]
                    if old_name in existing:
                        print(f'[drop] {table}: DROP CONSTRAINT {old_name}')
                        conn.execute(text(f'ALTER TABLE {table} DROP CONSTRAINT {old_name}'))
                for table, new_name, cols in NEW_UNIQUE_CONSTRAINTS:
                    existing = [c['name'] for c in inspector.get_unique_constraints(table)]
                    if new_name not in existing:
                        print(f'[unique] {table}: ADD CONSTRAINT {new_name} ({cols}) NOT VALID')
                        conn.execute(text(
                            f'ALTER TABLE {table} ADD CONSTRAINT {new_name} '
                            f'UNIQUE ({cols}) NOT VALID'))

        if is_postgres:
            with engine.begin() as conn:
                for table, new_name, _cols in NEW_UNIQUE_CONSTRAINTS:
                    existing = [c['name'] for c in db.inspect(engine).get_unique_constraints(table)]
                    if new_name in existing:
                        print(f'[validate] {table}: VALIDATE CONSTRAINT {new_name}')
                        conn.execute(text(f'ALTER TABLE {table} VALIDATE CONSTRAINT {new_name}'))
                for table in CAMPUS_SCOPED_TABLES:
                    if table in db.inspect(engine).get_table_names():
                        fk_name = f'fk_{table}_campus'
                        existing = [fk.get('name') for fk in db.inspect(engine).get_foreign_keys(table)]
                        if fk_name in existing:
                            print(f'[validate] {table}: VALIDATE CONSTRAINT {fk_name}')
                            conn.execute(text(f'ALTER TABLE {table} VALIDATE CONSTRAINT {fk_name}'))

        print('Done. Multi-campus migration complete.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'[error] {exc}', file=sys.stderr)
        sys.exit(1)
