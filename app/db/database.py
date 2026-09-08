"""
database.py — SQLAlchemy engine + session factory.

Reads connection details from EITHER source, in this order:
  1. Streamlit Cloud secrets (st.secrets) — used automatically once deployed,
     since Streamlit Cloud never reads .env files.
  2. Local .env file (see .env.example) — used when running on your laptop.

This means the exact same file works locally and on Streamlit Cloud with
zero code changes when you deploy — only where the values come from differs.

Every other module gets a DB session by calling get_session().
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

try:
    import streamlit as st
except Exception:
    st = None

# IMPORTANT: we check whether a secrets.toml file physically exists BEFORE
# ever touching st.secrets. Merely accessing st.secrets (even inside a
# try/except) has a side effect: if no secrets.toml exists, Streamlit
# renders a "No secrets found" warning directly in the app AND consumes
# Streamlit's "first command" slot — which then breaks st.set_page_config()
# elsewhere. Checking the file ourselves avoids ever triggering that.
_SECRETS_PATHS = [
    os.path.join(os.path.expanduser("~"), ".streamlit", "secrets.toml"),
    os.path.join(os.getcwd(), ".streamlit", "secrets.toml"),
]
_SECRETS_FILE_EXISTS = any(os.path.exists(p) for p in _SECRETS_PATHS)

load_dotenv()  # reads .env in the project root (no-op if the file doesn't exist)


def _get_config(key: str, default: str = "") -> str:
    """Check st.secrets first (Streamlit Cloud), then fall back to os.environ (local .env)."""
    if st is not None and _SECRETS_FILE_EXISTS:
        try:
            if key in st.secrets:
                return str(st.secrets[key])
        except Exception:
            pass
    return os.getenv(key, default)


DB_HOST = _get_config("DB_HOST", "localhost")
DB_PORT = _get_config("DB_PORT", "3306")
DB_NAME = _get_config("DB_NAME", "ikraceya_db")
DB_USER = _get_config("DB_USER", "root")
DB_PASSWORD = _get_config("DB_PASSWORD", "")

DATABASE_URL = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Aiven (and most hosted MySQL free tiers) require SSL. If you download the
# service's CA certificate from the Aiven console, set DB_SSL_CA to its path
# (locally) or paste its contents into a Streamlit secret and write it to a
# temp file before this import. If DB_SSL_CA isn't set, we still enable SSL
# without cert verification — enough to connect, though not fully hardened.
_ssl_ca = _get_config("DB_SSL_CA", "")
_connect_args = {"ssl_ca": _ssl_ca} if _ssl_ca else {"ssl_disabled": False}

# pool_pre_ping avoids "MySQL server has gone away" errors on idle connections,
# which show up a lot during live demos where the app sits open for a while.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_session():
    """Return a new SQLAlchemy session. Caller is responsible for closing it."""
    return SessionLocal()


def get_engine():
    """Return the shared engine (used by scripts/init_db.py to create tables)."""
    return engine