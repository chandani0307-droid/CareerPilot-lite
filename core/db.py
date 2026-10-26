"""Database access. Every visitor gets a private SQLite file, so one person's resume never reaches another visitor.

Files live in data/ and are deleted after VISITOR_TTL_HOURS. Set PER_VISITOR_DATA=false for one shared database.
"""
from __future__ import annotations

import time
import uuid
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from .config import ROOT_DIR, settings


class Base(DeclarativeBase):
    pass


DATA_DIR = ROOT_DIR / "data"
PER_VISITOR = settings.per_visitor_data and settings.database_url.startswith("sqlite")
_engines: dict = {}


def visitor_id() -> str:
    """A random id for this browser session. Scripts and tests (no Streamlit) get 'local'."""
    if not PER_VISITOR:
        return "local"
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is None:
            return "local"
        return st.session_state.setdefault("visitor_id", uuid.uuid4().hex[:16])
    except Exception:  # noqa: BLE001
        return "local"


def current_engine():
    """The engine for the visitor using the app right now. Tables are created on first use."""
    from models import tables  # noqa: F401  (registers the tables)

    vid = visitor_id()
    if vid not in _engines:
        if vid == "local":
            url = settings.database_url
        else:
            DATA_DIR.mkdir(exist_ok=True)
            url = f"sqlite:///{DATA_DIR / f'visitor_{vid}.db'}"
        engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
        Base.metadata.create_all(engine)
        _engines[vid] = engine
    return _engines[vid]


def purge_old_visitors() -> None:
    """Delete private database files that have not changed for VISITOR_TTL_HOURS."""
    if not PER_VISITOR or not DATA_DIR.exists():
        return
    cutoff = time.time() - settings.visitor_ttl_hours * 3600
    for file in DATA_DIR.glob("visitor_*.db"):
        if file.stat().st_mtime < cutoff:
            old = _engines.pop(file.stem.replace("visitor_", ""), None)
            if old is not None:
                old.dispose()
            file.unlink(missing_ok=True)


def init_db() -> None:
    purge_old_visitors()
    current_engine()


@contextmanager
def session():
    """`with session() as db:` gives a database session for the current visitor and always closes it."""
    db = Session(current_engine(), autoflush=False, expire_on_commit=False)
    try:
        yield db
    finally:
        db.close()
