import os
import secrets
from dotenv import load_dotenv

load_dotenv()


def _default_secret_key():
    """Return a stable secret for signing sessions.

    Prefers SECRET_KEY from the environment. Otherwise a key is generated once
    and persisted to instance/secret_key so all gunicorn workers sign sessions
    with the same key and sessions survive process restarts.
    """
    key = os.environ.get('SECRET_KEY')
    if key:
        return key
    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'secret_key')
    try:
        if os.path.exists(key_file):
            with open(key_file, 'r') as fh:
                stored = fh.read().strip()
            if stored:
                return stored
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        generated = secrets.token_hex(32)
        with open(key_file, 'w') as fh:
            fh.write(generated)
        return generated
    except Exception:
        return secrets.token_hex(32)


class Config:
    SECRET_KEY = _default_secret_key()
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///school_management.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@schoolbridge.zw')

    ENABLE_SETUP = os.environ.get('ENABLE_SETUP', '').lower() == 'true'
