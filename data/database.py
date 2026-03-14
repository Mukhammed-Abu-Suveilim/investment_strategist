"""Database bootstrap utilities.

This module initializes SQLAlchemy engine/session objects and exposes
helpers for table creation and transactional session management.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base declarative class for ORM models."""


engine: Engine | None = None
SessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


def init_database(database_url: str | None = None) -> None:
    """Initialize or reinitialize SQLAlchemy engine/session factory.

    Args:
        database_url: Optional SQLAlchemy URL override.
    """

    global engine

    resolved_url = database_url or settings.database_url
    engine = create_engine(
        resolved_url,
        echo=False,
        future=True,
    )
    SessionLocal.configure(bind=engine)
    logger.info("Database engine initialized for URL: %s", resolved_url)


# Initialize default engine at import time.
init_database()


def create_all_tables() -> None:
    """Create all ORM tables in the configured database."""

    if engine is None:
        raise RuntimeError("Database engine is not initialized.")

    logger.info("Creating all database tables if they do not already exist.")
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional session scope.

    Yields:
        Active SQLAlchemy session.
    """

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Database transaction failed. Rolled back session.")
        raise
    finally:
        session.close()
