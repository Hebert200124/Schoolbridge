"""Insert a super_admin account into the production database without touching existing data.

Usage:

    $env:DATABASE_URL="postgresql://USER:PASS@HOST:PORT/dbname"; $env:SA_USERNAME="superadmin"; $env:SA_PASSWORD="..." ; python create_superadmin.py

The username/password default to superadmin / superadmin123 if not set.
Also ensures a 'MAIN' campus exists (and backfills users/students to it if the
campus_id column is present but rows are NULL).
"""

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

MAIN = 'postgresql://'


def main():
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        print('[error] Set DATABASE_URL to the Render Postgres external URL first.')
        sys.exit(1)
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)

    username = os.environ.get('SA_USERNAME', 'superadmin')
    password = os.environ.get('SA_PASSWORD', 'superadmin123')
    email = os.environ.get('SA_EMAIL', 'superadmin@schoolbridge.zw')
    full_name = os.environ.get('SA_NAME', 'System Administrator')
    reg_number = f'REG-{username.upper()}'

    engine = create_engine(url, connect_args={'sslmode': 'require'})
    with Session(engine) as session:
        with session.begin():
            inspector_tables = set(session.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            ).scalars().all())

            if 'users' not in inspector_tables:
                print('[error] users table not found. Is this the right database?')
                sys.exit(1)

            # Ensure MAIN campus exists
            main_id = session.execute(
                text("SELECT id FROM campuses WHERE code = 'MAIN' LIMIT 1")
            ).scalar_one_or_none()
            if main_id is None:
                main_id = session.execute(
                    text("INSERT INTO campuses (name, code, address, created_at) "
                         "VALUES ('Main Campus', 'MAIN', '', now()) RETURNING id")
                ).scalar()
                print(f'[create] MAIN campus id={main_id}')

            # Backfill any NULL campus_id rows across scoped tables
            scoped_tables = ['users', 'students', 'subjects', 'monthly_tests', 'exam_marks',
                             'principal_comments', 'fee_accounts', 'payments', 'fee_settings',
                             'teacher_remarks', 'timetables', 'exam_timetables', 'activity_logs',
                             'activities', 'staff_leaves']
            for table in scoped_tables:
                if table not in inspector_tables:
                    continue
                cols = set(session.execute(
                    text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'")
                ).scalars().all())
                if 'campus_id' in cols:
                    session.execute(text(f'UPDATE {table} SET campus_id = :cid WHERE campus_id IS NULL'),
                                    {'cid': main_id})

            # Insert super admin if it does not already exist
            existing = session.execute(
                text("SELECT id FROM users WHERE username = :u LIMIT 1"), {'u': username}
            ).scalar_one_or_none()
            if existing:
                print(f'[skip] user "{username}" already exists (id={existing}). Nothing to do.')
                sys.exit(0)

            session.execute(
                text("INSERT INTO users (campus_id, username, email, password_hash, role, full_name, "
                     "reg_number, phone, is_active) "
                     "VALUES (:campus_id, :username, :email, :pwhash, 'super_admin', :full_name, "
                     ":reg_number, '', TRUE)"),
                {'campus_id': main_id, 'username': username, 'email': email,
                 'pwhash': generate_password_hash(password), 'full_name': full_name,
                 'reg_number': reg_number}
            )
            print(f'[create] super_admin "{username}" / "{password}" for campus #{main_id}')

    print('Done.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'[error] {exc}', file=sys.stderr)
        sys.exit(1)
