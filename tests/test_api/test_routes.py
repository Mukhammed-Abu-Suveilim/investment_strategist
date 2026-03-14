"""API endpoint tests."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app import create_app
from data.database import get_session
from data.models import Asset, HistoricalPrice, Strategy, StrategyAllocation


@pytest.fixture()
def client(tmp_path: pytest.TempPathFactory):
    """Create Flask test client with isolated SQLite database."""

    db_path = tmp_path / "test_api.db"
    app = create_app(database_url=f"sqlite:///{db_path}")

    with get_session() as session:
        asset = Asset(
            symbol="IMOEX",
            name="Moscow Exchange Index",
            category="Equity",
            source="MOEX",
            currency="RUB",
        )
        session.add(asset)
        session.flush()

        strategy = Strategy(name="Stocks Only", description="100% IMOEX")
        session.add(strategy)
        session.flush()

        session.add(
            StrategyAllocation(
                strategy_id=strategy.id,
                asset_id=asset.id,
                weight=1.0,
            )
        )

        start = date(2020, 1, 1)
        for offset in range(0, 900):
            session.add(
                HistoricalPrice(
                    asset_id=asset.id,
                    date=start + timedelta(days=offset),
                    price=100.0 + float(offset),
                )
            )

    app.testing = True
    return app.test_client()


def test_health_endpoint(client) -> None:
    """Health endpoint returns 200 and status ok."""

    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_assets_endpoint_returns_assets(client) -> None:
    """Assets endpoint returns seeded asset list."""

    response = client.get("/api/assets")
    payload = response.get_json()

    assert response.status_code == 200
    assert "assets" in payload
    assert len(payload["assets"]) == 1
    assert payload["assets"][0]["symbol"] == "IMOEX"


def test_strategies_endpoint_returns_allocations(client) -> None:
    """Strategies endpoint returns allocations with weights."""

    response = client.get("/api/strategies")
    payload = response.get_json()

    assert response.status_code == 200
    assert "strategies" in payload
    assert len(payload["strategies"]) == 1
    strategy = payload["strategies"][0]
    assert strategy["name"] == "Stocks Only"
    assert strategy["allocations"][0]["weight"] == 1.0


def test_simulate_endpoint_validates_payload(client) -> None:
    """Simulation endpoint validates request body and rejects invalid payload."""

    response = client.post(
        "/api/simulate", json={"amount": 0, "period_years": 2, "strategy_ids": [1]}
    )
    assert response.status_code == 400


def test_simulate_endpoint_returns_results(client) -> None:
    """Simulation endpoint returns selected-period and one-year expectation fields."""

    amount = 100000
    response = client.post(
        "/api/simulate",
        json={"amount": amount, "period_years": 2, "strategy_ids": [1]},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert "results" in payload
    assert len(payload["results"]) == 1

    result = payload["results"][0]
    assert result["strategy_name"] == "Stocks Only"

    assert result["selected_period_years"] == 2

    assert "selected_period_scenarios" in result
    assert set(result["selected_period_scenarios"].keys()) == {
        "worst",
        "median",
        "best",
    }
    assert "one_year_scenarios" in result
    assert set(result["one_year_scenarios"].keys()) == {"worst", "median", "best"}

    assert "expected_selected_period_return" in result
    assert "expected_selected_period_final_value" in result
    assert result["expected_selected_period_final_value"] == pytest.approx(
        amount * (1.0 + result["expected_selected_period_return"])
    )

    assert "expected_1y_return" in result
    assert "expected_1y_final_value" in result
    assert result["expected_1y_final_value"] == pytest.approx(
        amount * (1.0 + result["expected_1y_return"])
    )

    # Backward-compatible alias maps to the selected horizon expected value.
    assert result["final_value"] == pytest.approx(
        result["expected_selected_period_final_value"]
    )
    assert result["scenarios"] == result["selected_period_scenarios"]
    assert result["historical_full_period_final_value"] > 0

    # With positive trend data and period_years=2, selected-horizon expectation is
    # distinct from 1-year expectation.
    assert result["expected_selected_period_final_value"] != pytest.approx(
        result["expected_1y_final_value"]
    )
