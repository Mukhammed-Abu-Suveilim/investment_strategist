"""Flask application entrypoint."""

from __future__ import annotations

import logging

from flask import Flask, render_template
from flask_cors import CORS

from api import api_bp
from config import settings
from data.database import create_all_tables, init_database

logger = logging.getLogger(__name__)


def create_app(database_url: str | None = None) -> Flask:
    """Create and configure Flask application instance.

    Args:
        database_url: Optional SQLAlchemy URL override used in tests.

    Returns:
        Configured Flask application.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.secret_key
    app.config["DEBUG"] = settings.debug

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    init_database(database_url=database_url)
    create_all_tables()

    app.register_blueprint(api_bp)

    @app.get("/")
    def index() -> str:
        """Render the SPA index page."""

        return render_template("index.html")

    logger.info("Flask application initialized successfully.")
    return app


def main() -> None:
    """Run Flask development server for ``uv run server``."""

    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=settings.debug)


if __name__ == "__main__":
    main()
