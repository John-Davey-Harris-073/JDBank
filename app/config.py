import os
import sys


def _resource_dir() -> str:
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _data_dir() -> str:
    env = os.environ.get("JDBANK_DATA_DIR")
    if env:
        os.makedirs(env, exist_ok=True)
        return env
    if os.environ.get("JDBANK_DESKTOP") == "1":
        if sys.platform == "win32":
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
            path = os.path.join(base, "JDBank")
        elif sys.platform == "darwin":
            path = os.path.join(
                os.path.expanduser("~"), "Library", "Application Support", "JDBank"
            )
        else:
            path = os.path.join(os.path.expanduser("~"), ".jdbank")
        os.makedirs(path, exist_ok=True)
        return path
    return _resource_dir()


DATA_DIR = _data_dir()


class Config:
    DATA_DIR = DATA_DIR
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]
        if DATABASE_URL.startswith("postgresql://"):
            SQLALCHEMY_DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://"):]
        else:
            SQLALCHEMY_DATABASE_URL = DATABASE_URL
    else:
        SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'jdbank.db')}"

    IS_POSTGRES = SQLALCHEMY_DATABASE_URL.startswith("postgresql")

    SECRET_KEY = os.environ.get("SECRET_KEY", "jdbank-dev-secret-key-change-in-production")
    SESSION_COOKIE_NAME = "jdbank_session"
    SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 7
    SESSION_HTTPS_ONLY = os.environ.get("SESSION_HTTPS_ONLY", "false").lower() in ("1", "true", "yes")


config = Config()