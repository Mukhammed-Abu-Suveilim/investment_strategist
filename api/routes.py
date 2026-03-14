"""Flask API routes for investment simulation operations."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from flask import Blueprint, Response, jsonify, request

from config import settings
from services.simulation_service import SimulationService

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")
service = SimulationService()


def _parse_simulation_payload(payload: dict[str, Any]) -> tuple[float, int, list[int]]:
    """Validate and parse simulation request payload.

    Args:
        payload: JSON request body.

    Returns:
        Tuple of (amount, period_years, strategy_ids).

    Raises:
        ValueError: If payload validation fails.
    """

    amount = float(payload.get("amount", 0))
    period_years = int(payload.get("period_years", 0))
    strategy_ids_raw = payload.get("strategy_ids", [])

    if amount <= 0:
        raise ValueError("amount must be greater than zero.")
    if period_years < 1 or period_years > 30:
        raise ValueError("period_years must be between 1 and 30.")
    if not isinstance(strategy_ids_raw, list) or not strategy_ids_raw:
        raise ValueError("strategy_ids must be a non-empty list.")

    strategy_ids = [int(item) for item in strategy_ids_raw]
    return amount, period_years, strategy_ids


@api_bp.get("/health")
def health() -> tuple[Response, int]:
    """Health-check endpoint."""

    return jsonify({"status": "ok"}), 200


@api_bp.get("/assets")
def get_assets() -> tuple[Response, int]:
    """List available assets."""

    try:
        assets = service.list_assets()
        return jsonify({"assets": assets}), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load assets.")
        return jsonify({"error": str(exc)}), 500


@api_bp.get("/strategies")
def get_strategies() -> tuple[Response, int]:
    """List available strategies with allocations."""

    try:
        strategies = service.list_strategies()
        return jsonify({"strategies": strategies}), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load strategies.")
        return jsonify({"error": str(exc)}), 500


@api_bp.post("/simulate")
def simulate() -> tuple[Response, int]:
    """Run strategy simulations for selected strategy IDs."""

    try:
        payload = request.get_json(silent=True) or {}
        amount, period_years, strategy_ids = _parse_simulation_payload(payload)
        start_date = settings.start_date
        end_date = date.today()

        results = service.simulate(
            amount=amount,
            period_years=period_years,
            strategy_ids=strategy_ids,
            start_date=start_date,
            end_date=end_date,
        )
        return jsonify({"results": results}), 200
    except ValueError as exc:
        logger.warning("Simulation request validation failed: %s", exc)
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        logger.exception("Simulation request failed.")
        return jsonify({"error": str(exc)}), 500
