# Investment Strategist

Investment Strategist is a Flask-based web application for historical investment strategy simulation. It includes:

- Multi-source ETL (MOEX + Yahoo Finance)
- Currency normalization to RUB
- Strategy simulation over historical periods
- Scenario analysis (5th/50th/95th percentiles)
- REST API + single-page frontend
- SQLite development setup with PostgreSQL-ready SQLAlchemy configuration

---

## Features

1. **ETL Pipeline**
   - Downloads historical data from:
     - MOEX (IMOEX, RGBITR)
     - Yahoo Finance (GC=F and RUB=X)
   - Standardizes source data to `date` / `price`
   - Builds dense daily calendar and forward-fills missing values
   - Converts USD-denominated series to RUB using USD/RUB rates
   - Loads data idempotently into SQLAlchemy models

2. **Simulation Engine**
   - Portfolio return aggregation with strict weight validation (`1.0 ± 0.001`)
   - Rolling return calculations for user-selected horizon
   - Scenario percentiles: worst (5%), median (50%), best (95%)
   - Risk metrics: mean, std dev, min, max, Sharpe ratio

3. **Flask API**
   - `GET /api/health`
   - `GET /api/assets`
   - `GET /api/strategies`
   - `POST /api/simulate`

4. **Frontend**
   - Investment amount input
   - Period slider (1–30 years)
   - Multi-strategy selector
   - Growth comparison chart (Chart.js)
   - Scenario comparison results table

---

## Project Structure

The repository follows the requested modular structure:

- `etl/` for ingestion and normalization
- `data/` for database models and persistence helpers
- `simulation/` for calculations
- `services/` for orchestration
- `api/` + `app.py` for HTTP layer
- `templates/` + `static/` for frontend
- `tests/` for pytest coverage

---

## Configuration

Copy `.env.example` to `.env` and adjust values if needed:

- `DATABASE_URL` (default: `sqlite:///investment.db`)
- `START_DATE` (default: `2000-01-01`)
- `BASE_CURRENCY` (default: `RUB`)
- `RISK_FREE_RATE` (default: `0.02`)
- `DEBUG`
- `SECRET_KEY`

---

## Installation

Using `uv` with the project-standard virtual environment name (`investment_strategist`):

```powershell
uv venv investment_strategist
.\investment_strategist\Scripts\Activate.ps1
uv sync --active
```

Or install from requirements in the active virtual environment:

```powershell
python -m pip install -r requirements.txt
```

---

## Running the App (Windows/PowerShell)

### 1) Seed data (runs ETL + strategy seeding)

```powershell
.\investment_strategist\Scripts\Activate.ps1
uv run --active python -m data.data_loader
```

### 2) Start server

```powershell
.\investment_strategist\Scripts\Activate.ps1
uv run --active python -m app
```

Open: `http://localhost:5000`

> Why module commands instead of `uv run seed`?
>
> `uv run <command>` executes an installed console command from the current environment.
> In mixed or not-yet-installed environments this can fail with `program not found`.
> Running modules directly is deterministic and works consistently for this project layout.

---

## ETL Currency Normalization Methodology

For USD-denominated assets (e.g., Gold from Yahoo):

1. Create standardized daily USD price series (`date`, `price`)
2. Create standardized daily USD/RUB FX series (`date`, `price`)
3. Merge by date
4. Forward-fill missing FX values
5. Compute RUB price using:

```text
price_rub = price_usd * usd_rub_rate
```

This process is deterministic and idempotent.

---

## API Usage

### Health

```http
GET /api/health
```

### List strategies

```http
GET /api/strategies
```

### Simulate

```http
POST /api/simulate
Content-Type: application/json

{
  "amount": 100000,
  "period_years": 10,
  "strategy_ids": [1, 4, 5]
}
```

---

## Testing and Quality Checks

```powershell
.\investment_strategist\Scripts\Activate.ps1
uv run --active python -m black .
uv run --active python -m isort .
uv run --active python -m mypy .
uv run --active python -m pytest
```

---

## Default Strategies Seeded

- Stocks Only: 100% IMOEX
- Bonds Only: 100% RGBITR
- Gold: 100% GOLD_RUB
- Balanced: 60% IMOEX, 30% RGBITR, 10% GOLD_RUB
- Conservative: 30% IMOEX, 60% RGBITR, 10% GOLD_RUB

---

## Security & Reliability Notes

- All inputs to simulation API are validated.
- Strategy allocation sums are validated against tolerance.
- ETL and seed workflows are designed to be idempotent.
- Database transactions use commit/rollback guards.
- Sensitive settings are environment-driven and not hardcoded.

---

## Troubleshooting (Windows)

### Error: `uv run seed` -> `program not found`

Use module invocation from the active `investment_strategist` environment:

```powershell
.\investment_strategist\Scripts\Activate.ps1
uv run --active python -m data.data_loader
```

### Error: pandas import failure (`ArrowDtype` from partially initialized module)

This usually means a broken or mixed Python environment.

1. Ensure you are in the project root.
2. Remove conflicting environments and recreate only `investment_strategist`:

```powershell
if (Test-Path .venv) { Remove-Item -Recurse -Force .venv }
if (Test-Path venv) { Remove-Item -Recurse -Force venv }
if (Test-Path investment_strategist) { Remove-Item -Recurse -Force investment_strategist }
uv venv investment_strategist
.\investment_strategist\Scripts\Activate.ps1
uv sync --active
```

3. Verify pandas import through the active environment:

```powershell
uv run --active python -c "import pandas as pd; import sys; print(pd.__version__); print(sys.executable)"
```

4. Run seed and server again:

```powershell
uv run --active python -m data.data_loader
uv run --active python -m app
```

5. Optional sanity check helper:

```powershell
uv run --active python -m scripts.check_env
```
