from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import DATA_DIR, ROOT_DIR, get_settings


class Base(DeclarativeBase):
    pass


def _engine_url() -> str:
    settings = get_settings()
    url = settings.database_url
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if url.startswith("sqlite:///./"):
        # Resolve relative sqlite path to absolute path anchored at ROOT_DIR
        relative_path = url.replace("sqlite:///./", "")
        abs_db_path = (ROOT_DIR / relative_path).resolve()
        abs_db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{abs_db_path.as_posix()}"
    return url


_url = _engine_url()
_kwargs: dict = {"echo": False}
if _url.startswith("sqlite"):
    _kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in _url:
        _kwargs["poolclass"] = StaticPool
engine = create_engine(_url, **_kwargs)

if _url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def ensure_schema(bind_engine=None) -> None:
    """Safely apply column additions and new tables to existing SQLite tables without migrations."""
    target_engine = bind_engine or engine
    Base.metadata.create_all(bind=target_engine)
    try:
        with target_engine.connect() as conn:
            tables = [r[0] for r in conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
            if "households" in tables:
                cols = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(households);").fetchall()}
                if "chef_call_weekday_time" not in cols:
                    conn.exec_driver_sql("ALTER TABLE households ADD COLUMN chef_call_weekday_time VARCHAR(8) DEFAULT '08:30'")
                if "chef_call_weekend_lunch_time" not in cols:
                    conn.exec_driver_sql("ALTER TABLE households ADD COLUMN chef_call_weekend_lunch_time VARCHAR(8) DEFAULT '09:30'")
                if "chef_call_weekend_dinner_time" not in cols:
                    conn.exec_driver_sql("ALTER TABLE households ADD COLUMN chef_call_weekend_dinner_time VARCHAR(8) DEFAULT '17:00'")
            if "chef_calls" in tables:
                cols = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(chef_calls);").fetchall()}
                if "call_type" not in cols:
                    conn.exec_driver_sql("ALTER TABLE chef_calls ADD COLUMN call_type VARCHAR(40) DEFAULT 'daily'")
            conn.commit()
    except Exception:
        pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
