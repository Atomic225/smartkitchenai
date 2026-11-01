from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import DATA_DIR, get_settings


class Base(DeclarativeBase):
    pass


def _engine_url() -> str:
    settings = get_settings()
    url = settings.database_url
    if url.startswith("sqlite:///./"):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
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
    """Safely apply column additions to existing SQLite tables without migrations."""
    target_engine = bind_engine or engine
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
