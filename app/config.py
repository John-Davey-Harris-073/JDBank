import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]
        if DATABASE_URL.startswith("postgresql://"):
            SQLALCHEMY_DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://"):]
        else:
            SQLALCHEMY_DATABASE_URL = DATABASE_URL
    else:
        SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'jdbank.db')}"

    IS_POSTGRES = SQLALCHEMY_DATABASE_URL.startswith("postgresql")

    SECRET_KEY = os.environ.get("SECRET_KEY", "jdbank-dev-secret-key-change-in-production")
    SESSION_COOKIE_NAME = "jdbank_session"
    SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 7
    SESSION_HTTPS_ONLY = os.environ.get("SESSION_HTTPS_ONLY", "false").lower() in ("1", "true", "yes")


config = Config()