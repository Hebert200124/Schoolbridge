import os
import secrets

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///school_management.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@schoolbridge.zw')

    ENABLE_SETUP = os.environ.get('ENABLE_SETUP', '').lower() == 'true'
