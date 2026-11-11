import os
from collections.abc import Generator

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./smartexam.db")


def make_engine(database_url: str) -> Engine:
    options = (
        {"check_same_thread": False, "timeout": 30} if database_url.startswith("sqlite") else {}
    )
    engine = create_engine(
        database_url,
        connect_args=options,
        pool_pre_ping=True,
        hide_parameters=True,
    )
    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_db(request: Request) -> Generator[Session, None, None]:
    with request.app.state.session_factory() as session:
        yield session
