"""Application configuration management.

This module loads environment variables and exposes a strongly-typed
configuration object for the whole application.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Container for application settings.

    Attributes:
        database_url: SQLAlchemy database URL.
        start_date: Earliest date for ETL and simulation data.
        base_currency: Base reporting currency.
        risk_free_rate: Annualized risk-free rate for Sharpe ratio.
        debug: Flag indicating Flask debug mode.
        secret_key: Secret key for Flask sessions and CSRF-related features.
    """

    database_url: str
    start_date: date
    base_currency: str
    risk_free_rate: float
    debug: bool
    secret_key: str


def _parse_bool(value: str) -> bool:
    """Convert string-like booleans into Python bool.

    Args:
        value: Source environment variable value.

    Returns:
        Parsed boolean value.
    """

    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> Config:
    """Load application configuration from environment variables.

    Returns:
        Fully initialized Config instance.
    """

    return Config(
        database_url=os.getenv("DATABASE_URL", "sqlite:///investment.db"),
        start_date=date.fromisoformat(os.getenv("START_DATE", "2000-01-01")),
        base_currency=os.getenv("BASE_CURRENCY", "RUB").upper(),
        risk_free_rate=float(os.getenv("RISK_FREE_RATE", "0.02")),
        debug=_parse_bool(os.getenv("DEBUG", "false")),
        secret_key=os.getenv("SECRET_KEY", "change-me"),
    )


settings = load_config()
