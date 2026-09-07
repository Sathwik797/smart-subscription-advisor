import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    # JWT settings are loaded from the environment so secrets are not hardcoded.
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    jwt_expires_raw = os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600")
    try:
        JWT_ACCESS_TOKEN_EXPIRES = int(jwt_expires_raw)
    except (TypeError, ValueError):
        JWT_ACCESS_TOKEN_EXPIRES = 3600

    # JWT Cookie settings for browser/server-rendered requests
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "False").lower() in ("true", "1", "t")
    JWT_COOKIE_HTTPONLY = True
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_CHECK_FORM = True
    JWT_ACCESS_CSRF_COOKIE_NAME = "csrf_access_token"
    JWT_ACCESS_CSRF_HEADER_NAME = "X-CSRF-TOKEN"
    JWT_ACCESS_CSRF_FIELD_NAME = "csrf_token"
    JWT_ACCESS_COOKIE_NAME = "access_token_cookie"

    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    TEMPLATES_AUTO_RELOAD = True

    # Database connection: support full DATABASE_URL or individual DB parameters
    DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if DATABASE_URL:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        DB_HOST = os.getenv("DB_HOST", "localhost")
        DB_PORT = os.getenv("DB_PORT", "3306")
        DB_NAME = os.getenv("DB_NAME", "smart_subscription_advisor")
        DB_USER = os.getenv("DB_USER", "root")
        db_password_raw = os.getenv("DB_PASSWORD", "")
        DB_PASSWORD = quote_plus(db_password_raw) if db_password_raw else ""

        # Cloud MySQL / TiDB Cloud requires SSL connection
        ssl_query = ""
        db_ssl = os.getenv("DB_SSL", "").lower() in ("true", "1", "t")
        if db_ssl or "tidbcloud.com" in DB_HOST:
            if os.path.exists("/etc/ssl/certs/ca-certificates.crt"):
                ssl_query = "?ssl_ca=/etc/ssl/certs/ca-certificates.crt"
            else:
                ssl_query = "?ssl_verify_cert=true"

        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
            f"@{DB_HOST}:{DB_PORT}/{DB_NAME}{ssl_query}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email SMTP configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1", "t")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@smartsubscriptionadvisor.com")